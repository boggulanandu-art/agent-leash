import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock

from fastapi.testclient import TestClient

import backend.main as main
from backend.database import AuditDatabase
from backend.models import CartItem, ProposedTransaction
from backend.razorpay_service import RazorpayService


class TestASKDemo(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = AuditDatabase(Path(self.temp_dir.name) / "ask-demo.db")
        self.original_database = main.database
        self.original_service = main.razorpay_service
        self.original_ai_buyer = main.ai_buyer
        main.database = self.database
        main.ai_buyer = MagicMock()
        main.ai_buyer.propose_transaction.return_value = ProposedTransaction(
            user_id="ai-buyer-user",
            items=[
                CartItem(
                    product_name="Black Running Shoes",
                    unit_price=2799,
                    currency="INR",
                    category="footwear",
                    color="black",
                    size="9",
                )
            ],
            total_amount=2799,
            currency="INR",
            merchant_id="merchant-demo",
        )
        self.razorpay_client = MagicMock()
        main.razorpay_service = RazorpayService(
            key_id="test_key_id",
            key_secret="test_key_secret",
            client=self.razorpay_client,
        )
        self.client = TestClient(main.app)

    def tearDown(self):
        self.database.close()
        main.database = self.original_database
        main.razorpay_service = self.original_service
        main.ai_buyer = self.original_ai_buyer
        self.temp_dir.cleanup()

    def test_ask_demo_is_generated_by_policy_threshold(self):
        response = self.client.post("/demo/ask")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["policy_decision"]["decision"], "ASK")
        self.assertEqual(payload["policy_decision"]["evaluated_amount"], 279900)
        self.assertEqual(payload["user_intent"]["review_threshold"], 2500)
        self.assertTrue(payload["policy_decision"]["requires_human_confirmation"])
        main.ai_buyer.propose_transaction.assert_called_once_with(ANY, [main.AI_BUYER_CATALOG[0]])

    def test_ask_cannot_create_order_without_approval(self):
        payload = self.client.post("/demo/ask").json()
        transaction_id = payload["policy_decision"]["transaction_id"]

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())
        self.razorpay_client.order.create.assert_not_called()

    def test_approve_persists_and_allows_test_order(self):
        payload = self.client.post("/demo/ask").json()
        transaction_id = payload["policy_decision"]["transaction_id"]
        approval = self.client.post(
            "/approval",
            json={
                "transaction_id": transaction_id,
                "original_decision": "ASK",
                "human_decision": "APPROVE",
                "reviewer": "exam-reviewer",
            },
        )
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(self.database.get_latest_approval_for_transaction(transaction_id)["human_decision"], "APPROVE")

        self.razorpay_client.order.create.return_value = {
            "id": "order_ask_approved",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
        }
        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "created")

    def test_reject_persists_and_prevents_order(self):
        payload = self.client.post("/demo/ask").json()
        transaction_id = payload["policy_decision"]["transaction_id"]
        rejection = self.client.post(
            "/approval",
            json={
                "transaction_id": transaction_id,
                "original_decision": "ASK",
                "human_decision": "REJECT",
                "reviewer": "exam-reviewer",
            },
        )
        self.assertEqual(rejection.status_code, 200)
        self.assertEqual(self.database.get_latest_approval_for_transaction(transaction_id)["human_decision"], "REJECT")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())
        self.razorpay_client.order.create.assert_not_called()

    def test_existing_allow_and_block_payment_gates_remain(self):
        allow_id = "ask-demo-allow-check"
        block_id = "ask-demo-block-check"
        for transaction_id, decision, expected_status in [
            (allow_id, "ALLOW", 200),
            (block_id, "BLOCK", 403),
        ]:
            self.database.log_decision(
                transaction_id=transaction_id,
                user_id="test-user",
                decision=decision,
                reason="test decision",
                risk_score=10,
                total_amount=2799,
                currency="INR",
            )
            if decision == "ALLOW":
                self.razorpay_client.order.create.return_value = {
                    "id": "order_allow",
                    "amount": 279900,
                    "currency": "INR",
                    "status": "created",
                }
            response = self.client.post(f"/transactions/{transaction_id}/order")
            self.assertEqual(response.status_code, expected_status)


if __name__ == "__main__":
    unittest.main()