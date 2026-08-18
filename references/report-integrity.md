# Report integrity and localization

Treat language, format, and document layout as presentation projections of one canonical finding set. Preserve analytical content before improving prose.

## Contents

1. Integrity invariant
2. Finding registry
3. Executive-summary coverage
4. Annotated report markers
5. Localization workflow
6. Validation and completion gates

## 1. Integrity invariant

Keep these properties invariant across every report language and format:

- finding IDs and included finding set;
- priority and executive-summary membership;
- evidence class and claim type;
- key values, dates, units, populations, and scopes;
- limitations, leakage warnings, and non-causal qualifiers;
- links to source artifacts and reproducible support.

Language may change titles, prose, display labels, explanatory order within a finding, and locale-appropriate punctuation. Layout may move detailed evidence into tables or appendices. Neither may demote or omit a finding, number, limitation, or warning.

## 2. Finding registry

Create `finding-registry.json` before writing a substantive analysis report or translating an existing report. Include every conclusion intended for delivery, not every intermediate calculation.

Use this provider-neutral shape:

```json
{
  "registry_version": "1.0",
  "analysis_id": "cement_calcination_eda",
  "findings": [
    {
      "finding_id": "F001",
      "category": "temporal_quality",
      "priority": "high",
      "evidence": ["observed", "proposed"],
      "executive_summary_required": true,
      "required_literals": ["20", "7", "27", "9,822"],
      "required_tags": ["timestamp-repair-proposed", "timezone-unresolved"],
      "source_artifacts": ["time-quality.csv", "time-gaps.csv"],
      "limitations": ["timezone unresolved"]
    }
  ]
}
```

Rules:

- Assign stable `finding_id` values once; reuse them in every language and format.
- Use `critical`, `high`, `medium`, or `low` priority. Put every `critical` and `high` finding in the executive summary.
- Use `declared`, `observed`, `inferred`, or `proposed` evidence without translating these machine values. Use a unique list only when one finding intentionally combines separately qualified clauses; keep each clause's evidence explicit in the prose.
- Put language-invariant decision values—numbers, percentages, timestamps, metric symbols, and stable IDs—in `required_literals`. Use the exact display form that every localized report must retain; express translatable concepts through prose plus `required_tags`.
- Put leakage, non-causal, uncertainty, unresolved-semantics, and other decision-critical qualifiers in `required_tags`. Use stable lowercase tag IDs rather than translated prose.
- Link at least one `source_artifact` that supports each finding.
- Record material interpretation limits, leakage risks, causal qualifications, and unresolved semantics under `limitations`.

The registry is the content contract. It may use stable English keys and controlled values because it is machine-readable; localize its interpretation in the report.

## 3. Executive-summary coverage

Select summary findings by decision importance, not by section length or ease of translation. Include every applicable high-impact category:

- dataset grain, population, scale, and time structure;
- structural or temporal data-quality defects;
- target/outcome behavior and leakage risk;
- missing, zero, censored, or regime-dependent semantics;
- strongest measured relationships with causal qualification;
- important multivariate, cluster, dimensionality, or model structure;
- anomaly, failure, or risk concentrations and their leading drivers;
- operational constraints or unresolved questions that change the decision.

Use the registry's `executive_summary_required` value as the binding decision. Detailed sections may expand a summary finding; they do not replace its summary occurrence.

## 4. Annotated report markers

Use two distinct artifacts:

- `report-<language>.annotated.md`: internal validation source containing markers;
- `report-<language>.md`: clean user-facing report containing no internal markers.

Mark the internal artifact near its start:

```markdown
<!-- report-integrity:annotated -->
```

Add a language marker once near the start of each Markdown report:

```markdown
<!-- report-language:zh-Hant-TW -->
```

Add an invisible marker immediately before each finding occurrence:

```markdown
<!-- finding:F001 summary -->
<!-- finding-tag:F001:timestamp-repair-proposed -->
1. `Datetime` 有 20 個無法解析值，最大缺口為 9,822 分鐘。

## 時間戳品質

<!-- finding:F001 detail -->
| 無效時間戳 | 最大缺口（分鐘） |
|---:|---:|
| 20 | 9,822 |
```

Use `summary` for an executive-summary occurrence and `detail` elsewhere. A finding may appear in both. Keep markers outside code fences and place each marker directly before the text or table it identifies. Treat every marker as internal metadata; publish the clean artifact rather than relying on a Markdown renderer to hide comments.

## 5. Localization workflow

1. Freeze the registry before translation or formatting changes.
2. Draft the executive summary from findings marked `executive_summary_required`.
3. Draft detailed sections from the same finding set and source artifacts.
4. Localize user-facing prose, headings, labels, legends, annotations, and review questions.
5. Preserve stable identifiers and every `required_literal` exactly.
6. Render the meaning of every `required_tag` and place its invisible tag beside that text.
7. Preserve evidence, priority, scope, limitations, causal qualifiers, and executive-summary membership.
8. Add report and finding markers to the `.annotated.md` artifact while authoring.
9. Validate every annotated language variant against the same registry.
10. Publish a separate clean report by stripping only recognized internal markers.
11. Deliver the clean report; retain the registry and annotated report as internal audit artifacts.

When translating an existing report, derive the registry from the source report first. Compare source and localized variants through the registry rather than relying on paragraph counts, since layouts may legitimately differ.

## 6. Validation and completion gates

Run:

```bash
python scripts/validate_report_integrity.py finding-registry.json \
  report-zh-Hant-TW.annotated.md \
  --clean-output report-zh-Hant-TW.md
```

Validate multiple language variants together when they exist:

```bash
python scripts/validate_report_integrity.py finding-registry.json \
  report-zh-Hant-TW.annotated.md \
  report-en.annotated.md \
  --clean-output report-zh-Hant-TW.md \
  --clean-output report-en.md
```

The validator checks:

- registry structure, evidence, priority, unique IDs, and source support;
- all critical/high findings are summary-required;
- every registry finding occurs in every report;
- every summary-required finding has exactly one `summary` marker;
- every required literal appears in its finding block;
- every required semantic qualifier tag appears in the report;
- reports contain no unknown finding IDs.
- clean output paths cannot overwrite registries or annotated reports;
- each clean output contains no internal report, language, finding, or finding-tag marker.

Complete report delivery only when validation passes for every annotated language variant, the clean outputs contain no internal markers, and a human reader can recover every high-impact conclusion from the executive summary alone. Deliver only clean reports to users.
