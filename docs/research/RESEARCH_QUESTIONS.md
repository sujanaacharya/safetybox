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
| RQ-11 | Can autonomous AI agents remain useful and capable while deterministic, task-scoped authority prevents protected effects beyond explicitly delegated authority? | `AUTH-COVERAGE-002`, EXP-016, `UNAUTHORIZED-EFFECT-001`, and later real-agent evaluation form the dependency-ordered program. |
| RQ-12 | Does the production authorizer correctly bind subject/session, task, action, resource, constraints, and valid authority without cross-task reuse or amplification? | `AUTH-COVERAGE-002` plus future identity and Authority V2 studies. |
| RQ-13 | Which protected-effect primitives are compulsorily mediated, and which aliases or alternate routes bypass the reference monitor? | EXP-014/016, `UNAUTHORIZED-EFFECT-001`, and later network/MCP route studies. |
| RQ-14 | Can every observed protected effect be independently established and reconstructed to the responsible request, authority source, mediator, and causal/delegation lineage? | `UNAUTHORIZED-EFFECT-001` and the effect-provenance program. |
| RQ-15 | How should principal, agent, session, task, delegation, and authority-source identities be authenticated and bound without treating task-ID equality as identity? | Authority V2 identity architecture followed by replay and cross-principal experiments. |
| RQ-16 | Can probabilistic task interpretation be converted into deterministic least-authority proposals without model output or context becoming authority? | AI-to-authority compiler/verifier and `CONTEXT-AUTH-001`. |
| RQ-17 | Can delegation, attenuation, expiry, and revocation preserve a formal subset relation under concurrency, caching, in-flight operations, and child agents? | Authority V2 formal verification and later multi-agent experiments. |
| RQ-18 | Can trajectory evidence safely flag, request approval, or attenuate authority while never silently expanding it? | Follow-on B4 restriction/approval studies after lifecycle semantics exist. |
| RQ-19 | Under goal hijack or deliberately rogue behavior, do fixed deterministic authority and named mediated boundaries contain unauthorized effects? | `OWASP-AGENTIC-BENCH-001` after applicable authorization and mediator evidence. |
| RQ-20 | What completion, false-deny, approval, provenance, and recovery costs arise when the controls are applied to provider-neutral real agents? | Future real-agent harness and external scenario packs. |

## Interpretation constraints

- “Prevent” means the protected action did not execute, not merely that it was logged.
- “Before” requires a decision timestamp preceding any tool-side effect.
- “Generalize” is bounded to explicitly sampled models, frameworks, tasks, and adapters.
- RQ-07 requires reporting limitations even if other results are favorable.
- Experiment IDs are reserved candidate records; final protocols must be registered before execution.
- RQ-11 is the long-term primary question. No answer to its authorization component alone
  answers its mediation, effect, attribution, or utility components.
- Subject/session binding is not established by string equality between task identifiers.
- “Rogue-agent containment” must always name an evidenced mediator surface and its known
  bypasses.
