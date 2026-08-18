---
name: semantic-ontology-ml
description: Infer and validate dataset semantics, normalize a provider-neutral ontology, automatically route structural, semantic-role, process, temporal, analytical, statistical, decision, or relational ontology views, and use meaning to drive leakage-safe analysis and modeling. Use for ontology or process-semantic diagrams; CSV, JSON, Parquet, DataFrame-like, time-series, panel, event, relational, graph, numeric, categorical, boolean, datetime, or text data; no-target exploration, single-target prediction, multi-output or multilabel learning, multitask learning, constrained multi-objective optimization; or Palantir Foundry, LinkML, RDF, SQL catalog, and hand-authored metadata adapters.
---

# Semantic Ontology ML

Use ontology as the semantic control plane for analysis. First discover what rows, fields, times, entities, events, relationships, units, and outcomes mean. Then compile those meanings into valid analysis and modeling choices.

Keep four evidence classes separate:

1. **Declared** — supplied by a domain owner or trusted metadata.
2. **Observed** — measured from data values and distributions.
3. **Inferred** — candidate meaning derived from names, types, and patterns.
4. **Proposed** — an analysis, feature, constraint, or model choice.

Never promote a candidate target, identifier, timestamp, causal relationship, sensitive field, or null meaning to declared truth without evidence.

Default every user-facing deliverable to Traditional Chinese (`zh-Hant-TW`) unless the user explicitly requests another language. Write report prose, headings, display labels, legends, annotations, review questions, and diagram text in Traditional Chinese. Preserve source-native field names, normalized identifiers, JSON keys, code, formulas, metric symbols, and units; add Traditional Chinese display labels or explanations instead of translating stable identifiers. Helper-script diagnostics and machine-readable contract keys may remain English, but localize their user-facing interpretation before delivery.

Treat language and format as presentation projections of one canonical finding set. Preserve finding IDs, priority, evidence, key values, scope, limitations, warnings, and executive-summary membership across every projection.

## Route the request

- **Dataset first:** Read `references/dataset-semantic-discovery.md`, inspect the data, and run `scripts/profile_dataset.py`. Use this route when the user provides a table but no ontology.
- **Ontology first:** Normalize existing metadata with `references/semantic-contract.md`, run `scripts/profile_ontology.py`, and render a diagram when entities or relations need visual inspection.
- **Ontology views:** Read `references/diagram-routing.md` completely when a diagram is requested or relationships and meaning need visual explanation. Default to `diagram_intent: auto`; honor an explicit structural, semantic-role, process, temporal, analytical, statistical, decision, or relational intent.
- **Analysis or modeling:** Also read `references/problem-routing.md` and `references/analysis-playbook.md` before engineering features or choosing metrics.
- **Reports or localization:** Read `references/report-integrity.md` completely before writing, translating, or reformatting a substantive analysis report. Build the finding registry before prose, validate an internal annotated report, then publish a separate marker-free report.
- **Tool selection:** Read `references/open-source-tooling.md`. Verify versions, licenses, and current interfaces from primary sources before procurement or implementation decisions.
- **Palantir source:** Also read `references/palantir-integration.md`. Treat it as an input/output adapter, not a core dependency.

## 1. Establish the analysis boundary

Record:

- business question and downstream decision;
- available tables/files and their provenance;
- row/entity/event grain;
- candidate entity keys, event time, observation time, and ingestion/availability time;
- declared targets, objectives, constraints, and known sensitive or prohibited fields;
- deployment/scoring context, if modeling is requested;
- diagram question, intent, and evidence scope when visualization is in scope;
- output language, defaulting to `zh-Hant-TW` unless explicitly overridden;
- allowed reads, exports, writes, and external services.

Begin read-only. Keep credentials out of artifacts. Do not export governed data or mutate a source system without authorization.

Complete this step when the source, intended decision, access boundary, and unknowns are explicit.

## 2. Discover dataset semantics

Profile structure and values before performing substantive EDA. For a supported local file, run:

```bash
python scripts/profile_dataset.py data.csv \
  --target churned \
  --entity-column customer_id \
  --time-column observed_at \
  --format json \
  --output semantic-profile.json
```

