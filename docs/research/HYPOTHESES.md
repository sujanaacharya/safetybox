# Hypotheses

Unless a finalized evidence assessment is recorded below, hypotheses are **proposed and untested**. Operational thresholds, equivalence margins, sample sizes, and statistical tests must be fixed in the associated experiment registrations before data collection.

| ID | Hypothesis | RQs | Candidate experiments |
|---|---|---|---|
| H-01 | Deterministic capability enforcement will prevent nearly all explicitly unauthorized tool actions that are representable in the policy model and mediated by the reference monitor. | RQ-01 | EXP-001, EXP-002 |
| H-02 | Trajectory-aware deterministic monitoring will detect at least one preregistered class of suspicious behavior that independent single-action authorization does not detect. | RQ-02, RQ-08 | EXP-003, EXP-009 |
| H-03 | For deterministic policy violations, B2 will add less decision latency and direct monetary monitoring cost than B3 under matched workloads. | RQ-04, RQ-06 | EXP-005, EXP-007 |
| H-04 | Graduated capability reduction will preserve more benign task completions than immediate termination while meeting the same preregistered containment criterion. | RQ-03 | EXP-004 |
| H-05 | Some semantic or intent-level attacks conducted through otherwise authorized actions will not be reliably distinguishable using the available deterministic runtime telemetry alone. | RQ-07 | EXP-008 |
| H-06 | Equivalent normalized requests evaluated under the same state and policy version will produce consistent B2 decisions across repeated runs. | RQ-04, RQ-06 | EXP-005, EXP-007 |
| H-07 | Under matched contracts and policies, the deterministic core's authorization decisions will be invariant to model provider and agent framework; end-to-end outcomes may still differ. | RQ-05 | EXP-006 |
| H-08 | Task-scoped capabilities will reduce the set of resources reachable after successful prompt injection relative to broadly scoped authority. | RQ-09 | EXP-010 |
| H-09 | Stateful rate, sequence, and boundary-probing policies will contain more registered evasion trajectories than static per-action allow/deny lists. | RQ-08, RQ-10 | EXP-009, EXP-011 |
| H-10 | A deterministic-plus-LLM hybrid will improve detection for selected semantic scenarios over deterministic enforcement alone, but with higher latency, cost, and repeated-run variability. | RQ-06, RQ-07 | EXP-007, EXP-008 |

Failure to support a hypothesis is a valid research outcome. The [Claims Ledger](CLAIMS_LEDGER.md) must not treat these statements as conclusions.

## H-02 evidence assessment — EXP-009 Claim Synthesis v1

**Status:** `PARTIALLY_SUPPORTED`

**Hypothesis wording:** “Trajectory-aware deterministic monitoring will detect at least one preregistered class of suspicious behavior that independent single-action authorization does not detect.”

**Evidence:** EXP-009, EXP-009-A1, EXP-009-A2, and EXP-009-A3. In the frozen base, trajectory monitoring produced findings for 20/20 TRJ-001 positive scenarios with `policy_blocked_steps = 0`. A3 independently attributed these findings to TRJ-001.

**Scope:** synthetic held-out `EXP-009-CORPUS@1` and the frozen M5 deterministic observational rule architecture only.

**Limitations:** 33/40 trajectory-negative scenarios and 33/36 hard negatives were flagged. All 10/10 TRJ-001 contrast pairs had both the positive and opposite-label benign scenario flagged. A1 did not resolve TRJ-002 purpose ambiguity at the three preregistered thresholds, A2 exposed no window sensitivity at 4, 8, or 16, and A3 showed that both rule families independently contribute a similar false-positive burden. M5 findings are observational and do not establish prevention, pre-execution detection, or real-world generalization.
