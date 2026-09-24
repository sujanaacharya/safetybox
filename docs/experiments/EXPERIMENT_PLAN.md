# Experiment Plan

## Purpose

Experiments test registered questions and hypotheses; they do not exist to confirm a preferred architecture. Each final protocol must identify primary outcomes, denominators, exclusions, trial unit, stopping rule, analysis, uncertainty, and failure handling before execution.

## Candidate experiment registry

| ID | Title | RQs | Hypotheses | Primary comparison |
|---|---|---|---|---|
| EXP-001 | Explicit unauthorized-action prevention | RQ-01 | H-01 | B0/B1/B2 over policy-representable violations |
| EXP-002 | Complete mediation and fail-safe behavior | RQ-01 | H-01 | Fault/bypass cases under B2 |
| EXP-003 | Pre-execution task-deviation detection | RQ-02 | H-02 | Benign and adversarial deviations |
| EXP-004 | Graduated containment and utility | RQ-03 | H-04 | Degradation vs quarantine/termination |
| EXP-005 | Deterministic enforcement overhead | RQ-04 | H-03, H-06 | B0/B1/B2 under controlled loads |
| EXP-006 | Cross-model/framework stability | RQ-05 | H-07 | Matched contracts via conforming adapters |
| EXP-007 | Deterministic, LLM, and hybrid monitors | RQ-06 | H-03, H-06, H-10 | B2/B3/B4 on frozen scenarios |
| EXP-008 | Deterministic observability blind spots | RQ-07 | H-05, H-10 | Categorized semantic/authorized-channel cases |
| EXP-009 | Trajectory-level detection | RQ-08 | H-02, H-09 | Action-only vs stateful deterministic rules |
| EXP-010 | Prompt-injection blast-radius reduction | RQ-09 | H-08 | Broad/static/task-scoped authority |
| EXP-011 | Adaptive monitoring evasion | RQ-10 | H-09 | Static and stateful policies under evasion |
| EXP-012 | Context-aware deterministic trajectory monitoring | RQ-08 | H-02; H-CTX-01 through H-CTX-05 (operational) | Action authorization vs frozen M5 vs M5.1 on paired contextual scenarios |
| EXP-013 | Counterfactual multi-step contextual trajectory evaluation | RQ-08 | H-MS-01 through H-MS-05 (operational) | Frozen M5 and M5.1 vs a frozen single-observation context baseline on history-required counterfactual pairs |
| EXP-014 | Real filesystem mediation and complete-path evaluation | RQ-01, RQ-04, RQ-10 | Preregistered protocol questions | Adapter-routed real filesystem behavior and direct-route boundary at FMED-L1 |
| EXP-015 | Real subprocess mediation and command execution control | RQ-01, RQ-04, RQ-10 | Preregistered protocol questions | Adapter-routed direct executable/argv behavior and direct-route boundary at PMED-L1 |

These IDs reserve candidate studies; registration files will define executable protocols later.

## Shared design requirements

- Separate benign task utility from adversarial prevention outcomes.
- Use a versioned scenario/benchmark manifest with balanced, disclosed sampling.
- Record request authorization and actual tool-side execution separately.
- Distinguish a monitor's detection from controller containment.
- Use matched tasks and seeds where available; randomize order when order effects matter.
- Report adapter/parser failures and exclusions, not silently discard them.
- Include confidence intervals or suitable uncertainty and disclose multiple comparisons.
- Freeze analysis rules before primary evaluation; exploratory results are labeled.

## M4 simulator relationship

M4 supplies deterministic, harmless scenario execution and raw M3-linked evidence; it does not execute registered experiments or produce benchmark results. The initial corpus and its status are documented in [Threat Simulator](THREAT_SIMULATOR.md). Future protocols may select and freeze a versioned subset only after defining denominators, baselines, sampling, and analysis.

M5 supplies a separate deterministic trajectory-evaluation seam: scenario evidence may be evaluated with no trajectory monitor or with configured bounded rules without modifying the scenario runner. Its finding sequence ranges and detection sequence numbers prepare EXP-009 measurements; no registered experiment has yet run.

## Lifecycle

1. Draft registration and threat/benchmark mapping.
2. Review validity, ethics, data handling, and resource plan.
3. Freeze protocol, code/config versions, and analysis plan.
4. Run pilots only on designated non-primary data.
5. Execute trials and store raw immutable artifacts.
6. Validate metadata and checksums; finalize the result set.
7. Run scripted analysis, report deviations, and update the claims ledger conservatively.
