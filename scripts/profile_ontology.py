#!/usr/bin/env python3
"""Profile and visualize a provider-neutral ontology snapshot without dependencies."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


NUMERIC_TYPES = {
    "byte",
    "decimal",
    "double",
    "float",
    "integer",
    "long",
    "number",
    "short",
}
TEMPORAL_TYPES = {"date", "datetime", "timestamp"}
BOOLEAN_TYPES = {"bool", "boolean"}
TEXT_TYPES = {"string", "text"}
GEO_TYPES = {"geohash", "geopoint", "geoshape", "geometry"}
CATEGORICAL_HINTS = re.compile(
    r"(^|_)(category|class|code|country|currency|segment|state|status|type)($|_)", re.I
)
IDENTIFIER_HINTS = re.compile(r"(^|_)(id|key|rid|uuid)($|_)", re.I)
TEMPORAL_HINTS = re.compile(
    r"(^|_)(at|date|datetime|day|month|time|timestamp|week|year)($|_)", re.I
)
SENSITIVE_HINTS = re.compile(
    r"(^|[_ -])(age|sex)($|[_ -])|address|birth|biometric|disability|email|ethnicity|gender|health|income|"
    r"nationality|passport|phone|politic|race|religion|salary|sexual|ssn|tax[_ -]?id",
    re.I,
)
OUTCOME_HINTS = re.compile(
    r"actual|churn|closed|complete|converted|default|failure|final|fraud|label|"
    r"outcome|post[_ -]?event|resolved|target",
    re.I,
)
DEFAULT_LANGUAGE = "zh-Hant-TW"
LANGUAGES = {DEFAULT_LANGUAGE, "en"}
DIAGRAM_TEXT = {
    "zh-Hant-TW": {
        "diagram_title": "本體語意圖",
        "legend": "標記代表語意角色；`敏感?` 是待審查候選。關係標籤顯示名稱、證據、基數與連接鍵。",
        "no_fields": "（無欄位）",
        "target": "目標",
        "time": "時間",
        "sensitive?": "敏感?",
        "unnamed_relation": "未命名關係",
    },
    "en": {
        "diagram_title": "ontology diagram",
        "legend": "Markers are semantic roles; `sensitive?` is a review candidate. Relation labels show name, evidence, cardinality, and join keys.",
        "no_fields": "(no fields)",
        "target": "target",
        "time": "time",
        "sensitive?": "sensitive?",
        "unnamed_relation": "unnamed relation",
    },
}
EVIDENCE_LABELS = {
    "zh-Hant-TW": {
        "declared": "已宣告",
        "observed": "已觀測",
        "inferred": "推論",
        "proposed": "建議",
        "unspecified": "未指定",
    },
    "en": {},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and profile a normalized ontology snapshot."
    )
    parser.add_argument("input", help="Snapshot JSON path, or '-' for stdin")
    parser.add_argument(
        "--format", choices=("json", "markdown", "mermaid", "dot"), default="markdown"
    )
    parser.add_argument(
        "--language",
        choices=tuple(sorted(LANGUAGES)),
        default=DEFAULT_LANGUAGE,
        help="User-facing diagram language; defaults to Traditional Chinese",
    )
    parser.add_argument(
        "--diagram-detail",
        choices=("compact", "fields"),
        default="compact",
        help="For diagram formats, show key roles or every field",
    )
    parser.add_argument(
        "--diagram-direction",
        choices=("LR", "RL", "TB", "BT"),
        default="LR",
        help="For diagram formats, set left/right or top/bottom layout",
    )
    parser.add_argument("--output", help="Write output to this path instead of stdout")
    return parser.parse_args()


def load_snapshot(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("the snapshot root must be a JSON object")
    return value


def value_list(value: Any, field: str, errors: list[str]) -> list[dict[str, Any]]:
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


def api_name(item: dict[str, Any]) -> str:
    value = item.get("name", item.get("api_name"))
    return value.strip() if isinstance(value, str) else ""


def normalize_type(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    return value.strip().lower().replace(" ", "_") or "unknown"


def infer_roles(prop: dict[str, Any], primary_keys: set[str]) -> list[str]:
    name = api_name(prop)
    dtype = normalize_type(prop.get("physical_type", prop.get("data_type")))
    explicit = prop.get("semantic_role")
    roles: list[str] = []
    if isinstance(explicit, str) and explicit.strip():
        roles.append(explicit.strip().lower())
    for role in prop.get("roles", []) if isinstance(prop.get("roles"), list) else []:
        value = role.get("role") if isinstance(role, dict) else role
        if isinstance(value, str) and value.strip():
            roles.append(value.strip().lower())
    is_identifier = name in primary_keys or bool(IDENTIFIER_HINTS.search(name))
    if is_identifier:
        roles.append("identifier")
    else:
        if dtype in TEMPORAL_TYPES or TEMPORAL_HINTS.search(name):
            roles.append("temporal")
        elif dtype in NUMERIC_TYPES:
            roles.append("numeric")
        elif dtype in BOOLEAN_TYPES:
            roles.append("boolean")
        elif dtype in GEO_TYPES:
            roles.append("geospatial")
        elif dtype in TEXT_TYPES:
            roles.append("categorical" if CATEGORICAL_HINTS.search(name) else "text")
    if not roles:
        roles.append("unknown")
    return sorted(set(roles))


def connected_components(nodes: set[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    unseen = set(nodes)
    components: list[list[str]] = []
    while unseen:
        start = min(unseen)
        queue: deque[str] = deque([start])
        unseen.remove(start)
        component: list[str] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in sorted(adjacency[node]):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda part: (-len(part), part))


def directed_cycle_nodes(nodes: set[str], adjacency: dict[str, set[str]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    in_cycle: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            start = stack.index(node)
            in_cycle.update(stack[start:])
            return
        visiting.add(node)
        stack.append(node)
        for neighbor in sorted(adjacency[node]):
            visit(neighbor, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node, [])
    return sorted(in_cycle)


def profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    object_types = value_list(
        snapshot.get("entity_types", snapshot.get("object_types")), "entity_types", errors
    )
    link_types = value_list(
        snapshot.get("relations", snapshot.get("link_types")), "relations", errors
    )
    action_types = value_list(snapshot.get("action_types"), "action_types", errors)
    query_types = value_list(snapshot.get("query_types"), "query_types", errors)
    functions = value_list(snapshot.get("functions"), "functions", errors)
    interface_types = value_list(snapshot.get("interface_types"), "interface_types", errors)
    shared_property_types = value_list(
        snapshot.get("shared_property_types"), "shared_property_types", errors
    )
    value_types = value_list(snapshot.get("value_types"), "value_types", errors)
    object_type_groups = value_list(
        snapshot.get("object_type_groups"), "object_type_groups", errors
    )
    if not object_types:
        errors.append("entity_types must contain at least one entity type")

    object_names: set[str] = set()
    object_profiles: list[dict[str, Any]] = []
    described_objects = 0
    described_properties = 0
    property_total = 0
    sensitive_candidates: list[str] = []
    outcome_candidates: list[str] = []

    for index, obj in enumerate(object_types):
        name = api_name(obj)
        if not name:
            errors.append(f"entity_types[{index}].name is required")
            name = f"<entity-{index}>"
        elif name in object_names:
            errors.append(f"duplicate entity type: {name}")
        object_names.add(name)
        if obj.get("description"):
            described_objects += 1
        if str(obj.get("status", "")).lower() == "deprecated":
            warnings.append(f"{name} is deprecated")

        properties = value_list(
            obj.get("fields", obj.get("properties")), f"entity_types[{index}].fields", errors
        )
        primary_key_value = obj.get("primary_key")
        if isinstance(primary_key_value, str):
            primary_keys = {primary_key_value.strip()} if primary_key_value.strip() else set()
        elif isinstance(primary_key_value, list):
            primary_keys = {
                item.strip() for item in primary_key_value if isinstance(item, str) and item.strip()
            }
        else:
            primary_keys = set()
        seen_properties: set[str] = set()
        roles: dict[str, list[str]] = defaultdict(list)
        for prop_index, prop in enumerate(properties):
            prop_name = api_name(prop)
            if not prop_name:
                errors.append(
                    f"entity_types[{index}].fields[{prop_index}].name is required"
                )
                continue
            if prop_name in seen_properties:
                errors.append(f"duplicate field: {name}.{prop_name}")
            seen_properties.add(prop_name)
            property_total += 1
            if prop.get("description"):
                described_properties += 1
            if str(prop.get("status", "")).lower() == "deprecated":
                warnings.append(f"{name}.{prop_name} is deprecated")
            prop_roles = infer_roles(prop, primary_keys)
            for role in prop_roles:
                roles[role].append(prop_name)
            evidence = " ".join(
                str(prop.get(field, ""))
                for field in (
                    "name",
                    "api_name",
                    "display_name",
                    "description",
                    "semantic_role",
                    "roles",
                )
            )
            if any(role in prop_roles for role in ("sensitive", "sensitive_candidate")) or SENSITIVE_HINTS.search(evidence):
                sensitive_candidates.append(f"{name}.{prop_name}")
            if "target" in prop_roles or OUTCOME_HINTS.search(evidence):
                outcome_candidates.append(f"{name}.{prop_name}")
        if not primary_keys:
            warnings.append(f"{name} has no declared primary_key")
        else:
            for primary_key in sorted(primary_keys):
                if primary_key not in seen_properties:
                    errors.append(
                        f"{name}.primary_key references missing field {primary_key}"
                    )
        if not any(
            role in roles
            for role in ("temporal", "event_time", "observation_time", "availability_time")
        ):
            warnings.append(f"{name} has no obvious temporal field")
        object_profiles.append(
            {
                "name": name,
                "primary_key": sorted(primary_keys) or None,
                "field_count": len(properties),
                "roles": {key: sorted(value) for key, value in sorted(roles.items())},
            }
        )

    undirected: dict[str, set[str]] = defaultdict(set)
    directed: dict[str, set[str]] = defaultdict(set)
    link_names: set[str] = set()
    relation_features: list[dict[str, Any]] = []
    valid_multiplicities = {"one", "many"}
    for index, link in enumerate(link_types):
        name = api_name(link)
        if not name:
            errors.append(f"relations[{index}].name is required")
            name = f"<relation-{index}>"
        elif name in link_names:
            errors.append(f"duplicate relation: {name}")
        link_names.add(name)
        source = link.get("source_entity", link.get("source_object_type"))
        target = link.get("target_entity", link.get("target_object_type"))
        if source not in object_names:
            errors.append(f"{name}.source_entity references unknown entity {source!r}")
        if target not in object_names:
            errors.append(f"{name}.target_entity references unknown entity {target!r}")
        source_to_target = link.get("source_to_target")
        target_to_source = link.get("target_to_source")
        if source_to_target not in valid_multiplicities:
            errors.append(f"{name}.source_to_target must be 'one' or 'many'")
        if target_to_source not in valid_multiplicities:
            errors.append(f"{name}.target_to_source must be 'one' or 'many'")
        if source in object_names and target in object_names:
            undirected[source].add(target)
            undirected[target].add(source)
            directed[source].add(target)
            templates = (
                ["count", "numeric_aggregate", "recency", "distinct_count"]
                if source_to_target == "many"
                else ["linked_property"]
            )
            relation_features.append(
                {
                    "root_entity": source,
                    "path": name,
                    "linked_entity": target,
                    "templates": templates,
                }
            )
            reverse_templates = (
                ["count", "numeric_aggregate", "recency", "distinct_count"]
                if target_to_source == "many"
                else ["linked_property"]
            )
            relation_features.append(
                {
                    "root_entity": target,
                    "path": f"{name} (reverse)",
                    "linked_entity": source,
                    "templates": reverse_templates,
                }
            )

    for name in object_names:
        undirected[name]
        directed[name]
    components = connected_components(object_names, undirected) if object_names else []
    isolated = sorted(name for name in object_names if not undirected[name])
    if isolated:
        warnings.append("isolated entity types: " + ", ".join(isolated))

    ontology = snapshot.get("semantic_model", snapshot.get("ontology"))
    ontology = ontology if isinstance(ontology, dict) else {}
    description_coverage = {
            "entity_types": round(described_objects / len(object_types), 3) if object_types else 0,
            "fields": round(described_properties / property_total, 3) if property_total else 0,
        }
    return {
        "semantic_model": {
            "name": ontology.get("name", ontology.get("api_name")),
            "display_name": ontology.get("display_name"),
            "source_id": ontology.get("source_id", ontology.get("rid")),
        },
        "summary": {
            "entity_type_count": len(object_types),
            "field_count": property_total,
            "relation_count": len(link_types),
            "action_type_count": len(action_types),
            "query_type_count": len(query_types),
            "function_count": len(functions),
            "interface_type_count": len(interface_types),
            "shared_property_type_count": len(shared_property_types),
            "value_type_count": len(value_types),
            "object_type_group_count": len(object_type_groups),
            "connected_component_count": len(components),
        },
        "validation": {"errors": errors, "warnings": warnings},
        "quality": {
            "description_coverage": description_coverage,
            "isolated_entity_types": isolated,
            "sensitive_field_candidates": sorted(set(sensitive_candidates)),
            "outcome_or_leakage_field_candidates": sorted(set(outcome_candidates)),
        },
        "graph": {
            "connected_components": components,
            "directed_cycle_nodes": directed_cycle_nodes(object_names, directed),
        },
        "entity_profiles": sorted(object_profiles, key=lambda item: item["name"]),
        "relation_feature_templates": sorted(
            relation_features, key=lambda item: (item["root_entity"], item["path"])
        ),
        "interpretation_limits": [
            "Name- and type-based roles are candidates that require domain-owner confirmation.",
            "Schema profiling cannot prove data quality, feature availability, or causal validity.",
            "Outcome-like and sensitive fields require policy review; they are not automatic features.",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    validation = report["validation"]
    quality = report["quality"]
    graph = report["graph"]
    lines = [
        "# Ontology semantic profile",
        "",
        "## Summary",
        "",
        f"- Entity types: {summary['entity_type_count']}",
        f"- Fields: {summary['field_count']}",
        f"- Relations: {summary['relation_count']}",
        f"- Actions: {summary['action_type_count']}",
        f"- Queries: {summary['query_type_count']}",
        f"- Functions: {summary['function_count']}",
        f"- Interfaces: {summary['interface_type_count']}",
        f"- Shared property types: {summary['shared_property_type_count']}",
        f"- Value types: {summary['value_type_count']}",
        f"- Object type groups: {summary['object_type_group_count']}",
        f"- Connected components: {summary['connected_component_count']}",
        "",
        "## Validation",
        "",
    ]
    if validation["errors"]:
        lines.extend(f"- ERROR: {item}" for item in validation["errors"])
    if validation["warnings"]:
        lines.extend(f"- WARNING: {item}" for item in validation["warnings"])
    if not validation["errors"] and not validation["warnings"]:
        lines.append("- No structural issues detected.")
    lines.extend(["", "## Entity types", ""])
    for obj in report["entity_profiles"]:
        roles = "; ".join(
            f"{role}: {', '.join(names)}" for role, names in obj["roles"].items()
        )
        lines.append(
            f"- `{obj['name']}` — {obj['field_count']} fields; "
            f"primary key: `{', '.join(obj['primary_key']) if obj['primary_key'] else 'undeclared'}`; "
            f"{roles or 'no roles inferred'}"
        )
    lines.extend(["", "## Graph", ""])
    for index, component in enumerate(graph["connected_components"], start=1):
        lines.append(f"- Component {index}: {', '.join(component)}")
    if graph["directed_cycle_nodes"]:
        lines.append("- Directed-cycle candidates: " + ", ".join(graph["directed_cycle_nodes"]))
    lines.extend(["", "## Review candidates", ""])
    for label, key in (
        ("Sensitive fields", "sensitive_field_candidates"),
        ("Outcome or leakage fields", "outcome_or_leakage_field_candidates"),
    ):
        values = quality[key]
        lines.append(f"- {label}: {', '.join(values) if values else 'none inferred'}")
    lines.extend(["", "## Relation feature templates", ""])
    for item in report["relation_feature_templates"]:
        lines.append(
            f"- `{item['root_entity']}` via `{item['path']}` to "
            f"`{item['linked_entity']}`: {', '.join(item['templates'])}"
        )
    if not report["relation_feature_templates"]:
        lines.append("- No relations available for relational feature templates.")
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {item}" for item in report["interpretation_limits"])
    return "\n".join(lines) + "\n"


def snapshot_entities(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    value = snapshot.get("entity_types", snapshot.get("object_types"))
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def snapshot_relations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    value = snapshot.get("relations", snapshot.get("link_types"))
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def primary_keys(entity: dict[str, Any]) -> set[str]:
    value = entity.get("primary_key")
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, list):
        return {item.strip() for item in value if isinstance(item, str) and item.strip()}
    return set()


def role_evidence(prop: dict[str, Any], role_names: set[str], inferred_roles: list[str]) -> str:
    evidence: set[str] = set()
    explicit = prop.get("semantic_role")
    if isinstance(explicit, str) and explicit.strip().lower() in role_names:
        evidence.add("unspecified")
    value = prop.get("roles")
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            role = item.get("role")
            if isinstance(role, str) and role.strip().lower() in role_names:
                status = item.get("evidence", "unspecified")
                evidence.add(str(status).strip().lower() or "unspecified")
        elif isinstance(item, str) and item.strip().lower() in role_names:
            evidence.add("unspecified")
    if not evidence and any(role in inferred_roles for role in role_names):
        evidence.add("inferred")
    order = {"declared": 0, "observed": 1, "inferred": 2, "proposed": 3, "unspecified": 4}
    return "+".join(sorted(evidence, key=lambda item: (order.get(item, 5), item))) or "unspecified"


def diagram_field_metadata(
    entity: dict[str, Any], sensitive_candidates: set[str]
) -> list[dict[str, Any]]:
    entity_name = api_name(entity)
    keys = primary_keys(entity)
    value = entity.get("fields", entity.get("properties"))
    properties = [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    fields: list[dict[str, Any]] = []
    for prop in properties:
        name = api_name(prop)
        roles = infer_roles(prop, keys)
        markers: list[str] = []
        marker_evidence: dict[str, str] = {}
        if name in keys:
            markers.append("PK")
        if "target" in roles:
            markers.append("target")
            marker_evidence["target"] = role_evidence(prop, {"target"}, roles)
        if any(role in roles for role in ("event_time", "observation_time", "availability_time", "temporal")):
            markers.append("time")
            marker_evidence["time"] = role_evidence(
                prop, {"event_time", "observation_time", "availability_time", "temporal"}, roles
            )
        if f"{entity_name}.{name}" in sensitive_candidates or any(
            role in roles for role in ("sensitive", "sensitive_candidate")
        ):
            markers.append("sensitive?")
            marker_evidence["sensitive?"] = role_evidence(
                prop, {"sensitive", "sensitive_candidate"}, roles
            )
        fields.append(
            {
                "name": name,
                "physical_type": normalize_type(prop.get("physical_type", prop.get("data_type"))),
                "roles": roles,
                "markers": markers,
                "marker_evidence": marker_evidence,
            }
        )
    return fields


def diagram_entities(snapshot: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    sensitive = set(report["quality"]["sensitive_field_candidates"])
    result: list[dict[str, Any]] = []
    for index, entity in enumerate(snapshot_entities(snapshot)):
        name = api_name(entity) or f"<entity-{index}>"
        fields = diagram_field_metadata(entity, sensitive)
        result.append(
            {
                "id": f"N{index}",
                "name": name,
                "primary_key": sorted(primary_keys(entity)),
                "fields": fields,
                "has_target": any("target" in item["roles"] for item in fields),
                "has_sensitive": any("sensitive?" in item["markers"] for item in fields),
            }
        )
    return result


def evidence_label(relation: dict[str, Any]) -> str:
    value = relation.get("evidence", "unspecified")
    if isinstance(value, dict):
        value = value.get("class", value.get("type", value.get("status", "unspecified")))
    return str(value).strip().lower() or "unspecified"


def cardinality_label(relation: dict[str, Any]) -> str:
    pair = (relation.get("source_to_target"), relation.get("target_to_source"))
    return {
        ("one", "one"): "1:1",
        ("one", "many"): "N:1",
        ("many", "one"): "1:N",
        ("many", "many"): "N:M",
    }.get(pair, "?:?")


def join_label(relation: dict[str, Any]) -> str:
    value = relation.get("join")
    joins = [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    parts = []
    for item in joins:
        source = item.get("source_field")
        target = item.get("target_field")
        if isinstance(source, str) and isinstance(target, str):
            parts.append(f"{source}→{target}")
    return ", ".join(parts)


def localized_marker(value: str, language: str) -> str:
    return DIAGRAM_TEXT[language].get(value, value)


def localized_evidence(value: str, language: str) -> str:
    return EVIDENCE_LABELS[language].get(value, value)


def diagram_lines(
    entity: dict[str, Any], detail: str, language: str = DEFAULT_LANGUAGE
) -> list[str]:
    lines = [entity["name"]]
    if detail == "fields":
        for field in entity["fields"]:
            markers = " ".join(
                f"[{localized_marker(item, language)}:{localized_evidence(field['marker_evidence'][item], language)}]"
                if item in field["marker_evidence"]
                else f"[{localized_marker(item, language)}]"
                for item in field["markers"]
            )
            suffix = f" {markers}" if markers else ""
            lines.append(f"{field['name']}: {field['physical_type']}{suffix}")
        if not entity["fields"]:
            lines.append(DIAGRAM_TEXT[language]["no_fields"])
        return lines
    if entity["primary_key"]:
        lines.append("PK: " + ", ".join(entity["primary_key"]))
    for marker in ("target", "time", "sensitive?"):
        names = [
            f"{field['name']} [{localized_evidence(field['marker_evidence'][marker], language)}]"
            for field in entity["fields"]
            if marker in field["markers"]
        ]
        if names:
            lines.append(f"{localized_marker(marker, language)}: {', '.join(names)}")
    return lines


def mermaid_escape(value: str) -> str:
    return html.escape(value, quote=True).replace("|", "&#124;")


def mermaid(
    snapshot: dict[str, Any],
    report: dict[str, Any],
    detail: str = "compact",
    direction: str = "LR",
    language: str = DEFAULT_LANGUAGE,
) -> str:
    entities = diagram_entities(snapshot, report)
    ids = {entity["name"]: entity["id"] for entity in entities}
    model_name = report["semantic_model"].get("name") or (
        "本體模型" if language == DEFAULT_LANGUAGE else "Ontology"
    )
    lines = [
        f"# {model_name} {DIAGRAM_TEXT[language]['diagram_title']}",
        "",
        DIAGRAM_TEXT[language]["legend"],
        "",
        "```mermaid",
        f"flowchart {direction}",
    ]
    for entity in entities:
        label = "<br/>".join(
            mermaid_escape(item) for item in diagram_lines(entity, detail, language)
        )
        lines.append(f'    {entity["id"]}["{label}"]')
    styled_edges: list[tuple[int, str]] = []
    edge_index = 0
    for relation in snapshot_relations(snapshot):
        source = relation.get("source_entity", relation.get("source_object_type"))
        target = relation.get("target_entity", relation.get("target_object_type"))
        if source not in ids or target not in ids:
            continue
        name = api_name(relation) or DIAGRAM_TEXT[language]["unnamed_relation"]
        evidence = evidence_label(relation)
        parts = [
            f"{name} [{localized_evidence(evidence, language)}]",
            cardinality_label(relation),
        ]
        joins = join_label(relation)
        if joins:
            parts.append(joins)
        label = "<br/>".join(mermaid_escape(item) for item in parts)
        lines.append(f'    {ids[source]} -->|"{label}"| {ids[target]}')
        if evidence == "proposed":
            styled_edges.append((edge_index, "stroke:#64748b,stroke-width:1.5px,stroke-dasharray:5 5"))
        elif evidence == "inferred":
            styled_edges.append((edge_index, "stroke:#64748b,stroke-width:1.5px,stroke-dasharray:2 3"))
        elif evidence not in {"declared", "observed"}:
            styled_edges.append((edge_index, "stroke:#94a3b8,stroke-width:1.25px,stroke-dasharray:5 5"))
        edge_index += 1
    lines.extend(
        [
            "    classDef ordinary fill:#f8fafc,stroke:#475569,color:#0f172a",
            "    classDef target fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-width:2px",
            "    classDef sensitive fill:#fdf2f8,stroke:#be185d,color:#831843,stroke-width:2px",
            "    classDef targetSensitive fill:#fff1f2,stroke:#9f1239,color:#881337,stroke-width:3px",
        ]
    )
    classes: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        style = "targetSensitive" if entity["has_target"] and entity["has_sensitive"] else (
            "target" if entity["has_target"] else "sensitive" if entity["has_sensitive"] else "ordinary"
        )
        classes[style].append(entity["id"])
    for style, node_ids in sorted(classes.items()):
        lines.append(f"    class {','.join(node_ids)} {style}")
    for index, style in styled_edges:
        lines.append(f"    linkStyle {index} {style}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def dot(
    snapshot: dict[str, Any],
    report: dict[str, Any],
    detail: str = "compact",
    direction: str = "LR",
    language: str = DEFAULT_LANGUAGE,
) -> str:
    entities = diagram_entities(snapshot, report)
    ids = {entity["name"]: entity["id"] for entity in entities}
    model_name = report["semantic_model"].get("name") or (
        "本體模型" if language == DEFAULT_LANGUAGE else "Ontology"
    )
    lines = [
        f'digraph "{dot_escape(model_name)}" {{',
        f"  graph [rankdir={direction}, labelloc=t, label=\"{dot_escape(model_name)} {DIAGRAM_TEXT[language]['diagram_title']}\"];",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fillcolor="#f8fafc", color="#475569"];',
        '  edge [fontname="Helvetica", color="#475569"];',
    ]
    for entity in entities:
        label = dot_escape("\n".join(diagram_lines(entity, detail, language)))
        attributes = [f'label="{label}"']
        if entity["has_target"] and entity["has_sensitive"]:
            attributes.extend(['fillcolor="#fff1f2"', 'color="#9f1239"', "penwidth=3"])
        elif entity["has_target"]:
            attributes.extend(['fillcolor="#fff7ed"', 'color="#c2410c"', "penwidth=2"])
        elif entity["has_sensitive"]:
            attributes.extend(['fillcolor="#fdf2f8"', 'color="#be185d"', "penwidth=2"])
        lines.append(f"  {entity['id']} [{', '.join(attributes)}];")
    for relation in snapshot_relations(snapshot):
        source = relation.get("source_entity", relation.get("source_object_type"))
        target = relation.get("target_entity", relation.get("target_object_type"))
        if source not in ids or target not in ids:
            continue
        name = api_name(relation) or DIAGRAM_TEXT[language]["unnamed_relation"]
        evidence = evidence_label(relation)
        parts = [
            f"{name} [{localized_evidence(evidence, language)}]",
            cardinality_label(relation),
        ]
        joins = join_label(relation)
        if joins:
            parts.append(joins)
        attributes = [f'label="{dot_escape(chr(10).join(parts))}"']
        if evidence == "proposed":
            attributes.append('style="dashed"')
        elif evidence == "inferred":
            attributes.append('style="dotted"')
        elif evidence not in {"declared", "observed"}:
            attributes.extend(['style="dashed"', 'color="#94a3b8"'])
        lines.append(f"  {ids[source]} -> {ids[target]} [{', '.join(attributes)}];")
    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        snapshot = load_snapshot(args.input)
        report = profile(snapshot)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.format == "markdown":
        output = markdown(report)
    elif args.format == "mermaid":
        output = mermaid(
            snapshot,
            report,
            args.diagram_detail,
            args.diagram_direction,
            args.language,
        )
    elif args.format == "dot":
        output = dot(
            snapshot,
            report,
            args.diagram_detail,
            args.diagram_direction,
            args.language,
        )
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 2 if report["validation"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
