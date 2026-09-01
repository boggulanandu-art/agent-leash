import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as main
from backend.database import AuditDatabase


class TestAuditTrail(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = AuditDatabase(Path(self.temp_dir.name) / "audit.db")
        self.original_database = main.database
        main.database = self.database
        self.client = TestClient(main.app)

    def tearDown(self):
        self.database.close()
        main.database = self.original_database
        self.temp_dir.cleanup()

    def record_decision(self, transaction_id, decision):
        self.database.log_decision(
            transaction_id=transaction_id,
            user_id="audit-user",
            decision=decision,
            reason=f"{decision} policy reason",
            risk_score={"ALLOW": 10, "ASK": 45, "BLOCK": 90}[decision],
            total_amount=2799,
            currency="INR",
        )

    def test_empty_audit_log_returns_empty_list(self):
        response = self.client.get("/audit")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_endpoint_returns_persisted_decisions_newest_first(self):
        self.record_decision("allow-1", "ALLOW")
        self.record_decision("block-1", "BLOCK")
        self.record_decision("ask-1", "ASK")

        records = self.client.get("/audit").json()

        self.assertEqual([record["transaction_id"] for record in records], ["ask-1", "block-1", "allow-1"])
        self.assertEqual([record["decision"] for record in records], ["ASK", "BLOCK", "ALLOW"])

    def test_approval_and_payment_information_is_joined(self):
        self.record_decision("ask-approved", "ASK")
        self.database.record_approval(
            transaction_id="ask-approved",
            original_decision="ASK",
            human_decision="APPROVE",
            reviewer="reviewer-1",
            note="Reviewed",
        )
        self.database.save_razorpay_order(
            transaction_id="ask-approved",
            razorpay_order_id="order-1",
            amount=279900,
            currency="INR",
            status="created",
        )

        record = self.client.get("/audit").json()[0]

        self.assertEqual(record["human_decision"], "APPROVE")
        self.assertEqual(record["reviewer"], "reviewer-1")
        self.assertEqual(record["approval_note"], "Reviewed")
        self.assertEqual(record["razorpay_order_id"], "order-1")
        self.assertEqual(record["payment_status"], "created")

    def test_unapproved_ask_does_not_report_created_payment_order(self):
        self.record_decision("ask-pending", "ASK")
        self.database.conn.execute(
            "INSERT INTO razorpay_orders (transaction_id, razorpay_order_id, amount, currency, status) VALUES (?, ?, ?, ?, ?)",
            ("ask-pending", "order-invalid", 279900, "INR", "created"),
        )
        self.database.conn.commit()

        record = self.client.get("/audit").json()[0]

        self.assertEqual(record["decision"], "ASK")
        self.assertIsNone(record["human_decision"])
        self.assertIsNone(record["razorpay_order_id"])
        self.assertIsNone(record["payment_status"])


if __name__ == "__main__":
    unittest.main()