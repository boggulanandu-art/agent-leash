import unittest

from backend.models import CartItem, PolicyDecision, ProposedTransaction, UserIntent
from backend.policy_engine import PolicyEngine


class TestPolicyEngine(unittest.TestCase):
    def make_intent(self, **overrides):
        base = {
            "instruction": "Buy black running shoes, size 9, under ₹3000.",
            "product_name": "running shoes",
            "max_amount": 3000,
            "currency": "INR",
            "allowed_categories": ["footwear"],
            "allowed_merchants": [],
            "allowed_colors": ["black"],
            "allowed_sizes": ["9"],
            "allow_subscription": False,
            "allow_addons": False,
            "daily_limit": 5000,
            "session_limit": 5000,
            "review_threshold": 2500,
            "previous_approved_amounts": [],
        }
        base.update(overrides)
        return UserIntent(**base)

    def make_transaction(self, **overrides):
        base = {
            "user_id": "user-123",
            "items": [
                CartItem(
                    product_name="Black Running Shoes",
                    quantity=1,
                    unit_price=2500,
                    currency="INR",
                    category="footwear",
                    color="black",
                    size="9",
                    is_subscription=False,
                    is_addon=False,
                )
            ],
            "total_amount": 2500,
            "currency": "INR",
            "merchant_id": "merchant-1",
            "notes": "standard purchase",
        }
        base.update(overrides)
        return ProposedTransaction(**base)

    def test_valid_transaction_allows(self):
        engine = PolicyEngine()
        decision = engine.evaluate(self.make_intent(), self.make_transaction())
        self.assertIsInstance(decision, PolicyDecision)
        self.assertEqual(decision.decision, "ALLOW")

    def test_amount_above_limit_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(max_amount=3000),
            self.make_transaction(total_amount=3500),
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("max_amount", decision.violated_rules)

    def test_wrong_category_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(allowed_categories=["footwear"]),
            self.make_transaction(
                items=[
                    CartItem(
                        product_name="Wireless Charger",
                        quantity=1,
                        unit_price=900,
                        currency="INR",
                        category="electronics",
                        color="black",
                        size="9",
                        is_subscription=False,
                        is_addon=False,
                    )
                ],
                total_amount=900,
            ),
        )
        self.assertEqual(decision.decision, "BLOCK")

    def test_unauthorized_subscription_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(),
            self.make_transaction(
                items=[
                    CartItem(
                        product_name="Premium Plan",
                        quantity=1,
                        unit_price=2500,
                        currency="INR",
                        category="subscription",
                        color="black",
                        size="9",
                        is_subscription=True,
                        is_addon=False,
                    )
                ],
                total_amount=2500,
            ),
        )
        self.assertEqual(decision.decision, "BLOCK")

    def test_unauthorized_addon_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(),
            self.make_transaction(
                items=[
                    CartItem(
                        product_name="Black Running Shoes",
                        quantity=1,
                        unit_price=2200,
                        currency="INR",
                        category="footwear",
                        color="black",
                        size="9",
                        is_subscription=False,
                        is_addon=True,
                    )
                ],
                total_amount=2200,
            ),
        )
        self.assertEqual(decision.decision, "BLOCK")

    def test_valid_transaction_requiring_confirmation_asks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(review_threshold=2000),
            self.make_transaction(total_amount=2200),
        )
        self.assertEqual(decision.decision, "ASK")

    def test_aggregate_limit_exceeded_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(daily_limit=5000, previous_approved_amounts=[1800, 1200]),
            self.make_transaction(total_amount=2500),
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertGreater(decision.cumulative_amount, 5000)

    def test_transaction_splitting_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(max_amount=3000, daily_limit=3000, previous_approved_amounts=[1800]),
            self.make_transaction(total_amount=1700),
        )
        self.assertEqual(decision.decision, "BLOCK")

    def test_missing_amount_blocks(self):
        engine = PolicyEngine()
        tx = ProposedTransaction(
            user_id="user-123",
            items=[CartItem(product_name="No price item", quantity=1, unit_price=0, currency="INR", category="footwear")],
            total_amount=None,
            currency="INR",
            merchant_id="merchant-1",
        )
        decision = engine.evaluate(self.make_intent(), tx)
        self.assertEqual(decision.decision, "BLOCK")

    def test_negative_amount_blocks(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            self.make_intent(),
            self.make_transaction(total_amount=-10),
        )
        self.assertEqual(decision.decision, "BLOCK")


if __name__ == "__main__":
    unittest.main()
