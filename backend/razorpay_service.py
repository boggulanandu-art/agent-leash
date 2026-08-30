from __future__ import annotations

import os
from typing import Any, Dict, Optional

import razorpay
from dotenv import load_dotenv

load_dotenv()


class RazorpayService:
    """Create Razorpay test-mode orders without exposing secrets to the frontend."""

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, client: Optional[Any] = None):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.client = client or razorpay.Client(auth=(self.key_id, self.key_secret))

    @staticmethod
    def rupees_to_paise(amount: float | int | str) -> int:
        value = float(amount)
        return int(round(value * 100))

    @staticmethod
    def _safe_receipt(transaction_id: Optional[str]) -> str:
        raw = (transaction_id or "txn").strip()
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)
        if not safe:
            safe = "txn"
        return safe[:40]

    def create_test_order(self, amount: float, currency: str = "INR", transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a real Razorpay TEST order through the official SDK."""
        if not self.key_id or not self.key_secret:
            raise ValueError("Razorpay credentials are missing. Configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the backend environment.")

        amount_paise = self.rupees_to_paise(amount)
        order_payload = {
            "amount": int(amount_paise),
            "currency": (currency or "INR").upper(),
            "receipt": self._safe_receipt(transaction_id),
            "notes": {"transaction_id": transaction_id or "unknown", "mode": "test"},
        }

        try:
            response = self.client.order.create(data=order_payload)
        except Exception as exc:
            raise RuntimeError(f"Razorpay order creation failed: {exc}") from exc

        amount_from_response = int(response.get("amount", amount_paise))
        return {
            "id": response.get("id"),
            "entity": response.get("entity"),
            "amount": amount_from_response,
            "currency": str(response.get("currency") or "INR").upper(),
            "status": response.get("status", "created"),
            "receipt": response.get("receipt") or order_payload["receipt"],
            "amount_rupees": int(amount_from_response / 100),
            "razorpay_order_id": response.get("id"),
        }
