from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_report_integrity.py"
SPEC = importlib.util.spec_from_file_location("validate_report_integrity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


REGISTRY = {
    "registry_version": "1.0",
    "analysis_id": "example",
    "findings": [
        {
            "finding_id": "F001",
            "category": "data_shape",
            "priority": "high",
            "evidence": "observed",
            "executive_summary_required": True,
            "required_literals": ["80,882", "21"],
            "required_tags": ["shape-inferred"],
            "source_artifacts": ["profile.json"],
            "limitations": [],
        },
        {
            "finding_id": "F002",
            "category": "association",
            "priority": "medium",
            "evidence": "observed",
            "executive_summary_required": False,
            "required_literals": ["0.918"],
            "required_tags": ["non-causal"],
            "source_artifacts": ["correlations.csv"],
            "limitations": ["non-causal"],
        },
    ],
}

ZH_REPORT = """<!-- report-integrity:annotated -->
<!-- report-language:zh-Hant-TW -->
# 分析

## 主要發現

<!-- finding:F001 summary -->
<!-- finding-tag:F001:shape-inferred -->
1. 共 80,882 列、21 欄。

## 關聯

<!-- finding:F002 detail -->
<!-- finding-tag:F002:non-causal -->
Spearman ρ = 0.918；這是關聯，不代表因果。
"""

EN_REPORT = """<!-- report-integrity:annotated -->
<!-- report-language:en -->
# Analysis

## Main findings

<!-- finding:F001 summary -->
<!-- finding-tag:F001:shape-inferred -->
1. The dataset contains 80,882 rows and 21 columns.

## Associations

<!-- finding:F002 detail -->
<!-- finding-tag:F002:non-causal -->
Spearman rho = 0.918; this is non-causal.
"""


class ReportIntegrityTests(unittest.TestCase):
    def test_registry_and_two_languages_preserve_finding_coverage(self) -> None:
        self.assertEqual([], MODULE.validate_registry(REGISTRY))
        self.assertEqual([], MODULE.validate_report(REGISTRY, ZH_REPORT, "zh"))
        self.assertEqual([], MODULE.validate_report(REGISTRY, EN_REPORT, "en"))

    def test_clean_report_strips_only_internal_markers(self) -> None:
        annotated = ZH_REPORT + "\n<!-- reviewer-note:preserve -->\n"
        cleaned = MODULE.clean_report(annotated)
        self.assertNotIn("report-integrity", cleaned)
        self.assertNotIn("report-language", cleaned)
        self.assertNotIn("finding:F001", cleaned)
        self.assertNotIn("finding-tag:F002", cleaned)
        self.assertIn("# 分析", cleaned)
        self.assertIn("80,882 列、21 欄", cleaned)
        self.assertIn("<!-- reviewer-note:preserve -->", cleaned)

    def test_clean_report_rejects_unrecognized_internal_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "still contains an internal report marker"):
            MODULE.clean_report("<!-- finding:bad marker -->\n# 報告\n")

    def test_annotated_report_marker_is_required(self) -> None:
        report = ZH_REPORT.replace("<!-- report-integrity:annotated -->\n", "")
        errors = MODULE.validate_report(REGISTRY, report, "zh")
        self.assertTrue(any("annotated-report marker is required" in item for item in errors))

    def test_cli_publishes_clean_report_after_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "finding-registry.json"
            annotated = root / "report.annotated.md"
            clean = root / "report.md"
            registry.write_text(json.dumps(REGISTRY), encoding="utf-8")
            annotated.write_text(ZH_REPORT, encoding="utf-8")
            argv = [
                str(SCRIPT),
                str(registry),
                str(annotated),
                "--clean-output",
                str(clean),
            ]

            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(0, MODULE.main())

            cleaned = clean.read_text(encoding="utf-8")
            self.assertTrue(cleaned.startswith("# 分析"))
            self.assertNotRegex(cleaned, MODULE.INTERNAL_MARKER_RE)

    def test_cli_does_not_publish_when_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "finding-registry.json"
            annotated = root / "report.annotated.md"
            clean = root / "report.md"
            registry.write_text(json.dumps(REGISTRY), encoding="utf-8")
            annotated.write_text(ZH_REPORT.replace("80,882", "很多"), encoding="utf-8")
            argv = [
                str(SCRIPT),
                str(registry),
                str(annotated),
                "--clean-output",
                str(clean),
            ]

            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(2, MODULE.main())

            self.assertFalse(clean.exists())

    def test_cli_rejects_overwriting_annotated_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "finding-registry.json"
            annotated = root / "report.annotated.md"
            registry.write_text(json.dumps(REGISTRY), encoding="utf-8")
            annotated.write_text(ZH_REPORT, encoding="utf-8")
            argv = [
                str(SCRIPT),
                str(registry),
                str(annotated),
                "--clean-output",
                str(annotated),
            ]

            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(2, MODULE.main())

            self.assertEqual(ZH_REPORT, annotated.read_text(encoding="utf-8"))

    def test_high_priority_finding_must_be_summary_required(self) -> None:
        invalid = {
            **REGISTRY,
            "findings": [
                {**REGISTRY["findings"][0], "executive_summary_required": False}
            ],
        }
        errors = MODULE.validate_registry(invalid)
        self.assertTrue(any("must be executive-summary required" in item for item in errors))

    def test_missing_summary_marker_is_rejected(self) -> None:
        report = ZH_REPORT.replace("finding:F001 summary", "finding:F001 detail")
        errors = MODULE.validate_report(REGISTRY, report, "zh")
        self.assertTrue(any("requires exactly one summary marker" in item for item in errors))

    def test_missing_required_literal_is_rejected(self) -> None:
        report = ZH_REPORT.replace("80,882", "很多")
        errors = MODULE.validate_report(REGISTRY, report, "zh")
        self.assertTrue(any("missing required literal '80,882'" in item for item in errors))

    def test_short_number_does_not_match_inside_date_or_larger_number(self) -> None:
        self.assertFalse(MODULE.contains_required_literal("日期為 2024-03-10", "20"))
        self.assertFalse(MODULE.contains_required_literal("共有 27 筆", "7"))
        self.assertTrue(MODULE.contains_required_literal("共有 20 筆", "20"))

    def test_missing_semantic_qualifier_tag_is_rejected(self) -> None:
        report = ZH_REPORT.replace("<!-- finding-tag:F002:non-causal -->\n", "")
        errors = MODULE.validate_report(REGISTRY, report, "zh")
        self.assertTrue(any("missing finding tags: F002:non-causal" in item for item in errors))

    def test_missing_and_unknown_finding_ids_are_rejected(self) -> None:
        report = ZH_REPORT.replace("finding:F002 detail", "finding:F999 detail")
        errors = MODULE.validate_report(REGISTRY, report, "zh")
        self.assertTrue(any("unknown finding IDs: F999" in item for item in errors))
        self.assertTrue(any("missing finding IDs: F002" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
