# Dataset semantic discovery

Profile values to propose an ontology draft; do not confuse pattern recognition with business meaning.

## Input handling

Work from the smallest representative, policy-compliant sample. Record path/source, byte digest when practical, row sampling rule and seed, parsing options, encoding, delimiter, null tokens, timezone assumptions, and whether counts are exact or sampled. Do not use a head sample for time/entity/target-sorted data unless the prefix is deliberately the population under study.

`scripts/profile_dataset.py` directly supports CSV, TSV, JSON, JSONL/NDJSON, and Parquet. Parquet requires pandas plus a Parquet engine. The script reads at most `--sample-size` rows for value profiling and clearly reports that boundary. Use `--sample-strategy reservoir --sample-seed <integer>` for a deterministic sample across a sorted large file; this scans the source and reports the exact row count. Repeat `--entity-column` to declare a composite entity or series key.

## Discovery sequence

1. Read schema, field names, storage types, row count, and a bounded sample.
2. Compute missingness, distinct count/ratio, value-shape counts, numeric summaries, datetime range, text length, and representative redacted-safe examples.
3. Propose physical and semantic types independently.
4. Identify candidate keys, times, categories, measures, text, booleans, sensitive fields, and outcome-like fields.
5. Infer table shape: cross-sectional, ordinary time series, panel/entity time series, or event table.
6. Across tables, compare candidate key overlap and measured cardinality before proposing relations.
7. Produce confirmation questions for every choice that affects grain, time, target, units, privacy, policy, or leakage.

## Evidence rules

| Signal | Permitted inference | Must not conclude |
|---|---|---|
| Column name contains `id`, high uniqueness | identifier candidate | stable entity key |
| Most strings parse as dates | datetime candidate | event time or availability time |
| Low distinct ratio | category candidate | business categories are complete/ordered |
| Mostly numeric strings | numeric-storage candidate | unit, scale, or measure meaning |
| Long variable strings | free-text candidate | text is safe or useful for modeling |
| Names such as `label`, `outcome`, `churn` | outcome-like review candidate | approved prediction target |
| Names such as age, gender, race, email | sensitive/privacy review candidate | legal classification or permitted use |
| Repeated entity plus ordered time | panel candidate | forecasting is the requested task |

Use thresholds only to prioritize review. Preserve ratios and reasons so a reviewer can override them.

## Mixed and dirty columns

For each field, count null, boolean, integer, real, datetime, and string-shaped values. Mark the physical profile as `mixed` when no dominant parse class safely represents non-null values. Do not coerce identifiers with leading zeroes, categories encoded as integers, or numeric values containing unit/currency suffixes without an explicit rule.

Report invalid examples in a privacy-safe form: prefer shape, length, hashes, or bounded values. Never print full secrets, tokens, long free text, or sensitive identifiers merely to demonstrate a parse problem.

## Table-shape rules

- **Cross-sectional:** one row per unit and no repeated time-indexed observations.
- **Time series:** a value sequence indexed by time, commonly one series or one aggregate unit.
- **Panel:** multiple entities observed repeatedly over time. Both entity and time must stay in the split design.
- **Event table:** one row per event, usually with an entity link and event time; create snapshots/windows before ordinary supervised modeling.
- **Relational:** multiple grains connected by measured or declared keys; aggregate from child to prediction grain using time-valid windows.

The profiler reports candidates. Confirm row grain from process knowledge because duplicate-looking rows, slowly changing dimensions, snapshots, and transactions can share the same statistical shape.

## Confirmation checklist

Ask only questions that materially change analysis:

- What real-world thing or event does one row represent?
- Which field(s) form the stable key at that grain?
- Which clock controls feature availability at prediction time?
- What do null, zero, negative, default, and sentinel values mean?
- What units, scales, currencies, or category orderings apply?
- Which targets/objectives are authorized, and when do they become known?
- Are any fields prohibited, sensitive, action-derived, or post-outcome?
- Will deployment score new rows, future periods, unseen entities, or new sites?

## Output contract

Return dataset facts, per-field profiles, semantic candidates with reasons/confidence, shape candidates, explicit roles supplied by the user, warnings, and confirmation questions. Convert confirmed semantics to `semantic-contract.md`; keep unresolved candidates in the review queue.
