# Changelog

All notable changes will be documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow the repository's [versioning policy](docs/VERSIONING.md).

## [Unreleased]

### Added

- Research and engineering governance foundation.
- Initial research questions, hypotheses, claims ledger, and paper plan.
- Conceptual architecture, threat model, safety invariants, and ADRs.
- Experiment design, metrics, baselines, ablations, and reproducibility policy.
- Minimal framework-neutral Python project metadata.
- M1 deterministic in-process reference monitor with immutable action and decision types, explicit allow-only forwarding, default-deny static policy, and fail-closed authorization errors.
- Unit-test coverage for M1 authorization ordering, denied-action non-forwarding, default deny, authorization failure, and decision attribution preservation.
- M2 immutable task contracts and explicit action/resource capabilities, evaluated through the existing `Authorizer` abstraction with default deny.
- M2 unit tests for task binding, action and resource scope, path-boundary handling, immutable capability collections, and preserved monitor ordering/non-forwarding.
- M3 immutable canonical events, typed ReferenceMonitor lifecycle events, per-session in-memory sequencing, correlation, policy-rule provenance, and `AuditSink`/`InMemoryAuditSink` abstractions.
- M3 tests for allow, denial, authorization failure, execution failure, audit failure, correlation, ordering, and immutability.
- M4 deterministic, immutable threat-scenario simulator with harmless in-memory filesystem, network, shell, and database effect records.
- M4 starter corpus for TS-001, TS-006, TS-008, TS-009, TS-010, and BENIGN-001/BENIGN-002 controls, including M3 audit correlation and repeatability evidence.
- M5 bounded deterministic observational trajectory monitor, canonical terminal-action observation builder, immutable explainable findings, and `TRJ-001`/`TRJ-002` rules.

### Notes

- M1 evidence is limited to the supplied in-process `ReferenceMonitor` abstraction; it does not establish deployment-wide complete mediation.
- M2 capability evidence is limited to logical in-process request strings; it does not provide filesystem or OS-level confinement.
- M3 has no durable storage, cross-process ordering, distributed tracing, tamper evidence, cryptographic integrity, automatic experiment provenance, or secret-redaction guarantee.
- M5 does not contain, block, authorize, execute, or mutate task authority; TS-009 remains individually allowed even when `TRJ-001` is observed.
