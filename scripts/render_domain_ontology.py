#!/usr/bin/env python3
"""Validate and render an evidence-labeled domain knowledge ontology."""

from __future__ import annotations

import argparse
import html
import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any


EVIDENCE_CLASSES = ("declared", "observed", "inferred", "proposed")
CONCEPT_KINDS = (
    "control_variable",
    "unmeasured_action",
    "mechanism",
    "process_state",
    "measurement",
    "constraint",
    "event",
    "risk",
    "data_quality",
    "action",
    "goal",
)
LANES = ("inputs", "mechanisms", "observations", "decisions")
LANE_LABELS = {
    "inputs": "Inputs & controls",
    "mechanisms": "Mechanisms",
    "observations": "States & observations",
    "decisions": "Events, risks & decisions",
}
DEFAULT_LANE = {
    "control_variable": "inputs",
    "unmeasured_action": "inputs",
    "mechanism": "mechanisms",
    "process_state": "observations",
    "measurement": "observations",
    "constraint": "observations",
    "event": "decisions",
    "risk": "decisions",
    "data_quality": "decisions",
    "action": "decisions",
    "goal": "decisions",
}
KIND_STYLE = {
    "control_variable": ("#dceaff", "#5b9cff", "#17324d"),
    "unmeasured_action": ("#fff1cc", "#e7a817", "#6f4a00"),
    "mechanism": ("#d9faf3", "#17b99e", "#124d45"),
    "process_state": ("#dcfce7", "#39c86b", "#17472a"),
    "measurement": ("#dcfce7", "#39c86b", "#17472a"),
    "constraint": ("#e8f5e9", "#16a34a", "#14532d"),
    "event": ("#fff3d6", "#cc7a00", "#6f3d00"),
    "risk": ("#ffe3e3", "#ef6262", "#991b1b"),
    "data_quality": ("#ffe3e3", "#ef6262", "#991b1b"),
    "action": ("#ede9fe", "#8b5cf6", "#4c1d95"),
    "goal": ("#0f766e", "#0f766e", "#ffffff"),
}
EVIDENCE_STYLE = {
    "declared": ("#16a34a", "", "declared"),
    "observed": ("#0f766e", "", "observed"),
    "inferred": ("#718096", "8 7", "inferred"),
    "proposed": ("#c56a00", "3 7", "proposed"),
}
CAUSAL_PREDICATES = {"causes", "prevents"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render a domain knowledge ontology graph."
    )
    parser.add_argument("input", help="Domain ontology JSON path, or '-' for stdin")
    parser.add_argument(
        "--format", choices=("json", "markdown", "mermaid", "svg"), default="markdown"
    )
    parser.add_argument("--focus", help="Concept id to display in the SVG detail panel")
    parser.add_argument("--output", help="Write output to this path instead of stdout")
    return parser.parse_args()


