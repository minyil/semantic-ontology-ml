# Ontology view routing

Treat an ontology diagram as a task-specific projection of the semantic contract. Preserve the canonical entity/relation ontology, then select views that answer the reader's question.

## Contents

1. Request interface
2. Automatic routing
3. View construction
4. Evidence and claim rules
5. Semantic-view JSON
6. Rendering and completion gates

## 1. Request interface

Accept natural-language equivalents of these controls:

```yaml
diagram_intent: auto
diagram_question: null
evidence_scope: include_inferred
output_language: zh-Hant-TW
```

Supported intents are `auto`, `structural`, `semantic-role`, `process`, `temporal`, `analytical`, `statistical`, `decision`, and `relational`.

Use the sibling contract in `domain-knowledge-ontology.md` when the question needs explicit mechanisms, candidate causes, events, risks, verification actions, goals, or a focused concept review. Keep the `process` task view for a compact, data-linked projection of process groups; use the domain route for a richer explanatory graph with concept kinds, evidence sources, confidence, and installation-specific confirmation.

Default `output_language` to `zh-Hant-TW`. Localize every user-facing title, label, legend, annotation, support explanation, and review item to Traditional Chinese unless the user explicitly requests another language. Keep normalized field IDs, source-native names, JSON keys, code, formulas, metric symbols, and units stable for traceability.

Supported evidence scopes are:

- `declared_only`: declared claims only;
- `declared_observed`: declared and measured claims;
- `include_inferred`: declared, observed, and inferred claims; use this default for semantic discovery;
- `include_proposed`: all evidence classes; use when analysis or decision proposals are requested.

Honor an explicit intent. Under `auto`, select the smallest view set that answers the business or analytical question. Ask for clarification only when different choices would materially change the decision; otherwise render the best candidate and label uncertainty.

## 2. Automatic routing

| Signal | Primary view | Add when useful |
|---|---|---|
| Multiple tables, keys, joins, or graph paths | `structural` or `relational` | `temporal` for time-valid joins |
| One flat cross-sectional table | `semantic-role` | `analytical` when a target is declared |
| Process, IoT, sensor, operations, or workflow series | `process` | `temporal`; `statistical` only for measured associations |
| Forecast, event, lag, window, or availability question | `temporal` | `analytical` for target/feature lineage |
| Supervised target, feature engineering, or leakage review | `analytical` | `temporal`; `semantic-role` for a flat table |
| Correlation, cluster, anomaly, or unsupervised structure | `statistical` | `semantic-role`; `temporal` for series |
| Intervention, optimization, constraints, or trade-offs | `decision` | `analytical` for predictive inputs |

For an ontology-diagram request, deliver a canonical structural view plus at least one task view when both add distinct information. A single flat table with no declared relations normally needs `semantic-role` or another task view; a field box alone is not a useful account of meaning.

## 3. View construction

Construct views from the stable semantic contract and analysis evidence:

- `structural`: entities, fields, keys, joins, and measured cardinalities;
- `semantic-role`: group fields by identifier, time, input, state, measure, category, target candidate, policy, and sensitive role;
- `process`: group observations into inputs, controls, equipment/load, process states, transformations, outputs, and quality candidates;
- `temporal`: show event, effective, observation, availability, and target clocks plus lags, windows, cadence, and horizons;
- `analytical`: show source fields, derived features, exclusions, targets, splits, and leakage boundaries;
- `statistical`: show only measured, scoped, and sensitivity-checked associations or anomaly/cluster relationships;
- `decision`: show predictions, decision variables, objectives, constraints, utilities, actions, and feedback;
- `relational`: show entity paths, join keys, direction, cardinality, temporal validity, and aggregation boundaries.

Keep task-view nodes as semantic groups when field-level boxes would obscure the relationship. Put the member field names inside each group so the view stays traceable to the contract.

## 4. Evidence and claim rules

Every node, member, and edge carries `evidence`: `declared`, `observed`, `inferred`, or `proposed`.

Every edge carries a `claim_type`:

- `structural`: key, membership, or containment relation;
- `association`: measured non-causal statistical relation;
- `temporal`: ordering, lag, availability, or horizon;
- `lineage`: source-to-feature/target/decision derivation;
- `process_flow`: domain-confirmed material, energy, or workflow flow;
- `hypothesis`: candidate domain influence or conceptual relation;
- `constraint`: logical, policy, physical, or optimization constraint;
- `causal`: explicitly supported causal relation.

Use `causal: false` for associations and hypotheses. Permit `causal: true` only with declared domain evidence or observed causal-design evidence; record the design under `support.design`. Arrow direction may express process, temporal, or lineage order without asserting causality.

Every observed edge includes `support.metric`, `support.value`, `support.n`, and `support.scope`. Add lag, filter, confidence interval, causal design, or sensitivity result when relevant. Keep statistical associations out of canonical `relations`.

Render evidence redundantly in text and line style:

- declared: solid dark line;
- observed: blue dashed line with measured support;
- inferred: amber dashed line;
- proposed: gray dotted line.

## 5. Semantic-view JSON

Store each non-structural projection as a sibling artifact, not as source-owned ontology truth:

```json
{
  "view_version": "1.0",
  "language": "zh-Hant-TW",
  "name": "水泥煅燒製程語意圖",
  "view_type": "process",
  "question": "哪些製程群組可能與游離氧化鈣有關？",
  "direction": "LR",
  "evidence_scope": "include_inferred",
  "ontology_digest": "sha256 of the canonical ontology snapshot",
  "nodes": [
    {
      "id": "inputs",
      "label": "原料與能源投入",
      "kind": "process_input",
      "evidence": "inferred",
      "members": [
        {"name": "feed_rate_feedback", "evidence": "inferred"},
        {"name": "calciner_coal_feed_feedback", "evidence": "inferred"}
      ]
    },
    {
      "id": "thermal_state",
      "label": "熱工狀態",
      "kind": "process_state",
      "evidence": "inferred",
      "members": [
        {"name": "kiln_tail_temperature_mean", "evidence": "inferred"}
      ]
    }
  ],
  "edges": [
    {
      "source": "inputs",
      "target": "thermal_state",
      "relation": "候選影響",
      "claim_type": "hypothesis",
      "evidence": "inferred",
      "directed": true,
      "causal": false
    }
  ],
  "notes": ["將假設升格為正式關係前，需由領域專家審查。"]
}
```

Reference canonical fields by normalized name. Preserve source names in the semantic contract instead of duplicating mappings in every view.

## 6. Rendering and completion gates

Render a task view with:

```bash
python scripts/render_semantic_view.py semantic-view.json \
  --format mermaid \
  --output task-semantic-view.md
```

The renderer defaults to `zh-Hant-TW`. Override only when the user requests another language:

```bash
python scripts/render_semantic_view.py semantic-view.json \
  --language en \
  --format mermaid \
  --output task-semantic-view-en.md
```

Override evidence at delivery time when needed:

```bash
python scripts/render_semantic_view.py semantic-view.json \
  --evidence-scope declared_only \
  --format dot \
  --output declared-view.dot
```

Complete the diagram step only when:

1. every visible node and edge has an evidence class;
2. every observed edge has reproducible support and scope;
3. every arrow's direction has a structural, temporal, lineage, process-flow, or explicitly causal meaning;
4. inferred/proposed relations remain outside canonical source relations;
5. the selected view answers the stated question without requiring the reader to decode a field inventory;
6. a legend and unresolved review items accompany the diagram;
7. every user-facing string uses the selected output language while stable identifiers remain unchanged.
