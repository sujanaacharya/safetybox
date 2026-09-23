# Versioning Policy

## Software versions

SafetyBox uses Semantic Versioning once implementation begins. During pre-implementation and early incompatible development, versions remain `0.y.z`; `0.0.0` denotes the current specification-only state. A release tag must point to a reviewed, reproducible repository state.

## Independently versioned artifacts

Event schemas, task-contract schemas, policy sets, benchmark suites, and datasets carry their own explicit versions because their compatibility and scientific meaning may change independently of the package. Experiment metadata records all applicable versions and the Git SHA.

- Breaking schema or semantic changes increment the artifact major version.
- Backward-compatible additions increment the minor version.
- Clarifications or corrections that do not change interpretation increment the patch version.

Policy content changes require a new policy-set version even if the engine is unchanged. Benchmark task, label, or scoring changes require a new benchmark version.

## Documentation and results

Documentation normally versions with the repository. ADRs preserve decision history. Finalized experimental results are immutable and are not silently revised as part of a software release; corrections create a linked successor artifact.

## Release requirements

A release must include changelog entries, tagged source, environment/dependency information, schema and policy versions, known limitations, and applicable artifact checksums. Claims remain governed by the claims ledger regardless of release version.
