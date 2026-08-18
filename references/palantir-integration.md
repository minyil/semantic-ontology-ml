# Palantir integration boundary

Use this reference only when Palantir Foundry is an actual source or deployment target. The core semantic discovery, feature engineering, analysis, and modeling workflow does not require Palantir or its API.

Use current official Palantir documentation and the interfaces enabled in the user's enrollment. Generated OSDK package shapes and preview endpoints can change; inspect the installed package or exported specification instead of inventing method names.

## Choose the direct interface

| Need | Direct interface | Boundary |
|---|---|---|
| Typed application over a known Ontology subset | Generated OSDK for Python, Java, or TypeScript | Package is Ontology-specific; isolate it behind an adapter |
| Generic analyzer across Ontologies | Foundry REST API or official Platform SDK | Handle pagination, scopes, branches, version drift, and partial visibility |
| Other language | Developer Console OpenAPI export plus an open-source generator | Generated transport types do not supply RDF/OWL or ML semantics |
| Small samples, object sets, linked objects, aggregations | Ontology object/link/query APIs | Bound every request and preserve filters/provenance |
| Bulk training data | Governed Foundry dataset/transform path; authorized dataset export when required | Keep the Ontology snapshot and dataset transaction/snapshot linked |

Official entry points: [OSDK overview](https://www.palantir.com/docs/foundry/ontology-sdk/overview), [SDK comparison](https://www.palantir.com/docs/foundry/api/general/overview/sdks), [Foundry API reference](https://www.palantir.com/docs/foundry/api), [Platform Python SDK source](https://github.com/palantir/foundry-platform-python), and [OpenAPI export](https://www.palantir.com/docs/foundry/ontology-sdk/generate-osdk-for-other-languages).

The Platform Python SDK is Apache-2.0; that license applies to the client code, not to Foundry, the Ontology service, platform runtimes, or data access. Confirm permissions and the actual artifact license independently.

## Extract metadata

1. Resolve ontology API name/RID, branch, enrollment label, client/package version, and capture time.
2. Request only metadata visible to the authorized client.
3. Prefer a stable list/get composition for production adapters. Treat V2 `fullMetadata` as a convenience path while the official page marks it preview; record omissions and fall back to stable resource calls when completeness matters. See [Get Ontology Full Metadata](https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/ontologies/get-ontology-full-metadata).
4. Collect object types, properties, links and both directions/cardinalities, interfaces, shared properties, value types, action types, query types/functions, groups, lifecycle status, descriptions, RIDs, and API names when exposed. See [Ontology resources](https://www.palantir.com/docs/foundry/ontologies/ontologies-overview) and [type reference](https://www.palantir.com/docs/foundry/object-link-types/type-reference).
5. Normalize to `semantic-contract.md`. Preserve an `omissions` list for forbidden, missing, truncated, unsupported, or preview-only entities.
6. Hash the canonical snapshot and store its provenance sidecar before reading training data.

The metadata response reflects the caller's visibility. Absence may mean authorization or endpoint behavior rather than nonexistence; emit diagnostics instead of silently treating an omitted entity as deleted.

## Extract instances safely

Use object APIs to list/get/search/aggregate objects and traverse linked objects or object sets. Generated Python OSDK link behavior reflects link multiplicity; inspect the installed package and current [Python OSDK guidance](https://www.palantir.com/docs/foundry/ontology-sdk/python-osdk-migration) before implementing traversal.

Handle source encodings explicitly:

- arrays and nested structs;
- timestamps, dates, time series, and their observation/availability time;
- vectors and dimensions;
- attachment references without automatic content download;
- secured values and missing/omitted values without collapsing them into ordinary nulls;
- pagination, branch, object-set scope, filters, query parameters, and retry diagnostics.

The [Get Object API](https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/ontology-objects/get-object) documents supported property JSON encodings. Use samples for semantic checks; use governed dataset paths for bulk training tables when available. Foundry transforms can read tabular datasets into Arrow, pandas, Polars, or related engines; choose a compute engine from data size and platform constraints. See [Transforms Dataset API](https://www.palantir.com/docs/foundry/api-reference/transforms-python-library/api-dataset) and [Python compute engines](https://www.palantir.com/docs/foundry/transforms-python/compute-engines).

## Preserve operational semantics

- Map object types/properties/links into schema and instance views.
- Keep interfaces/shared properties/value types as reusable semantic definitions.
- Represent actions as commands/state transitions and queries/functions as callable operations with provenance.
- Keep authorization and secured-property behavior in the source adapter; an external RDF graph, dataframe, feature store, or graph database does not inherit Foundry governance.
- Treat a Palantir-to-RDF/OWL/LinkML mapping as an explicit adapter decision. Palantir's type system draws on related standards but is not documented as a native OWL ontology.

Default to read-only operations. Before any action application, object edit, dataset write, deployment, schedule, or model write-back, produce the target, scope, validation/dry-run option, affected population, permissions, and rollback plan; wait for explicit user authorization.
