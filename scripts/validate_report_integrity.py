#!/usr/bin/env python3
"""Validate finding coverage and content fidelity in localized Markdown reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EVIDENCE = {"declared", "observed", "inferred", "proposed"}
PRIORITIES = {"critical", "high", "medium", "low"}
FINDING_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]*$")
TAG_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
ANNOTATED_RE = re.compile(r"<!--\s*report-integrity:annotated\s*-->")
LANGUAGE_RE = re.compile(r"<!--\s*report-language:([^\s]+)\s*-->")
MARKER_RE = re.compile(
    r"<!--\s*finding:([A-Z][A-Z0-9_-]*)\s+(summary|detail)\s*-->"
)
TAG_RE = re.compile(
    r"<!--\s*finding-tag:([A-Z][A-Z0-9_-]*):([a-z][a-z0-9_-]*)\s*-->"
)
CONTROL_LINE_RE = re.compile(
    r"(?m)^[ \t]*<!--\s*(?:"
    r"report-integrity:annotated|"
    r"report-language:[^\s]+|"
    r"finding:[A-Z][A-Z0-9_-]*\s+(?:summary|detail)|"
    r"finding-tag:[A-Z][A-Z0-9_-]*:[a-z][a-z0-9_-]*"
    r")\s*-->[ \t]*(?:\r?\n|$)"
)
INTERNAL_MARKER_RE = re.compile(
    r"<!--\s*(?:report-integrity:|report-language:|finding:|finding-tag:)"
)
HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate localized Markdown reports against a canonical finding registry."
    )
    parser.add_argument("registry", help="Finding-registry JSON path")
    parser.add_argument("reports", nargs="+", help="One or more annotated Markdown reports")
    parser.add_argument(
        "--clean-output",
        action="append",
        default=[],
        help="Publish a marker-free report after validation; repeat once per input report",
    )
    return parser.parse_args()


def load_registry(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("the finding-registry root must be a JSON object")
    return value


def registry_findings(registry: dict[str, Any]) -> list[dict[str, Any]]:
    value = registry.get("findings")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("registry_version") != "1.0":
        errors.append("registry_version must be '1.0'")
    if not isinstance(registry.get("analysis_id"), str) or not registry["analysis_id"].strip():
        errors.append("analysis_id is required")
    raw_findings = registry.get("findings")
    if not isinstance(raw_findings, list) or not raw_findings:
        errors.append("findings must contain at least one object")
        return errors

    seen: set[str] = set()
    for index, finding in enumerate(raw_findings):
        prefix = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        finding_id = finding.get("finding_id")
        if not isinstance(finding_id, str) or not FINDING_ID_RE.fullmatch(finding_id):
            errors.append(f"{prefix}.finding_id must match {FINDING_ID_RE.pattern}")
        elif finding_id in seen:
            errors.append(f"duplicate finding_id: {finding_id}")
        else:
            seen.add(finding_id)
        if not isinstance(finding.get("category"), str) or not finding["category"].strip():
            errors.append(f"{prefix}.category is required")
        priority = finding.get("priority")
        if not isinstance(priority, str) or priority not in PRIORITIES:
            errors.append(f"{prefix}.priority must be critical, high, medium, or low")
        evidence = finding.get("evidence")
        evidence_values = [evidence] if isinstance(evidence, str) else evidence
        if (
            not isinstance(evidence_values, list)
            or not evidence_values
            or any(
                not isinstance(item, str) or item not in EVIDENCE
                for item in evidence_values
            )
            or len(evidence_values) != len(set(evidence_values))
        ):
            errors.append(
                f"{prefix}.evidence must be one evidence class or a unique non-empty list of evidence classes"
            )
        summary_required = finding.get("executive_summary_required")
        if not isinstance(summary_required, bool):
            errors.append(f"{prefix}.executive_summary_required must be boolean")
        elif priority in {"critical", "high"} and not summary_required:
            errors.append(f"{prefix} with {priority} priority must be executive-summary required")
        literals = finding.get("required_literals")
        if not isinstance(literals, list) or any(
            not isinstance(item, str) or not item for item in literals
        ):
            errors.append(f"{prefix}.required_literals must be a list of non-empty strings")
        tags = finding.get("required_tags")
        if not isinstance(tags, list) or any(
            not isinstance(item, str) or not TAG_ID_RE.fullmatch(item) for item in tags
        ):
            errors.append(
                f"{prefix}.required_tags must be a list matching {TAG_ID_RE.pattern}"
            )
        sources = finding.get("source_artifacts")
        if not isinstance(sources, list) or not sources or any(
            not isinstance(item, str) or not item.strip() for item in sources
        ):
            errors.append(f"{prefix}.source_artifacts must contain at least one path")
        limitations = finding.get("limitations")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) or not item.strip() for item in limitations
        ):
            errors.append(f"{prefix}.limitations must be a list of strings")
    return errors


def marker_blocks(text: str) -> list[tuple[str, str, str]]:
    markers = list(MARKER_RE.finditer(text))
    result: list[tuple[str, str, str]] = []
    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        heading = HEADING_RE.search(text, start, end)
        if heading:
            end = heading.start()
        result.append((marker.group(1), marker.group(2), text[start:end]))
    return result


def contains_required_literal(text: str, literal: str) -> bool:
    prefix = r"(?<![\d,.])" if literal[0].isdigit() else ""
    if literal[-1].isdigit():
        suffix = r"(?![\d,.])"
    elif literal[-1] == "%":
        suffix = r"(?![\d%])"
    else:
        suffix = ""
    return re.search(prefix + re.escape(literal) + suffix, text) is not None


def clean_report(text: str) -> str:
    cleaned = CONTROL_LINE_RE.sub("", text).lstrip("\r\n")
    if INTERNAL_MARKER_RE.search(cleaned):
        raise ValueError("clean report still contains an internal report marker")
    return cleaned


def validate_report(
    registry: dict[str, Any], text: str, report_name: str = "report"
) -> list[str]:
    errors: list[str] = []
    annotations = ANNOTATED_RE.findall(text)
    if len(annotations) != 1:
        errors.append(f"{report_name}: exactly one annotated-report marker is required")
    languages = LANGUAGE_RE.findall(text)
    if len(languages) != 1:
        errors.append(f"{report_name}: exactly one report-language marker is required")

    findings = {item["finding_id"]: item for item in registry_findings(registry)}
    blocks = marker_blocks(text)
    present = {finding_id for finding_id, _, _ in blocks}
    unknown = sorted(present - set(findings))
    missing = sorted(set(findings) - present)
    if unknown:
        errors.append(f"{report_name}: unknown finding IDs: {', '.join(unknown)}")
    if missing:
        errors.append(f"{report_name}: missing finding IDs: {', '.join(missing)}")

    report_tags = set(TAG_RE.findall(text))
    known_tags = {
        (finding_id, tag)
        for finding_id, finding in findings.items()
        for tag in finding.get("required_tags", [])
    }
    unknown_tags = sorted(report_tags - known_tags)
    missing_tags = sorted(known_tags - report_tags)
    if unknown_tags:
        rendered = ", ".join(f"{finding_id}:{tag}" for finding_id, tag in unknown_tags)
        errors.append(f"{report_name}: unknown finding tags: {rendered}")
    if missing_tags:
        rendered = ", ".join(f"{finding_id}:{tag}" for finding_id, tag in missing_tags)
        errors.append(f"{report_name}: missing finding tags: {rendered}")

    for finding_id, finding in findings.items():
        finding_blocks = [block for block in blocks if block[0] == finding_id]
        summary_blocks = [block[2] for block in finding_blocks if block[1] == "summary"]
        if finding.get("executive_summary_required") and len(summary_blocks) != 1:
            errors.append(
                f"{report_name}: {finding_id} requires exactly one summary marker; found {len(summary_blocks)}"
            )
        target_text = "\n".join(
            summary_blocks
            if finding.get("executive_summary_required")
            else [block[2] for block in finding_blocks]
        )
        for literal in finding.get("required_literals", []):
            if not contains_required_literal(target_text, literal):
                location = "summary" if finding.get("executive_summary_required") else "report"
                errors.append(
                    f"{report_name}: {finding_id} is missing required literal {literal!r} from its {location} block"
                )
    return errors


def main() -> int:
    args = parse_args()
    if args.clean_output and len(args.clean_output) != len(args.reports):
        print(
            "error: repeat --clean-output exactly once per input report",
            file=sys.stderr,
        )
        return 2
    try:
        registry_path = Path(args.registry)
        report_paths = [Path(value) for value in args.reports]
        clean_paths = [Path(value) for value in args.clean_output]
        protected_paths = {registry_path.resolve(), *(path.resolve() for path in report_paths)}
        if len({path.resolve() for path in clean_paths}) != len(clean_paths):
            raise ValueError("clean-output paths must be unique")
        if any(path.resolve() in protected_paths for path in clean_paths):
            raise ValueError("clean output must not overwrite the registry or an annotated report")

        registry = load_registry(registry_path)
        errors = validate_registry(registry)
        report_results: list[tuple[Path, str, str]] = []
        if not errors:
            for report_path in report_paths:
                text = report_path.read_text(encoding="utf-8")
                report_errors = validate_report(registry, text, str(report_path))
                errors.extend(report_errors)
                languages = LANGUAGE_RE.findall(text)
                language = languages[0] if len(languages) == 1 else "unknown"
                report_results.append((report_path, language, text))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    published: dict[Path, Path] = {}
    try:
        for (report_path, _, text), clean_path in zip(report_results, clean_paths):
            clean_path.write_text(clean_report(text), encoding="utf-8")
            published[report_path] = clean_path
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    finding_count = len(registry_findings(registry))
    for report_path, language, _ in report_results:
        suffix = f" clean_output={published[report_path]}" if report_path in published else ""
        print(
            f"OK: {report_path} language={language} findings={finding_count}{suffix}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
