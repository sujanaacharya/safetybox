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
| CL-009 | Ordered deterministic trajectory evidence provides discriminative information beyond single-observation context evaluation. | Frozen history-free baseline; held-out matched history-required pairs; hard negatives; leakage, coupling, and label-isolation audits. | EXP-013 | PARTIALLY_SUPPORTED |
| CL-010 | SafetyBox can correctly mediate real filesystem operations at the explicitly bounded FMED-L1 adapter route. | Frozen held-out real-tool outcomes; independent authorization/canonicalization/state checks; bypass, failure, audit, and validity analysis. | EXP-014 | PARTIALLY_SUPPORTED |
| CL-011 | SafetyBox can mediate adapter-routed subprocess execution with deterministic authorize-before-spawn ordering and prevent denied child-process creation within the tested PMED-L1 boundary. | Frozen process adapter; held-out real-tool outcomes; denied-spawn, argv, executable/cwd, environment, ordering, failure, audit, bypass, and validity analysis. | EXP-015 | PROPOSED |

M5 provides implementation readiness for controlled trajectory experiments only. It does not change any claim status.

## CL-002 evidence review — EXP-009 Claim Synthesis v1

**Status:** `PARTIALLY_SUPPORTED`

**Evidence:** EXP-009, EXP-009-A1, EXP-009-A2, and EXP-009-A3. The frozen base detected 40/40 trajectory positives, including 20/20 TRJ-001 positives with zero action-level policy blocks. The component ablation attributed those 20 incremental observational findings to TRJ-001.

**Scope:** synthetic held-out `EXP-009-CORPUS@1` only, using the frozen M5 deterministic observational rule architecture.

**Limitations:** the base also flagged 33/40 negatives and 33/36 hard negatives; all 10/10 TRJ-001 contrast pairs had both labels flagged. A1 found a sharp TRJ-002 sensitivity/specificity tradeoff at thresholds 2, 3, and 4; A2 found no outcome change at windows 4, 8, and 16; A3 showed independent false-positive burdens of 16 for TRJ-001 and 17 for TRJ-002 with no interaction. Findings are observational, not preventive. The evidence does not establish real-world generalization or general unsafe-behavior detection.

The broad candidate wording is retained, but it must be cited with this scope. A bounded empirical result is: on `EXP-009-CORPUS@1`, deterministic trajectory monitoring identified all 40/40 preregistered trajectory-positive scenarios, including 20 TRJ-001 cases with no action-level policy block, but produced 33 false positives among 40 negatives.

Candidate claims must be narrowed if evidence covers only particular tools, scenarios, models, or deployment assumptions. No claim may be promoted on intuition, demonstrations alone, or non-finalized results.

## CL-009 evidence review — EXP-013 Claim Synthesis v1

**Status:** `PARTIALLY_SUPPORTED` in the repository-wide ledger; the candidate is
`SUPPORTED_WITHIN_EXP_013` under the experiment-specific assessment.

**Evidence:** `EXP-013-RUN-001`, `EXP-013-CORPUS@1`,
`B2-SINGLE-OBSERVATION@1`, and `B4-BOUNDED-CONTEXT-TRAJECTORY@1`. All 80 primary
observations were locally `CONTEXT_CONSISTENT`. B2 detected 0/40 positives, produced
0/40 matched-negative false positives, and discriminated 0/40 pairs. B4 detected 38/40
positives, produced 0/40 matched-negative false positives, and discriminated 38/40
pairs. B4 corrected 38 B2 false negatives without changing any B2 true negative. All
ten frozen success criteria passed and 60/60 normalized semantic repeat comparisons
agreed.

**Scope:** synthetic held-out `EXP-013-CORPUS@1` only, using frozen structured
declarations and the frozen bounded deterministic B4 architecture. A bounded empirical
statement is: on `EXP-013-CORPUS@1`, B4 correctly discriminated 38 of 40
history-required counterfactual pairs that B2 could not distinguish, with no false
positives among 40 matched hard negatives.

**Limitations:** the corpus is handcrafted and had protocol/schema-only separation from
detector source, without independent authorship or label review. Two allowed-restart
cases were missed because the frozen context/rule contract lacks an allowed episode-start
relation. Five earliest detections use an initial-phase declaration at action 1, although
those scenarios later produce cross-observation findings. B4 is observational, uses
synthetic events and clean trusted declarations, cannot detect internally consistent
semantic staleness, and does not prove payload or causal data flow. No real-agent,
real-tool, containment, window-ablation, or production evaluation exists.

The status is not a claim that SafetyBox detects unsafe agent behavior generally.

## CL-010 evidence review — EXP-014 Claim Synthesis v1

**Status:** `PARTIALLY_SUPPORTED` in the repository-wide ledger; the bounded empirical
claim is `SUPPORTED_WITHIN_EXP_014_FMED_L1` under `EXP-014-ANALYSIS-001`.

**Evidence:** `EXP-014-RUN-001`, `EXP-014-CORPUS@1`, and frozen `FS-ADAPTER@1`.
All 94 adapter-routed scenarios produced the registered terminal outcome; independent
policy derivation matched 91/91 authorization labels and decisions; 19/19 policy-denied
mutations had neither a wrapped primitive call nor independently observed state change;
and 9/9 policy-denied retrievals had no protected primitive call or protected result in
the evaluated caller, safe-error, and serialized audit/event channels. Tested ordering,
audit reconstruction fields, and audit truthfulness passed 94/94.

**Bounded empirical statement:** on `EXP-014-CORPUS@1`, frozen `FS-ADAPTER@1` correctly
mediated all 94 adapter-routed held-out scenarios in an isolated temporary Linux
filesystem at FMED-L1 under the registered outcome and observation rules.

**Limitations:** FMED-L1 assumes calls enter the adapter. Direct OS/pathlib, shell, native
code, inherited descriptors, races, concurrency, process compromise, and kernel bypass
remain outside the boundary. Nondisclosure did not instrument every process/debug
channel; reconstruction is partly schema-coupled; failure injections are conformance
tests; the corpus is same-team authored; audit is in-process and non-durable; and no real
agent, customer deployment, external replication, cross-platform, or production evidence
exists. The result must not be restated as complete filesystem security or whole-category
OWASP coverage.
