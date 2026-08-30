import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

import backend.main as main
from backend.database import AuditDatabase
from backend.models import ApprovalRecord


class TestApprovalWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "approvals.db"
        self.database = AuditDatabase(self.db_path)
        self.original_database = main.database
        main.database = self.database

    def tearDown(self):
        self.database.close()
        main.database = self.original_database
        self.temp_dir.cleanup()

    def test_valid_approve(self):
        payload = main.record_human_approval(
            ApprovalRecord(
                transaction_id="txn-approve-1",
                original_decision="ASK",
                human_decision="APPROVE",
                reviewer="human-reviewer",
                note="Approved after review",
            )
        )

        self.assertEqual(payload["status"], "recorded")
        self.assertEqual(payload["human_decision"], "APPROVE")
        self.assertEqual(payload["transaction_id"], "txn-approve-1")
        records = self.database.list_approvals()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["human_decision"], "APPROVE")

    def test_valid_reject(self):
        payload = main.record_human_approval(
            ApprovalRecord(
                transaction_id="txn-reject-1",
                original_decision="ASK",
                human_decision="REJECT",
                reviewer="human-reviewer",
                note="Rejected after review",
            )
        )

        self.assertEqual(payload["status"], "recorded")
        self.assertEqual(payload["human_decision"], "REJECT")

    def test_invalid_original_decision(self):
        with self.assertRaises(ValueError):
            ApprovalRecord(
                transaction_id="txn-invalid-original",
                original_decision="ALLOW",
                human_decision="APPROVE",
                reviewer="human-reviewer",
            )

    def test_invalid_human_decision(self):
        with self.assertRaises(ValueError):
            ApprovalRecord(
                transaction_id="txn-invalid-human",
                original_decision="ASK",
                human_decision="PENDING",
                reviewer="human-reviewer",
            )

    def test_missing_transaction_id(self):
        with self.assertRaises(ValueError):
            ApprovalRecord(
                original_decision="ASK",
                human_decision="APPROVE",
                reviewer="human-reviewer",
            )

    def test_missing_reviewer(self):
        with self.assertRaises(ValueError):
            ApprovalRecord(
                transaction_id="txn-missing-reviewer",
                original_decision="ASK",
                human_decision="APPROVE",
            )


if __name__ == "__main__":
    unittest.main()
