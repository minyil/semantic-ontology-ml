#!/usr/bin/env python3
"""Create an evidence-labeled semantic profile for a local tabular dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


IDENTIFIER_HINTS = re.compile(r"(^|[_ -])(id|key|uuid|guid|rid)($|[_ -])", re.I)
TIME_HINTS = re.compile(
    r"(^|[_ -])(at|date|datetime|day|month|period|time|timestamp|week|year)($|[_ -])",
    re.I,
)
CATEGORY_HINTS = re.compile(
    r"(^|[_ -])(category|class|code|country|currency|grade|group|segment|state|status|type)($|[_ -])",
    re.I,
)
TEXT_HINTS = re.compile(r"comment|description|message|note|reason|review|summary|text", re.I)
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
INTEGER_RE = re.compile(r"^[+-]?\d+$")
REAL_RE = re.compile(
    r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$"
)
BOOLEAN_STRINGS = {"true", "false"}
DEFAULT_NULLS = {"", "na", "n/a", "nan", "none", "null"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile dataset values and propose evidence-labeled semantic roles."
    )
    parser.add_argument("input", help="CSV, TSV, JSON, JSONL/NDJSON, or Parquet path")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Declared target column; repeat for multiple targets",
    )
    parser.add_argument(
        "--entity-column",
        action="append",
        default=[],
        help="Declared entity/group key column; repeat for a composite key",
    )
    parser.add_argument("--time-column", help="Declared observation/as-of time column")
    parser.add_argument(
        "--sample-size", type=int, default=100000, help="Maximum rows to profile"
    )
    parser.add_argument(
        "--sample-strategy",
        choices=("head", "reservoir"),
        default="head",
        help="Use the first rows or a deterministic reservoir sample",
    )
    parser.add_argument(
        "--sample-seed", type=int, default=17, help="Seed for reservoir sampling"
    )
    parser.add_argument("--delimiter", help="Override CSV/TSV delimiter")
    parser.add_argument("--encoding", default="utf-8", help="Text-file encoding")
    parser.add_argument(
        "--null-token", action="append", default=[], help="Additional null token"
    )
    parser.add_argument("--dataset-name", help="Stable dataset name for the report")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", help="Write the report instead of stdout")
    args = parser.parse_args()
    if args.sample_size <= 0:
        parser.error("--sample-size must be positive")
    return args


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_row(row: dict[Any, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items() if key is not None}


def sample_rows(
    rows: Iterable[dict[str, Any]], limit: int, strategy: str, seed: int
) -> tuple[list[dict[str, Any]], bool, int | None]:
    result: list[dict[str, Any]] = []
    if strategy == "head":
        for row in rows:
            if len(result) >= limit:
                return result, True, None
            result.append(normalize_row(row))
        return result, False, len(result)

    rng = random.Random(seed)
    total = 0
    for row in rows:
        normalized = normalize_row(row)
        total += 1
        if len(result) < limit:
            result.append(normalized)
            continue
        replacement = rng.randrange(total)
        if replacement < limit:
            result[replacement] = normalized
    return result, total > limit, total


def load_delimited(
    path: Path,
    limit: int,
    encoding: str,
    delimiter: str | None,
    strategy: str,
    seed: int,
) -> tuple[list[dict[str, Any]], bool, list[str], int | None]:
    with path.open("r", encoding=encoding, newline="") as stream:
        if delimiter is None:
            sample = stream.read(8192)
            stream.seek(0)
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
            except csv.Error:
                delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        reader = csv.DictReader(stream, delimiter=delimiter)
        rows, truncated, total = sample_rows(reader, limit, strategy, seed)
        return rows, truncated, [str(name) for name in (reader.fieldnames or [])], total


def load_json(
    path: Path, limit: int, encoding: str, strategy: str, seed: int
) -> tuple[list[dict[str, Any]], bool, list[str], int]:
    value = json.loads(path.read_text(encoding=encoding))
    if isinstance(value, dict) and isinstance(value.get("records"), list):
        value = value["records"]
    if not isinstance(value, list):
        raise ValueError("JSON must be a list of objects or an object with a records list")
    if any(not isinstance(item, dict) for item in value[: limit + 1]):
        raise ValueError("every profiled JSON record must be an object")
    source_rows = value
    if strategy == "reservoir" and len(value) > limit:
        indices = sorted(random.Random(seed).sample(range(len(value)), limit))
        source_rows = [value[index] for index in indices]
    rows = [normalize_row(item) for item in source_rows[:limit]]
    return rows, len(value) > limit, ordered_columns(rows), len(value)


def load_json_lines(
    path: Path, limit: int, encoding: str, strategy: str, seed: int
) -> tuple[list[dict[str, Any]], bool, list[str], int | None]:
    def records() -> Iterable[dict[str, Any]]:
        with path.open("r", encoding=encoding) as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"line {line_number} must contain a JSON object")
                yield item

    rows, truncated, total = sample_rows(records(), limit, strategy, seed)
    return rows, truncated, ordered_columns(rows), total


def load_parquet(
    path: Path, limit: int, strategy: str, seed: int
) -> tuple[list[dict[str, Any]], bool, list[str], int]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise ValueError("Parquet input requires pandas and pyarrow or fastparquet") from exc
    frame = pd.read_parquet(path)
    columns = [str(value) for value in frame.columns]
    sampled = frame.head(limit)
    if strategy == "reservoir" and len(frame) > limit:
        sampled = frame.sample(n=limit, random_state=seed).sort_index()
    rows = [normalize_row(item) for item in sampled.to_dict(orient="records")]
    return rows, len(frame) > limit, columns, len(frame)


def ordered_columns(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        for name in row:
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def load_dataset(
    path: Path,
    limit: int,
    encoding: str,
    delimiter: str | None,
    strategy: str,
    seed: int,
) -> tuple[list[dict[str, Any]], bool, list[str], str, int | None]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        rows, truncated, columns, total = load_delimited(
            path, limit, encoding, delimiter, strategy, seed
        )
        return rows, truncated, columns, suffix[1:], total
    if suffix == ".json":
        rows, truncated, columns, total = load_json(path, limit, encoding, strategy, seed)
        return rows, truncated, columns, "json", total
    if suffix in {".jsonl", ".ndjson"}:
        rows, truncated, columns, total = load_json_lines(
            path, limit, encoding, strategy, seed
        )
        return rows, truncated, columns, "jsonl", total
    if suffix in {".parquet", ".pq"}:
        rows, truncated, columns, total = load_parquet(path, limit, strategy, seed)
        return rows, truncated, columns, "parquet", total
    raise ValueError(f"unsupported input extension: {suffix or '<none>'}")


def is_missing(value: Any, nulls: set[str]) -> bool:
    if value is None:
        return True
    if type(value).__name__ in {"NAType", "NaTType"}:
        return True
    if isinstance(value, str):
        return value.strip().lower() in nulls
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) < 6 or not any(char in text for char in "-/:T"):
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y/%m/%d", "%Y%m%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue
    return None


def value_shape(value: Any) -> tuple[str, Any]:
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, int):
        return "integer", float(value)
    if isinstance(value, float) and math.isfinite(value):
        return "real", value
    if isinstance(value, (datetime, date)):
        return "datetime", parse_datetime(value)
    if isinstance(value, (dict, list, tuple)):
        return "nested", None
    text = str(value).strip()
    lowered = text.lower()
    if lowered in BOOLEAN_STRINGS:
        return "boolean", lowered == "true"
    unsigned_integer = text.lstrip("+-")
    has_leading_zero = len(unsigned_integer) > 1 and unsigned_integer.startswith("0")
    if INTEGER_RE.fullmatch(text):
        if has_leading_zero:
            return "string", text
        try:
            return "integer", float(text)
        except ValueError:
            pass
    if REAL_RE.fullmatch(text):
        try:
            number = float(text)
            if math.isfinite(number):
                return "real", number
        except ValueError:
            pass
    parsed_time = parse_datetime(text)
    if parsed_time is not None:
        return "datetime", parsed_time
    return "string", text


def add_role(
    roles: list[dict[str, Any]], role: str, evidence: str, confidence: float, reason: str
) -> None:
    if any(item["role"] == role and item["evidence"] == evidence for item in roles):
        return
    item: dict[str, Any] = {"role": role, "evidence": evidence, "reason": reason}
    if evidence in {"inferred", "proposed"}:
        item["confidence"] = round(confidence, 2)
    roles.append(item)


def profile_field(
    name: str,
    rows: list[dict[str, Any]],
    nulls: set[str],
    targets: set[str],
    entity_columns: set[str],
    time_column: str | None,
) -> dict[str, Any]:
    type_counts: Counter[str] = Counter()
    distinct: set[str] = set()
    non_null = 0
    numeric_count = 0
    numeric_values: set[float] = set()
    numeric_sum = 0.0
    numeric_min: float | None = None
    numeric_max: float | None = None
    text_length_sum = 0
    text_length_min: int | None = None
    text_length_max: int | None = None
    time_min: datetime | None = None
    time_max: datetime | None = None

    for row in rows:
        value = row.get(name)
        if is_missing(value, nulls):
            continue
        non_null += 1
        shape, parsed = value_shape(value)
        type_counts[shape] += 1
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        distinct.add(canonical)
        if shape in {"integer", "real"} and isinstance(parsed, float):
            numeric_count += 1
            numeric_values.add(parsed)
            numeric_sum += parsed
            numeric_min = parsed if numeric_min is None else min(numeric_min, parsed)
            numeric_max = parsed if numeric_max is None else max(numeric_max, parsed)
        if shape == "string":
            length = len(str(parsed))
            text_length_sum += length
            text_length_min = length if text_length_min is None else min(text_length_min, length)
            text_length_max = length if text_length_max is None else max(text_length_max, length)
        if shape == "datetime" and isinstance(parsed, datetime):
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            time_min = parsed if time_min is None else min(time_min, parsed)
            time_max = parsed if time_max is None else max(time_max, parsed)

    row_count = len(rows)
    missing = row_count - non_null
    distinct_count = len(distinct)
    unique_ratio = distinct_count / non_null if non_null else 0.0
    dominant_shape = "unknown"
    dominant_ratio = 0.0
    if type_counts:
        dominant_shape, dominant_count = type_counts.most_common(1)[0]
        dominant_ratio = dominant_count / non_null
        numeric_ratio = (type_counts["integer"] + type_counts["real"]) / non_null
        if numeric_ratio >= 0.95:
            dominant_shape = (
                "integer" if type_counts["real"] == 0 else "numeric"
            )
            dominant_ratio = numeric_ratio
    physical_profile = dominant_shape if dominant_ratio >= 0.95 else "mixed"
    roles: list[dict[str, Any]] = []

    if name in targets:
        add_role(roles, "target", "declared", 1.0, "supplied with --target")
    if name in entity_columns:
        add_role(roles, "entity_key", "declared", 1.0, "supplied with --entity-column")
    if name == time_column:
        add_role(
            roles, "observation_time", "declared", 1.0, "supplied with --time-column"
        )

    if IDENTIFIER_HINTS.search(name) and non_null and unique_ratio >= 0.8:
        add_role(
            roles,
            "identifier",
            "inferred",
            min(0.98, 0.65 + unique_ratio * 0.3),
            "identifier-like name and high sampled uniqueness",
        )
    if dominant_shape == "datetime" and dominant_ratio >= 0.8:
        add_role(
            roles,
            "temporal",
            "inferred",
            min(0.97, dominant_ratio),
            "most non-null values parse as datetime",
        )
    elif TIME_HINTS.search(name):
        add_role(
            roles,
            "temporal_candidate",
            "inferred",
            0.45,
            "time-like field name but values do not strongly confirm it",
        )
    if dominant_shape == "boolean" and dominant_ratio >= 0.95:
        add_role(roles, "boolean", "inferred", dominant_ratio, "boolean-shaped values")
    if dominant_shape in {"integer", "real", "numeric"} and dominant_ratio >= 0.9:
        low_cardinality = distinct_count <= max(20, int(math.sqrt(max(non_null, 1))))
        if numeric_values and numeric_values <= {0.0, 1.0}:
            add_role(
                roles,
                "boolean",
                "inferred",
                0.85,
                "numeric values are limited to zero and one",
            )
        elif low_cardinality and CATEGORY_HINTS.search(name):
            add_role(
                roles,
                "category",
                "inferred",
                0.8,
                "numeric storage, low cardinality, and category-like name",
            )
        elif low_cardinality and not any(
            item["role"] in {"identifier", "entity_key"} for item in roles
        ):
            add_role(
                roles,
                "category_candidate",
                "inferred",
                0.55,
                "low-cardinality numeric values may encode classes or discrete measures",
            )
            add_role(
                roles,
                "measure_candidate",
                "inferred",
                0.5,
                "numeric values may instead be a discrete measure; confirm meaning",
            )
        elif not any(item["role"] in {"identifier", "entity_key"} for item in roles):
            add_role(
                roles,
                "measure",
                "inferred",
                min(0.95, dominant_ratio),
                "predominantly numeric values; unit and scale remain unknown",
            )
    if dominant_shape == "string" and dominant_ratio >= 0.8:
        average_length = text_length_sum / type_counts["string"] if type_counts["string"] else 0
        categorical = distinct_count <= max(20, int(math.sqrt(max(non_null, 1))))
        if categorical and not TEXT_HINTS.search(name):
            add_role(
                roles,
                "category",
                "inferred",
                0.75,
                "string values have low sampled cardinality",
            )
        elif not any(item["role"] in {"identifier", "entity_key"} for item in roles):
            add_role(
                roles,
                "text",
                "inferred",
                0.8 if average_length >= 20 or TEXT_HINTS.search(name) else 0.6,
                "variable string content suggests free text",
            )
    if SENSITIVE_HINTS.search(name):
        add_role(
            roles,
            "sensitive_candidate",
            "inferred",
            0.6,
            "field name requires privacy/policy review",
        )
    if OUTCOME_HINTS.search(name) and name not in targets:
        add_role(
            roles,
            "outcome_or_leakage_candidate",
            "inferred",
            0.55,
            "outcome-like name; not an approved target",
        )

    numeric_summary = None
    if numeric_count:
        numeric_summary = {
            "count": numeric_count,
            "min": numeric_min,
            "max": numeric_max,
            "mean": numeric_sum / numeric_count,
        }
    text_summary = None
    if type_counts["string"]:
        text_summary = {
            "count": type_counts["string"],
            "length_min": text_length_min,
            "length_max": text_length_max,
            "length_mean": text_length_sum / type_counts["string"],
        }
    datetime_summary = None
    if time_min is not None and time_max is not None:
        datetime_summary = {"min": time_min.isoformat(), "max": time_max.isoformat()}
    return {
        "name": name,
        "observed": {
            "profiled_rows": row_count,
            "non_null_count": non_null,
            "missing_count": missing,
            "missing_ratio": round(missing / row_count, 6) if row_count else 0.0,
            "distinct_count": distinct_count,
            "unique_ratio": round(unique_ratio, 6),
            "value_shape_counts": dict(sorted(type_counts.items())),
            "dominant_shape": dominant_shape,
            "dominant_ratio": round(dominant_ratio, 6),
            "physical_profile": physical_profile,
            "numeric": numeric_summary,
            "text": text_summary,
            "datetime": datetime_summary,
        },
        "semantic_roles": roles,
    }


def infer_shape(
    profiles: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    entity_columns: list[str],
    time_column: str | None,
) -> list[dict[str, Any]]:
    by_name = {item["name"]: item for item in profiles}
    time_candidates = [
        item["name"]
        for item in profiles
        if any(
            role["role"] in {"temporal", "observation_time"}
            for role in item["semantic_roles"]
        )
    ]
    candidates: list[dict[str, Any]] = []
    chosen_time = time_column or (time_candidates[0] if len(time_candidates) == 1 else None)
    if chosen_time:
        evidence = "declared" if time_column else "inferred"
        if entity_columns and all(column in by_name for column in entity_columns):
            entity_values = {
                tuple(str(row.get(column, "")) for column in entity_columns)
                for row in rows
            }
            entity_unique = len(entity_values) / len(rows) if rows else 0.0
            shape = "panel_or_event" if entity_unique < 0.99 else "time_indexed_snapshot"
            reason = (
                "time plus repeated entity key"
                if entity_unique < 0.99
                else "time plus mostly unique entity key"
            )
        else:
            shape = "time_series_candidate"
            reason = "one usable time field; entity/grain is not declared"
        candidates.append(
            {
                "shape": shape,
                "evidence": evidence,
                "time_field": chosen_time,
                "entity_fields": entity_columns,
                "reason": reason,
            }
        )
    else:
        candidates.append(
            {
                "shape": "cross_sectional_candidate",
                "evidence": "inferred",
                "reason": "no single confirmed time field",
            }
        )
    return candidates


def build_questions(
    profiles: list[dict[str, Any]],
    targets: list[str],
    entity_columns: list[str],
    time: str | None,
) -> list[str]:
    questions = ["What real-world entity or event does one row represent?"]
    if not entity_columns:
        questions.append("Which field or field combination is the stable key at that grain?")
    if not time:
        questions.append(
            "Which clocks represent event, observation/as-of, availability, and target time?"
        )
    if not targets:
        questions.append(
            "Is this target-free analysis, or which outcome(s) and decision are authorized?"
        )
    elif len(targets) > 1:
        questions.append(
            "Are the targets joint outputs, multilabels, separate tasks, or competing objectives with constraints?"
        )
    if any(item["observed"]["missing_count"] for item in profiles):
        questions.append("What do nulls, defaults, zeros, and sentinel values mean by field?")
    if any(
        role["role"] == "measure"
        for item in profiles
        for role in item["semantic_roles"]
    ):
        questions.append("What units, scales, currencies, and valid ranges apply to measures?")
    if any(
        role["role"] == "sensitive_candidate"
        for item in profiles
        for role in item["semantic_roles"]
    ):
        questions.append("Which fields are sensitive, prohibited, or restricted to fairness auditing?")
    return questions


def profile(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.input)
    if not path.is_file():
        raise ValueError(f"input file does not exist: {path}")
    rows, truncated, columns, source_format, exact_row_count = load_dataset(
        path,
        args.sample_size,
        args.encoding,
        args.delimiter,
        args.sample_strategy,
        args.sample_seed,
    )
    columns = list(dict.fromkeys(columns + ordered_columns(rows)))
    explicit = [*args.target]
    explicit.extend(args.entity_column)
    if args.time_column:
        explicit.append(args.time_column)
    missing_explicit = sorted(set(explicit) - set(columns))
    errors = [f"declared column is absent: {name}" for name in missing_explicit]
    nulls = DEFAULT_NULLS | {item.strip().lower() for item in args.null_token}
    profiles = [
        profile_field(
            name,
            rows,
            nulls,
            set(args.target),
            set(args.entity_column),
            args.time_column,
        )
        for name in columns
    ]
    warnings: list[str] = []
    if not rows:
        warnings.append("no data rows were available for profiling")
    if truncated:
        warnings.append(
            f"value statistics are based on a bounded {args.sample_strategy} sample, not all rows"
        )
    for item in profiles:
        observed = item["observed"]
        if observed["physical_profile"] == "mixed":
            warnings.append(f"{item['name']} has mixed value shapes")
        if item["name"] in args.target and observed["missing_count"]:
            warnings.append(f"declared target {item['name']} contains missing values")
    target_mode = "no_target"
    if len(args.target) == 1:
        target_mode = "single_target_requires_task_subtype"
    elif len(args.target) > 1:
        target_mode = "multiple_targets_require_mode_confirmation"
    target_mode_candidates: list[str] = []
    if len(args.target) > 1:
        by_name = {item["name"]: item for item in profiles}
        target_roles = {
            target: {role["role"] for role in by_name[target]["semantic_roles"]}
            for target in args.target
            if target in by_name
        }
        if len(target_roles) == len(args.target) and all(
            "boolean" in roles for roles in target_roles.values()
        ):
            target_mode_candidates = ["multilabel", "multi_output"]
        else:
            target_mode_candidates = ["multi_output", "multitask"]
    return {
        "dataset": {
            "name": args.dataset_name or path.stem,
            "source_path": str(path.resolve()),
            "source_format": source_format,
            "sha256": sha256_file(path),
            "rows_profiled": len(rows),
            "row_count_exact": exact_row_count,
            "sample_truncated": truncated,
            "sample_strategy": args.sample_strategy,
            "sample_seed": args.sample_seed if args.sample_strategy == "reservoir" else None,
            "column_count": len(columns),
        },
        "explicit_semantics": {
            "targets": args.target,
            "entity_columns": args.entity_column,
            "time_column": args.time_column,
        },
        "validation": {"errors": errors, "warnings": warnings},
        "field_profiles": profiles,
        "shape_candidates": infer_shape(
            profiles, rows, args.entity_column, args.time_column
        ),
        "problem_routing": {
            "target_mode": target_mode,
            "target_mode_candidates": target_mode_candidates,
            "note": "Multiple target columns do not by themselves define multi-output, multilabel, multitask, or multi-objective semantics.",
        },
        "confirmation_questions": build_questions(
            profiles, args.target, args.entity_column, args.time_column
        ),
        "interpretation_limits": [
            "Declared CLI roles come from the caller; other roles are inferred review candidates.",
            "Sampled values cannot prove row grain, business meaning, units, target validity, or feature availability.",
            "Sensitive and outcome-like name matches are review cues, not legal or modeling decisions.",
            "The report contains aggregate statistics and no representative raw values by design.",
        ],
    }


def escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown(report: dict[str, Any]) -> str:
    dataset = report["dataset"]
    validation = report["validation"]
    lines = [
        "# Dataset semantic profile",
        "",
        "## Dataset",
        "",
        f"- Name: `{dataset['name']}`",
        f"- Format: {dataset['source_format']}",
        f"- Rows profiled: {dataset['rows_profiled']}",
        f"- Exact row count: {dataset['row_count_exact'] if dataset['row_count_exact'] is not None else 'unknown (sampled)' }",
        f"- Sampling: {dataset['sample_strategy']}"
        + (
            f" (seed {dataset['sample_seed']})"
            if dataset["sample_seed"] is not None
            else ""
        ),
        f"- Columns: {dataset['column_count']}",
        f"- SHA-256: `{dataset['sha256']}`",
        "",
        "## Validation",
        "",
    ]
    if not validation["errors"] and not validation["warnings"]:
        lines.append("- No structural warnings detected.")
    lines.extend(f"- ERROR: {item}" for item in validation["errors"])
    lines.extend(f"- WARNING: {item}" for item in validation["warnings"])
    lines.extend(
        [
            "",
            "## Field profiles",
            "",
            "| Field | Physical profile | Missing | Distinct | Semantic roles |",
            "|---|---|---:|---:|---|",
        ]
    )
    for item in report["field_profiles"]:
        observed = item["observed"]
        roles = "; ".join(
            f"{role['role']} ({role['evidence']})" for role in item["semantic_roles"]
        ) or "unresolved"
        lines.append(
            f"| `{escape_cell(item['name'])}` | {observed['physical_profile']} | "
            f"{observed['missing_ratio']:.1%} | {observed['distinct_count']} | {escape_cell(roles)} |"
        )
    lines.extend(["", "## Shape and problem routing", ""])
    for item in report["shape_candidates"]:
        lines.append(
            f"- {item['shape']} ({item['evidence']}): {item['reason']}"
        )
    lines.append(f"- Target mode: {report['problem_routing']['target_mode']}")
    if report["problem_routing"]["target_mode_candidates"]:
        lines.append(
            "- Target mode candidates: "
            + ", ".join(report["problem_routing"]["target_mode_candidates"])
        )
    lines.append(f"- {report['problem_routing']['note']}")
    lines.extend(["", "## Confirmation questions", ""])
    lines.extend(f"- {item}" for item in report["confirmation_questions"])
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {item}" for item in report["interpretation_limits"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        report = profile(args)
    except (OSError, ValueError, json.JSONDecodeError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
    if args.format == "markdown":
        output = markdown(report)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 2 if report["validation"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
