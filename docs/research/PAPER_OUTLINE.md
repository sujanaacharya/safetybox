# Paper Outline

## Working title

*SafetyBox: Evaluating External Deterministic Runtime Controls for Tool-Using AI Agents*

## Proposed structure

1. **Abstract** — bounded question, method, measured results, and limitations; written after experiments.
2. **Introduction** — consequential agent actions, external-control motivation, questions, and validated contributions only.
3. **Background and related work** — reference monitors, capabilities, runtime verification, agent guardrails, monitoring, and benchmarks.
4. **Problem formulation** — agent/tool boundary, task contracts, authorization decisions, attacker and trust assumptions.
5. **SafetyBox design** — deterministic core, event model, trajectory state, containment, audit, and optional semantic signals.
6. **Research methodology** — RQs, hypotheses, scenarios, benchmarks, baselines, metrics, protocol, and analysis plan.
7. **Implementation** — only behavior actually implemented at the evaluated version.
8. **Evaluation** — prevention/detection, utility, overhead, portability, deterministic-versus-LLM comparison, evasion, and ablations.
9. **Discussion** — interpretation, failed hypotheses, blind spots, deployment implications, and threats to validity.
10. **Ethics and responsible disclosure** — misuse, data, human approval, and release considerations.
11. **Reproducibility statement** — artifact contents, versions, immutable results, and known nondeterminism.
12. **Conclusion** — evidence-bounded findings without universal safety claims.

## Traceability requirement

Every result paragraph should reference experiment IDs; every headline claim should map to the [Claims Ledger](CLAIMS_LEDGER.md); design rationale should cite ADRs; limitations should include results relevant to RQ-07 and the documented trust boundaries.
