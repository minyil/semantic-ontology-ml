# Open-source tooling selection

Research basis: official project documentation, repositories, and licenses checked on 2026-08-16. Recheck versions, maintenance, connectors, and artifact licenses before adoption.

## Compatibility grades

- **A — source-native:** an official or native interface that preserves the source system's identifiers and permissions.
- **B — semantic adapter/core:** a schema, relation, graph, or ML abstraction connected through an explicit mapping.
- **C — complementary:** feature serving, experiments, quality, catalog, or lineage; the tool does not supply business semantics by itself.

No reviewed third-party project is a lossless open-source replacement for Foundry Ontology. Actions, queries/functions, interfaces, security, and operational behavior prevent a mechanical equivalence with RDF/OWL or a property graph. Do not call a B/C tool “Palantir-compatible” without first-party evidence.

## Recommended layers

| Tool | Grade | Job | License | Adopt when |
|---|---:|---|---|---|
| CSV/JSON/Parquet plus pandas/Arrow | A | Local/open tabular source adapter | pandas BSD-3-Clause; Arrow Apache-2.0 | Dataset-first discovery and reproducible snapshots |
| Palantir OSDK or `foundry-platform-sdk` | A | Optional Foundry metadata/objects/links adapter | SDK repo Apache-2.0; service proprietary | Only when Foundry is the authorized source |
| [LinkML](https://github.com/linkml/linkml) | B | Versioned neutral schema contract; generate JSON Schema/Python/RDF/OWL/SHACL views | Apache-2.0 | The adapter needs a durable multi-format IR |
| [RDFLib](https://github.com/RDFLib/rdflib) | B | Python RDF graph, SPARQL, JSON-LD/Turtle serialization | BSD-3-Clause | RDF exchange, semantic graph tests, or light SPARQL is required |
| [Featuretools](https://github.com/alteryx/featuretools) | B | Relational/time-aware feature synthesis over entity relationships | BSD-3-Clause | Object/link tables support bounded aggregates; represent many-to-many links with a junction table |
| [NetworkX](https://github.com/networkx/networkx) | B | In-memory topology statistics and graph baseline | BSD-3-Clause | First graph features on small/medium samples |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | B/C | Preprocessing, tabular baselines, selection, evaluation | BSD-3-Clause | Every MVP before graph-specific complexity |
| [MLflow](https://github.com/mlflow/mlflow) | C | Dataset/run/model/evaluation tracking | Apache-2.0 | Record snapshot, mapping, features, split, metrics, and artifacts |

Suggested MVP: one source adapter, the semantic contract, pandas/Arrow, scikit-learn baselines, and optional MLflow. Add Featuretools or NetworkX only when measured relations justify them. RDFLib and LinkML are useful exchange/contracts, not mandatory runtime databases.

## Add only after the need is demonstrated

| Tool | Grade | Add for | Important constraint |
|---|---:|---|---|
| [PyTorch Geometric](https://github.com/pyg-team/pytorch_geometric) | B | Heterogeneous GNN, node/edge/graph tasks | Build typed tensors and leakage-safe time/group/component masks |
| [PyKEEN](https://github.com/pykeen/pykeen) | B | Knowledge-graph embeddings/link prediction | Constrain negative samples by type, cardinality, and temporal existence |
| [Feast](https://github.com/feast-dev/feast) | C | Offline/online feature serving and point-in-time retrieval | No native Palantir semantic layer/store; write an adapter |
| [OpenLineage](https://github.com/OpenLineage/OpenLineage) | C | Runtime job/run/dataset lineage events | Put ontology identity/mapping digest in custom facets |
| [OpenMetadata](https://github.com/open-metadata/OpenMetadata) | B/C | Organization-wide catalog, quality, lineage, ML metadata | Build a custom Palantir connector; choose instead of DataHub |
| [DataHub](https://github.com/datahub-project/datahub) | B/C | Metadata graph, discovery, lineage, ML assets | Build entity mapping/ingestion; choose instead of OpenMetadata |
| [Great Expectations](https://github.com/great-expectations/great_expectations) | C | Generate dataframe/SQL quality checks from semantic constraints | Does not validate the complete link graph or operational semantics |
| [Kedro](https://github.com/kedro-org/kedro) | C | Modular extraction-to-evaluation pipelines | Orchestrator/catalog, not semantic layer |
| [SHAP](https://github.com/shap/shap) | C | Model explanations mapped back to property/link API names | Explanations are associational, not causal proof |

PyTorch Geometric and PyKEEN are MIT; Feast, OpenLineage, OpenMetadata, DataHub, Great Expectations, and Kedro are Apache-2.0; SHAP is MIT. Verify the exact release artifact and transitive dependencies.

## Special-purpose choices

- [Apache Jena/Fuseki](https://jena.apache.org/): choose for a shared/persistent SPARQL service, Java stack, SHACL, or explicit RDFS/OWL inference. Apache-2.0; adds a Java/server runtime.
- [Owlready2](https://pypi.org/project/owlready2/): choose for Python OWL 2 class/restriction/SWRL reasoning. LGPL-3.0-or-later requires product/legal review.
- [Neo4j Community](https://github.com/neo4j/neo4j) plus [neosemantics](https://github.com/neo4j-labs/neosemantics): choose for an existing persistent property-graph/Cypher platform with explicit RDF interop. Neo4j Community is GPL-3.0; n10s is Apache-2.0. This creates a governed synchronized copy.
- Neo4j GDS/OpenGDS: distinguish the GPL-3.0 open-source code from distribution/edition-specific closed or licensed capabilities. Prefer NetworkX/PyG for a lighter new MVP.
- DGL: retain for existing investments. For new projects, prefer PyTorch Geometric because the reviewed official [DGL release history](https://github.com/dmlc/dgl/releases) showed a materially older release and potential current PyTorch/CUDA compatibility risk.

## Adapter architecture

```text
CSV/Parquet  SQL/catalog  LinkML/RDF  Palantir
     \           |          |          /
          read-only source adapters
                    |
      semantic contract + provenance
          /          |           \
 tabular/text   relational/time   graph views
          \          |           /
           analysis/model/optimizer
                    |
       optional tracking/serving/lineage
```

Keep the semantic contract as the source of truth. Generate LinkML/RDF, Featuretools entities, NetworkX graphs, PyG tensors, feature-store definitions, and catalog entities as downstream views with deterministic mappings and digests.

## Selection test

For each proposed dependency, answer:

1. Which necessary job does it own that the existing stack cannot perform simply?
2. Is it A, B, or C, and where is the adapter seam?
3. What source identifiers, time semantics, cardinality, security behavior, and provenance could be lost?
4. Is its license compatible with the delivery model?
5. Can the baseline run if the tool is removed?
6. What measured criterion justifies moving from tabular/relational features to graph infrastructure or a GNN?

Reject selections that cannot answer all six.