def load_model(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("the domain ontology root must be a JSON object")
    return value


def object_list(value: Any, field: str, errors: list[str]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            result.append(item)
        else:
            errors.append(f"{field}[{index}] must be an object")
    return result


def string_list(value: Any, field: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        else:
            errors.append(f"{field}[{index}] must be a non-empty string")
    return result


def evidence_value(item: dict[str, Any]) -> str:
    value = item.get("evidence", "")
    if isinstance(value, dict):
        value = value.get("class", value.get("type", value.get("status", "")))
    return str(value).strip().lower()


def valid_confidence(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def profile(model: dict[str, Any], focus: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    domain_model = model.get("domain_model")
    if not isinstance(domain_model, dict):
        errors.append("domain_model must be an object")
        domain_model = {}
    model_name = domain_model.get("name")
    if not isinstance(model_name, str) or not model_name.strip():
        errors.append("domain_model.name is required")

    sources = object_list(model.get("evidence_sources"), "evidence_sources", errors)
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"evidence_sources[{index}].id is required")
            continue
        source_id = source_id.strip()
        if source_id in source_ids:
            errors.append(f"duplicate evidence source: {source_id}")
        source_ids.add(source_id)

    concepts = object_list(model.get("concepts"), "concepts", errors)
    if not concepts:
        errors.append("concepts must contain at least one concept")
    concept_ids: set[str] = set()
    lane_counts: dict[str, int] = defaultdict(int)
    evidence_counts: dict[str, int] = defaultdict(int)
    kind_counts: dict[str, int] = defaultdict(int)
    for index, concept in enumerate(concepts):
        prefix = f"concepts[{index}]"
        concept_id = concept.get("id")
        if not isinstance(concept_id, str) or not concept_id.strip():
            errors.append(f"{prefix}.id is required")
            continue
        concept_id = concept_id.strip()
        if concept_id in concept_ids:
            errors.append(f"duplicate concept: {concept_id}")
        concept_ids.add(concept_id)
        if not isinstance(concept.get("name"), str) or not concept["name"].strip():
            errors.append(f"{prefix}.name is required")
        kind = str(concept.get("kind", "")).strip().lower()
        if kind not in CONCEPT_KINDS:
            errors.append(f"{prefix}.kind must be one of {', '.join(CONCEPT_KINDS)}")
        else:
            kind_counts[kind] += 1
        lane = str(concept.get("lane", DEFAULT_LANE.get(kind, ""))).strip().lower()
        if lane not in LANES:
            errors.append(f"{prefix}.lane must be one of {', '.join(LANES)}")
        else:
            lane_counts[lane] += 1
        evidence = evidence_value(concept)
        if evidence not in EVIDENCE_CLASSES:
            errors.append(f"{prefix}.evidence must be one of {', '.join(EVIDENCE_CLASSES)}")
        else:
            evidence_counts[evidence] += 1
        if evidence in {"inferred", "proposed"} and not valid_confidence(
            concept.get("confidence")
        ):
            errors.append(f"{prefix}.confidence from 0 to 1 is required for {evidence}")
        refs = string_list(concept.get("source_refs"), f"{prefix}.source_refs", errors)
        if evidence in {"declared", "observed"} and not refs:
            warnings.append(f"{concept_id} has {evidence} evidence but no source_refs")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{prefix}.source_refs references unknown source {ref!r}")

    relationships = object_list(model.get("relationships"), "relationships", errors)
    relationship_ids: set[str] = set()
    predicate_counts: dict[str, int] = defaultdict(int)
    relationship_evidence_counts: dict[str, int] = defaultdict(int)
    for index, relation in enumerate(relationships):
        prefix = f"relationships[{index}]"
        relation_id = relation.get("id")
        if not isinstance(relation_id, str) or not relation_id.strip():
            errors.append(f"{prefix}.id is required")
            relation_id = f"<relationship-{index}>"
        else:
            relation_id = relation_id.strip()
            if relation_id in relationship_ids:
                errors.append(f"duplicate relationship: {relation_id}")
            relationship_ids.add(relation_id)
        source = relation.get("source")
        target = relation.get("target")
        if source not in concept_ids:
            errors.append(f"{relation_id}.source references unknown concept {source!r}")
        if target not in concept_ids:
            errors.append(f"{relation_id}.target references unknown concept {target!r}")
        predicate = str(relation.get("predicate", "")).strip().lower()
        if not predicate:
            errors.append(f"{relation_id}.predicate is required")
        else:
            predicate_counts[predicate] += 1
        evidence = evidence_value(relation)
        if evidence not in EVIDENCE_CLASSES:
            errors.append(
                f"{relation_id}.evidence must be one of {', '.join(EVIDENCE_CLASSES)}"
            )
        else:
            relationship_evidence_counts[evidence] += 1
        if evidence in {"inferred", "proposed"} and not valid_confidence(
            relation.get("confidence")
        ):
            errors.append(f"{relation_id}.confidence from 0 to 1 is required for {evidence}")
        refs = string_list(relation.get("source_refs"), f"{prefix}.source_refs", errors)
        if evidence in {"declared", "observed"} and not refs:
            errors.append(f"{relation_id} requires source_refs for {evidence} evidence")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{prefix}.source_refs references unknown source {ref!r}")
        if predicate in CAUSAL_PREDICATES and evidence != "declared":
            errors.append(
                f"{relation_id} uses causal predicate {predicate!r} without declared evidence; "
                "use 'may_cause' or 'influences'"
            )
        if relation.get("plant_confirmed") is True and evidence != "declared":
            errors.append(f"{relation_id}.plant_confirmed requires declared evidence")
        lag = relation.get("temporal_lag")
        if lag is not None and (not isinstance(lag, str) or not lag.strip()):
            errors.append(f"{relation_id}.temporal_lag must be null or a non-empty string")

    questions = model.get("unresolved_questions", [])
    if not isinstance(questions, list) or any(not isinstance(item, str) for item in questions):
        errors.append("unresolved_questions must be a list of strings")
        questions = []
    if not relationships:
        warnings.append("domain ontology has no relationships")
    if focus and focus not in concept_ids:
        errors.append(f"focus references unknown concept {focus!r}")

    return {
        "domain_model": {
            "name": model_name,
            "description": domain_model.get("description"),
            "analysis_goal": domain_model.get("analysis_goal"),
            "focus_concept": domain_model.get("focus_concept"),
        },
        "summary": {
            "concept_count": len(concepts),
            "relationship_count": len(relationships),
            "evidence_source_count": len(sources),
            "unresolved_question_count": len(questions),
            "lane_counts": dict(sorted(lane_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "concept_evidence_counts": dict(sorted(evidence_counts.items())),
            "relationship_evidence_counts": dict(
                sorted(relationship_evidence_counts.items())
            ),
            "predicate_counts": dict(sorted(predicate_counts.items())),
        },
        "validation": {"errors": errors, "warnings": warnings},
        "interpretation_limits": [
            "Observed temporal order and co-occurrence do not prove causality.",
            "General domain references support inferred mechanisms, not plant-specific declared truth.",
            "Proposed causes, risks, and actions require domain-owner or source-system validation.",
        ],
    }


def concept_lane(concept: dict[str, Any]) -> str:
    kind = str(concept.get("kind", "")).strip().lower()
    return str(concept.get("lane", DEFAULT_LANE.get(kind, "inputs"))).strip().lower()


def markdown(model: dict[str, Any], report: dict[str, Any]) -> str:
    meta = report["domain_model"]
    validation = report["validation"]
    lines = [f"# {meta.get('name') or 'Domain knowledge ontology'}", ""]
    if meta.get("description"):
        lines.extend([str(meta["description"]), ""])
    if meta.get("analysis_goal"):
        lines.extend(["## Analysis goal", "", str(meta["analysis_goal"]), ""])
    lines.extend(
        [
            "## Validation",
            "",
            *([f"- ERROR: {item}" for item in validation["errors"]] or []),
            *([f"- WARNING: {item}" for item in validation["warnings"]] or []),
        ]
    )
    if not validation["errors"] and not validation["warnings"]:
        lines.append("- No structural or evidence-boundary issues detected.")
    lines.extend(
        [
            "",
            "## Concepts",
            "",
            "| Concept | Kind | Lane | Evidence | Confidence | Source fields |",
            "|---|---|---|---|---:|---|",
        ]
    )
    for concept in model.get("concepts", []):
        confidence = concept.get("confidence", "")
        fields = ", ".join(concept.get("source_fields", []))
        lines.append(
            f"| {concept.get('name', concept.get('id'))} | {concept.get('kind', '')} | "
            f"{concept_lane(concept)} | {evidence_value(concept)} | {confidence} | {fields} |"
        )
    lines.extend(
        [
            "",
            "## Relationships",
            "",
            "| Source | Predicate | Target | Evidence | Confidence | Lag | Plant confirmed |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    names = {item.get("id"): item.get("name", item.get("id")) for item in model.get("concepts", [])}
    for relation in model.get("relationships", []):
        lines.append(
            f"| {names.get(relation.get('source'), relation.get('source'))} | "
            f"{relation.get('label', relation.get('predicate', ''))} | "
            f"{names.get(relation.get('target'), relation.get('target'))} | "
            f"{evidence_value(relation)} | {relation.get('confidence', '')} | "
            f"{relation.get('temporal_lag') or ''} | "
            f"{'yes' if relation.get('plant_confirmed') is True else 'no'} |"
        )
    lines.extend(["", "## Evidence sources", ""])
    for source in model.get("evidence_sources", []):
        lines.append(
            f"- `{source.get('id')}` — {source.get('kind', 'unspecified')} / "
            f"{source.get('authority', 'unspecified')}: {source.get('description', '')} "
            f"({source.get('locator', 'no locator')})"
        )
    lines.extend(["", "## Unresolved questions", ""])
    questions = model.get("unresolved_questions", [])
    lines.extend(f"- {item}" for item in questions)
    if not questions:
        lines.append("- None recorded.")
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {item}" for item in report["interpretation_limits"])
    return "\n".join(lines) + "\n"


def mermaid_escape(value: Any) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;")


def mermaid(model: dict[str, Any], report: dict[str, Any]) -> str:
    name = report["domain_model"].get("name") or "Domain knowledge ontology"
    concepts = model.get("concepts", [])
    ids = {concept["id"]: f"N{index}" for index, concept in enumerate(concepts)}
    lines = [
        f"# {name}",
        "",
        "Node color shows concept kind; edge style shows evidence. Dashed and dotted edges remain candidates.",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for lane in LANES:
        lane_concepts = [concept for concept in concepts if concept_lane(concept) == lane]
        if not lane_concepts:
            continue
        lines.append(f'    subgraph {lane}["{mermaid_escape(LANE_LABELS[lane])}"]')
        for concept in lane_concepts:
            label = (
                f"{mermaid_escape(concept.get('name', concept['id']))}<br/>"
                f"{mermaid_escape(concept.get('kind', ''))} · {mermaid_escape(evidence_value(concept))}"
            )
            lines.append(f'        {ids[concept["id"]]}["{label}"]')
        lines.append("    end")
    edge_styles: list[tuple[int, str]] = []
    for index, relation in enumerate(model.get("relationships", [])):
        if relation.get("source") not in ids or relation.get("target") not in ids:
            continue
        evidence = evidence_value(relation)
        label = relation.get("label", relation.get("predicate", "related to"))
        lag = relation.get("temporal_lag")
        suffix = f" · {lag}" if lag else ""
        lines.append(
            f'    {ids[relation["source"]]} -->|"{mermaid_escape(label)} '
            f'[{mermaid_escape(evidence)}]{mermaid_escape(suffix)}"| {ids[relation["target"]]}'
        )
        if evidence == "inferred":
            edge_styles.append((index, "stroke:#718096,stroke-width:2px,stroke-dasharray:8 7"))
        elif evidence == "proposed":
            edge_styles.append((index, "stroke:#c56a00,stroke-width:2px,stroke-dasharray:3 7"))
        elif evidence == "observed":
            edge_styles.append((index, "stroke:#0f766e,stroke-width:2.5px"))
        elif evidence == "declared":
            edge_styles.append((index, "stroke:#16a34a,stroke-width:2.5px"))
    lines.extend(
        [
            "    classDef input fill:#dceaff,stroke:#5b9cff,color:#17324d",
            "    classDef mechanism fill:#d9faf3,stroke:#17b99e,color:#124d45",
            "    classDef observation fill:#dcfce7,stroke:#39c86b,color:#17472a",
            "    classDef decision fill:#fff3d6,stroke:#cc7a00,color:#6f3d00",
            "    classDef risk fill:#ffe3e3,stroke:#ef6262,color:#991b1b",
            "    classDef goal fill:#0f766e,stroke:#0f766e,color:#ffffff",
        ]
    )
    classes: dict[str, list[str]] = defaultdict(list)
    for concept in concepts:
        kind = concept.get("kind")
        style = "risk" if kind in {"risk", "data_quality"} else (
            "goal" if kind == "goal" else {
                "inputs": "input",
                "mechanisms": "mechanism",
                "observations": "observation",
                "decisions": "decision",
            }[concept_lane(concept)]
        )
        classes[style].append(ids[concept["id"]])
    for style, node_ids in sorted(classes.items()):
        lines.append(f"    class {','.join(node_ids)} {style}")
    for index, style in edge_styles:
        lines.append(f"    linkStyle {index} {style}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def xml_text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def wrap(value: Any, width: int) -> list[str]:
    text = str(value or "").strip()
    return textwrap.wrap(text, width=width, break_long_words=False) if text else []


def svg_text(
    x: float,
    y: float,
    value: Any,
    size: int = 16,
    color: str = "#20364a",
    weight: int = 400,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Microsoft JhengHei, Noto Sans TC, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">'
        f"{xml_text(value)}</text>"
    )


def svg_card(concept: dict[str, Any], box: tuple[float, float, float, float], selected: bool) -> str:
    x, y, width, height = box
    kind = str(concept.get("kind", "measurement"))
    fill, stroke, title_color = KIND_STYLE.get(kind, KIND_STYLE["measurement"])
    evidence = evidence_value(concept)
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="16" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{4 if selected else 2.2}"/>'
    ]
    title_lines = wrap(concept.get("name", concept.get("id")), 25)[:2]
    for index, line in enumerate(title_lines):
        parts.append(
            svg_text(x + width / 2, y + 31 + index * 23, line, 18, title_color, 700, "middle")
        )
    badge_y = y + 66 if len(title_lines) > 1 else y + 48
    badge_width = max(72, len(evidence) * 8 + 20)
    parts.append(
        f'<rect x="{x+width/2-badge_width/2}" y="{badge_y}" width="{badge_width}" height="22" '
        f'rx="11" fill="#ffffff" fill-opacity="0.78"/>'
    )
    parts.append(svg_text(x + width / 2, badge_y + 16, evidence, 12, stroke, 700, "middle"))
    detail_y = badge_y + 42
    detail_lines: list[str] = []
    for item in concept.get("details", []) if isinstance(concept.get("details"), list) else []:
        detail_lines.extend(wrap(item, 31))
    if not detail_lines:
        detail_lines = wrap(concept.get("description", ""), 31)
    detail_color = "#d8fff7" if kind == "goal" else "#4e6478"
    for index, line in enumerate(detail_lines[:2]):
        parts.append(svg_text(x + width / 2, detail_y + index * 20, line, 13, detail_color, 400, "middle"))
    return "\n".join(parts)


def svg_edge(
    source_box: tuple[float, float, float, float],
    target_box: tuple[float, float, float, float],
    relation: dict[str, Any],
) -> str:
    sx, sy, sw, sh = source_box
    tx, ty, tw, th = target_box
    source_center = sx + sw / 2
    target_center = tx + tw / 2
    same_lane = abs(source_center - target_center) < 1
    if same_lane:
        x1, y1 = sx + sw, sy + sh / 2
        x2, y2 = tx + tw, ty + th / 2
        outside_x = max(x1, x2) + 42
        path = f"M{x1},{y1} C{outside_x},{y1} {outside_x},{y2} {x2},{y2}"
    elif source_center < target_center:
        x1, y1 = sx + sw, sy + sh / 2
        x2, y2 = tx, ty + th / 2
    else:
        x1, y1 = sx, sy + sh / 2
        x2, y2 = tx + tw, ty + th / 2
    if not same_lane:
        dx = max(28, abs(x2 - x1) * 0.42)
        direction = 1 if x2 >= x1 else -1
        path = f"M{x1},{y1} C{x1+direction*dx},{y1} {x2-direction*dx},{y2} {x2},{y2}"
    evidence = evidence_value(relation)
    color, dash, marker = EVIDENCE_STYLE.get(evidence, EVIDENCE_STYLE["proposed"])
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    label = str(relation.get("label", relation.get("predicate", "related to")))
    lag = relation.get("temporal_lag")
    full_label = f"{label} [{evidence}]" + (f"; lag {lag}" if lag else "")
    display_label = label if len(label) <= 16 else label[:15] + "…"
    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
    label_width = min(140, max(72, len(display_label) * 7.5 + 18))
    path_element = (
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.3"{dash_attr} '
        f'marker-end="url(#{marker})"><title>{xml_text(full_label)}</title></path>'
    )
    if same_lane or abs(x2 - x1) < 95:
        return path_element
    return "\n".join(
        [
            path_element,
            f'<rect x="{mid_x-label_width/2}" y="{mid_y-14}" width="{label_width}" height="25" '
            f'rx="7" fill="#ffffff" fill-opacity="0.92" stroke="#d8e3ea"/>',
            svg_text(mid_x, mid_y + 4, display_label, 11, color, 600, "middle"),
        ]
    )


def svg_detail_panel(
    model: dict[str, Any], focus: dict[str, Any] | None, x: int, y: int, width: int, height: int
) -> str:
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="20" fill="#ffffff" stroke="#d5e2e8"/>',
        svg_text(x + 28, y + 42, "SELECTED ONTOLOGY NODE" if focus else "MODEL REVIEW", 13, "#0f766e", 700),
    ]
    cursor = y + 86
    if focus:
        for line in wrap(focus.get("name", focus.get("id")), 27)[:2]:
            parts.append(svg_text(x + 28, cursor, line, 23, "#243b53", 800))
            cursor += 30
        parts.append(
            svg_text(
                x + 28,
                cursor + 5,
                f"{focus.get('kind', '')} · {evidence_value(focus)}",
                14,
                "#0f766e",
                700,
            )
        )
        cursor += 45
        parts.append(svg_text(x + 28, cursor, "Definition", 15, "#0f766e", 700))
        cursor += 30
        for line in wrap(focus.get("description", "No description supplied."), 44)[:6]:
            parts.append(svg_text(x + 28, cursor, line, 14, "#405466"))
            cursor += 23
        details = focus.get("details", []) if isinstance(focus.get("details"), list) else []
        if details:
            cursor += 20
            parts.append(svg_text(x + 28, cursor, "Details", 15, "#0f766e", 700))
            cursor += 30
            for item in details[:7]:
                for index, line in enumerate(wrap(item, 40)[:2]):
                    prefix = "• " if index == 0 else "  "
                    parts.append(svg_text(x + 35, cursor, prefix + line, 14, "#405466"))
                    cursor += 23
        source_fields = focus.get("source_fields", [])
        source_refs = focus.get("source_refs", [])
        cursor += 18
        parts.append(svg_text(x + 28, cursor, "Evidence links", 15, "#9b3d55", 700))
        cursor += 30
        for label, values in (("Fields", source_fields), ("Sources", source_refs)):
            value = ", ".join(values) if isinstance(values, list) and values else "none recorded"
            for index, line in enumerate(wrap(f"{label}: {value}", 42)[:3]):
                parts.append(svg_text(x + 28, cursor, line, 13, "#405466"))
                cursor += 21
    else:
        domain_model = model.get("domain_model", {})
        for line in wrap(domain_model.get("name", "Domain knowledge ontology"), 30)[:2]:
            parts.append(svg_text(x + 28, cursor, line, 23, "#243b53", 800))
            cursor += 30
        cursor += 15
        parts.append(svg_text(x + 28, cursor, "Analysis goal", 15, "#0f766e", 700))
        cursor += 30
        for line in wrap(domain_model.get("analysis_goal", "No analysis goal supplied."), 44)[:6]:
            parts.append(svg_text(x + 28, cursor, line, 14, "#405466"))
            cursor += 23
        cursor += 25
        parts.append(svg_text(x + 28, cursor, "Unresolved questions", 15, "#c56a00", 700))
        cursor += 30
        for question in model.get("unresolved_questions", [])[:8]:
            for index, line in enumerate(wrap(question, 40)[:2]):
                parts.append(svg_text(x + 35, cursor, ("• " if index == 0 else "  ") + line, 13, "#405466"))
                cursor += 22
    return "\n".join(parts)


def svg(model: dict[str, Any], report: dict[str, Any], focus_id: str | None = None) -> str:
    concepts = model.get("concepts", [])
    by_lane: dict[str, list[dict[str, Any]]] = {
        lane: [concept for concept in concepts if concept_lane(concept) == lane] for lane in LANES
    }
    focus_id = focus_id or model.get("domain_model", {}).get("focus_concept")
    focus = next((concept for concept in concepts if concept.get("id") == focus_id), None)
    max_nodes = max((len(items) for items in by_lane.values()), default=1)
    graph_top = 145
    node_top = graph_top + 105
    node_height = 120
    node_gap = 32
    graph_height = max(800, 135 + max_nodes * (node_height + node_gap))
    footer_y = graph_top + graph_height + 25
    height = footer_y + 110
    width = 1980
    graph_x, graph_width = 35, 1460
    panel_x, panel_width = 1520, 425
    lane_x = {"inputs": 75, "mechanisms": 430, "observations": 785, "decisions": 1140}
    node_width = 300
    boxes: dict[str, tuple[float, float, float, float]] = {}
    for lane, items in by_lane.items():
        for index, concept in enumerate(items):
            boxes[concept["id"]] = (
                lane_x[lane],
                node_top + index * (node_height + node_gap),
                node_width,
                node_height,
            )
    title = report["domain_model"].get("name") or "Domain knowledge ontology"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
    ]
    for evidence, (color, _dash, marker) in EVIDENCE_STYLE.items():
        parts.append(
            f'<marker id="{marker}" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="{color}"/></marker>'
        )
    parts.extend(
        [
            "</defs>",
            '<rect width="100%" height="100%" fill="#f7fafc"/>',
            svg_text(42, 38, "DOMAIN KNOWLEDGE ONTOLOGY", 14, "#0f766e", 700),
            svg_text(42, 82, title, 32, "#172b3a", 800),
            svg_text(
                42,
                116,
                "Node kind organizes the domain narrative; edge style preserves declared, observed, inferred, and proposed evidence.",
                15,
                "#617386",
            ),
            f'<rect x="{graph_x}" y="{graph_top}" width="{graph_width}" height="{graph_height}" rx="22" fill="#f1f7f9" stroke="#d5e2e8"/>',
        ]
    )
    for lane in LANES:
        parts.append(svg_text(lane_x[lane], graph_top + 43, LANE_LABELS[lane], 15, "#4b6b83", 700))
    for relation in model.get("relationships", []):
        if relation.get("source") in boxes and relation.get("target") in boxes:
            parts.append(svg_edge(boxes[relation["source"]], boxes[relation["target"]], relation))
    for concept in concepts:
        if concept.get("id") in boxes:
            parts.append(svg_card(concept, boxes[concept["id"]], concept.get("id") == focus_id))
    parts.append(svg_detail_panel(model, focus, panel_x, graph_top, panel_width, graph_height))
    parts.extend(
        [
            f'<rect x="35" y="{footer_y}" width="1910" height="74" rx="15" fill="#ffffff" stroke="#d5e2e8"/>',
            svg_text(65, footer_y + 28, "Evidence legend", 15, "#243b53", 700),
        ]
    )
    legend_x = 245
    for evidence in EVIDENCE_CLASSES:
        color, dash, _marker = EVIDENCE_STYLE[evidence]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<line x1="{legend_x}" y1="{footer_y+39}" x2="{legend_x+52}" y2="{footer_y+39}" '
            f'stroke="{color}" stroke-width="3"{dash_attr}/>'
        )
        parts.append(svg_text(legend_x + 63, footer_y + 44, evidence, 14, "#405466"))
        legend_x += 270
    parts.append(svg_text(1915, footer_y + 44, "review graph", 13, "#7c8b98", 600, "end"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    args = parse_args()
    try:
        model = load_model(args.input)
        report = profile(model, args.focus)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.format == "markdown":
        output = markdown(model, report)
    elif args.format == "mermaid":
        output = mermaid(model, report)
    elif args.format == "svg":
        output = svg(model, report, args.focus)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 2 if report["validation"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
