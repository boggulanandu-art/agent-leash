import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import backend.main as main
from backend.ai_buyer import AIBuyer
from backend.database import AuditDatabase
from backend.models import CartItem, ProposedTransaction, UserIntent


class TestAgentBuyEndpoint(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = AuditDatabase(Path(self.temp_dir.name) / "agent-buy.db")
        self.original_database = main.database
        self.original_parser = main.parser
        self.original_ai_buyer = main.ai_buyer
        self.original_policy_engine = main.policy_engine
        self.original_razorpay_service = main.razorpay_service
        main.database = self.database
        main.parser = MagicMock()
        main.ai_buyer = MagicMock(spec=AIBuyer)
        main.policy_engine = main.PolicyEngine()
        main.razorpay_service = MagicMock()
        self.client = TestClient(main.app)

        self.intent = UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
        )

    def tearDown(self):
        self.database.close()
        main.database = self.original_database
        main.parser = self.original_parser
        main.ai_buyer = self.original_ai_buyer
        main.policy_engine = self.original_policy_engine
        main.razorpay_service = self.original_razorpay_service
        self.temp_dir.cleanup()

    def make_transaction(self, price=2799, is_addon=False):
        return ProposedTransaction(
            user_id="ai-buyer-user",
            items=[
                CartItem(
                    product_name="Black Running Shoes",
                    unit_price=price,
                    currency="INR",
                    category="footwear",
                    color="black",
                    size="9",
                    is_addon=is_addon,
                )
            ],
            total_amount=price,
            currency="INR",
            merchant_id="merchant-demo",
        )

    def configure_success(self, transaction=None):
        main.parser.parse.return_value = self.intent
        main.ai_buyer.propose_transaction.return_value = transaction or self.make_transaction()

    def test_valid_instruction_flows_to_allow(self):
        self.configure_success()

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "ALLOW")
        self.assertEqual(payload["risk_score"], 10)
        self.assertEqual(payload["violated_rules"], [])
        self.assertTrue(payload["transaction_id"])
        self.assertTrue(payload["payment_ready"])
        main.parser.parse.assert_called_once_with(self.intent.instruction)
        main.ai_buyer.propose_transaction.assert_called_once()
        main.razorpay_service.assert_not_called()

    def test_repeated_request_id_does_not_duplicate_audit_entry(self):
        self.configure_success()
        request = {"instruction": self.intent.instruction, "request_id": "retry-1"}

        first = self.client.post("/agent/buy", json=request)
        second = self.client.post("/agent/buy", json=request)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["transaction_id"], second.json()["transaction_id"])
        self.assertEqual(len(self.client.get("/audit").json()), 1)

    def test_separate_requests_get_separate_audit_transaction_ids(self):
        self.configure_success()

        first = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})
        second = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()["transaction_id"], second.json()["transaction_id"])
        self.assertEqual(len(self.client.get("/audit").json()), 2)

    def test_policy_violation_returns_block(self):
        self.configure_success(self.make_transaction(price=2799, is_addon=True))

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "BLOCK")
        self.assertIn("addon_not_allowed", payload["violated_rules"])
        self.assertFalse(payload["payment_ready"])

    def test_ai_buyer_failure_returns_safe_error(self):
        main.parser.parse.return_value = self.intent
        main.ai_buyer.propose_transaction.side_effect = ValueError("no matching catalog product")

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 502)
        self.assertIn("AI Buyer failed", response.json()["detail"])

    def test_parser_failure_returns_safe_error(self):
        main.parser.parse.side_effect = ValueError("Gemini unavailable")

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 502)
        self.assertIn("Intent parsing failed", response.json()["detail"])
        main.ai_buyer.propose_transaction.assert_not_called()

    def test_parser_quota_failure_returns_service_unavailable(self):
        main.parser.parse.side_effect = ValueError("Gemini API quota temporarily unavailable. Please try again later.")

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 503)
        self.assertIn("quota", response.json()["detail"].lower())
        main.ai_buyer.propose_transaction.assert_not_called()

    def test_ai_buyer_failure_never_creates_payment_order(self):
        main.parser.parse.return_value = self.intent
        main.ai_buyer.propose_transaction.side_effect = ValueError("Gemini API request failed. Please try again later.")

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 502)
        self.assertIn("AI Buyer failed", response.json()["detail"])
        main.razorpay_service.create_test_order.assert_not_called()

    def test_agent_buy_never_calls_razorpay(self):
        self.configure_success()

        response = self.client.post("/agent/buy", json={"instruction": self.intent.instruction})

        self.assertEqual(response.status_code, 200)
        main.razorpay_service.create_test_order.assert_not_called()

    def test_empty_instruction_is_rejected(self):
        response = self.client.post("/agent/buy", json={"instruction": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())
        main.parser.parse.assert_not_called()

    def test_demo_scenario_behavior_is_preserved(self):
        payload = main.demo_scenario_evaluation("SAFE_PURCHASE")

        self.assertEqual(payload["policy_decision"]["decision"], "ALLOW")
        self.assertEqual(payload["proposed_transaction"]["total_amount"], 2799)
        self.assertEqual(payload["proposed_transaction"]["notes"], "simulated demo transaction")

    def test_authoritative_catalog_contains_expected_products(self):
        product_ids = [product["product_id"] for product in main.AI_BUYER_CATALOG]
        self.assertEqual(
            sorted(product_ids),
            sorted([
                "black-running-shoes",
                "blue-backpack",
                "wireless-headphones",
                "smartwatch",
                "laptop",
            ]),
        )
        for product in main.AI_BUYER_CATALOG:
            self.assertEqual(product["merchant_id"], "merchant-demo")
            self.assertEqual(product["currency"], "INR")
            self.assertFalse(product["is_subscription"])
            self.assertFalse(product["is_addon"])


if __name__ == "__main__":
    unittest.main()