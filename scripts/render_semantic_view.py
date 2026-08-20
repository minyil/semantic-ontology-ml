#!/usr/bin/env python3
"""Validate and render a task-specific semantic ontology view without dependencies."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


EVIDENCE = {"declared", "observed", "inferred", "proposed"}
EVIDENCE_SCOPES = {
    "declared_only": {"declared"},
    "declared_observed": {"declared", "observed"},
    "include_inferred": {"declared", "observed", "inferred"},
    "include_proposed": EVIDENCE,
}
VIEW_TYPES = {
    "structural",
    "semantic-role",
    "process",
    "temporal",
    "analytical",
    "statistical",
    "decision",
    "relational",
}
CLAIM_TYPES = {
    "structural",
    "association",
    "temporal",
    "lineage",
    "process_flow",
    "hypothesis",
    "constraint",
    "causal",
}
DIRECTIONS = {"LR", "RL", "TB", "BT"}
DEFAULT_LANGUAGE = "zh-Hant-TW"
LANGUAGES = {DEFAULT_LANGUAGE, "en"}

TEXT = {
    "zh-Hant-TW": {
        "view": "視圖",
        "question": "問題",
        "evidence_legend": "每項主張均標示證據：已宣告＝深色實線、已觀測＝藍色虛線、推論＝琥珀色虛線、建議＝灰色點線。除非關係明確標示為「因果」，否則箭頭方向不代表因果關係。",
        "members": "成員",
        "scope": "範圍",
        "design": "研究設計",
        "causal": "因果",
        "non_causal": "非因果",
        "review_notes": "審查事項",
        "colon": "：",
        "separator": "。",
    },
    "en": {
        "view": "View",
        "question": "Question",
        "evidence_legend": "Evidence is printed on every claim: declared=solid, observed=blue dashed, inferred=amber dashed, proposed=gray dotted. Arrow direction is not causal unless the edge says `causal`.",
        "members": "members",
        "scope": "scope",
        "design": "design",
        "causal": "causal",
        "non_causal": "non-causal",
        "review_notes": "Review notes",
        "colon": ": ",
        "separator": ". ",
    },
}
EVIDENCE_LABELS = {
    "zh-Hant-TW": {
        "declared": "已宣告",
        "observed": "已觀測",
        "inferred": "推論",
        "proposed": "建議",
    },
    "en": {value: value for value in EVIDENCE},
}
KIND_LABELS = {
    "zh-Hant-TW": {
        "entity": "實體",
        "semantic_group": "語意群組",
        "process_input": "製程輸入",
        "process_control": "製程控制／負載",
        "process_state": "製程狀態",
        "process_output": "製程輸出",
        "quality": "品質／績效",
        "time": "時間",
        "feature": "特徵",
        "target": "目標",
        "decision": "決策",
        "objective": "目標函數",
        "constraint": "限制條件",
        "policy": "政策",
    },
    "en": {},
}
VIEW_TYPE_LABELS = {
    "zh-Hant-TW": {
        "structural": "結構",
        "semantic-role": "語意角色",
        "process": "製程",
        "temporal": "時間",
        "analytical": "分析",
        "statistical": "統計",
        "decision": "決策",
        "relational": "關聯式",
    },
    "en": {},
}
CLAIM_LABELS = {
    "zh-Hant-TW": {
        "structural": "結構",
        "association": "關聯",
        "temporal": "時間",
        "lineage": "資料譜系",
        "process_flow": "製程流",
        "hypothesis": "假設",
        "constraint": "限制",
        "causal": "因果",
    },
    "en": {},
}
TEMPORAL_KEY_LABELS = {
    "zh-Hant-TW": {
        "repairs": "修正數",
        "source_mutated": "來源已修改",
        "median_nonzero_run_minutes": "非零值中位連續分鐘",
        "exact_60_minute_nonzero_runs_pct": "恰為 60 分鐘的非零連續區段占比",
        "lag": "落後期數",
        "window": "時間窗",
        "horizon": "預測期距",
    },
    "en": {},
}

KIND_STYLES = {
    "entity": ("#f8fafc", "#475569"),
    "semantic_group": ("#f8fafc", "#475569"),
    "process_input": ("#eff6ff", "#2563eb"),
    "process_control": ("#eef2ff", "#4f46e5"),
    "process_state": ("#fff7ed", "#c2410c"),
    "process_output": ("#f0fdf4", "#15803d"),
    "quality": ("#fdf2f8", "#be185d"),
    "time": ("#ecfeff", "#0e7490"),
    "feature": ("#f5f3ff", "#7c3aed"),
    "target": ("#fff1f2", "#be123c"),
    "decision": ("#ecfdf5", "#047857"),
    "objective": ("#fefce8", "#a16207"),
    "constraint": ("#fef2f2", "#b91c1c"),
    "policy": ("#f8fafc", "#334155"),
}
EDGE_STYLES = {
    "declared": "stroke:#0f172a,stroke-width:2px",
    "observed": "stroke:#2563eb,stroke-width:2px,stroke-dasharray:4 2",
    "inferred": "stroke:#b45309,stroke-width:2px,stroke-dasharray:7 4",
    "proposed": "stroke:#64748b,stroke-width:1.5px,stroke-dasharray:2 4",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render a task-specific semantic ontology view."
    )
    parser.add_argument("input", help="Semantic-view JSON path, or '-' for stdin")
    parser.add_argument("--format", choices=("mermaid", "dot"), default="mermaid")
    parser.add_argument("--direction", choices=tuple(sorted(DIRECTIONS)))
    parser.add_argument("--evidence-scope", choices=tuple(EVIDENCE_SCOPES))
    parser.add_argument("--language", choices=tuple(sorted(LANGUAGES)))
    parser.add_argument("--output", help="Write output instead of stdout")
    return parser.parse_args()


def load_view(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("the semantic-view root must be a JSON object")
    return value


def object_list(value: Any, field: str, errors: list[str]) -> list[dict[str, Any]]:
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


def clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def evidence_of(item: dict[str, Any]) -> str:
    return clean_string(item.get("evidence")).lower()


def validate_view(view: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if clean_string(view.get("view_version")) != "1.0":
        errors.append("view_version must be '1.0'")
    if not clean_string(view.get("name")):
        errors.append("name is required")
    if clean_string(view.get("view_type")) not in VIEW_TYPES:
        errors.append("view_type must be a supported ontology view")
    if not clean_string(view.get("question")):
        errors.append("question is required")
    if view.get("direction", "LR") not in DIRECTIONS:
        errors.append("direction must be LR, RL, TB, or BT")
    if view.get("evidence_scope", "include_inferred") not in EVIDENCE_SCOPES:
        errors.append("evidence_scope is unsupported")
    if view.get("language", DEFAULT_LANGUAGE) not in LANGUAGES:
        errors.append("language must be zh-Hant-TW or en")

    nodes = object_list(view.get("nodes"), "nodes", errors)
    if not nodes:
        errors.append("nodes must contain at least one node")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        node_id = clean_string(node.get("id"))
        if not node_id:
            errors.append(f"nodes[{index}].id is required")
        elif node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        if not clean_string(node.get("label")):
            errors.append(f"nodes[{index}].label is required")
        if not clean_string(node.get("kind")):
            errors.append(f"nodes[{index}].kind is required")
        evidence = evidence_of(node)
        if evidence not in EVIDENCE:
            errors.append(f"nodes[{index}].evidence must be declared, observed, inferred, or proposed")
        members = node.get("members", [])
        if not isinstance(members, list):
            errors.append(f"nodes[{index}].members must be a list")
            continue
        for member_index, member in enumerate(members):
            if isinstance(member, str):
                if not member.strip():
                    errors.append(f"nodes[{index}].members[{member_index}] must not be empty")
                continue
            if not isinstance(member, dict):
                errors.append(f"nodes[{index}].members[{member_index}] must be a string or object")
                continue
            if not clean_string(member.get("name")):
                errors.append(f"nodes[{index}].members[{member_index}].name is required")
            member_evidence = evidence_of(member)
            if member_evidence not in EVIDENCE:
                errors.append(
                    f"nodes[{index}].members[{member_index}].evidence must be declared, observed, inferred, or proposed"
                )

    edges = object_list(view.get("edges", []), "edges", errors)
    for index, edge in enumerate(edges):
        source = clean_string(edge.get("source"))
        target = clean_string(edge.get("target"))
        if source not in node_ids:
            errors.append(f"edges[{index}].source references unknown node {source!r}")
        if target not in node_ids:
            errors.append(f"edges[{index}].target references unknown node {target!r}")
        if not clean_string(edge.get("relation")):
            errors.append(f"edges[{index}].relation is required")
        claim_type = clean_string(edge.get("claim_type"))
        if claim_type not in CLAIM_TYPES:
            errors.append(f"edges[{index}].claim_type is unsupported")
        evidence = evidence_of(edge)
        if evidence not in EVIDENCE:
            errors.append(f"edges[{index}].evidence must be declared, observed, inferred, or proposed")
        if "directed" in edge and not isinstance(edge["directed"], bool):
            errors.append(f"edges[{index}].directed must be boolean")
        causal = edge.get("causal", False)
        if not isinstance(causal, bool):
            errors.append(f"edges[{index}].causal must be boolean")
        if causal and evidence in {"inferred", "proposed"}:
            errors.append(f"edges[{index}] cannot assert causality from {evidence} evidence")
        if claim_type == "causal" and causal is not True:
            errors.append(f"edges[{index}] with claim_type causal must set causal to true")
        if causal is True and claim_type != "causal":
            errors.append(f"edges[{index}] with causal true must use claim_type causal")
        support = edge.get("support")
        if evidence == "observed":
            if not isinstance(support, dict):
                errors.append(f"edges[{index}].support is required for an observed edge")
            else:
                for field in ("metric", "value", "n", "scope"):
                    if field not in support or support[field] in (None, ""):
                        errors.append(f"edges[{index}].support.{field} is required")
        if causal and evidence == "observed":
            if not isinstance(support, dict) or not clean_string(support.get("design")):
                errors.append(f"edges[{index}].support.design is required for observed causality")
    return errors


def member_evidence(member: str | dict[str, Any], node_evidence: str) -> str:
    return node_evidence if isinstance(member, str) else evidence_of(member)


def filter_view(view: dict[str, Any], scope_name: str) -> dict[str, Any]:
    allowed = EVIDENCE_SCOPES[scope_name]
    nodes: list[dict[str, Any]] = []
    for node in view["nodes"]:
        if evidence_of(node) not in allowed:
            continue
        filtered_node = dict(node)
        filtered_node["members"] = [
            member
            for member in node.get("members", [])
            if member_evidence(member, evidence_of(node)) in allowed
        ]
        nodes.append(filtered_node)
    node_ids = {node["id"] for node in nodes}
    edges = [
        edge
        for edge in view.get("edges", [])
        if evidence_of(edge) in allowed
        and edge.get("source") in node_ids
        and edge.get("target") in node_ids
    ]
    result = dict(view)
    result["nodes"] = nodes
    result["edges"] = edges
    result["evidence_scope"] = scope_name
    if not nodes:
        raise ValueError(f"no nodes remain under evidence scope {scope_name!r}")
    return result


def mermaid_escape(value: Any) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;")


def dot_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def localized_label(labels: dict[str, dict[str, str]], value: str, language: str) -> str:
    return labels[language].get(value, value)


def localized_value(value: Any, language: str) -> Any:
    if language == DEFAULT_LANGUAGE and isinstance(value, bool):
        return "是" if value else "否"
    return value


def node_lines(node: dict[str, Any], language: str = DEFAULT_LANGUAGE) -> list[str]:
    kind = localized_label(KIND_LABELS, clean_string(node["kind"]), language)
    evidence = localized_label(EVIDENCE_LABELS, evidence_of(node), language)
    lines = [clean_string(node["label"]), f"{kind} [{evidence}]"]
    description = clean_string(node.get("description"))
    if description:
        lines.append(description)
    members = []
    for member in node.get("members", []):
        if isinstance(member, str):
            members.append(member)
        else:
            name = clean_string(member.get("name"))
            role = clean_string(member.get("role"))
            member_evidence = localized_label(EVIDENCE_LABELS, evidence_of(member), language)
            suffix = f" ({role}; {member_evidence})" if role else f" [{member_evidence}]"
            members.append(name + suffix)
    if members:
        lines.append(f"{TEXT[language]['members']}: " + ", ".join(members))
    return lines


def format_support(edge: dict[str, Any], language: str = DEFAULT_LANGUAGE) -> str:
    support = edge.get("support")
    if not isinstance(support, dict):
        return ""
    metric_names = {
        "spearman_rho": "Spearman ρ",
        "pearson_r": "Pearson r",
        "mutual_information": "MI",
    }
    parts: list[str] = []
    metric = support.get("metric")
    if metric not in (None, "") and support.get("value") not in (None, ""):
        parts.append(f"{metric_names.get(str(metric), metric)}={support['value']}")
    if support.get("n") not in (None, ""):
        parts.append(f"n={support['n']}")
    if support.get("scope") not in (None, ""):
        parts.append(f"{TEXT[language]['scope']}={support['scope']}")
    if support.get("design") not in (None, ""):
        parts.append(f"{TEXT[language]['design']}={support['design']}")
    return "; ".join(parts)


def edge_lines(edge: dict[str, Any], language: str = DEFAULT_LANGUAGE) -> list[str]:
    claim_type = clean_string(edge["claim_type"])
    evidence = localized_label(EVIDENCE_LABELS, evidence_of(edge), language)
    claim = localized_label(CLAIM_LABELS, claim_type, language)
    lines = [f"{edge['relation']} [{evidence}; {claim}]"]
    support = format_support(edge, language)
    if support:
        lines.append(support)
    temporal = edge.get("temporal")
    if isinstance(temporal, dict):
        temporal_parts = [
            f"{localized_label(TEMPORAL_KEY_LABELS, key, language)}={localized_value(value, language)}"
            for key, value in temporal.items()
            if value not in (None, "")
        ]
        if temporal_parts:
            lines.append("; ".join(temporal_parts))
    if edge.get("causal", False):
        lines.append(TEXT[language]["causal"])
    elif claim_type in {"association", "hypothesis"}:
        lines.append(TEXT[language]["non_causal"])
    return lines


def edge_is_directed(edge: dict[str, Any]) -> bool:
    if "directed" in edge:
        return bool(edge["directed"])
    return clean_string(edge.get("claim_type")) != "association"


def mermaid(
    view: dict[str, Any], direction: str, language: str = DEFAULT_LANGUAGE
) -> str:
    ids = {node["id"]: f"N{index}" for index, node in enumerate(view["nodes"])}
    lines = [
        f"# {view['name']}",
        "",
        f"{TEXT[language]['view']}{TEXT[language]['colon']}`{localized_label(VIEW_TYPE_LABELS, view['view_type'], language)}`{TEXT[language]['separator']}{TEXT[language]['question']}{TEXT[language]['colon']}{view['question']}",
        "",
        TEXT[language]["evidence_legend"],
        "",
        "```mermaid",
        f"flowchart {direction}",
    ]
    for node in view["nodes"]:
        label = "<br/>".join(mermaid_escape(item) for item in node_lines(node, language))
        lines.append(f'    {ids[node["id"]]}["{label}"]')
        fill, stroke = KIND_STYLES.get(node["kind"], KIND_STYLES["semantic_group"])
        dash = {
            "inferred": ",stroke-dasharray:7 4",
            "proposed": ",stroke-dasharray:2 4",
        }.get(evidence_of(node), "")
        lines.append(
            f"    style {ids[node['id']]} fill:{fill},stroke:{stroke},color:#0f172a,stroke-width:2px{dash}"
        )
    for edge_index, edge in enumerate(view["edges"]):
        label = "<br/>".join(mermaid_escape(item) for item in edge_lines(edge, language))
        connector = "-->" if edge_is_directed(edge) else "---"
        lines.append(
            f'    {ids[edge["source"]]} {connector}|"{label}"| {ids[edge["target"]]}'
        )
        lines.append(f"    linkStyle {edge_index} {EDGE_STYLES[evidence_of(edge)]}")
    notes = [str(note) for note in view.get("notes", []) if str(note).strip()]
    lines.extend(["```", ""])
    if notes:
        lines.extend(
            [
                f"{TEXT[language]['review_notes']}{TEXT[language]['colon'].rstrip()}",
                "",
                *(f"- {note}" for note in notes),
                "",
            ]
        )
    return "\n".join(lines)


def dot(view: dict[str, Any], direction: str, language: str = DEFAULT_LANGUAGE) -> str:
    ids = {node["id"]: f"N{index}" for index, node in enumerate(view["nodes"])}
    lines = [
        f'digraph "{dot_escape(view["name"])}" {{',
        f"  graph [rankdir={direction}, labelloc=t, label=\"{dot_escape(view['name'])}\"] ;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica"];',
        '  edge [fontname="Helvetica"];',
    ]
    for node in view["nodes"]:
        fill, stroke = KIND_STYLES.get(node["kind"], KIND_STYLES["semantic_group"])
        evidence = evidence_of(node)
        style = "rounded,filled,dashed" if evidence in {"inferred", "proposed"} else "rounded,filled"
        label = dot_escape("\n".join(node_lines(node, language)))
        lines.append(
            f'  {ids[node["id"]]} [label="{label}", fillcolor="{fill}", color="{stroke}", style="{style}"];'
        )
    dot_edge_style = {
        "declared": ('"solid"', '"#0f172a"', "2"),
        "observed": ('"dashed"', '"#2563eb"', "2"),
        "inferred": ('"dashed"', '"#b45309"', "2"),
        "proposed": ('"dotted"', '"#64748b"', "1.5"),
    }
    for edge in view["edges"]:
        style, color, width = dot_edge_style[evidence_of(edge)]
        direction_attr = "forward" if edge_is_directed(edge) else "none"
        label = dot_escape("\n".join(edge_lines(edge, language)))
        lines.append(
            f'  {ids[edge["source"]]} -> {ids[edge["target"]]} '
            f'[label="{label}", style={style}, color={color}, penwidth={width}, dir={direction_attr}];'
        )
    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        view = load_view(args.input)
        errors = validate_view(view)
        if errors:
            raise ValueError("; ".join(errors))
        scope = args.evidence_scope or view.get("evidence_scope", "include_inferred")
        filtered = filter_view(view, scope)
        direction = args.direction or filtered.get("direction", "LR")
        language = args.language or filtered.get("language", DEFAULT_LANGUAGE)
        output = (
            mermaid(filtered, direction, language)
            if args.format == "mermaid"
            else dot(filtered, direction, language)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
