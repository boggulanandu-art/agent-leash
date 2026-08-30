from __future__ import annotations

import hashlib
import json
from typing import Any, List, Optional

from .models import PolicyDecision, ProposedTransaction, UserIntent


class PolicyEngine:
    """Deterministic policy engine for merchant-side authorization checks."""

    @staticmethod
    def _to_paise(value: Any) -> Optional[int]:
        if value is None or isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            amount = float(value)
        elif isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned:
                return None
            try:
                amount = float(cleaned)
            except ValueError:
                return None
        else:
            return None

        if amount < 0:
            return None
        return int(round(amount * 100))

    @staticmethod
    def _normalize_currency(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip().upper()
        if normalized in {"INR", "₹"}:
            return "INR"
        return normalized or None

    @staticmethod
    def _build_transaction_id(user_id: str, transaction: ProposedTransaction) -> str:
        payload = {
            "user_id": user_id,
            "merchant_id": transaction.merchant_id,
            "currency": transaction.currency,
            "total_amount": transaction.total_amount,
            "notes": transaction.notes,
            "items": [
                {
                    "product_name": item.product_name,
                    "category": item.category,
                    "color": item.color,
                    "size": item.size,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "is_subscription": item.is_subscription,
                    "is_addon": item.is_addon,
                }
                for item in transaction.items
            ],
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        return digest[:16]

    def evaluate(self, user_intent: UserIntent, transaction: ProposedTransaction) -> PolicyDecision:
        """Return ALLOW, ASK, or BLOCK based on deterministic rules."""
        reasons: List[str] = []
        violated_rules: List[str] = []
        policy_id = user_intent.policy_id or "default-policy"
        transaction_id = transaction.transaction_id or self._build_transaction_id(transaction.user_id, transaction)

        evaluated_amount = self._to_paise(transaction.total_amount)
        if evaluated_amount is None:
            return PolicyDecision(
                decision="BLOCK",
                reasons=["Missing or invalid transaction amount; transaction is blocked."],
                violated_rules=["missing_amount"],
                evaluated_amount=0,
                cumulative_amount=0,
                remaining_limit=0,
                policy_id=policy_id,
                transaction_id=transaction_id,
                reason="Missing or invalid transaction amount; transaction is blocked.",
                risk_score=100,
                flags=["missing_amount"],
                requires_human_confirmation=False,
            )

        if evaluated_amount < 0:
            return PolicyDecision(
                decision="BLOCK",
                reasons=["Negative amounts are not allowed."],
                violated_rules=["negative_amount"],
                evaluated_amount=evaluated_amount,
                cumulative_amount=evaluated_amount,
                remaining_limit=0,
                policy_id=policy_id,
                transaction_id=transaction_id,
                reason="Negative amounts are not allowed.",
                risk_score=100,
                flags=["negative_amount"],
                requires_human_confirmation=False,
            )

        user_currency = self._normalize_currency(user_intent.currency)
        tx_currency = self._normalize_currency(transaction.currency)
        if user_currency and tx_currency and user_currency != tx_currency:
            violated_rules.append("currency_mismatch")
            reasons.append(f"Currency mismatch: {tx_currency} does not match {user_currency}.")

        max_amount_value = user_intent.max_amount if user_intent.max_amount is not None else user_intent.max_price
        max_amount = self._to_paise(max_amount_value) if max_amount_value is not None else None
        if max_amount is not None and evaluated_amount > max_amount:
            violated_rules.append("max_amount")
            reasons.append(f"Transaction amount exceeds the maximum authorized amount: {evaluated_amount} paise > {max_amount} paise.")

        if user_intent.allowed_merchants and transaction.merchant_id not in user_intent.allowed_merchants:
            violated_rules.append("merchant_not_allowed")
            reasons.append(f"Merchant {transaction.merchant_id} is not in the authorized list.")

        if user_intent.blocked_merchants and transaction.merchant_id in user_intent.blocked_merchants:
            violated_rules.append("merchant_blocked")
            reasons.append(f"Merchant {transaction.merchant_id} is explicitly blocked.")

        allowed_categories = {str(value).strip().lower() for value in (user_intent.allowed_categories or user_intent.categories or [])}
        for item in transaction.items:
            item_category = (item.category or "").strip().lower()
            if allowed_categories and item_category and item_category not in allowed_categories:
                violated_rules.append("category_not_allowed")
                reasons.append(f"Category '{item.category}' is not permitted for this authorization.")

            if user_intent.allowed_colors and item.color and item.color.strip().lower() not in {str(value).strip().lower() for value in user_intent.allowed_colors}:
                violated_rules.append("attribute_mismatch")
                reasons.append(f"Color '{item.color}' does not match the allowed color list.")

            if user_intent.allowed_sizes and item.size and str(item.size).strip() not in {str(value).strip() for value in user_intent.allowed_sizes}:
                violated_rules.append("attribute_mismatch")
                reasons.append(f"Size '{item.size}' does not match the allowed size list.")

            if not user_intent.allow_subscription and item.is_subscription:
                violated_rules.append("subscription_not_allowed")
                reasons.append("Subscriptions are not authorized for this transaction.")

            if not user_intent.allow_addons and item.is_addon:
                violated_rules.append("addon_not_allowed")
                reasons.append("Add-ons are not authorized for this transaction.")

        previous_amounts = [self._to_paise(value) or 0 for value in (user_intent.previous_approved_amounts or [])]
        cumulative_amount = sum(previous_amounts) + evaluated_amount

        daily_limit = self._to_paise(user_intent.daily_limit) if user_intent.daily_limit is not None else None
        session_limit = self._to_paise(user_intent.session_limit) if user_intent.session_limit is not None else None
        review_threshold = self._to_paise(user_intent.review_threshold) if user_intent.review_threshold is not None else None

        active_limits = [limit for limit in [daily_limit, session_limit] if limit is not None]
        remaining_limit = min((limit - cumulative_amount for limit in active_limits), default=0) if active_limits else 0

        if daily_limit is not None and cumulative_amount > daily_limit:
            violated_rules.append("daily_limit_exceeded")
            reasons.append(f"Daily spending limit exceeded: {cumulative_amount} paise / {daily_limit} paise.")
        if session_limit is not None and cumulative_amount > session_limit:
            violated_rules.append("session_limit_exceeded")
            reasons.append(f"Session spending limit exceeded: {cumulative_amount} paise / {session_limit} paise.")

        if review_threshold is not None and evaluated_amount > review_threshold and (max_amount is None or evaluated_amount < max_amount):
            reasons.append(f"Amount is at or above the review threshold of {review_threshold} paise; human confirmation is required.")

        if violated_rules:
            return PolicyDecision(
                decision="BLOCK",
                reasons=reasons,
                violated_rules=violated_rules,
                evaluated_amount=evaluated_amount,
                cumulative_amount=cumulative_amount,
                remaining_limit=max(remaining_limit, 0),
                policy_id=policy_id,
                transaction_id=transaction_id,
                reason="; ".join(reasons),
                risk_score=90,
                flags=["policy_violation"],
                requires_human_confirmation=False,
            )

        if review_threshold is not None and evaluated_amount > review_threshold:
            return PolicyDecision(
                decision="ASK",
                reasons=reasons + [f"Amount is at or above the review threshold of {review_threshold} paise; human confirmation is required."],
                violated_rules=[],
                evaluated_amount=evaluated_amount,
                cumulative_amount=cumulative_amount,
                remaining_limit=max(remaining_limit, 0),
                policy_id=policy_id,
                transaction_id=transaction_id,
                reason="Amount is at or above the review threshold of {review_threshold} paise; human confirmation is required.".format(review_threshold=review_threshold),
                risk_score=45,
                flags=["requires_manual_review"],
                requires_human_confirmation=True,
            )

        return PolicyDecision(
            decision="ALLOW",
            reasons=reasons or ["Transaction satisfies all mandatory policy checks."],
            violated_rules=[],
            evaluated_amount=evaluated_amount,
            cumulative_amount=cumulative_amount,
            remaining_limit=max(remaining_limit, 0),
            policy_id=policy_id,
            transaction_id=transaction_id,
            reason="Transaction satisfies all mandatory policy checks.",
            risk_score=10,
            flags=["within_policy"],
            requires_human_confirmation=False,
        )
