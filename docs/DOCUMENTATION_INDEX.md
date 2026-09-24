# Documentation Index

This index identifies the canonical owner of each concept. Other documents should link rather than redefine it.

## Project governance

- [Project Governance](PROJECT_GOVERNANCE.md): contribution, artifacts, datasets, and research-integrity rules.
- [Glossary](GLOSSARY.md): canonical terminology.
- [Naming Conventions](NAMING_CONVENTIONS.md): identifiers and filesystem names.
- [Versioning](VERSIONING.md): software, schema, policy, benchmark, and artifact versions.
- [Roadmap](../ROADMAP.md): staged delivery and exit criteria.

## Research

- [Research Proposal](research/RESEARCH_PROPOSAL.md)
- [Research Questions](research/RESEARCH_QUESTIONS.md)
- [Hypotheses](research/HYPOTHESES.md)
- [Related Work](research/RELATED_WORK.md)
- [Contributions](research/CONTRIBUTIONS.md)
- [Scope and Non-Goals](research/SCOPE_AND_NON_GOALS.md)
- [Claims Ledger](research/CLAIMS_LEDGER.md)
- [Paper Outline](research/PAPER_OUTLINE.md)

## Architecture

- [System Architecture](architecture/SYSTEM_ARCHITECTURE.md) and [Component Model](architecture/COMPONENT_MODEL.md)
- [Deterministic Engine](architecture/DETERMINISTIC_ENGINE.md), [Policy Engine](architecture/POLICY_ENGINE.md), and [Controller](architecture/CONTROLLER.md)
- [Task Contract](architecture/TASK_CONTRACT.md), [Task Context](architecture/TASK_CONTEXT.md), [Context Evaluation](architecture/CONTEXT_EVALUATION.md), and [Capability Model](architecture/CAPABILITY_MODEL.md)
- [Event Model](architecture/EVENT_MODEL.md), [Trajectory Monitor](architecture/TRAJECTORY_MONITOR.md), [Single-Observation Context Baseline](architecture/SINGLE_OBSERVATION_BASELINE.md), [Context-Aware Trajectory Monitor](architecture/CONTEXT_AWARE_TRAJECTORY_MONITOR.md), [B4 Bounded Context Trajectory Monitor](architecture/B4_BOUNDED_CONTEXT_TRAJECTORY.md), [B4 History Context](architecture/B4_HISTORY_CONTEXT.md), and [Trust Model](architecture/TRUST_MODEL.md)
- [Audit and Provenance](architecture/AUDIT_AND_PROVENANCE.md)
- [Threat Boundaries](architecture/THREAT_BOUNDARIES.md), [Failure Modes](architecture/FAILURE_MODES.md), and [Safety Invariants](architecture/SAFETY_INVARIANTS.md)

## Threat model and experiments

- [Threat Model](threat-model/THREAT_MODEL.md) and [Attack Scenarios](threat-model/ATTACK_SCENARIOS.md)
- [Assets](threat-model/ASSETS.md), [Trust Boundaries](threat-model/TRUST_BOUNDARIES.md), [Attacker Models](threat-model/ATTACKER_MODELS.md), and [Out of Scope](threat-model/OUT_OF_SCOPE.md)
- [Experiment Plan](experiments/EXPERIMENT_PLAN.md), [Schema](experiments/EXPERIMENT_SCHEMA.md), and [Metrics](experiments/METRICS.md)
- [Baselines](experiments/BASELINES.md), [Ablations](experiments/ABLATIONS.md), and [Reproducibility](experiments/REPRODUCIBILITY.md)
- [EXP-013 Results](experiments/EXP-013-RESULTS.md), [Synthesis](experiments/EXP-013-SYNTHESIS.md), [Counterfactual-Pair Audit](experiments/EXP-013-COUNTERFACTUAL-PAIR-AUDIT.md), [False-Negative Audit](experiments/EXP-013-FALSE-NEGATIVE-AUDIT.md), and [Label-Isolation Audit](experiments/EXP-013-LABEL-ISOLATION-AUDIT.md)

## Strategy

- [OWASP GenAI and Agentic Coverage Plan](strategy/OWASP_GENAI_AGENTIC_COVERAGE_PLAN.md)

## Architecture decisions

See [`docs/decisions/`](decisions/) for numbered ADRs. Architecture changes require a new record rather than silent edits to prior decisions.

## Documentation validation

Before merge: verify relative links and filenames; check identifier formats and duplicate allocations; search unsupported certainty language; allow citation-verification placeholders only in related-work planning; confirm citations against primary sources before adding them; and inspect the final Git diff and tree.
