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
| EXP-014 | Frozen `FS-ADAPTER@1`, held-out `EXP-014-CORPUS@1`, one-shot `EXP-014-RUN-001`, and adversarial post-run analysis for isolated filesystem mediation. | Level 4 evidence for named FMED-L1 sub-properties: 94/94 adapter-routed terminal outcomes, 91/91 independently derived authorization decisions, 19/19 denied mutations without wrapped call or independently observed state change, and tested audit/order evidence; RTM-1 recommended. | Real filesystem tool evidence, not real-agent deployment: direct routes bypass, TOCTOU/concurrency are untested, audit is non-durable, failure evidence is partly injected, and no production/external claim follows. |
| EXP-015 | Frozen process protocol/adapter, `EXP-015-CORPUS@2`, one-shot `EXP-015-RUN-001`, and `EXP-015-ANALYSIS-001`. | Level 3 same-team held-out synthetic evidence for exact TaskContract authorization: 60/60 allows, 60/60 denies, 0 observed false allows/denies, and 60/60 denied requests not forwarded to spawn. | All 50 expected-regular helpers were non-ELF scripts, while ten other positives intentionally had invalid executable shapes; all 60 stopped at executable validation: zero children, benign completion 0/44, terminal accuracy 0/120, no held-out cwd/argv/environment/output/failure/positive-order evidence, invalid direct controls, low oracle independence, and confounded repeat scoring. |
| EXP-016 Protocol@2 | Versioned pre-corpus governance for native direct-child execution semantics. | Synthetic development proofs validate route-aware lifecycle, nonvacuous scoring, and definition/population separation before exposure. | No held-out corpus, execution, prediction, result, or promoted claim; infrastructure evidence only. |
| AUTH-COVERAGE-001 | Frozen large authorization protocol/corpus and adversarial final pre-run gate. | Methodology, bounded formal checks, and failure analysis remain useful negative research evidence. | `BLOCKED_BENCHMARK_LEAKAGE`: labels are reconstructable from runtime IDs, HELD_OUT was previously exercised by production conformance tests, and the canonical raw-first/partial-exposure/scoring path is incomplete. It is never valid held-out performance evidence. |
| Research Program@1 | North-star effect model, authority lifecycle/trust boundary, mediation/provenance models, OWASP matrices, replacement benchmark design, tracks, DAG, flagship target, and paper program. | Architecture/evaluation design only (Level 0 unless a linked existing artifact supplies a narrower higher level). | Most controls are proposed; no new implementation or empirical result is created by consolidation. |

Filesystem held-out real-tool evaluation is complete at FMED-L1. EXP-015 provided
strong bounded authorization-conformance evidence but did not establish real process
execution semantics. Repository maturity remains RTM-1; RTM-2 is not supported. The
next transition is authorship and independent freeze auditing of the EXP-016 native-helper
held-out corpus under Protocol@2. In parallel, the highest-leverage program task is to
freeze and implement the `AUTH-COVERAGE-002` canonical raw-first runner plus reusable
exposure ledger before authoring its corpus. HTTP/network and MCP mediation,
shell-specific evaluation, a real agent
harness, stronger interception, concurrency, durable audit, and external deployment
evidence remain later stages.
