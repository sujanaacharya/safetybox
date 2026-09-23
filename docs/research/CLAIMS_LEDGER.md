# Claims Ledger

Allowed statuses are `PROPOSED`, `TESTING`, `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`, and `RETIRED`. Status changes require linked finalized evidence and review. All initial entries are `PROPOSED`.

| Claim ID | Candidate claim | Evidence needed | Experiments | Status |
|---|---|---|---|---|
| CL-001 | SafetyBox prevents policy-represented unauthorized tool actions when mediation is complete. | Execution-side evidence across explicit violations; bypass and failure tests; confidence intervals. | EXP-001, EXP-002 | PROPOSED |
| CL-002 | Trajectory-aware rules detect registered suspicious sequences missed by independent action authorization. | Matched trajectory suite and component ablation. | EXP-003, EXP-009 | PROPOSED |
| CL-003 | Deterministic enforcement adds lower latency and direct monitoring cost than an LLM-only monitor for deterministic violations. | Controlled performance/cost comparison with workload and provider details. | EXP-005, EXP-007 | PROPOSED |
| CL-004 | Graduated restriction preserves benign utility while meeting a defined containment target. | Matched trials against immediate termination and preregistered containment/utility criteria. | EXP-004 | PROPOSED |
| CL-005 | Core authorization behavior is portable across selected models and agent frameworks after request normalization. | Cross-platform matrix, adapter conformance tests, and scoped interpretation. | EXP-006 | PROPOSED |
| CL-006 | Deterministic telemetry alone has identifiable blind spots for semantic misuse through authorized channels. | Categorized negative results and observability analysis. | EXP-008 | PROPOSED |
| CL-007 | Task-scoped capabilities reduce reachable resources under prompt injection relative to broad authority. | Blast-radius definition and matched compromised-agent trials. | EXP-010 | PROPOSED |
| CL-008 | Stateful policies improve resistance to registered monitoring-evasion trajectories over static allow/deny lists. | Adaptive scenario trials and ablations with false-positive reporting. | EXP-009, EXP-011 | PROPOSED |

M5 provides implementation readiness for controlled trajectory experiments only. It does not change any claim status.

Candidate claims must be narrowed if evidence covers only particular tools, scenarios, models, or deployment assumptions. No claim may be promoted on intuition, demonstrations alone, or non-finalized results.
