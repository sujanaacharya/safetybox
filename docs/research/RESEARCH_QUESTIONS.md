# Research Questions

These questions define the initial study. Candidate experiments are designs, not completed studies.

| ID | Research question | Candidate experiments |
|---|---|---|
| RQ-01 | To what extent can an external deterministic runtime prevent policy-represented unauthorized agent actions without an LLM safety judge? | EXP-001 compares B0/B1/B2 on explicit capability violations; EXP-002 tests fail-safe behavior and mediation completeness. |
| RQ-02 | Can observable runtime behavior identify deviations from a declared task contract before a harmful external action executes? | EXP-003 measures pre-execution detection over task-deviation scenarios, with action-level and contextual rules. |
| RQ-03 | Can dynamic capability restriction contain suspicious behavior while preserving more benign task completion than immediate termination? | EXP-004 compares graduated degradation, quarantine, and immediate termination. |
| RQ-04 | What latency, CPU, memory, throughput, and operational overhead does deterministic runtime enforcement introduce? | EXP-005 benchmarks B0/B1/B2 under controlled action mixes and load. |
| RQ-05 | How stable are SafetyBox decisions and outcomes across selected model providers and agent frameworks using equivalent tasks and policies? | EXP-006 runs a preregistered cross-model/framework matrix while controlling adapters and task contracts. |
| RQ-06 | How do deterministic and LLM-as-a-judge monitoring compare in detection quality, errors, latency, monetary cost, token usage, reproducibility, and explanation traceability? | EXP-007 compares B2/B3/B4 on a frozen scenario suite. |
| RQ-07 | Which unsafe behavior classes are not reliably identifiable from the deterministic runtime signals available to SafetyBox? | EXP-008 performs categorized blind-spot and observability analysis, including authorized-channel semantic misuse. |
| RQ-08 | Does trajectory-level monitoring detect suspicious multi-step behavior missed by independently authorizing each action? | EXP-009 compares action-only rules with ordered-sequence policies on matched trajectories. |
| RQ-09 | To what extent do task-scoped capability contracts reduce realized harm and reachable resources under prompt injection or agent compromise? | EXP-010 measures execution and blast-radius outcomes across unscoped, static, and task-scoped authority. |
| RQ-10 | How robust is SafetyBox against agents that intentionally probe, evade, obfuscate, or disable monitoring? | EXP-011 evaluates adaptive evasion scenarios against documented assumptions and failure modes. |

## Interpretation constraints

- “Prevent” means the protected action did not execute, not merely that it was logged.
- “Before” requires a decision timestamp preceding any tool-side effect.
- “Generalize” is bounded to explicitly sampled models, frameworks, tasks, and adapters.
- RQ-07 requires reporting limitations even if other results are favorable.
- Experiment IDs are reserved candidate records; final protocols must be registered before execution.
