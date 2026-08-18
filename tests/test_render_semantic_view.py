from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_semantic_view.py"
SPEC = importlib.util.spec_from_file_location("render_semantic_view", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


VIEW = {
    "view_version": "1.0",
    "language": "zh-Hant-TW",
    "name": "Calcination process view",
    "view_type": "process",
    "question": "Which process groups may relate to free CaO?",
    "direction": "LR",
    "evidence_scope": "include_inferred",
    "nodes": [
        {
            "id": "declared_input",
            "label": "Declared input",
            "kind": "process_input",
            "evidence": "declared",
            "members": ["feed_rate"],
        },
        {
            "id": "thermal_state",
            "label": "Thermal state",
            "kind": "process_state",
            "evidence": "inferred",
            "members": [
                {
                    "name": "kiln_tail_temperature_mean",
                    "role": "measure",
                    "evidence": "inferred",
                }
            ],
        },
        {
            "id": "quality",
            "label": "Quality candidate",
            "kind": "quality",
            "evidence": "inferred",
            "members": [{"name": "free_cao", "evidence": "inferred"}],
        },
    ],
    "edges": [
        {
            "source": "declared_input",
            "target": "thermal_state",
            "relation": "candidate influence",
            "claim_type": "hypothesis",
            "evidence": "inferred",
            "directed": True,
            "causal": False,
        },
        {
            "source": "thermal_state",
            "target": "quality",
            "relation": "same-row association",
            "claim_type": "association",
            "evidence": "observed",
            "directed": False,
            "causal": False,
            "support": {
                "metric": "spearman_rho",
                "value": -0.275,
                "n": 51458,
                "scope": "positive-value sensitivity subset",
            },
        },
    ],
    "notes": ["Review with a process engineer."],
}


class SemanticViewTests(unittest.TestCase):
    def test_valid_process_view_renders_evidence_and_support(self) -> None:
        self.assertEqual([], MODULE.validate_view(VIEW))
        filtered = MODULE.filter_view(VIEW, "include_inferred")
        output = MODULE.mermaid(filtered, "LR")
        self.assertIn("flowchart LR", output)
        self.assertIn("製程輸入 [已宣告]", output)
        self.assertIn("candidate influence [推論; 假設]", output)
        self.assertIn("非因果", output)
        self.assertIn("Spearman ρ=-0.275", output)
        self.assertIn("n=51458", output)
        self.assertIn("視圖：`製程`", output)
        self.assertIn("審查事項", output)
        self.assertIn("---", output)
        self.assertIn("linkStyle 0", output)

    def test_declared_only_filters_inferred_nodes_and_edges(self) -> None:
        filtered = MODULE.filter_view(VIEW, "declared_only")
        self.assertEqual(["declared_input"], [node["id"] for node in filtered["nodes"]])
        self.assertEqual([], filtered["edges"])

    def test_observed_edge_requires_reproducible_support(self) -> None:
        invalid = {**VIEW, "edges": [{**VIEW["edges"][1], "support": {"metric": "spearman_rho"}}]}
        errors = MODULE.validate_view(invalid)
        self.assertTrue(any("support.value is required" in error for error in errors))
        self.assertTrue(any("support.n is required" in error for error in errors))
        self.assertTrue(any("support.scope is required" in error for error in errors))

    def test_inferred_edge_cannot_claim_causality(self) -> None:
        invalid_edge = {**VIEW["edges"][0], "causal": True}
        invalid = {**VIEW, "edges": [invalid_edge]}
        errors = MODULE.validate_view(invalid)
        self.assertTrue(any("cannot assert causality" in error for error in errors))

    def test_causal_boolean_and_claim_type_must_agree(self) -> None:
        declared_causal = {
            **VIEW["edges"][0],
            "evidence": "declared",
            "claim_type": "causal",
            "causal": False,
        }
        errors = MODULE.validate_view({**VIEW, "edges": [declared_causal]})
        self.assertTrue(any("claim_type causal must set causal to true" in error for error in errors))

    def test_dot_output_preserves_noncausal_and_evidence_styles(self) -> None:
        filtered = MODULE.filter_view(VIEW, "include_inferred")
        output = MODULE.dot(filtered, "TB")
        self.assertIn("rankdir=TB", output)
        self.assertIn("非因果", output)
        self.assertIn('color="#2563eb"', output)
        self.assertIn("dir=none", output)

    def test_english_override_localizes_renderer_chrome(self) -> None:
        filtered = MODULE.filter_view(VIEW, "include_inferred")
        output = MODULE.mermaid(filtered, "LR", "en")
        self.assertIn("View: `process`", output)
        self.assertIn("process_input [declared]", output)
        self.assertIn("candidate influence [inferred; hypothesis]", output)
        self.assertIn("non-causal", output)
        self.assertIn("Review notes", output)

    def test_unsupported_language_is_rejected(self) -> None:
        errors = MODULE.validate_view({**VIEW, "language": "zh-Hans-CN"})
        self.assertTrue(any("language must be zh-Hant-TW or en" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
