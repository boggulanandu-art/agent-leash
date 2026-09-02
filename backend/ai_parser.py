from __future__ import annotations

import json
import os
from typing import Any, Optional

from pydantic import ValidationError

from .models import UserIntent


_MISSING = object()


_CANONICAL_CATEGORY_ALIASES = {
    "shoe": "footwear",
    "shoes": "footwear",
    "running shoe": "footwear",
    "running shoes": "footwear",
}


def _canonicalize_categories(categories: list[str]) -> list[str]:
    return [
        _CANONICAL_CATEGORY_ALIASES.get(
            category.strip().lower(),
            category.strip(),
        )
        for category in categories
    ]


def _as_strings(values: Any) -> list[str]:
    """Convert AI-returned list values into strings safely."""
    if not isinstance(values, list):
        return []

    return [str(value) for value in values]


class AIParser:
    """Converts natural-language shopping instructions into UserIntent using OpenRouter."""

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
            return "AI API quota temporarily unavailable. Please try again later."

        return "AI API request failed. Please try again later."

    def __init__(self, api_key: object = _MISSING, model=None):
        """Initialize AIParser with an OpenRouter API key."""

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

    def parse(self, instruction: str) -> UserIntent:
        """Convert natural-language purchase request into a structured UserIntent."""

        cleaned = instruction.strip()

        if not cleaned:
            raise ValueError("Instruction cannot be empty.")

        schema = {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "nullable": True,
                },
                "brand": {
                    "type": "string",
                    "nullable": True,
                },
                "color": {
                    "type": "string",
                    "nullable": True,
                },
                "size": {
                    "type": "string",
                    "nullable": True,
                },
                "max_amount": {
                    "type": "number",
                    "nullable": True,
                },
                "currency": {
                    "type": "string",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "allowed_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "allowed_colors": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "allowed_sizes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "allow_subscription": {
                    "type": "boolean",
                },
                "allow_addons": {
                    "type": "boolean",
                },
                "allowed_merchants": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "blocked_merchants": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "daily_limit": {
                    "type": "number",
                    "nullable": True,
                },
                "session_limit": {
                    "type": "number",
                    "nullable": True,
                },
                "review_threshold": {
                    "type": "number",
                    "nullable": True,
                },
            },
            "required": [
                "product_name",
                "brand",
                "color",
                "size",
                "max_amount",
                "currency",
                "categories",
                "allowed_categories",
                "allowed_colors",
                "allowed_sizes",
                "allow_subscription",
                "allow_addons",
                "allowed_merchants",
                "blocked_merchants",
                "daily_limit",
                "session_limit",
                "review_threshold",
            ],
        }

        prompt = f"""You are a shopping intent parser.

User instruction:
"{cleaned}"

Return ONLY valid JSON.

Rules:
1. Extract product name, brand, color and size.
2. Extract maximum price.
3. Detect currency. Use INR by default.
4. Add product categories.
5. Add specified colors to allowed_colors.
6. Add specified sizes to allowed_sizes as STRINGS.
7. Subscriptions are false unless explicitly allowed.
8. Add-ons are false unless explicitly allowed.
9. Use empty arrays for unknown list fields.
10. Use null for unknown numeric fields.
11. Always return every required field.
12. allowed_sizes MUST contain strings, for example ["9"], never [9].
"""

        try:
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model="openrouter/free",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    response_format={
                        "type": "json_object",
                    },
                )
            else:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    },
                )

        except Exception as e:
            raise ValueError(self._safe_api_error(e)) from e

        if self.client is not None:
            try:
                response_text = response.choices[0].message.content
            except (AttributeError, IndexError, TypeError):
                response_text = None
        else:
            response_text = (
                getattr(response, "text", None)
                if response is not None
                else None
            )

        if not response_text:
            raise ValueError("AI API returned empty response.")

        try:
            parsed_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from AI API: {str(e)}"
            ) from e

        if not isinstance(parsed_data, dict):
            raise ValueError("AI response must be a JSON object.")

        defaults = {
            "product_name": None,
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": None,
            "currency": "INR",
            "categories": [],
            "allowed_categories": [],
            "allowed_colors": [],
            "allowed_sizes": [],
            "allow_subscription": False,
            "allow_addons": False,
            "allowed_merchants": [],
            "blocked_merchants": [],
            "daily_limit": None,
            "session_limit": None,
            "review_threshold": None,
        }

        for key, default_value in defaults.items():
            if key not in parsed_data or parsed_data[key] is None:
                parsed_data[key] = default_value

        # Normalize AI output before passing it to Pydantic.
        parsed_data["categories"] = _as_strings(
            parsed_data.get("categories", [])
        )
        parsed_data["allowed_categories"] = _as_strings(
            parsed_data.get("allowed_categories", [])
        )
        parsed_data["allowed_colors"] = _as_strings(
            parsed_data.get("allowed_colors", [])
        )
        parsed_data["allowed_sizes"] = _as_strings(
            parsed_data.get("allowed_sizes", [])
        )
        parsed_data["allowed_merchants"] = _as_strings(
            parsed_data.get("allowed_merchants", [])
        )
        parsed_data["blocked_merchants"] = _as_strings(
            parsed_data.get("blocked_merchants", [])
        )

        try:
            intent = UserIntent(
                instruction=cleaned,
                product_name=parsed_data.get("product_name"),
                brand=parsed_data.get("brand"),
                color=parsed_data.get("color"),
                size=(
                    str(parsed_data["size"])
                    if parsed_data.get("size") is not None
                    else None
                ),
                max_price=parsed_data.get("max_amount"),
                max_amount=parsed_data.get("max_amount"),
                currency=parsed_data.get("currency", "INR"),
                categories=_canonicalize_categories(
                    parsed_data.get("categories", [])
                ),
                allowed_categories=_canonicalize_categories(
                    parsed_data.get("allowed_categories", [])
                ),
                allowed_colors=parsed_data.get(
                    "allowed_colors",
                    [],
                ),
                allowed_sizes=parsed_data.get(
                    "allowed_sizes",
                    [],
                ),
                allow_subscription=parsed_data.get(
                    "allow_subscription",
                    False,
                ),
                allow_addons=parsed_data.get(
                    "allow_addons",
                    False,
                ),
                allowed_merchants=parsed_data.get(
                    "allowed_merchants",
                    [],
                ),
                blocked_merchants=parsed_data.get(
                    "blocked_merchants",
                    [],
                ),
                daily_limit=parsed_data.get("daily_limit"),
                session_limit=parsed_data.get("session_limit"),
                review_threshold=parsed_data.get("review_threshold"),
            )

            return intent

        except ValidationError as e:
            raise ValueError(
                f"Failed to validate parsed intent: {str(e)}"
            ) from e