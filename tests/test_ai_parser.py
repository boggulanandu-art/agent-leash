import json
import sys
import unittest
from unittest.mock import MagicMock

sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

from backend.ai_parser import AIParser
from backend.models import UserIntent


class MockResponse:
    def __init__(self, text):
        self.text = text


class TestAIParser(unittest.TestCase):
    def _parser(self, response_data=None, error=None, response_text=None):
        model = MagicMock()
        if error:
            model.generate_content.side_effect = error
        elif response_text is not None:
            model.generate_content.return_value = MockResponse(response_text)
        else:
            model.generate_content.return_value = MockResponse(json.dumps(response_data))
        return AIParser(api_key="test-key", model=model)

    def _response(self, **overrides):
        data = {
            "product_name": "shoes", "brand": None, "color": None, "size": None,
            "max_amount": 3000, "currency": "INR", "categories": [],
            "allowed_categories": [], "allowed_colors": [], "allowed_sizes": [],
            "allow_subscription": False, "allow_addons": False,
            "allowed_merchants": [], "blocked_merchants": [], "daily_limit": None,
            "session_limit": None, "review_threshold": None,
        }
        data.update(overrides)
        return data

    def test_normal_shopping_request(self):
        parser = self._parser(self._response(
            product_name="Nike running shoes", brand="Nike", color="black", size="9",
            categories=["footwear"], allowed_categories=["footwear"],
            allowed_colors=["black"], allowed_sizes=["9"], max_amount=3000))
        intent = parser.parse("Buy me Nike running shoes, size 9, under ₹3000.")
        self.assertIsInstance(intent, UserIntent)
        self.assertEqual(intent.product_name, "Nike running shoes")
        self.assertEqual(intent.brand, "Nike")
        self.assertEqual(intent.allowed_categories, ["footwear"])
        self.assertEqual(intent.max_amount, 3000)

    def test_amount_extraction(self):
        intent = self._parser(self._response(max_amount=5000.50)).parse("Buy shoes under ₹5000.50")
        self.assertEqual(intent.max_amount, 5000.50)

    def test_subscription_prohibited(self):
        intent = self._parser(self._response(product_name="software")).parse("Buy software")
        self.assertFalse(intent.allow_subscription)

    def test_addon_prohibited(self):
        intent = self._parser(self._response()).parse("Buy shoes. No extra items or add-ons.")
        self.assertFalse(intent.allow_addons)

    def test_invalid_json_response(self):
        parser = self._parser(response_text="{invalid json}")
        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")
        self.assertIn("Invalid JSON", str(context.exception))

    def test_empty_instruction(self):
        with self.assertRaises(ValueError) as context:
            self._parser(self._response()).parse("")
        self.assertIn("empty", str(context.exception).lower())

    def test_api_failure(self):
        parser = self._parser(error=Exception("API rate limit exceeded"))
        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")
        self.assertIn("quota temporarily unavailable", str(context.exception).lower())

    def test_empty_api_response(self):
        with self.assertRaises(ValueError) as context:
            self._parser(response_text="").parse("Buy shoes")
        self.assertIn("empty response", str(context.exception).lower())

    def test_missing_required_fields(self):
        with self.assertRaises(ValueError) as context:
            self._parser({"product_name": "shoes"}).parse("Buy shoes")
        self.assertIn("validate", str(context.exception).lower())

    def test_no_api_key(self):
        with self.assertRaises(ValueError) as context:
            AIParser(api_key=None)
        self.assertIn("API key", str(context.exception))

    def test_category_extraction(self):
        intent = self._parser(self._response(
            product_name="wireless headphones", brand="Sony",
            categories=["electronics", "audio"], allowed_categories=["electronics", "audio"],
            max_amount=8000)).parse("Buy Sony wireless headphones under ₹8000")
        self.assertEqual(intent.allowed_categories, ["electronics", "audio"])
        self.assertEqual(intent.brand, "Sony")

    def test_merchant_extraction(self):
        intent = self._parser(self._response(
            product_name="books", allowed_merchants=["amazon", "flipkart"], max_amount=500
        )).parse("Buy books from Amazon or Flipkart, under ₹500")
        self.assertEqual(intent.allowed_merchants, ["amazon", "flipkart"])

    def test_currency_detection(self):
        intent = self._parser(self._response()).parse("Buy shoes for ₹3000 maximum")
        self.assertEqual(intent.currency, "INR")

    def test_attributes_extraction(self):
        intent = self._parser(self._response(
            product_name="running shoes", brand="Nike", color="blue", size="10",
            categories=["footwear"], allowed_categories=["footwear"],
            allowed_colors=["blue"], allowed_sizes=["10"], max_amount=4500
        )).parse("Buy blue Nike running shoes, size 10, under ₹4500")
        self.assertEqual(intent.color, "blue")
        self.assertEqual(intent.size, "10")
        self.assertEqual(intent.allowed_categories, ["footwear"])
        self.assertEqual(intent.allowed_colors, ["blue"])
        self.assertEqual(intent.allowed_sizes, ["10"])


if __name__ == "__main__":
    unittest.main()
