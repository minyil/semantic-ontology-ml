# Problem and validation routing

Classify target mode and time mode independently. The same multiple-target table may be multi-output prediction, multilabel classification, separate tasks, or optimization; the correct route depends on the decision.

## Target modes

| Mode | Definition | Starting point | Required reporting |
|---|---|---|---|
| No target | Explore structure, quality, clusters, anomalies, associations, or representations | semantic EDA; simple rules or unsupervised baseline | stability, cluster/anomaly diagnostics, sensitivity; no predictive claims |
| Single target | One outcome per learning unit | naive + simple supervised baseline | target metric, calibration/threshold or residual diagnostics |
| Multi-output | Several aligned outcomes for the same unit, population, and horizon; types/losses may differ | independent models, then shared/multi-head model | per-target metrics, coherence violations, plus declared aggregate |
| Multilabel | Each row can have several binary labels simultaneously | independent binary baseline | per-label, micro/macro, prevalence, threshold policy |
| Multitask | Related tasks have non-aligned populations, horizons, label availability, or task definitions | separate task baselines | per-task gains, negative transfer, missing-label handling |
| Multi-objective | Select a decision under competing objectives and constraints | feasible baselines, explicit utility/constraints, Pareto analysis | objective vector, feasibility, Pareto frontier, selected trade-off rule |

Do not collapse multi-objective results to one score without declaring direction, normalization, weights, constraints, and sensitivity to those choices. A predictive model may estimate inputs to an optimizer; prediction and decision optimization remain separate stages.

Heterogeneous outputs such as a binary churn label and continuous revenue remain analytically multi-output when they describe the same aligned example. A shared multi-head network is a multitask learning implementation, not evidence that the business problem is multi-objective. Compare it with independent models. Declare loss normalization/weights, test weight sensitivity and negative transfer, and never interpret training-loss weights as business utility weights.

Document cross-target relationships only when domain semantics support them: mutual exclusion, hierarchy, ordering, conservation, logical implication, or temporal dependence. Enforce hard constraints only when they are truly invariant; otherwise report coherence violations and compare unconstrained versus constrained predictions.

## Single-target task subtype

- Continuous outcome: regression; inspect censoring, skew, and heteroscedasticity.
- Categorical/binary outcome: classification; preserve class meanings and prevalence.
- Ordered category: ordinal model or ordinal-aware metric when ordering is real.
- Time-indexed future value: forecasting only when future time and horizon define the question.
- Time-to-event with censoring: survival/event-history analysis.
- Relative ordering: ranking when the decision consumes an ordered list.
- Rare/unlabeled deviation: anomaly detection; do not call anomalies failures without labels.

## Time modes

| Shape | Learning unit | First valid split | Leakage checks |
|---|---|---|---|
| Exchangeable cross-section | row/entity | random or stratified | duplicates, households/groups, preprocessing scope |
| Repeated entity snapshots | entity at as-of time | temporal plus entity-aware policy | same-entity history, overlapping windows, late labels |
| Single/multiple regular series | series at forecast origin | rolling-origin temporal | future lags, global transforms, horizon overlap |
| Irregular events | entity-event or snapshot | temporal/group or event-history split | post-event fields, observation process, censoring |
| Relational/graph | root entity/node/edge | group/component/temporal as deployment requires | neighbor leakage, transductive assumptions, future edges |

State whether deployment allows known entities (transductive) or must generalize to unseen entities/components (inductive).

## Metric routing

- Regression: compare MAE/RMSE or domain loss; include residual slices and uncertainty when decisions need it.
- Classification: use discrimination plus calibration and threshold utility; for imbalance include precision/recall or PR-oriented metrics.
- Forecasting: include naive/seasonal baselines and scale-aware or domain metrics by horizon.
- Multilabel/multi-output: report every target before any aggregate; prevent high-volume/easy targets from hiding failures.
- Ranking: evaluate at the decision cutoff and by relevant groups.
- Survival: account for censoring and evaluation horizon.
- Multi-objective: report feasibility and Pareto dominance; use a declared utility only for final selection.

## Analysis specification

Write a machine-readable or tabular specification containing:

```yaml
learning_unit: customer at observed_at
population: active customers eligible for intervention
target_mode: multi_output
targets:
  - name: churn_30d
    type: binary
    available_after: P30D
  - name: revenue_30d
    type: continuous
    available_after: P30D
target_relationships:
  - relationship: "domain-defined relationship or null"
    evidence: declared
time_mode: repeated_entity_snapshots
as_of_field: observed_at
split: temporal_with_entity_policy
metrics:
  churn_30d: [pr_auc, calibration, intervention_utility]
  revenue_30d: [mae]
aggregate_rule: null
constraints: []
```

Leave `aggregate_rule` null until the user/domain owner defines a trade-off. Never choose target weights merely because numeric scales differ.
