from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from .models import CartItem, ProposedTransaction, UserIntent

_MISSING = object()


def _extract_json_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return cleaned[start : end + 1]
    return cleaned


class AIBuyer:
    """Select one product from an authoritative catalog using OpenRouter."""

    @staticmethod
    def _safe_api_error(exc: Exception) -> str:
        message = str(exc).lower()

        if any(
            token in message
            for token in (
                "429",
                "quota",
                "rate limit",
                "resourceexhausted",
                "exhausted",
            )
        ):
            return "Gemini API quota temporarily unavailable. Please try again later."

        return "Gemini API request failed. Please try again later."


    def __init__(self, api_key: object = _MISSING, model=None):
        # Preserve injected model support for existing tests.
        if model is not None:
            self.model = model
            self.client = None
            return

        if api_key is _MISSING:
            key = os.getenv("OPENROUTER_API_KEY")
            if not key:
                raise ValueError(
                    "OpenRouter API key not provided and "
                    "OPENROUTER_API_KEY environment variable not set."
                )
        elif api_key is None:
            raise ValueError(
                "OpenRouter API key not provided and "
                "OPENROUTER_API_KEY environment variable not set."
            )
        else:
            key = str(api_key)

        from openai import OpenAI

        self.client = OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = None

    @staticmethod
    def _validate_catalog(
        catalog: Sequence[Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        if not catalog:
            raise ValueError("Catalog cannot be empty.")

        if isinstance(catalog, (str, bytes)):
            raise ValueError("Catalog must be a sequence of product objects.")

        required_fields = {
            "product_id",
            "product_name",
            "unit_price",
            "currency",
            "merchant_id",
            "category",
            "color",
            "size",
            "is_subscription",
            "is_addon",
        }

        products: dict[str, dict[str, Any]] = {}

        try:
            for raw_product in catalog:
                if not isinstance(raw_product, Mapping):
                    raise ValueError("Each catalog product must be an object.")

                missing = required_fields - raw_product.keys()

                if missing:
                    raise ValueError(
                        "Catalog product is missing field(s): "
                        + ", ".join(sorted(missing))
                    )

                product_id = raw_product["product_id"]

                if not isinstance(product_id, str) or not product_id.strip():
                    raise ValueError(
                        "Catalog product_id must be a non-empty string."
                    )

                if product_id in products:
                    raise ValueError(
                        f"Duplicate catalog product_id: {product_id}"
                    )

                normalized = dict(raw_product)
                normalized["color"] = raw_product.get("color")
                normalized["size"] = raw_product.get("size")
                normalized["is_subscription"] = bool(
                    raw_product.get("is_subscription", False)
                )
                normalized["is_addon"] = bool(
                    raw_product.get("is_addon", False)
                )

                CartItem.model_validate(
                    {
                        key: value
                        for key, value in normalized.items()
                        if key != "product_id"
                    }
                )

                products[product_id] = normalized

        except (TypeError, ValidationError) as exc:
            raise ValueError(f"Invalid catalog data: {exc}") from exc

        return products

    def propose_transaction(
        self,
        user_intent: UserIntent,
        catalog: Sequence[Mapping[str, Any]],
        user_id: str = "ai-buyer-user",
    ) -> ProposedTransaction:

        products = self._validate_catalog(catalog)

        catalog_for_prompt = [
            {"product_id": product_id, **product}
            for product_id, product in products.items()
        ]

        if self.client is not None:
            catalog_summary = [
                {
                    "product_id": pid,
                    "product_name": p["product_name"],
                    "price": p["unit_price"],
                    "category": p.get("category"),
                    "color": p.get("color"),
                    "size": p.get("size"),
                }
                for pid, p in products.items()
            ]
            prompt = f"""You are a product matching assistant.
Select the best matching product from the catalog for the user request.

User request:
- Instruction: {user_intent.instruction}
- Product: {user_intent.product_name}
- Category: {user_intent.categories or user_intent.allowed_categories}
- Color: {user_intent.color or user_intent.allowed_colors}
- Size: {user_intent.size or user_intent.allowed_sizes}
- Max budget: {user_intent.max_amount} {user_intent.currency}

Available Catalog Products:
{json.dumps(catalog_summary, indent=2)}

You must respond with ONLY a JSON object containing the chosen "product_id".
Example format:
{{"product_id": "black-running-shoes"}}
"""
        else:
            prompt = f"""You are an AI shopping buyer. Select exactly one product from the supplied catalog for the user's request.

Security rules:
- You may only return a product_id that exactly matches one of the catalog entries below.
- You must NOT invent, change, or control any catalog value such as price, merchant, category, color, size, subscription status, or add-on status.
- Return ONLY JSON with exactly this shape: {{"product_id": "<one existing catalog product_id>"}}.
- Do not return multiple products, extra fields, or a product_id outside the catalog.

User authorization:
{json.dumps(user_intent.model_dump(mode="json"), sort_keys=True)}

Authoritative catalog:
{json.dumps(catalog_for_prompt, sort_keys=True)}

Choose the single best matching product_id from the catalog."""

        response_text = None
        for attempt in range(2):
            try:
                if self.client is not None:
                    response = self.client.chat.completions.create(
                        model="openrouter/free",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a shopping buyer assistant that selects a product_id from a catalog. Always respond with valid JSON.",
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        response_format={
                            "type": "json_object",
                        },
                    )
                    try:
                        response_text = response.choices[0].message.content
                    except (AttributeError, IndexError, TypeError):
                        response_text = None
                else:
                    # Preserve compatibility with injected mock models used by tests.
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "response_mime_type": "application/json",
                            "response_schema": {
                                "type": "object",
                                "properties": {
                                    "product_id": {
                                        "type": "string"
                                    }
                                },
                                "required": ["product_id"],
                            },
                        },
                    )
                    response_text = getattr(response, "text", None) if response is not None else None

                if response_text and response_text.strip():
                    ct = _extract_json_text(response_text)
                    if ct and ct.startswith("{") and "product_id" in ct:
                        break
                    if self.model is not None:
                        break
            except Exception as exc:
                if attempt == 1 or self.model is not None:
                    raise ValueError(self._safe_api_error(exc)) from exc

        if not response_text or not response_text.strip():
            raise ValueError("AI API returned an empty response.")

        clean_text = _extract_json_text(response_text)
        if not clean_text:
            raise ValueError("AI API returned an empty response.")
        try:
            selection = json.loads(clean_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed Gemini response: {exc}"
            ) from exc

        if not isinstance(selection, dict) or "product_id" not in selection:
            raise ValueError(
                "AI response must contain exactly one product_id."
            )

        if self.model is not None and set(selection) != {"product_id"}:
            raise ValueError(
                "AI response must contain exactly one product_id."
            )

        product_id = selection.get("product_id")

        if not isinstance(product_id, str) or not product_id.strip():
            raise ValueError(
                "AI response is missing a product identifier."
            )

        if product_id not in products:
            raise ValueError(
                f"AI selected unknown catalog product_id: {product_id}"
            )

        product = products[product_id]

        item = CartItem.model_validate(
            {
                key: value
                for key, value in product.items()
                if key != "product_id"
            }
        )

        total_amount = (item.unit_price or 0) * item.quantity

        return ProposedTransaction(
            user_id=user_id,
            items=[item],
            total_amount=total_amount,
            currency=item.currency,
            merchant_id=product["merchant_id"],
            notes="AI Buyer catalog selection",
        )