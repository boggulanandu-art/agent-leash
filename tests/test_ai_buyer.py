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
        self.catalog = [
            {
                "product_id": "black-running-shoes",
                "product_name": "Black Running Shoes",
                "unit_price": 2799,
                "currency": "INR",
                "merchant_id": "merchant-demo",
                "category": "footwear",
                "color": "black",
                "size": "9",
                "is_subscription": False,
                "is_addon": False,
            },
            {
                "product_id": "blue-backpack",
                "product_name": "Blue Backpack",
                "unit_price": 1499,
                "currency": "INR",
                "merchant_id": "merchant-demo",
                "category": "backpack",
                "color": "blue",
                "size": None,
                "is_subscription": False,
                "is_addon": False,
            },
            {
                "product_id": "wireless-headphones",
                "product_name": "Wireless Headphones",
                "unit_price": 2499,
                "currency": "INR",
                "merchant_id": "merchant-demo",
                "category": "electronics",
                "color": None,
                "size": None,
                "is_subscription": False,
                "is_addon": False,
            },
            {
                "product_id": "smartwatch",
                "product_name": "Smartwatch",
                "unit_price": 3999,
                "currency": "INR",
                "merchant_id": "merchant-demo",
                "category": "electronics",
                "color": None,
                "size": None,
                "is_subscription": False,
                "is_addon": False,
            },
            {
                "product_id": "laptop",
                "product_name": "Laptop",
                "unit_price": 45000,
                "currency": "INR",
                "merchant_id": "merchant-demo",
                "category": "electronics",
                "color": None,
                "size": None,
                "is_subscription": False,
                "is_addon": False,
            },
        ]
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

    def buyer_for(self, response_text=None, error=None):
        model = MagicMock()
        if error:
            model.generate_content.side_effect = error
        else:
            model.generate_content.return_value = MockResponse(response_text)
        return AIBuyer(model=model), model

    def test_valid_product_selection(self):
        buyer, _ = self.buyer_for('{"product_id": "black-running-shoes"}')

        transaction = buyer.propose_transaction(self.intent, self.catalog)

        self.assertEqual(transaction.user_id, "ai-buyer-user")
        self.assertEqual(len(transaction.items), 1)
        self.assertEqual(transaction.items[0].product_name, "Black Running Shoes")
        self.assertEqual(transaction.items[0].unit_price, 2799)

    def test_blue_backpack_request_selects_blue_backpack(self):
        intent = UserIntent(
            instruction="Buy a blue backpack under ₹2000.",
            product_name="backpack",
            max_amount=2000,
            currency="INR",
            categories=["backpack"],
            allowed_categories=["backpack"],
            allowed_colors=["blue"],
            allow_subscription=False,
            allow_addons=False,
        )
        buyer, _ = self.buyer_for('{"product_id": "blue-backpack"}')

        transaction = buyer.propose_transaction(intent, self.catalog)

        self.assertEqual(transaction.items[0].product_name, "Blue Backpack")
        self.assertEqual(transaction.items[0].color, "blue")
        self.assertEqual(transaction.items[0].unit_price, 1499)
        self.assertEqual(transaction.total_amount, 1499)

    def test_black_shoe_request_selects_black_running_shoes(self):
        intent = UserIntent(
            instruction="Buy black running shoes size 9 under ₹3000.",
            product_name="running shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
        )
        buyer, _ = self.buyer_for('{"product_id": "black-running-shoes"}')

        transaction = buyer.propose_transaction(intent, self.catalog)

        self.assertEqual(transaction.items[0].product_name, "Black Running Shoes")
        self.assertEqual(transaction.items[0].size, "9")
        self.assertEqual(transaction.items[0].unit_price, 2799)

    def test_headphones_can_be_selected(self):
        buyer, _ = self.buyer_for('{"product_id": "wireless-headphones"}')

        transaction = buyer.propose_transaction(
            UserIntent(
                instruction="Buy wireless headphones under ₹3000.",
                product_name="headphones",
                max_amount=3000,
                currency="INR",
                categories=["electronics"],
                allowed_categories=["electronics"],
                allow_subscription=False,
                allow_addons=False,
            ),
            self.catalog,
        )

        self.assertEqual(transaction.items[0].product_name, "Wireless Headphones")
        self.assertEqual(transaction.total_amount, 2499)

    def test_smartwatch_can_be_selected(self):
        buyer, _ = self.buyer_for('{"product_id": "smartwatch"}')

        transaction = buyer.propose_transaction(
            UserIntent(
                instruction="Buy a smartwatch under ₹5000.",
                product_name="smartwatch",
                max_amount=5000,
                currency="INR",
                categories=["electronics"],
                allowed_categories=["electronics"],
                allow_subscription=False,
                allow_addons=False,
            ),
            self.catalog,
        )

        self.assertEqual(transaction.items[0].product_name, "Smartwatch")
        self.assertEqual(transaction.total_amount, 3999)

    def test_unknown_product_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "invented-product"}')

        with self.assertRaisesRegex(ValueError, "unknown catalog"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_gemini_cannot_change_catalog_price(self):
        buyer, _ = self.buyer_for(json.dumps({
            "product_id": "blue-backpack",
            "unit_price": 1,
        }))

        with self.assertRaisesRegex(ValueError, "exactly one product_id"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_gemini_cannot_change_merchant(self):
        buyer, _ = self.buyer_for(json.dumps({
            "product_id": "black-running-shoes",
            "merchant_id": "malicious-merchant",
        }))

        with self.assertRaisesRegex(ValueError, "exactly one product_id"):
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
            "product_id": "blue-backpack",
            "product_name": "Invented Product",
            "unit_price": 1,
            "merchant_id": "invented-merchant",
        }))

        with self.assertRaises(ValueError):
            buyer.propose_transaction(self.intent, self.catalog)

        prompt = model.generate_content.call_args.args[0]
        self.assertIn("blue-backpack", prompt)
        self.assertIn("merchant-demo", prompt)

        buyer, _ = self.buyer_for('{"product_id": "blue-backpack"}')
        transaction = buyer.propose_transaction(self.intent, self.catalog)
        item = transaction.items[0]
        self.assertEqual(item.unit_price, 1499)
        self.assertEqual(transaction.merchant_id, "merchant-demo")
        self.assertEqual(item.category, "backpack")

    def test_multiple_selected_products_are_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "black-running-shoes", "another_product_id": "blue-backpack"}')

        with self.assertRaisesRegex(ValueError, "exactly one"):
            buyer.propose_transaction(self.intent, self.catalog)

    def test_empty_catalog_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "black-running-shoes"}')

        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            buyer.propose_transaction(self.intent, [])

    def test_invalid_catalog_data_is_rejected(self):
        buyer, _ = self.buyer_for('{"product_id": "black-running-shoes"}')
        invalid_catalog = [{"product_id": "black-running-shoes", "product_name": "Missing fields"}]

        with self.assertRaisesRegex(ValueError, "missing field"):
            buyer.propose_transaction(self.intent, invalid_catalog)


if __name__ == "__main__":
    unittest.main()