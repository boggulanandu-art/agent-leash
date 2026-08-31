import json
import unittest
from unittest.mock import MagicMock

from backend.ai_buyer import AIBuyer
from backend.models import UserIntent


class MockResponse:
    def __init__(self, text):
        self.text = text


class TestAIBuyer(unittest.TestCase):
    def setUp(self):
        self.intent = UserIntent(
            instruction="Buy black running shoes under ₹3000.",
            product_name="running shoes",
            max_amount=3000,
            currency="INR",
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
        )
        self.catalog = [
            {
                "product_id": "shoe-black-9",
                "product_name": "Black Running Shoes",
                "unit_price": 2799,
                "currency": "INR",
                "merchant_id": "merchant-authoritative",
                "category": "footwear",
                "color": "black",
                "size": "9",
                "is_subscription": False,
                "is_addon": False,
            },
            {
                "product_id": "shoe-blue-9",
                "product_name": "Blue Running Shoes",
                "unit_price": 2899,
                "currency": "INR",
                "merchant_id": "merchant-two",
                "category": "footwear",
                "color": "blue",
                "size": "9",
                "is_subscription": False,
                "is_addon": False,
            },
        ]

    def buyer_for(self, response_text=None, error=None):
        model = MagicMock()
        if error:
            model.generate_content.side_effect = error
        else:
            model.generate_content.return_value = MockResponse(response_text)
        return AIBuyer(model=model), model

    def test_valid_product_selection(self):
        buyer, _ = self.buyer_for('{"product_id": "shoe-black-9"}')

        transaction = buyer.propose_transaction(self.intent, self.catalog)

        self.assertEqual(transaction.user_id, "ai-buyer-user")
        self.assertEqual(len(transaction.items), 1)
        self.assertEqual(transaction.items[0].product_name, "Black Running Shoes")

    def test_unknown_product_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "invented-product"}')

        with self.assertRaisesRegex(ValueError, "unknown catalog"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_malformed_response_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id":')

        with self.assertRaisesRegex(ValueError, "Malformed Gemini response"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_missing_product_identifier_is_rejected(self):
        buyer, _ = self.buyer_for("{}")

        with self.assertRaisesRegex(ValueError, "exactly one product_id"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_api_failure_is_handled(self):
        buyer, _ = self.buyer_for(error=RuntimeError("service unavailable"))

        with self.assertRaisesRegex(ValueError, "Gemini API request failed"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_catalog_values_override_gemini_values(self):
        buyer, model = self.buyer_for(json.dumps({
            "product_id": "shoe-black-9",
            "product_name": "Invented Product",
            "unit_price": 1,
            "merchant_id": "invented-merchant",
        }))

        with self.assertRaises(ValueError):
            buyer.propose_transaction(self.intent, self.catalog)

        prompt = model.generate_content.call_args.args[0]
        self.assertIn("shoe-black-9", prompt)
        self.assertIn("merchant-authoritative", prompt)

        buyer, _ = self.buyer_for('{"product_id": "shoe-black-9"}')
        transaction = buyer.propose_transaction(self.intent, self.catalog)
        item = transaction.items[0]
        self.assertEqual(item.unit_price, 2799)
        self.assertEqual(transaction.merchant_id, "merchant-authoritative")
        self.assertEqual(item.category, "footwear")

    def test_multiple_selected_products_are_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "shoe-black-9", "another_product_id": "shoe-blue-9"}')

        with self.assertRaisesRegex(ValueError, "exactly one"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_empty_catalog_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "shoe-black-9"}')

        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            buyer.propose_transaction(self.intent, [])

    def test_invalid_catalog_data_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "shoe-black-9"}')
        invalid_catalog = [{"product_id": "shoe-black-9", "product_name": "Missing fields"}]

        with self.assertRaisesRegex(ValueError, "missing field"):
            buyer.propose_transaction(self.intent, invalid_catalog)


if __name__ == "__main__":
    unittest.main()