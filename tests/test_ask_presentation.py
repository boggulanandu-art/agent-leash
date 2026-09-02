import ast
import unittest
from pathlib import Path


class TestASKPresentation(unittest.TestCase):
    def test_policy_reason_is_rendered_once_for_ask(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        decision_source = ast.get_source_segment(source_path.read_text(encoding="utf-8"), functions["render_policy_decision"])
        review_source = ast.get_source_segment(source_path.read_text(encoding="utf-8"), functions["render_human_review"])

        self.assertEqual(decision_source.count("Policy Reasons"), 1)
        self.assertNotIn("Policy reasons", review_source)
        self.assertNotIn('st.warning("ASK', source_path.read_text(encoding="utf-8"))

    def test_payment_button_key_includes_ui_instance(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertIn('key=f"payment_{ui_instance}_{transaction_id}"', source)
        self.assertIn('render_payment_flow(tx, decision, "ai_buyer")', source)
        self.assertIn('render_payment_flow(ask_tx, ask_decision, "ask_demo")', source)
        self.assertIn('render_payment_flow(tx, decision, "scenario")', source)

    def test_evaluation_request_ids_are_stable_across_reruns(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertIn("def stable_request_id(state_key: str, logical_input=None)", source)
        self.assertIn('stable_request_id("ai_buyer_request_id", instruction)', source)
        self.assertIn('stable_request_id("ask_demo_request_id", "ASK_DEMO")', source)
        self.assertIn('f"scenario_request_id_{scenario[\'name\']}"', source)
        self.assertNotIn('"request_id": new_request_id()', source)

    def test_audit_compaction_keeps_latest_duplicate_and_distinct_transactions(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        compact_function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "compact_audit_records"
        )
        namespace = {}
        exec(compile(ast.Module(body=[compact_function], type_ignores=[]), str(source_path), "exec"), namespace)

        records = [
            {"transaction_id": "legacy", "timestamp": "newest"},
            {"transaction_id": "legacy", "timestamp": "older"},
            {"transaction_id": "new-evaluation", "timestamp": "separate"},
        ]

        compacted = namespace["compact_audit_records"](records)

        self.assertEqual(compacted, [records[0], records[2]])

    def test_current_risk_maps_latest_evaluation_decision(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        risk_function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "risk_label_for_result"
        )
        namespace = {}
        exec(compile(ast.Module(body=[risk_function], type_ignores=[]), str(source_path), "exec"), namespace)

        self.assertEqual(namespace["risk_label_for_result"](None), "AWAITING DECISION")
        self.assertEqual(namespace["risk_label_for_result"]({"decision": "ALLOW"}), "LOW RISK")
        self.assertEqual(namespace["risk_label_for_result"]({"decision": "BLOCK"}), "HIGH RISK")
        self.assertEqual(
            namespace["risk_label_for_result"]({"policy_decision": {"decision": "ASK"}}),
            "REVIEW REQUIRED",
        )
        self.assertIn("latest_evaluation_result", source)

    def test_current_risk_uses_existing_evaluation_fallbacks(self):
        source_path = Path(__file__).parent.parent / "frontend" / "app.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertIn("def latest_evaluation_result():", source)
        self.assertIn('("latest_evaluation_result", "ai_buyer_result", "ask_demo_result", "result")', source)
        self.assertIn("current_result = latest_evaluation_result()", source)
        self.assertIn("risk_label_for_result(current_result)", source)


if __name__ == "__main__":
    unittest.main()