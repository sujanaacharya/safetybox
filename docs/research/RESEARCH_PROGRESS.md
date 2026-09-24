# Research Progress

This is a compact map of established repository stages. It does not replace frozen
protocols, results, analyses, or the [claims ledger](CLAIMS_LEDGER.md).

| Stage | Implementation | Evidence | Limitation |
|---|---|---|---|
| M0 | Governance, research questions, architecture, threat model, experiment rules, and ADR foundation. | Reviewed specification/design artifacts only. | No runtime or empirical result. |
| M1 | Deterministic in-process `ReferenceMonitor`. | Unit tests cover allow-before-forward, denial non-forwarding, and authorization failure. | Logical protected-tool interface; direct routes and real tools untested. |
| M2 | Immutable `TaskContract`, action/resource `Capability`, and deterministic `TaskContractPolicy`. | Unit and M4 regression tests cover represented task/action/resource matching. | Canonical logical resources only; no filesystem resolution or confinement. |
| M3 | Immutable lifecycle events, session-local sequencing, rule attribution, and in-memory audit failure semantics. | Unit and M4 regression tests cover order, attribution, pre-effect audit failure, and post-effect uncertainty. | Single process/in-memory sink; no durability or complete forensic claim. |
| M4 | Deterministic threat-scenario simulator with harmless in-memory effects. | Repeatable development/regression scenarios. | Synthetic logical world, not a real sandbox or tool. |
| M5 | Bounded deterministic sequence monitor over canonical observations. | Development tests before EXP-009. | Observational; no containment or real-tool enforcement. |
| EXP-009 | No new production runtime; frozen M5 protocol, corpus, evaluator, results, and ablations. | Held-out synthetic evidence: 40/40 positives detected, including 20 TRJ-001 cases with no policy block; 33/40 negatives flagged. | Level 3 synthetic sub-property evidence, poor specificity, no prevention claim. |
| M5.1-A/B/C | Trusted structured task context, stateless evaluator, and bounded context-aware trajectory monitor. | Development/unit evidence for immutable schemas, deterministic evaluation, and bounded ordered state. | Declaration-dependent; context does not grant authority; development fixtures are contaminated. |
| EXP-012 | No new production runtime; frozen context-aware protocol, corpus, evaluator, and results. | Held-out synthetic evidence: 40/40 positives and 40/40 negatives classified. | Every positive was recoverable from single-observation mismatch, so history necessity was not established. |
| B2/B4 | Frozen history-free B2 comparator and bounded historical B4 candidate. | Unit/development evidence plus a frozen capability audit before EXP-013 authorship. | Structured synthetic semantics; B4 remains observational. |
| EXP-013 | No new production runtime; frozen 40-pair history-required corpus/evaluation. | B4 discriminated 38/40 pairs B2 could not and had 0/40 matched-negative false positives. | Level 3 handcrafted, declaration-dependent synthetic evidence; two misses and no real effects, bypass, or agent integration. |
| EXP-014 transition | Protocol/design only for isolated filesystem mediation at FMED-L1/target RTM-1. | Preregistered questions, requirements, threat analysis, metrics, and failure gates; no empirical evidence. | Current state remains RTM-0: no adapter, unit tests, corpus, run, result, real-system evidence, or supported claim. |

The planned evidence sequence is protocol freeze, adapter implementation, adapter freeze,
held-out real-tool corpus, then evaluation. Filesystem is first; subprocess/shell,
HTTP/network, MCP, database, browser, and a multi-tool agent harness remain later work.
