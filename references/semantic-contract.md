# Provider-neutral semantic contract

Use this contract as the seam between source adapters and analysis. Keep source-native identifiers; never turn display names or statistical guesses into source truth.

This contract describes datasets and structural entity relations. For mechanism, process-state, event, risk, or operational-decision graphs, keep this snapshot as the source seam and create the separate contract in [`domain-knowledge-ontology.md`](domain-knowledge-ontology.md).

## Canonical shape

```json
{
  "contract_version": "1.0",
  "source": {
    "provider": "csv|parquet|sql|linkml|rdf|palantir|manual",
    "locator": "non-secret stable reference",
    "captured_at": "2026-08-16T12:00:00Z",
    "source_version": null,
    "digest": "sha256 of canonical snapshot"
  },
  "datasets": [
    {
      "name": "customer_snapshot",
      "source_id": "warehouse.customer_snapshot",
      "grain": "one row per customer and observed_at",
      "entity_type": "CustomerSnapshot",
      "row_count": 120000,
      "time": {
        "event_time": null,
        "observation_time": "observed_at",
        "availability_time": null
      }
    }
  ],
  "entity_types": [
    {
      "name": "CustomerSnapshot",
      "source_id": "customer_snapshot",
      "description": "Customer state observed at a scoring time.",
      "primary_key": ["customer_id", "observed_at"],
      "fields": [
        {
          "name": "customer_id",
          "source_id": "customer_id",
          "physical_type": "string",
          "nullable": false,
          "roles": [
            {"role": "identifier", "evidence": "declared", "confidence": 1.0}
          ],
          "unit": null,
          "description": "Stable customer identifier."
        },
        {
          "name": "revenue_30d",
          "physical_type": "double",
          "roles": [
            {"role": "measure", "evidence": "inferred", "confidence": 0.8}
          ],
          "unit": "TWD",
          "availability_lag": "P1D"
        }
      ]
    }
  ],
  "relations": [
    {
      "name": "customer_orders",
      "source_entity": "Customer",
      "target_entity": "Order",
      "source_to_target": "many",
      "target_to_source": "one",
      "join": [{"source_field": "customer_id", "target_field": "customer_id"}],
      "evidence": "declared"
    }
  ],
  "semantic_types": [],
  "constraints": [],
  "conflicts": [],
  "omissions": []
}
```

## Required semantics

- `name` is the normalized stable name used by analysis code.
- `source_id` preserves the native table, object type, property, URI, RID, or API identifier.
- `grain` states what one row represents. Treat an unknown grain as a blocking analysis question, not an empty string.
- `roles` may contain `identifier`, `entity_key`, `event_time`, `observation_time`, `availability_time`, `effective_from`, `effective_to`, `measure`, `ordinal`, `category`, `boolean`, `text`, `geospatial`, `target`, `weight`, `group`, `sensitive`, `policy`, or `ignored`.
- Every role has `evidence`: `declared`, `observed`, `inferred`, or `proposed`. Add `confidence` only to inferred/proposed roles.
- `physical_type` describes storage. A string can still be a timestamp, identifier, category, or text; a number can be a category or identifier.
- `unit`, scale, allowed values, null meaning, timezone, and availability lag remain explicit when relevant.
- `source_to_target` is the number of target records reachable from one source record; `target_to_source` is the reverse. Use `one` or `many` only after measuring or receiving a declaration.

## Time semantics

Keep these clocks separate:

| Clock | Meaning |
|---|---|
| Event time | When the real-world event occurred |
| Effective time | Interval in which a state/fact is valid |
| Observation/as-of time | Cutoff for constructing one analytical example |
| Availability time | When the value became usable by the scoring system |
| Target time | When the outcome is evaluated |

Feature validity is governed by availability time, not merely event time. Record timezone, clock precision, late-arrival policy, and imputation assumptions.

## Merge rules

1. Preserve declared semantics even when values look inconsistent; add a conflict.
2. Add observed statistics without changing declared roles.
3. Keep name/value-based roles as inferred candidates until confirmed.
4. Keep modeling choices and feature definitions as proposed artifacts outside source-owned metadata.
5. Hash canonical snapshots and link every analysis run to the input digest.

## Source mappings

- **DataFrame/files:** dataset name becomes `source_id`; columns become fields; statistics are observed.
- **SQL/catalog:** tables/views become datasets/entity types; keys and foreign keys become declared relations when catalog constraints are trustworthy.
- **LinkML/RDF:** classes become entity types, slots/properties become fields/relations, and constraints retain source identifiers.
- **Palantir:** object types become entity types, properties become fields, link types become relations, and API names/RIDs remain `source_id`; actions/functions stay in adapter-specific operational metadata.

Legacy snapshots using `object_types`/`properties`/`link_types` remain accepted by `scripts/profile_ontology.py`; new snapshots should use `entity_types`/`fields`/`relations`.