Omit options that are not known; the profiler must report candidates rather than silently confirming them. For multiple explicit targets, repeat `--target`.

Treat profiler JSON as working evidence. Author the user-facing semantic profile and analysis report in the selected output language; do not deliver raw English helper-script prose when `zh-Hant-TW` is selected.

Repeat `--entity-column` for a composite entity/series key. For files sorted by time, entity, or outcome, use deterministic `--sample-strategy reservoir --sample-seed <integer>` so a bounded profile is not restricted to the first block; retain `head` only when the prefix itself is the intended population.

Determine:

- table grain and likely entity/event boundaries;
- physical types and candidate semantic roles;
- identifier uniqueness, missingness, cardinality, mixed-type values, units, and null semantics;
- temporal order, sampling cadence, repeated entities, and possible panel/event structure;
- relations between tables, including key compatibility and cardinality;
- text fields, categories, measures, timestamps, geospatial values, sensitive candidates, and outcome-like candidates.

Use `references/dataset-semantic-discovery.md` for confirmation rules and profiler limitations.

Complete this step when each in-scope field has an evidence-backed role or an unresolved question.

## 3. Normalize the ontology

Create a provider-neutral snapshot using `references/semantic-contract.md`. Represent datasets, entity types, fields, relations, events, measures, units, semantic roles, targets, and provenance. Preserve source-native identifiers beside normalized names.

Merge declared metadata with observed profiles without overwriting conflicts. Record conflicts as review items. Model time explicitly: distinguish event time, effective time, observation/as-of time, availability time, and target time.

Run `scripts/profile_ontology.py` for an object/link-oriented snapshot. Treat its role, outcome, and sensitive detections as review queues. Use JSON as internal evidence so helper prose does not leak into a differently localized deliverable:

```bash
python scripts/profile_ontology.py ontology.json \
  --format json \
  --output ontology-profile.json
```

Render the canonical structural ontology as dependency-free Mermaid or Graphviz DOT source:

```bash
python scripts/profile_ontology.py ontology.json \
  --format mermaid \
  --language zh-Hant-TW \
  --diagram-detail fields \
  --diagram-direction LR \
  --output ontology-diagram.md

python scripts/profile_ontology.py ontology.json \
  --format dot \
  --language zh-Hant-TW \
  --output ontology-diagram.dot
```

Use `compact` detail for large ontologies and `fields` when field-level roles fit legibly. Read relationship labels as structural paths, not causal effects: each label includes evidence, cardinality, and join keys; dashed relations are non-declared candidates.

Complete this step when analysis code can depend on one stable semantic contract rather than source-specific schemas.

## 4. Select and render task views

Treat each diagram as a projection of the semantic contract, not as the ontology itself. Keep source-owned entities and relations in the canonical contract; store inferred process groupings, measured associations, analytical lineage, and decision hypotheses in a separate semantic-view JSON artifact.

Follow `references/diagram-routing.md` as the single source of truth for view selection, evidence scopes, the semantic-view schema, edge claims, and completion gates. Under `auto`, choose the smallest view set that answers the question. Use `include_inferred` by default; include proposed claims only when the task asks for analysis or decision proposals.

For a diagram request, deliver the canonical structural view plus at least one task view when they answer different questions. For a flat table with no declared relations, group fields by semantic role or task meaning; make the reader's requested relationships visible rather than ending at a field inventory.

Render a task view with:

```bash
python scripts/render_semantic_view.py semantic-view.json \
  --format mermaid \
  --output task-semantic-view.md
```

Every visible node and edge must carry an evidence class. Give observed associations reproducible metric, sample, and scope support. Use arrow direction only for structural, temporal, lineage, process-flow, constraint, or supported causal meaning; label hypotheses and associations `causal: false`.

Complete this step when the selected views answer the stated question, remain traceable to canonical fields, and expose unresolved review items without promoting task-view claims into source truth.

## 5. Select the problem mode

Classify the request using `references/problem-routing.md`:

- exploration or unsupervised analysis with no target;
- single-target regression, classification, forecasting, ranking, survival, or anomaly detection;
- multi-output regression/classification;
- multilabel classification;
- multitask learning;
- multi-objective optimization with explicit utilities, constraints, and trade-offs.

