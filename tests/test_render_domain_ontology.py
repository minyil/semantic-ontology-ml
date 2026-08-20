from __future__ import annotations

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_domain_ontology.py"
SPEC = importlib.util.spec_from_file_location("render_domain_ontology", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


MODEL = {
    "contract_version": "1.0",
    "domain_model": {
        "name": "Synthetic process anomaly",
        "description": "A test model with process and evidence concepts.",
        "analysis_goal": "Explain the event without promoting candidates to fact.",
        "focus_concept": "event",
    },
    "concepts": [
        {
            "id": "airflow",
            "name": "System airflow",
            "kind": "control_variable",
            "description": "Measured process airflow.",
            "evidence": "observed",
            "source_fields": ["airflow_tag"],
            "source_refs": ["dataset"],
            "details": ["Changed at event onset"],
        },
        {
            "id": "draft",
            "name": "Draft and pressure balance",
            "kind": "mechanism",
            "description": "Candidate mechanism connecting flow and pressure.",
            "evidence": "inferred",
            "confidence": 0.8,
            "source_refs": ["domain_doc"],
        },
        {
            "id": "event",
            "name": "07:48 multivariate deviation",
            "kind": "event",
            "description": "Observed deviation across multiple measurements.",
            "evidence": "observed",
            "source_refs": ["dataset"],
            "details": ["Airflow changed first", "Gas indicator followed after 45 seconds"],
        },
        {
            "id": "risk",
            "name": "Safety review state",
            "kind": "risk",
            "description": "Candidate operational risk requiring review.",
            "evidence": "proposed",
            "confidence": 0.65,
            "source_refs": ["domain_doc"],
        },
        {
            "id": "goal",
            "name": "Confirm source and safe recovery",
            "kind": "goal",
            "description": "Decision objective.",
            "evidence": "proposed",
            "confidence": 0.9,
            "source_refs": ["analysis"],
        },
    ],
    "relationships": [
        {
            "id": "airflow_indicates_draft",
            "source": "airflow",
            "target": "draft",
            "predicate": "indicates",
            "label": "indicates operating state",
            "evidence": "inferred",
            "confidence": 0.8,
            "source_refs": ["domain_doc"],
        },
        {
            "id": "airflow_precedes_event",
            "source": "airflow",
            "target": "event",
            "predicate": "precedes",
            "label": "changed before",
            "evidence": "observed",
            "source_refs": ["dataset"],
            "temporal_lag": "PT0S",
        },
        {
            "id": "draft_may_contribute",
            "source": "draft",
            "target": "event",
            "predicate": "may_cause",
            "label": "candidate contributor",
            "evidence": "proposed",
            "confidence": 0.55,
            "source_refs": ["domain_doc"],
            "plant_confirmed": False,
        },
        {
            "id": "event_requires_review",
            "source": "event",
            "target": "risk",
            "predicate": "requires_validation",
            "label": "requires safety review",
            "evidence": "inferred",
            "confidence": 0.8,
            "source_refs": ["domain_doc"],
        },
        {
            "id": "risk_supports_goal",
            "source": "risk",
            "target": "goal",
            "predicate": "supports",
            "label": "provides risk evidence",
            "evidence": "proposed",
            "confidence": 0.85,
            "source_refs": ["analysis"],
        },
    ],
    "evidence_sources": [
        {
            "id": "dataset",
            "kind": "dataset",
            "authority": "observed",
            "locator": "synthetic.csv",
            "description": "Synthetic test data",
        },
        {
            "id": "domain_doc",
            "kind": "domain_document",
            "authority": "general_domain",
            "locator": "synthetic-manual",
            "description": "Synthetic domain reference",
        },
        {
            "id": "analysis",
            "kind": "analysis",
            "authority": "proposed",
            "locator": "analysis-spec",
            "description": "Synthetic analysis goal",
        },
    ],
    "unresolved_questions": ["Which equipment boundary applies to airflow_tag?"],
}


class DomainOntologyTests(unittest.TestCase):
    def test_valid_model_has_no_validation_findings(self) -> None:
        report = MODULE.profile(MODEL, focus="event")
        self.assertEqual([], report["validation"]["errors"])
        self.assertEqual([], report["validation"]["warnings"])
        self.assertEqual(5, report["summary"]["concept_count"])
        self.assertEqual(5, report["summary"]["relationship_count"])

    def test_non_declared_causal_claim_is_rejected(self) -> None:
        model = deepcopy(MODEL)
        model["relationships"][2]["predicate"] = "causes"
        report = MODULE.profile(model)
        self.assertTrue(
            any("without declared evidence" in item for item in report["validation"]["errors"])
        )

    def test_observed_relationship_requires_source_reference(self) -> None:
        model = deepcopy(MODEL)
        model["relationships"][1]["source_refs"] = []
        report = MODULE.profile(model)
        self.assertTrue(
            any("requires source_refs" in item for item in report["validation"]["errors"])
        )

    def test_svg_contains_lanes_focus_details_and_evidence_styles(self) -> None:
        report = MODULE.profile(MODEL, focus="event")
        output = MODULE.svg(MODEL, report, focus_id="event")
        self.assertIn("Inputs &amp; controls", output)
        self.assertIn("07:48 multivariate", output)
        self.assertIn("deviation", output)
        self.assertIn("SELECTED ONTOLOGY NODE", output)
        self.assertIn('stroke-dasharray="8 7"', output)
        self.assertIn('stroke-dasharray="3 7"', output)
        self.assertIn('marker-end="url(#observed)"', output)

    def test_mermaid_and_markdown_are_auditable(self) -> None:
        report = MODULE.profile(MODEL)
        mermaid = MODULE.mermaid(MODEL, report)
        review = MODULE.markdown(MODEL, report)
        self.assertIn("subgraph mechanisms", mermaid)
        self.assertIn("candidate contributor [proposed]", mermaid)
        self.assertIn("linkStyle", mermaid)
        self.assertIn("## Relationships", review)
        self.assertIn("Which equipment boundary applies", review)
        self.assertIn("Observed temporal order", review)


if __name__ == "__main__":
    unittest.main()
