# Semantic Ontology ML

An agent skill for using ontology as the semantic control plane for exploratory analysis and machine learning.

The skill discovers and validates what rows, fields, entities, events, relationships, units, times, and outcomes mean before compiling those semantics into leakage-safe feature engineering, problem routing, validation, modeling, and evaluation choices.

## What it provides

- Evidence-labeled semantics: declared, observed, inferred, and proposed
- Dataset profiling for CSV, TSV, JSON, JSONL/NDJSON, and Parquet
- A provider-neutral semantic contract for datasets, entities, fields, relations, time, units, roles, targets, and provenance
- Ontology validation and dependency-free Mermaid or Graphviz DOT diagrams
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
tests/test_profile_ontology_diagrams.py
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
  --format markdown \
  --output semantic-profile.md
```

Omit roles that are not known. The profiler reports candidates instead of silently treating statistical patterns as business truth.

## Ontology profiling and diagrams

```bash
python scripts/profile_ontology.py ontology.json \
  --format markdown \
  --output ontology-profile.md

python scripts/profile_ontology.py ontology.json \
  --format mermaid \
  --diagram-detail fields \
  --diagram-direction LR \
  --output ontology-diagram.md
```

The profiler accepts the provider-neutral `entity_types`/`fields`/`relations` shape and legacy `object_types`/`properties`/`link_types` snapshots.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Safety and interpretation

This skill begins read-only and keeps credentials out of artifacts. It does not promote candidate identifiers, targets, timestamps, causal relationships, sensitive fields, or null meanings to declared truth without evidence. Source-system writes, governed-data exports, deployments, and model write-backs require explicit authorization.
