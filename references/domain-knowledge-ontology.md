# Domain knowledge ontology graphs

Use this route when the user wants a concept map that explains a process, mechanism, event, risk, constraint, or operational decision. Keep it separate from the structural entity/relation ontology: a join path says how records connect, while a domain relationship says how a domain owner, source document, dataset observation, or analyst believes concepts relate.

## Contents

1. Evidence boundary
2. Canonical shape
3. Concept kinds and lanes
4. Relationship predicates
5. Synthesis workflow
6. Renderer and language

## Evidence boundary

Every concept and relationship has one evidence class:

- `declared`: supplied by a domain owner, plant-specific controlled document, trusted metadata, or other authoritative source;
- `observed`: measured in the in-scope dataset or event analysis;
- `inferred`: candidate meaning or mechanism supported by names, patterns, or general domain knowledge;
- `proposed`: a hypothesis, action, risk framing, or analysis choice awaiting validation.

General vendor or regulatory knowledge may support an `inferred` mechanism. It becomes `declared` for a specific installation only when plant-specific evidence or a domain owner confirms it. Temporal precedence is `observed`; it is not a causal relationship by itself.

## Canonical shape

```json
{
  "contract_version": "1.0",
  "domain_model": {
    "name": "Industrial process anomaly review",
    "description": "Explains the event with process and evidence concepts.",
    "analysis_goal": "Identify the disturbance and the evidence required to confirm it",
    "focus_concept": "event"
  },
  "concepts": [
    {
      "id": "airflow",
      "name": "System airflow",
      "kind": "control_variable",
      "description": "Measured airflow associated with the process train.",
      "evidence": "observed",
      "source_fields": ["airflow_tag"],
      "source_refs": ["dataset_profile"],
      "details": ["Changed at event onset"],
      "review_status": "candidate"
    },
    {
      "id": "draft_balance",
      "name": "Draft and pressure balance",
      "kind": "mechanism",
      "description": "Candidate mechanism linking flow, resistance, and pressure.",
      "evidence": "inferred",
      "confidence": 0.75,
      "source_refs": ["domain_reference"],
      "review_status": "candidate"
    }
  ],
  "relationships": [
    {
      "id": "airflow_indicates_draft",
      "source": "airflow",
      "target": "draft_balance",
      "predicate": "indicates",
      "label": "indicates operating state",
      "evidence": "inferred",
      "confidence": 0.75,
      "temporal_lag": null,
      "source_refs": ["domain_reference"],
      "plant_confirmed": false
    }
  ],
  "evidence_sources": [
    {
      "id": "dataset_profile",
      "kind": "dataset",
      "authority": "observed",
      "locator": "semantic-profile.md",
      "description": "Profile of the in-scope measurements"
    },
    {
      "id": "domain_reference",
      "kind": "domain_document",
      "authority": "general_domain",
      "locator": "non-secret source reference",
      "description": "General process reference, not plant-specific truth"
    }
  ],
  "unresolved_questions": [
    "Which equipment boundary and engineering unit apply to airflow_tag?"
  ]
}
```

## Concept kinds and lanes

| Kind | Default lane | Meaning |
|---|---|---|
| `control_variable` | Inputs & controls | Measured or commanded operating variable |
| `unmeasured_action` | Inputs & controls | Candidate operator, control-system, or equipment action absent from the dataset |
| `mechanism` | Mechanisms | Physical, chemical, business, or operational mechanism |
| `process_state` | States & observations | Latent or aggregate state of the process |
| `measurement` | States & observations | Direct measurement or grouped indicators |
| `constraint` | States & observations | Declared limit, invariant, or operating envelope |
| `event` | Events, risks & decisions | Observed or declared event |
| `risk` | Events, risks & decisions | Safety, quality, financial, or operational risk |
| `data_quality` | Events, risks & decisions | Measurement quality or semantic conflict |
| `action` | Events, risks & decisions | Verification or mitigation action |
| `goal` | Events, risks & decisions | Decision or analytical objective |

Set `lane` only when the default placement obscures the intended narrative. Supported lanes are `inputs`, `mechanisms`, `observations`, and `decisions`.

## Relationship predicates

Prefer predicates that preserve the evidence boundary:

- structural or observational: `measures`, `indicates`, `precedes`, `co_occurs_with`, `exceeds`, `constrains`;
- mechanism candidates: `influences`, `mediates`, `transports`, `balances`, `may_cause`;
- operational: `requires_validation`, `mitigates`, `supports`, `targets`.

Use `causes` or `prevents` only for `declared` relationships with a source reference. Otherwise use `may_cause` or `influences`. A relationship with `plant_confirmed: true` must be `declared`.

For `inferred` and `proposed` concepts or relationships, provide `confidence` from `0` to `1`. For `declared` and `observed` relationships, provide at least one `source_refs` entry. `temporal_lag` describes an observed or expected lag; it does not prove the mechanism.

## Synthesis workflow

1. Establish the decision, event, process boundary, data sources, and intended audience.
2. Profile supplied data before interpreting it. Preserve source fields and observed timing as measurement concepts.
3. Collect domain sources in this order when available: domain-owner statements; plant-specific P&ID, tag dictionary, control narrative, alarm or operating manual; equipment-vendor documentation; regulator or standards material; general literature.
4. Build separate concepts for measurements, process states, mechanisms, unmeasured actions, risks, and data-quality hypotheses. Do not disguise an unmeasured action as an observation.
5. Write relationships with evidence, confidence, source references, and temporal lag. Use candidate predicates until installation-specific evidence confirms a causal relationship.
6. Run `scripts/render_domain_ontology.py` and review all validation findings. Resolve errors before publishing; keep warnings visible in the review draft.
7. Give the domain owner the review Markdown and rendered graph. Promote a concept or relationship to `declared` only after the owner or a plant-specific controlled source confirms it.

Complete this route when every visible node and arrow has an auditable evidence class, unresolved plant-specific assumptions are listed, and the graph distinguishes what the data shows from what the analyst proposes.

## Renderer and language

Default user-facing review Markdown, diagram chrome, lane labels, evidence labels, annotations, and detail panels to Traditional Chinese (`zh-Hant-TW`). Preserve concept IDs, source field names, JSON keys, predicates, units, and formulas for traceability. Use `--language en` only when the user explicitly requests English.

```bash
python scripts/render_domain_ontology.py domain-ontology.json \
  --format markdown \
  --language zh-Hant-TW \
  --output domain-ontology-review.md

python scripts/render_domain_ontology.py domain-ontology.json \
  --format svg \
  --language zh-Hant-TW \
  --focus event \
  --output domain-ontology.svg

python scripts/render_domain_ontology.py domain-ontology.json \
  --format mermaid \
  --language zh-Hant-TW \
  --output domain-ontology.md
```

The SVG renderer groups concepts into four lanes, colors nodes by concept kind, styles arrows by evidence, and displays a detail panel for `--focus`. Mermaid is the editable fallback. Neither renderer converts a candidate mechanism into causal proof.
