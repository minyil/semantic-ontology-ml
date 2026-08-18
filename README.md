# Semantic Ontology ML

An agent skill for using ontology as the semantic control plane for exploratory analysis and machine learning.

The skill discovers and validates what rows, fields, entities, events, relationships, units, times, and outcomes mean before compiling those semantics into leakage-safe feature engineering, problem routing, validation, modeling, and evaluation choices.

## What it provides

- Evidence-labeled semantics: declared, observed, inferred, and proposed
- Traditional Chinese (`zh-Hant-TW`) user-facing reports and diagrams by default, with explicit language override support
- Canonical finding registries and report-integrity validation that preserve summary coverage, key values, and semantic warnings across languages
- Dataset profiling for CSV, TSV, JSON, JSONL/NDJSON, and Parquet
- A provider-neutral semantic contract for datasets, entities, fields, relations, time, units, roles, targets, and provenance
- Automatic routing for structural, semantic-role, process, temporal, analytical, statistical, decision, and relational ontology views
- Ontology validation and dependency-free Mermaid or Graphviz DOT diagrams with evidence-aware task views
- Routing for target-free exploration, single-target, multi-output, multilabel, multitask, and multi-objective problems
- Leakage-safe feature lineage, deployment-aware validation, baselines, ablations, and auditable evidence bundles
- Optional adapter guidance for Palantir Foundry, LinkML, RDF, SQL catalogs, and hand-authored metadata

## Skill layout

```text
SKILL.md
agents/openai.yaml
references/
scripts/profile_dataset.py
scripts/profile_ontology.py
scripts/render_semantic_view.py
scripts/validate_report_integrity.py
tests/test_profile_ontology_diagrams.py
tests/test_render_semantic_view.py
tests/test_validate_report_integrity.py
```

Start with [`SKILL.md`](SKILL.md). It routes each request to the relevant reference documents and scripts.

## Dataset profiling

```bash
python scripts/profile_dataset.py data.csv \
  --target churned \
  --entity-column customer_id \
  --time-column observed_at \
  --sample-strategy reservoir \
  --sample-seed 17 \
  --format json \
  --output semantic-profile.json
```

Omit roles that are not known. The profiler reports candidates instead of silently treating statistical patterns as business truth. Treat profiler JSON as internal evidence, then author the user-facing semantic and EDA reports in the selected language.

## Ontology profiling and diagrams

```bash
python scripts/profile_ontology.py ontology.json \
  --format json \
  --output ontology-profile.json

python scripts/profile_ontology.py ontology.json \
  --format mermaid \
  --language zh-Hant-TW \
  --diagram-detail fields \
  --diagram-direction LR \
  --output ontology-diagram.md
```

The profiler accepts the provider-neutral `entity_types`/`fields`/`relations` shape and legacy `object_types`/`properties`/`link_types` snapshots.

For task-specific views, write a semantic-view JSON using [`references/diagram-routing.md`](references/diagram-routing.md), then render it separately from the canonical ontology:

```bash
python scripts/render_semantic_view.py semantic-view.json \
  --format mermaid \
  --output task-semantic-view.md
```

`diagram_intent: auto` is the default. Explicit intents and evidence scopes override automatic routing without changing the canonical semantic contract.

User-facing report prose, diagram titles, labels, legends, annotations, and review items default to Traditional Chinese. Source-native field names, normalized IDs, JSON keys, code, formulas, metric symbols, and units stay unchanged for traceability. Use `--language en` with either diagram renderer only when English output is explicitly requested.

For substantive reports, create a canonical finding registry, add invisible finding markers to each localized Markdown report, and validate coverage and required values:

```bash
python scripts/validate_report_integrity.py finding-registry.json \
  report-zh-Hant-TW.annotated.md \
  --clean-output report-zh-Hant-TW.md
```

The annotated report and registry are internal audit artifacts. Deliver the clean output so users never see validation markers.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Safety and interpretation

This skill begins read-only and keeps credentials out of artifacts. It does not promote candidate identifiers, targets, timestamps, causal relationships, sensitive fields, or null meanings to declared truth without evidence. Source-system writes, governed-data exports, deployments, and model write-backs require explicit authorization.
