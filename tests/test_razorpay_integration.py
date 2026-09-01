import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import backend.main as main
from backend.database import AuditDatabase
from backend.razorpay_service import RazorpayService


class TestRazorpayIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "razorpay.db"
        self.database = AuditDatabase(self.db_path)
        self.original_database = main.database
        self.original_service = main.razorpay_service
        main.database = self.database
        main.razorpay_service = RazorpayService(
            key_id="test_key_id",
            key_secret="test_key_secret",
            client=MagicMock(),
        )
        self.client = TestClient(main.app)

    def tearDown(self):
        self.database.close()
        main.database = self.original_database
        main.razorpay_service = self.original_service
        self.temp_dir.cleanup()

    def _record_decision(self, transaction_id: str, decision: str):
        self.database.log_decision(
            transaction_id=transaction_id,
            user_id="user-razorpay",
            decision=decision,
            reason="test decision",
            risk_score=10,
            total_amount=2799,
            currency="INR",
        )

    def _approve(self, transaction_id: str):
        self.database.record_approval(
            transaction_id=transaction_id,
            original_decision="ASK",
            human_decision="APPROVE",
            reviewer="human-reviewer",
            note="Approved for payment",
        )

    def _reject(self, transaction_id: str):
        self.database.record_approval(
            transaction_id=transaction_id,
            original_decision="ASK",
            human_decision="REJECT",
            reviewer="human-reviewer",
            note="Rejected for payment",
        )

    def test_allow_can_create_razorpay_order(self):
        transaction_id = "tx-allow"
        self._record_decision(transaction_id, "ALLOW")
        main.razorpay_service.client.order.create.return_value = {
            "id": "order_allow_123",
            "entity": "order",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
            "receipt": "txn_tx-allow",
        }

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["transaction_id"], transaction_id)
        self.assertEqual(payload["policy_decision"], "ALLOW")
        self.assertEqual(payload["status"], "created")
        self.assertEqual(payload["amount"], 2799)
        self.assertEqual(payload["currency"], "INR")

    def test_block_cannot_create_order(self):
        transaction_id = "tx-block"
        self._record_decision(transaction_id, "BLOCK")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("blocked", response.json()["detail"].lower())

    def test_ask_without_approval_cannot_create_order(self):
        transaction_id = "tx-ask-no-approval"
        self._record_decision(transaction_id, "ASK")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())

    def test_ask_approve_can_create_order(self):
        transaction_id = "tx-ask-approve"
        self._record_decision(transaction_id, "ASK")
        self._approve(transaction_id)
        main.razorpay_service.client.order.create.return_value = {
            "id": "order_allow_after_approval",
            "entity": "order",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
            "receipt": "txn_tx-ask-approve",
        }

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["policy_decision"], "ASK")
        self.assertEqual(response.json()["status"], "created")

    def test_ask_reject_cannot_create_order(self):
        transaction_id = "tx-ask-reject"
        self._record_decision(transaction_id, "ASK")
        self._reject(transaction_id)

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())

    def test_missing_razorpay_credentials_are_handled_safely(self):
        with patch.dict(os.environ, {}, clear=True):
            service = RazorpayService(key_id=None, key_secret=None)
            with self.assertRaises(ValueError):
                service.create_test_order(amount=2799, currency="INR", transaction_id="missing-creds")

    def test_amount_rupees_to_paise_conversion(self):
        service = RazorpayService(key_id="foo", key_secret="bar", client=MagicMock())
        self.assertEqual(service.rupees_to_paise(2799), 279900)
        self.assertEqual(service.rupees_to_paise("2799"), 279900)

    def test_razorpay_sdk_call_is_mocked_in_tests(self):
        transaction_id = "tx-sdk-call"
        self._record_decision(transaction_id, "ALLOW")
        main.razorpay_service.client.order.create.return_value = {
            "id": "sdk_order_1",
            "entity": "order",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
            "receipt": "txn_tx-sdk-call",
        }

        self.client.post(f"/transactions/{transaction_id}/order")

        main.razorpay_service.client.order.create.assert_called_once()

    def test_razorpay_failure_is_handled_safely(self):
        transaction_id = "tx-sdk-failure"
        self._record_decision(transaction_id, "ALLOW")
        main.razorpay_service.client.order.create.side_effect = Exception("Razorpay API failure")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 502)
        self.assertIn("razorpay", response.json()["detail"].lower())

    def test_demo_safe_purchase_persists_transaction_for_order_lookup(self):
        payload = main.demo_scenario_evaluation("SAFE_PURCHASE")
        decision = payload["policy_decision"]
        transaction_id = decision["transaction_id"]

        self.assertTrue(transaction_id)
        self.assertEqual(
            self.database.get_latest_decision_for_transaction(transaction_id)["decision"],
            "ALLOW",
        )

        main.razorpay_service.client.order.create.return_value = {
            "id": "order_demo_safe_purchase",
            "entity": "order",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
            "receipt": f"txn_{transaction_id}",
        }

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transaction_id"], transaction_id)
        self.assertEqual(response.json()["status"], "created")

    def test_ask_payment_blocked_before_approval(self):
        transaction_id = "tx-ask-pending"
        self._record_decision(transaction_id, "ASK")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())
        main.razorpay_service.client.order.create.assert_not_called()

    def test_allow_payment_allowed(self):
        transaction_id = "tx-allow-regression"
        self._record_decision(transaction_id, "ALLOW")
        main.razorpay_service.client.order.create.return_value = {
            "id": "order_allow_regression",
            "entity": "order",
            "amount": 279900,
            "currency": "INR",
            "status": "created",
            "receipt": f"txn_{transaction_id}",
        }

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["policy_decision"], "ALLOW")
        self.assertEqual(response.json()["status"], "created")
        main.razorpay_service.client.order.create.assert_called_once()

    def test_block_payment_blocked(self):
        transaction_id = "tx-block-regression"
        self._record_decision(transaction_id, "BLOCK")

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("blocked", response.json()["detail"].lower())
        main.razorpay_service.client.order.create.assert_not_called()

    def test_ask_reject_keeps_payment_blocked(self):
        transaction_id = "tx-ask-reject-regression"
        self._record_decision(transaction_id, "ASK")
        self._reject(transaction_id)

        response = self.client.post(f"/transactions/{transaction_id}/order")

        self.assertEqual(response.status_code, 403)
        self.assertIn("approval", response.json()["detail"].lower())
        main.razorpay_service.client.order.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