Do not equate multiple target columns with multi-objective optimization. Do not claim a “best” solution until the objective, metric, constraints, validation population, and tie-breaking rule are defined.

Treat aligned outcomes for the same learning unit/population/horizon as multi-output even when their types and losses differ; a shared multi-head implementation may use multitask learning internally. Use the broader multitask route when populations, horizons, label availability, or task definitions are not aligned. Record declared relationships and coherence constraints among targets, and measure violations rather than inventing them from names.

For time-indexed data, separately classify cross-sectional snapshots, ordinary time series, panel time series, irregular events, or temporal relations.

Complete this step when the learning unit, target mode, time mode, valid split, metrics, and constraints are explicit.

## 6. Compile ontology-guided analysis and features

Build a feature lineage table before materializing features. Include source field or relation path, semantic role, transformation, observation window, availability lag, unit, null handling, fit scope, and leakage rationale.

Generate features by meaning, not dtype alone:

- measures: unit-aware transforms, robust summaries, rates, ratios with compatible denominators, and bounded temporal aggregates;
- categories: rare-level handling and train-fitted encodings that preserve missing/unknown states;
- text: length/language/metadata baselines, sparse representations, or embeddings fitted without validation leakage;
- time: calendar, elapsed-time, lag, rolling, recency, trend, seasonality, and availability-aware windows;
- relations: to-one attributes, to-many counts/distinct counts/rates, recency, bounded aggregates, and topology only when relation instances carry relevant meaning;
- missingness: indicators only when missingness has a plausible measurement or process interpretation.

Exclude raw identifiers, post-outcome state, future observations, target proxies, action results, unrestricted relation neighborhoods, and transforms fitted outside training partitions unless explicitly justified and tested.

Complete this step when each feature is reproducible from the ontology and valid at scoring time.

## 7. Analyze and model progressively

Follow `references/analysis-playbook.md`:

1. Perform semantic data-quality checks and target-aware or target-free EDA.
2. Establish naive, business-rule, and simple statistical baselines.
3. Build preprocessing by semantic role and fit it on training partitions only.
4. Compare the smallest relevant model families.
5. Add sequence, relation, text representation, graph, or multitask complexity only when a simpler baseline exposes a justified gap.
6. Run ablations to measure whether ontology-derived features add stable value.

Match validation to deployment: random only for exchangeable rows; group-aware for repeated entities; temporal for future prediction; purged/gapped where labels or windows overlap; component-aware for connected graphs.

Before drafting the report, create the canonical finding registry defined in `references/report-integrity.md`. Assign stable IDs, evidence, priority, executive-summary membership, required literals, source artifacts, and limitations. Treat every critical/high finding as executive-summary content.

Complete this step when the comparison answers the business question under a deployment-valid split.

## 8. Deliver auditable evidence

Return the applicable artifacts:

- semantic profile with declared/observed/inferred/proposed labels;
- normalized ontology snapshot and provenance;
- canonical structural diagram plus task-semantic view specification and Mermaid or DOT output when visual relationships aid review;
- selected diagram intent, question, evidence scope, claim types, and unresolved view assertions;
- unresolved semantic questions and conflicts;
- problem specification, target/time mode, objectives, constraints, and validation design;
- EDA findings tied to semantic roles;
- canonical finding registry and validated executive-summary coverage;
- feature lineage and exclusions;
- reproducible split, preprocessing, training, and evaluation configuration;
- baseline/model or Pareto comparison with uncertainty and failure slices;
- model/analysis card and operational recommendation;
- provider adapters and source-system mutations listed separately.

Before delivery, run `scripts/validate_report_integrity.py` with `--clean-output` for every substantive report. Verify that each annotated artifact uses the selected language, every registered finding and required literal survives, all critical/high findings remain in the executive summary, and stable identifiers stay traceable. Deliver only the marker-free clean output; keep finding markers, language markers, and annotated reports internal. State limitations plainly. Separate “the data shows,” “the ontology declares,” “the profiler suggests,” and “the analyst proposes.”
