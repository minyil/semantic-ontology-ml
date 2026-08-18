from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "profile_ontology.py"
SPEC = importlib.util.spec_from_file_location("profile_ontology", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


SNAPSHOT = {
    "semantic_model": {"name": "Orders & Customers"},
    "entity_types": [
        {
            "name": 'Order "Line"',
            "primary_key": ["order_id", "line_id"],
            "fields": [
                {"name": "order_id", "physical_type": "integer"},
                {"name": "line_id", "physical_type": "integer"},
                {"name": "customer_id", "physical_type": "string"},
                {
                    "name": "amount",
                    "physical_type": "double",
                    "roles": [{"role": "target", "evidence": "declared"}],
                },
                {
                    "name": "observed_at",
                    "physical_type": "timestamp",
                    "roles": [{"role": "observation_time", "evidence": "declared"}],
                },
            ],
        },
        {
            "name": "Customer",
            "primary_key": ["customer_id"],
            "fields": [
                {"name": "customer_id", "physical_type": "string"},
                {
                    "name": "sex",
                    "physical_type": "string",
                    "roles": [{"role": "sensitive", "evidence": "proposed"}],
                },
            ],
        },
    ],
    "relations": [
        {
            "name": "owned | by",
            "source_entity": 'Order "Line"',
            "target_entity": "Customer",
            "source_to_target": "one",
            "target_to_source": "many",
            "join": [{"source_field": "customer_id", "target_field": "customer_id"}],
            "evidence": "proposed",
        }
    ],
}


class OntologyDiagramTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = MODULE.profile(SNAPSHOT)
        self.assertEqual([], self.report["validation"]["errors"])

    def test_mermaid_compact_contains_roles_relation_and_safe_text(self) -> None:
        output = MODULE.mermaid(SNAPSHOT, self.report, detail="compact", direction="TB")
        self.assertIn("flowchart TB", output)
        self.assertIn("Order &quot;Line&quot;", output)
        self.assertIn("target: amount [declared]", output)
        self.assertIn("time: observed_at [declared]", output)
        self.assertIn("sensitive?: sex [proposed]", output)
        self.assertIn("owned &#124; by [proposed]", output)
        self.assertIn("N:1", output)
        self.assertIn("customer_id→customer_id", output)
        self.assertIn("linkStyle 0", output)

    def test_mermaid_fields_lists_types_and_markers(self) -> None:
        output = MODULE.mermaid(SNAPSHOT, self.report, detail="fields")
        self.assertIn("amount: double [target:declared]", output)
        self.assertIn("observed_at: timestamp [time:declared]", output)
        self.assertIn("sex: string [sensitive?:proposed]", output)

    def test_dot_is_dependency_free_graphviz_source(self) -> None:
        output = MODULE.dot(SNAPSHOT, self.report, detail="compact", direction="RL")
        self.assertIn("rankdir=RL", output)
        self.assertIn('Order \\"Line\\"', output)
        self.assertIn('style="dashed"', output)
        self.assertIn("N0 -> N1", output)

    def test_explicit_sensitive_role_enters_review_queue(self) -> None:
        self.assertIn(
            "Customer.sex", self.report["quality"]["sensitive_field_candidates"]
        )


if __name__ == "__main__":
    unittest.main()
