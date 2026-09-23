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

### Notes

- M1 evidence is limited to the supplied in-process `ReferenceMonitor` abstraction; it does not establish deployment-wide complete mediation.
