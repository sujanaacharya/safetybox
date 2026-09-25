# AUTH-COVERAGE-002 pre-run validity audit

**Audit identity:** `AUTH-COVERAGE-002_PRE_RUN_VALIDITY_AUDIT@1`
**Decision:** `BLOCKED_PREREGISTRATION_AND_EXPLANATION_COMPATIBILITY`
**Substrate:** `8e3ba29bbadcdc9c4de4c0d306e8eaaf013dab78`
**Protocol-first commit:** `7840c0e`
**HELD_OUT production exposure:** 0

**Superseding notice:** the earlier pass table below describes an invalidated development
fixture and is retained only as an audit trail. The authoritative disposition is
`AUTH-COVERAGE-002_BLOCKED_AUDIT@1`. No corpus freeze was authorized.

This audit concerns corpus authorship before any canonical HELD_OUT authorization call.
It is not a result report.

| Gate | Evidence | Disposition |
|---|---|---|
| Protocol precedence | protocol/spec checksummed and committed before corpus generation | PASS |
| Blinding | HELD_OUT runtime has four production-input files; labels and all analysis fields are outside it | PASS |
| Oracle agreement | 4,000/4,000; no adjudication | PASS |
| Oracle independence | predicate evaluator versus permitted-relation constructor; segment-independent resource logic | PASS, common-spec risk bounded |
| Pair quality | 2,000 registered; 1,600 strict strong; 400 strong auxiliary; weak 0 | PASS |
| Structural difficulty | 3,820 hard and 180 moderate; independent recomputation mismatch 0 | PASS |
| Structural diversity | 3,900 templates; largest cluster 2; exact/cross-split duplicates 0 | PASS |
| Leakage | individual attacks near chance; combined superficial classifier 61.125% < 65% block threshold | PASS with bounded residual |
| Generator leakage | branch accuracy 24.75%; every branch label rate 50% | PASS |
| Split isolation | DEV 800, VALIDATION 800, HELD_OUT 2,400; dependency roots atomic; near-template crossovers 0 | PASS |
| Baseline discipline | learned attacks train DEV and evaluate VALIDATION only | PASS |
| Zero exposure | no ledger, reservation, start, exposure, completion, raw record, or result package | PASS |
| Runner isolation | fresh process blocks analysis reads/imports; production call counter 0 | PASS |
| Raw reconstruction | all 4,000 shapes parse and bind to frozen raw-input digests without production; DEV/VALIDATION scorer simulation passes | PASS |
| Metrics | frozen scorer consumes plain label/pair/group registries; denominators reconstruct | PASS |
| Statistics | exact Clopper-Pearson, exact zero-error upper bound, and deterministic cluster bootstrap are frozen | PASS |
| Explanation | normative expected fields map explicitly to production structured fields; prose excluded | PASS |
| Exhaustive model | 72,660 states, nine properties, zero failures, zero production calls | PASS |
| OWASP | analysis-side `RELEVANT_CONTROL_EVIDENCE` only | PASS |
| External packs | stable schema requires separated runtime/analysis/labels and dual-oracle verification | PASS |
| Same-team bias | retained as a major limitation | BOUNDED |
| Claim pressure | candidate wording and non-claims frozen before execution | PASS |

The runtime packages are bound directly to every scenario's canonical production-input
digest. A canonical run manifest is deliberately deferred to the independent final gate,
because it must bind the then-current final production implementation SHA and one-shot
run identity. Creating that execution envelope may not change any frozen runtime byte,
label, pair, split, oracle, metric, or claim artifact.

Critical substrate coverage began at 83%. Meaningful fail-closed tests lifted raw evidence
to 95% and run-state to 92%; exposure ledger is 89%, reconciliation 87%, runner 86%, and
subprocess isolation 70%, for 88% across the six critical modules. The aspirational 90%
per-module target was not met. Remaining branches are chiefly injected I/O failures,
subprocess import-hook internals, recovery-only ledger anchor races, partial-seal error
paths, and invalid/tampered seal variants. Existing 12-point crash, duplicate token,
duplicate scenario, reconstruction, tamper, seal, label-isolation, HELD_OUT guard,
implementation-binding, and corpus-binding regressions remain mandatory and pass.

Freeze is permitted because no primary validity issue is unresolved and production
exposure is zero. Authorization of `AUTH-COVERAGE-002-RUN-001` remains outside this audit.
