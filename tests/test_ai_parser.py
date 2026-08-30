import json
import sys
import unittest
from unittest.mock import MagicMock

# Pre-mock google.generativeai to prevent import errors
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

from backend.ai_parser import AIParser
from backend.models import UserIntent


class MockResponse:
    """Mock Gemini API response."""

    def __init__(self, text):
        self.text = text


class TestAIParser(unittest.TestCase):
    """Test suite for AI Intent Parser with mocked Gemini API."""

    def test_normal_shopping_request(self):
        """Test parsing a normal shopping request."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "Nike running shoes",
            "brand": "Nike",
            "color": "black",
            "size": "9",
            "max_amount": 3000,
            "currency": "INR",
            "categories": ["footwear"],
            "allowed_categories": ["footwear"],
            "allowed_colors": ["black"],
            "allowed_sizes": ["9"],
            "allow_subscription": False,
            "allow_addons": False,
            "allowed_merchants": [],
            "blocked_merchants": [],
            "daily_limit": None,
            "session_limit": None,
            "review_threshold": None,
        }
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        instruction = "Buy me Nike running shoes, size 9, under ₹3000."
        intent = parser.parse(instruction)

        self.assertIsInstance(intent, UserIntent)
        self.assertEqual(intent.product_name, "Nike running shoes")
        self.assertEqual(intent.brand, "Nike")
        self.assertEqual(intent.color, "black")
        self.assertEqual(intent.size, "9")
        self.assertEqual(intent.max_amount, 3000)
        self.assertEqual(intent.currency, "INR")
        self.assertEqual(intent.allowed_categories, ["footwear"])
        self.assertFalse(intent.allow_subscription)
        self.assertFalse(intent.allow_addons)

    def test_amount_extraction(self):
        """Test extraction of maximum price/amount."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "shoes",
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": 5000.50,
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
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy shoes under ₹5000.50")

        self.assertEqual(intent.max_amount, 5000.50)
        self.assertEqual(intent.currency, "INR")

    def test_subscription_prohibited(self):
        """Test detection of explicit subscription prohibition."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "software",
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": 2000,
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
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy software under ₹2000. I don't want a subscription.")

        self.assertFalse(intent.allow_subscription)

    def test_addon_prohibited(self):
        """Test detection of explicit add-on prohibition."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "shoes",
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": 1500,
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
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy shoes under ₹1500. No extra items or add-ons.")

        self.assertFalse(intent.allow_addons)

    def test_invalid_json_response(self):
        """Test handling of invalid JSON from Gemini."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MockResponse('{invalid json}')

        parser = AIParser(api_key="test-key", model=mock_model)

        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")

        self.assertIn("Invalid JSON", str(context.exception))

    def test_empty_instruction(self):
        """Test handling of empty instruction."""
        mock_model = MagicMock()
        parser = AIParser(api_key="test-key", model=mock_model)

        with self.assertRaises(ValueError) as context:
            parser.parse("")

        self.assertIn("empty", str(context.exception).lower())

    def test_api_failure(self):
        """Test handling of Gemini API failure."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API rate limit exceeded")

        parser = AIParser(api_key="test-key", model=mock_model)

        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")

        self.assertIn("API request failed", str(context.exception))

    def test_empty_api_response(self):
        """Test handling of empty API response."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MockResponse("")

        parser = AIParser(api_key="test-key", model=mock_model)

        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")

        self.assertIn("empty response", str(context.exception).lower())

    def test_missing_required_fields(self):
        """Test handling of missing required fields in response."""
        mock_model = MagicMock()
        response_data = {"product_name": "shoes"}
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)

        with self.assertRaises(ValueError) as context:
            parser.parse("Buy shoes")

        self.assertIn("validate", str(context.exception).lower())

    def test_no_api_key(self):
        """Test initialization without API key."""
        with self.assertRaises(ValueError) as context:
            AIParser(api_key=None)

        self.assertIn("API key", str(context.exception))

    def test_category_extraction(self):
        """Test category extraction from product type."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "wireless headphones",
            "brand": "Sony",
            "color": None,
            "size": None,
            "max_amount": 8000,
            "currency": "INR",
            "categories": ["electronics", "audio"],
            "allowed_categories": ["electronics", "audio"],
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
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy Sony wireless headphones under ₹8000")

        self.assertEqual(intent.allowed_categories, ["electronics", "audio"])
        self.assertEqual(intent.brand, "Sony")

    def test_merchant_extraction(self):
        """Test merchant/brand extraction."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "books",
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": 500,
            "currency": "INR",
            "categories": [],
            "allowed_categories": [],
            "allowed_colors": [],
            "allowed_sizes": [],
            "allow_subscription": False,
            "allow_addons": False,
            "allowed_merchants": ["amazon", "flipkart"],
            "blocked_merchants": [],
            "daily_limit": None,
            "session_limit": None,
            "review_threshold": None,
        }
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy books from Amazon or Flipkart, under ₹500")

        self.assertEqual(intent.allowed_merchants, ["amazon", "flipkart"])

    def test_currency_detection(self):
        """Test currency detection from instruction."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "shoes",
            "brand": None,
            "color": None,
            "size": None,
            "max_amount": 3000,
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
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy shoes for ₹3000 maximum")

        self.assertEqual(intent.currency, "INR")

    def test_attributes_extraction(self):
        """Test extraction of color and size attributes."""
        mock_model = MagicMock()
        response_data = {
            "product_name": "running shoes",
            "brand": "Nike",
            "color": "blue",
            "size": "10",
            "max_amount": 4500,
            "currency": "INR",
            "categories": ["footwear"],
            "allowed_categories": ["footwear"],
            "allowed_colors": ["blue"],
            "allowed_sizes": ["10"],
            "allow_subscription": False,
            "allow_addons": False,
            "allowed_merchants": [],
            "blocked_merchants": [],
            "daily_limit": None,
            "session_limit": None,
            "review_threshold": None,
        }
        mock_model.generate_content.return_value = MockResponse(json.dumps(response_data))

        parser = AIParser(api_key="test-key", model=mock_model)
        intent = parser.parse("Buy blue Nike running shoes, size 10, under ₹4500")

        self.assertEqual(intent.color, "blue")
        self.assertEqual(intent.size, "10")
        self.assertEqual(intent.allowed_colors, ["blue"])
        self.assertEqual(intent.allowed_sizes, ["10"])


if __name__ == "__main__":
    unittest.main()
