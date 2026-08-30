from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "agent_leash.db"


class AuditDatabase:
    """Simple SQLite-backed audit log manager."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.init_db()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                user_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                original_decision TEXT NOT NULL,
                human_decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS razorpay_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                razorpay_order_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        try:
            self.conn.execute("ALTER TABLE audit_logs ADD COLUMN transaction_id TEXT")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def log_decision(
        self,
        user_id: str,
        decision: str,
        reason: str,
        risk_score: int,
        total_amount: float,
        currency: str,
        transaction_id: str | None = None,
    ) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO audit_logs (transaction_id, user_id, decision, reason, risk_score, total_amount, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (transaction_id, user_id, decision, reason, risk_score, total_amount, currency),
        )
        self.conn.commit()
        record_id = cursor.lastrowid

        return {
            "id": record_id,
            "transaction_id": transaction_id,
            "user_id": user_id,
            "decision": decision,
            "reason": reason,
            "risk_score": risk_score,
            "total_amount": total_amount,
            "currency": currency,
        }

    def get_latest_decision_for_transaction(self, transaction_id: str) -> dict | None:
        row = self.conn.execute(
            """
            SELECT transaction_id, user_id, decision, reason, risk_score, total_amount, currency, created_at
            FROM audit_logs
            WHERE transaction_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (transaction_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "transaction_id": row[0],
            "user_id": row[1],
            "decision": row[2],
            "reason": row[3],
            "risk_score": row[4],
            "total_amount": row[5],
            "currency": row[6],
            "created_at": row[7],
        }

    def get_latest_approval_for_transaction(self, transaction_id: str) -> dict | None:
        row = self.conn.execute(
            """
            SELECT transaction_id, original_decision, human_decision, reviewer, note, timestamp
            FROM approvals
            WHERE transaction_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (transaction_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "transaction_id": row[0],
            "original_decision": row[1],
            "human_decision": row[2],
            "reviewer": row[3],
            "note": row[4],
            "timestamp": row[5],
        }

    def save_razorpay_order(
        self,
        transaction_id: str,
        razorpay_order_id: str,
        amount: int,
        currency: str,
        status: str,
    ) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO razorpay_orders (transaction_id, razorpay_order_id, amount, currency, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_id, razorpay_order_id, amount, currency, status),
        )
        self.conn.commit()
        record_id = cursor.lastrowid
        row = self.conn.execute(
            "SELECT transaction_id, razorpay_order_id, amount, currency, status, timestamp FROM razorpay_orders WHERE id = ?",
            (record_id,),
        ).fetchone()
        return {
            "transaction_id": row[0],
            "razorpay_order_id": row[1],
            "amount": row[2],
            "currency": row[3],
            "status": row[4],
            "timestamp": row[5],
        }

    def record_approval(self, transaction_id: str, original_decision: str, human_decision: str, reviewer: str, note: str | None = None) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO approvals (transaction_id, original_decision, human_decision, reviewer, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_id, original_decision, human_decision, reviewer, note),
        )
        self.conn.commit()
        record_id = cursor.lastrowid
        timestamp = self.conn.execute(
            "SELECT timestamp FROM approvals WHERE id = ?",
            (record_id,),
        ).fetchone()[0]

        return {
            "id": record_id,
            "transaction_id": transaction_id,
            "original_decision": original_decision,
            "human_decision": human_decision,
            "reviewer": reviewer,
            "note": note,
            "timestamp": timestamp,
        }

    def list_approvals(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT transaction_id, original_decision, human_decision, reviewer, note, timestamp
            FROM approvals
            ORDER BY id DESC
            """
        ).fetchall()

        return [
            {
                "transaction_id": row[0],
                "original_decision": row[1],
                "human_decision": row[2],
                "reviewer": row[3],
                "note": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]
