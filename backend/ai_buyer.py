from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from .models import CartItem, ProposedTransaction, UserIntent

_MISSING = object()


class AIBuyer:
    """Select one product from an authoritative catalog using Gemini."""

    def __init__(self, api_key: object = _MISSING, model=None):
        if model is not None:
            self.model = model
            return

        if api_key is _MISSING:
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("Gemini API key not provided and GEMINI_API_KEY environment variable not set.")
        elif api_key is None:
            raise ValueError("Gemini API key not provided and GEMINI_API_KEY environment variable not set.")
        else:
            key = str(api_key)

        import google.generativeai as genai

        genai.configure(api_key=key)
        self.model = genai.GenerativeModel("gemini-3.6-flash")

    @staticmethod
    def _validate_catalog(catalog: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
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
                    raise ValueError("Catalog product is missing field(s): " + ", ".join(sorted(missing)))

                product_id = raw_product["product_id"]
                if not isinstance(product_id, str) or not product_id.strip():
                    raise ValueError("Catalog product_id must be a non-empty string.")
                if product_id in products:
                    raise ValueError(f"Duplicate catalog product_id: {product_id}")

                normalized = dict(raw_product)
                normalized["color"] = raw_product.get("color")
                normalized["size"] = raw_product.get("size")
                normalized["is_subscription"] = bool(raw_product.get("is_subscription", False))
                normalized["is_addon"] = bool(raw_product.get("is_addon", False))
                CartItem.model_validate({key: value for key, value in normalized.items() if key != "product_id"})
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
        catalog_for_prompt = [{"product_id": product_id, **product} for product_id, product in products.items()]
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

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {"product_id": {"type": "string"}},
                        "required": ["product_id"],
                    },
                },
            )
        except Exception as exc:
            raise ValueError(f"Gemini API request failed: {exc}") from exc

        response_text = getattr(response, "text", None) if response is not None else None
        if not response_text:
            raise ValueError("Gemini API returned an empty response.")

        try:
            selection = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed Gemini response: {exc}") from exc

        if not isinstance(selection, dict) or set(selection) != {"product_id"}:
            raise ValueError("Gemini response must contain exactly one product_id.")
        product_id = selection.get("product_id")
        if not isinstance(product_id, str) or not product_id.strip():
            raise ValueError("Gemini response is missing a product identifier.")
        if product_id not in products:
            raise ValueError(f"Gemini selected unknown catalog product_id: {product_id}")

        product = products[product_id]
        item = CartItem.model_validate({key: value for key, value in product.items() if key != "product_id"})
        total_amount = (item.unit_price or 0) * item.quantity
        return ProposedTransaction(
            user_id=user_id,
            items=[item],
            total_amount=total_amount,
            currency=item.currency,
            merchant_id=product["merchant_id"],
            notes="AI Buyer catalog selection",
        )