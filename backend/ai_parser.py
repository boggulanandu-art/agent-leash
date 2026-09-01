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
        _CANONICAL_CATEGORY_ALIASES.get(category.strip().lower(), category.strip())
        for category in categories
    ]


class AIParser:
    """Converts natural-language shopping instructions into structured UserIntent using Gemini API."""

    def __init__(self, api_key: object = _MISSING, model=None):
        """Initialize AIParser with Gemini API key.
        
        Args:
            api_key: Gemini API key. If omitted, reads from GEMINI_API_KEY environment variable.
            model: Optional model instance for testing. If None, creates a new Gemini model.
        
        Raises:
            ValueError: If no API key is provided and GEMINI_API_KEY env var is not set.
        """
        if api_key is _MISSING:
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("Gemini API key not provided and GEMINI_API_KEY environment variable not set.")
        elif api_key is None:
            raise ValueError("Gemini API key not provided and GEMINI_API_KEY environment variable not set.")
        else:
            key = str(api_key)

        if model is not None:
            # Use provided model (for testing)
            self.model = model
        else:
            # Lazy-load google.generativeai to allow mocking in tests
            import google.generativeai as genai
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel("gemini-3.6-flash")

    def parse(self, instruction: str) -> UserIntent:
        """Convert natural-language purchase request into a structured UserIntent.
        
        Args:
            instruction: Natural language shopping instruction.
        
        Returns:
            UserIntent: Validated structured intent with extracted constraints.
        
        Raises:
            ValueError: If instruction is empty, API fails, or response cannot be parsed.
        """
        cleaned = instruction.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be empty.")

        # Define the schema for structured output
        schema = {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "nullable": True, "description": "Product name or type being requested"},
                "brand": {"type": "string", "nullable": True, "description": "Brand name if specified"},
                "color": {"type": "string", "nullable": True, "description": "Preferred color"},
                "size": {"type": "string", "nullable": True, "description": "Preferred size"},
                "max_amount": {"type": "number", "nullable": True, "description": "Maximum price in the stated currency"},
                "currency": {"type": "string", "description": "Currency code (default INR)"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Product categories",
                },
                "allowed_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed categories",
                },
                "allowed_colors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed colors",
                },
                "allowed_sizes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed sizes",
                },
                "allow_subscription": {"type": "boolean", "description": "Whether subscriptions are allowed"},
                "allow_addons": {"type": "boolean", "description": "Whether add-ons are allowed"},
                "allowed_merchants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed merchant names or IDs",
                },
                "blocked_merchants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Blocked merchant names or IDs",
                },
                "daily_limit": {"type": "number", "nullable": True, "description": "Daily spending limit"},
                "session_limit": {"type": "number", "nullable": True, "description": "Session spending limit"},
                "review_threshold": {"type": "number", "nullable": True, "description": "Amount threshold requiring human review"},
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

        prompt = f"""You are a shopping intent parser. Extract structured information from the user's natural language shopping instruction.

User instruction: "{cleaned}"

Convert this into a JSON object matching the schema. Rules:
1. Extract the product name, brand, color, size if mentioned.
2. Extract maximum price/amount if specified. Preserve the numerical value as-is (will be converted to currency later).
3. Detect currency from symbols (₹ or INR = Indian Rupees). Default to INR if not specified.
4. If a category is mentioned (e.g., "shoes", "electronics"), add it to allowed_categories.
5. Extract allowed/blocked merchants if named.
6. If color/size are specified, add them to allowed lists.
7. Check if the user explicitly rejects subscriptions or add-ons. If they say "no subscriptions", "don't want subscription", etc., set allow_subscription to false. Default to false if not mentioned.
8. Check if the user explicitly rejects add-ons. If they say "no add-ons", "don't want extra items", etc., set allow_addons to false. Default to false if not mentioned.
9. Set daily_limit, session_limit, review_threshold to null unless explicitly stated.
10. Always return valid JSON with all required fields. Use null for unknown/unspecified fields.

Return ONLY valid JSON, no other text."""

        try:
            import google.generativeai as genai
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                },
            )
        except Exception as e:
            raise ValueError(f"Gemini API request failed: {str(e)}")

        if not response or not response.text:
            raise ValueError("Gemini API returned empty response.")

        # Parse the JSON response
        try:
            parsed_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Gemini API: {str(e)}")

        missing_required_fields = [key for key in schema["required"] if key not in parsed_data]
        if missing_required_fields:
            raise ValueError(
                "Failed to validate parsed intent: missing required field(s): "
                + ", ".join(missing_required_fields)
            )

        # Validate and construct UserIntent
        try:
            intent = UserIntent(
                instruction=cleaned,
                product_name=parsed_data.get("product_name"),
                brand=parsed_data.get("brand"),
                color=parsed_data.get("color"),
                size=parsed_data.get("size"),
                max_price=parsed_data.get("max_amount"),
                max_amount=parsed_data.get("max_amount"),
                currency=parsed_data.get("currency", "INR"),
                categories=_canonicalize_categories(parsed_data.get("categories", [])),
                allowed_categories=_canonicalize_categories(parsed_data.get("allowed_categories", [])),
                allowed_colors=parsed_data.get("allowed_colors", []),
                allowed_sizes=parsed_data.get("allowed_sizes", []),
                allow_subscription=parsed_data.get("allow_subscription", False),
                allow_addons=parsed_data.get("allow_addons", False),
                allowed_merchants=parsed_data.get("allowed_merchants", []),
                blocked_merchants=parsed_data.get("blocked_merchants", []),
                daily_limit=parsed_data.get("daily_limit"),
                session_limit=parsed_data.get("session_limit"),
                review_threshold=parsed_data.get("review_threshold"),
            )
            return intent
        except ValidationError as e:
            raise ValueError(f"Failed to validate parsed intent: {str(e)}")
