# Changelog

All notable changes will be documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow the repository's [versioning policy](docs/VERSIONING.md).

## [Unreleased]

### Added

- Development-only `PROC-ADAPTER@1` PMED-L1 implementation for EXP-015 with exact
  executable/cwd compound authorization through `TaskContractPolicy`, pure lexical
  canonicalization, post-allow validation, fixed environment, shell-false argv-native
  execution, bounded byte capture, direct-child timeout/signal observation, and an
  additive M3 audit envelope. Contaminated native-helper tests and traceability/diligence
  documents are included; no held-out corpus, EXP-015 result, RTM-2 promotion, or
  supported claim is included.
- Independent EXP-015 pre-corpus implementation freeze audit, including conservative
  indeterminate classification for real `Popen` failures, deterministic immutable
  authorization provenance, and bounded helper-fixture completion.
- EXP-015 Level 0 preregistration for PMED-L1 direct subprocess mediation, including
  `REQ-033`–`REQ-062`, `INV-020`–`INV-023`, ADR-007, architecture and threat boundaries,
  human/machine-readable protocols, and a pre-freeze authorization-quality audit. No
  process adapter, helper, held-out corpus, subprocess run, maturity upgrade, or supported
  claim is included.
- Development-only `FS-ADAPTER@1` pre-corpus implementation freeze for EXP-014 with pure lexical
  logical-path canonicalization, existing M1/M2 authorization, compound rename
  authorization, post-allow link/type validation, real temporary-filesystem primitives,
  deterministic state digests, and an additive M3-compatible audit envelope.
- Contaminated filesystem development validation, REQ-001–REQ-032 and
  INV-016–INV-019 traceability, and self-critical technical diligence notes. No held-out
  EXP-014 corpus, run, result, RTM-1 claim, production claim, or FMED-L2/3/4 claim is
  included.
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
- M5.1-A immutable versioned `TaskContext` model with structured purpose, outcomes,
  resource/data roles, destination and logical-flow constraints, bounded fallback
  declarations, per-declaration trusted provenance, deterministic validation/lookups,
  and explicit sufficient/insufficient context representation.
- M5.1-B immutable reason-coded `ContextEvaluation` and stateless `ContextEvaluator`
  for single completed observations, including resource/data roles, destination/outcome
  and action-purpose compatibility, optional declared logical-flow comparison, fallback
  membership, provenance, and explicit mismatch/insufficient/not-applicable states.
- M5.1-C separate bounded `ContextAwareTrajectoryMonitor`, immutable context-aware
  findings/snapshots, `CTXTRJ-001` access-to-outbound interpretation, and `CTXTRJ-002`
  fallback-aware repeated-denial interpretation using M5.1-B evidence.
- `B2-SINGLE-OBSERVATION@1`, a frozen stateless executable context baseline over
  M5.1-B results, with immutable evidence, explicit abstention, and commutative,
  duplicate-insensitive scenario aggregation.
- `B4-BOUNDED-CONTEXT-TRAJECTORY@1` with immutable `B4-HISTORY-CONTEXT@1`, fixed
  `B4-CONFIG@1`, 16-observation recomputed state, four declaration-driven history
  rules, bounded finding/key capacity, development-only B2 parity probes, and
  machine-readable capability/version provenance.

### Notes

- M1 evidence is limited to the supplied in-process `ReferenceMonitor` abstraction; it does not establish deployment-wide complete mediation.
- M2 capability evidence is limited to logical in-process request strings; it does not provide filesystem or OS-level confinement.
- M3 has no durable storage, cross-process ordering, distributed tracing, tamper evidence, cryptographic integrity, automatic experiment provenance, or secret-redaction guarantee.
- M5 does not contain, block, authorize, execute, or mutate task authority; TS-009 remains individually allowed even when `TRJ-001` is observed.
- M5.1-A adds representation only: context does not grant capabilities, perform
  natural-language inference, track runtime lineage, or change M5 trajectory behavior.
- M5.1-B adds interpretation only: it does not retain history, count attempts, inspect
  payloads, emit trajectory findings, alter authorization, or change M5 rules.
- M5.1-C findings remain observational and do not establish payload lineage, safety,
  prevention, containment, or generalization beyond contaminated development cases.
- The B2 baseline is history-free and observational: sequence numbers are provenance
  only, incomplete context abstains, and it cannot emit findings or alter authorization.
- B4 development probes are contaminated expressivity checks, not held-out EXP-013
  evidence. B4 does not infer payload lineage, recover evicted semantics, or detect
  internally consistent but real-world-stale declarations.
