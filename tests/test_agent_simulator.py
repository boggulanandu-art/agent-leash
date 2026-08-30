import unittest

from backend.agent_simulator import SimulatedBuyer
from backend.main import demo_scenario_evaluation, demo_scenarios
from backend.models import ProposedTransaction, UserIntent


class TestSimulatedBuyer(unittest.TestCase):
    def setUp(self):
        self.intent = UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=5000,
            session_limit=5000,
            review_threshold=2500,
        )

    def test_safe_purchase_produces_valid_transaction(self):
        buyer = SimulatedBuyer(self.intent)
        tx = buyer.generate_transaction("SAFE_PURCHASE")

        self.assertIsInstance(tx, ProposedTransaction)
        self.assertEqual(tx.total_amount, 2799)
        self.assertFalse(any(item.is_addon for item in tx.items))
        self.assertFalse(any(item.is_subscription for item in tx.items))

    def test_unauthorized_addon_scenario_contains_addon(self):
        buyer = SimulatedBuyer(self.intent)
        tx = buyer.generate_transaction("UNAUTHORIZED_ADDON")

        self.assertTrue(any(item.is_addon for item in tx.items))
        self.assertGreater(tx.total_amount, self.intent.max_amount)

    def test_subscription_scenario_contains_subscription(self):
        buyer = SimulatedBuyer(self.intent)
        tx = buyer.generate_transaction("UNAUTHORIZED_SUBSCRIPTION")

        self.assertTrue(any(item.is_subscription for item in tx.items))

    def test_over_limit_scenario_exceeds_limit(self):
        buyer = SimulatedBuyer(self.intent)
        tx = buyer.generate_transaction("OVER_LIMIT")

        self.assertGreater(tx.total_amount, self.intent.max_amount)

    def test_aggregate_scenario_produces_multiple_transactions(self):
        buyer = SimulatedBuyer(self.intent)
        txs = buyer.generate_transactions("AGGREGATE_SPLIT")

        self.assertGreaterEqual(len(txs), 2)
        self.assertTrue(all(isinstance(tx, ProposedTransaction) for tx in txs))


class TestDemoEndpoints(unittest.TestCase):
    def test_demo_scenarios_list(self):
        payload = demo_scenarios()

        self.assertIsInstance(payload, list)
        self.assertIn("name", payload[0])
        self.assertIn("description", payload[0])
        self.assertIn("SAFE_PURCHASE", [item["name"] for item in payload])

    def test_demo_scenario_evaluation(self):
        payload = demo_scenario_evaluation("SAFE_PURCHASE")

        self.assertIn("user_intent", payload)
        self.assertIn("proposed_transaction", payload)
        self.assertIn("policy_decision", payload)
        self.assertEqual(payload["policy_decision"]["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
