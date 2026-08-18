# Ontology-guided analysis playbook

Use this after semantic discovery and problem routing. The ontology narrows valid operations; it does not replace measurement, validation, or domain review.

## 1. Write the analysis specification

Record the learning unit, population, decision, targets/objectives, cross-target relationships, observation/as-of time, horizon, feature availability rule, split unit, metrics, constraints, error costs, and intended deployment population. For target-free analysis, replace prediction details with the exploratory question and stability/quality criteria.

Reject a supervised specification with an ambiguous target, row grain, or scoring-time boundary.

## 2. Perform semantic EDA

Evaluate data quality against meaning:

- keys: uniqueness at declared grain, missingness, stability, and cross-table compatibility;
- measures: unit consistency, impossible ranges, robust distributions, censoring, and denominator validity;
- categories: allowed values, rare/unknown states, ordering, and label drift;
- text: language, length, boilerplate, duplicate content, privacy, and whether text exists at scoring time;
- time: monotonicity by entity, cadence, gaps, duplicate timestamps, timezone, lateness, and regime change;
- relations: observed cardinality, orphan records, fan-out, temporal validity, and coverage;
- targets: prevalence/distribution by time, group, and availability lag; missing outcome mechanism;
- sensitive/policy fields: permitted use, subgroup coverage, proxy risks, and audit requirements.

Report observations separately from causal or business interpretations.

## 3. Compile features with lineage

Create this table before materialization:

| Feature | Root field/path | Role | Transform/window | Availability rule | Fit scope | Unit/null rule | Leakage status |
|---|---|---|---|---|---|---|---|
| `orders_30d_count` | `Customer -> orders` | event aggregate | count, trailing 30d | available by as-of | none | count; zero means no observed order | review complete |

### Feature families

| Meaning | Safe baseline | Escalate when |
|---|---|---|
| Numeric measure | median/robust scaling, missing indicator, monotonic/bin transform | stable nonlinear interactions justify trees/splines |
| Category/ordinal | explicit missing/unknown, one-hot/ordinal mapping fit on train | high cardinality justifies regularized target/frequency encoding with nested fitting |
| Free text | length/language/quality, train-fitted TF-IDF | fixed or tuned embeddings add held-out value and comply with privacy constraints |
| Datetime/time series | calendar, elapsed time, lags, rolling/expanding windows | sequence/forecasting models beat valid lag baselines |
| Relation/event | counts, distinct counts, rates, recency, bounded measure aggregates | topology/sequence effects survive ablation and valid splits |
| Geospatial | valid coordinates, coarse regions, distances to declared anchors | spatial models are needed and geographic holdouts validate |

Only combine measures when units and semantic denominators permit it. Fit encoders, imputers, vocabularies, scaling, feature selection, and learned graph/text representations on training data only.

## 4. Establish baselines

Compare against applicable baselines:

- last value, seasonal naive, prevalence/mean/median, random, or business rule;
- regularized linear/logistic or other interpretable generalized model;
- a tree ensemble for mixed tabular features;
- independent per-target models before joint multi-output/multitask models;
- tabular relation aggregates before graph neural networks;
- sparse text before task-tuned embeddings.

The baseline must use the same split, population, target definition, and scoring-time information as complex models.

For heterogeneous aligned outputs, compare independent models with a shared multi-head implementation. Normalize and weight joint losses explicitly, document the rationale, and run weight-sensitivity and negative-transfer checks. Never feed one current-window realized target into another target's predictor; only mature prior outcomes available at scoring time may become features.

## 5. Evaluate for the real scoring context

Use random splits only when rows are exchangeable. Otherwise use group, temporal/rolling-origin, site/geographic, or graph-component splits. Add a time gap or purging when feature windows, labels, or entity history can overlap partitions.

Report:

- task metrics with uncertainty or fold variability;
- calibration/threshold outcomes for decisions;
- per-target and aggregate metrics for multiple targets;
- domain-declared cross-target coherence constraints and their violation rate;
- performance by time, entity group, missingness state, and relevant subgroup;
- data/semantic drift and failure examples;
- operational cost, latency, abstention, and constraint violations;
- the exact aggregation or Pareto rule for multi-objective comparisons.

Do not average multiple metrics unless their direction, scale, normalization, and weights are declared.

## 6. Measure the value of semantics

Run ablations for:

- raw fields only versus ontology-derived features;
- identifiers and outcome-like fields removed;
- temporal windows shortened or delayed;
- relational aggregates removed;
- text or graph representations removed;
- independent targets versus shared representations;
- alternative ontology mappings where semantics are uncertain.

Treat large performance loss after removing suspicious fields as a leakage investigation signal. Treat small gain from a complex semantic family as evidence against operational complexity.

## 7. Publish the evidence bundle

Version the semantic contract, data profile, analysis specification, split indices/rules, feature lineage, code/environment, seeds, model configurations, metrics, ablations, and limitations. Keep source-system integration and write-back as separate adapters requiring explicit authorization.
