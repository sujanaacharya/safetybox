# Claims Ledger

Allowed statuses are `PROPOSED`, `TESTING`, `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`, and `RETIRED`. Status changes require linked finalized evidence and review. All initial entries are `PROPOSED`.

| Claim ID | Candidate claim | Evidence needed | Experiments | Status |
|---|---|---|---|---|
| CL-001 | SafetyBox prevents policy-represented unauthorized tool actions when mediation is complete. | Execution-side evidence across explicit violations; bypass and failure tests; confidence intervals. | EXP-001, EXP-002 | PROPOSED |
| CL-002 | Trajectory-aware rules detect registered suspicious sequences missed by independent action authorization. | Matched trajectory suite and component ablation. | EXP-003, EXP-009 | PARTIALLY_SUPPORTED |
| CL-003 | Deterministic enforcement adds lower latency and direct monitoring cost than an LLM-only monitor for deterministic violations. | Controlled performance/cost comparison with workload and provider details. | EXP-005, EXP-007 | PROPOSED |
| CL-004 | Graduated restriction preserves benign utility while meeting a defined containment target. | Matched trials against immediate termination and preregistered containment/utility criteria. | EXP-004 | PROPOSED |
| CL-005 | Core authorization behavior is portable across selected models and agent frameworks after request normalization. | Cross-platform matrix, adapter conformance tests, and scoped interpretation. | EXP-006 | PROPOSED |
| CL-006 | Deterministic telemetry alone has identifiable blind spots for semantic misuse through authorized channels. | Categorized negative results and observability analysis. | EXP-008 | PROPOSED |
| CL-007 | Task-scoped capabilities reduce reachable resources under prompt injection relative to broad authority. | Blast-radius definition and matched compromised-agent trials. | EXP-010 | PROPOSED |
| CL-008 | Stateful policies improve resistance to registered monitoring-evasion trajectories over static allow/deny lists. | Adaptive scenario trials and ablations with false-positive reporting. | EXP-009, EXP-011 | PROPOSED |

M5 provides implementation readiness for controlled trajectory experiments only. It does not change any claim status.

## CL-002 evidence review — EXP-009 Claim Synthesis v1

**Status:** `PARTIALLY_SUPPORTED`

**Evidence:** EXP-009, EXP-009-A1, EXP-009-A2, and EXP-009-A3. The frozen base detected 40/40 trajectory positives, including 20/20 TRJ-001 positives with zero action-level policy blocks. The component ablation attributed those 20 incremental observational findings to TRJ-001.

**Scope:** synthetic held-out `EXP-009-CORPUS@1` only, using the frozen M5 deterministic observational rule architecture.

**Limitations:** the base also flagged 33/40 negatives and 33/36 hard negatives; all 10/10 TRJ-001 contrast pairs had both labels flagged. A1 found a sharp TRJ-002 sensitivity/specificity tradeoff at thresholds 2, 3, and 4; A2 found no outcome change at windows 4, 8, and 16; A3 showed independent false-positive burdens of 16 for TRJ-001 and 17 for TRJ-002 with no interaction. Findings are observational, not preventive. The evidence does not establish real-world generalization or general unsafe-behavior detection.

The broad candidate wording is retained, but it must be cited with this scope. A bounded empirical result is: on `EXP-009-CORPUS@1`, deterministic trajectory monitoring identified all 40/40 preregistered trajectory-positive scenarios, including 20 TRJ-001 cases with no action-level policy block, but produced 33 false positives among 40 negatives.

Candidate claims must be narrowed if evidence covers only particular tools, scenarios, models, or deployment assumptions. No claim may be promoted on intuition, demonstrations alone, or non-finalized results.
