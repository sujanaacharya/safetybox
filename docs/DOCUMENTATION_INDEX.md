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
- [Research Progress](research/RESEARCH_PROGRESS.md)
- [Evidence Matrix](research/EVIDENCE_MATRIX.md)
- [Real Filesystem Mediation Requirements](research/REAL_FILESYSTEM_MEDIATION_REQUIREMENTS.md)
- [Real Subprocess Mediation Requirements](research/REAL_SUBPROCESS_MEDIATION_REQUIREMENTS.md)
- [EXP-014 Requirement Traceability](research/EXP-014_REQUIREMENT_TRACEABILITY.md)
- [EXP-015 Requirement Traceability](research/EXP-015_REQUIREMENT_TRACEABILITY.md)
- [Paper Outline](research/PAPER_OUTLINE.md)

## Architecture

- [System Architecture](architecture/SYSTEM_ARCHITECTURE.md) and [Component Model](architecture/COMPONENT_MODEL.md)
- [Deterministic Engine](architecture/DETERMINISTIC_ENGINE.md), [Policy Engine](architecture/POLICY_ENGINE.md), and [Controller](architecture/CONTROLLER.md)
- [Task Contract](architecture/TASK_CONTRACT.md), [Task Context](architecture/TASK_CONTEXT.md), [Context Evaluation](architecture/CONTEXT_EVALUATION.md), and [Capability Model](architecture/CAPABILITY_MODEL.md)
- [Event Model](architecture/EVENT_MODEL.md), [Trajectory Monitor](architecture/TRAJECTORY_MONITOR.md), [Single-Observation Context Baseline](architecture/SINGLE_OBSERVATION_BASELINE.md), [Context-Aware Trajectory Monitor](architecture/CONTEXT_AWARE_TRAJECTORY_MONITOR.md), [B4 Bounded Context Trajectory Monitor](architecture/B4_BOUNDED_CONTEXT_TRAJECTORY.md), [B4 History Context](architecture/B4_HISTORY_CONTEXT.md), and [Trust Model](architecture/TRUST_MODEL.md)
- [Audit and Provenance](architecture/AUDIT_AND_PROVENANCE.md)
- [Real Filesystem Mediation](architecture/REAL_FILESYSTEM_MEDIATION.md)
- [Real Subprocess Mediation](architecture/REAL_SUBPROCESS_MEDIATION.md)
- [Threat Boundaries](architecture/THREAT_BOUNDARIES.md), [Failure Modes](architecture/FAILURE_MODES.md), and [Safety Invariants](architecture/SAFETY_INVARIANTS.md)

## Threat model and experiments

- [Threat Model](threat-model/THREAT_MODEL.md) and [Attack Scenarios](threat-model/ATTACK_SCENARIOS.md)
- [Real Filesystem Threat Extension](threat-model/REAL_FILESYSTEM_THREATS.md)
- [Real Subprocess Threat Extension](threat-model/REAL_SUBPROCESS_THREATS.md)
- [Assets](threat-model/ASSETS.md), [Trust Boundaries](threat-model/TRUST_BOUNDARIES.md), [Attacker Models](threat-model/ATTACKER_MODELS.md), and [Out of Scope](threat-model/OUT_OF_SCOPE.md)
- [Experiment Plan](experiments/EXPERIMENT_PLAN.md), [Schema](experiments/EXPERIMENT_SCHEMA.md), and [Metrics](experiments/METRICS.md)
- [Baselines](experiments/BASELINES.md), [Ablations](experiments/ABLATIONS.md), and [Reproducibility](experiments/REPRODUCIBILITY.md)
- [EXP-013 Results](experiments/EXP-013-RESULTS.md), [Synthesis](experiments/EXP-013-SYNTHESIS.md), [Counterfactual-Pair Audit](experiments/EXP-013-COUNTERFACTUAL-PAIR-AUDIT.md), [False-Negative Audit](experiments/EXP-013-FALSE-NEGATIVE-AUDIT.md), and [Label-Isolation Audit](experiments/EXP-013-LABEL-ISOLATION-AUDIT.md)
- [EXP-014 Real Filesystem Mediation Protocol](experiments/EXP-014-real-filesystem-mediation.md)
- [EXP-014 Adapter Development Validation](experiments/EXP-014-ADAPTER-DEVELOPMENT-VALIDATION.md)
- [EXP-014 Results](experiments/EXP-014-RESULTS.md), [Synthesis](experiments/EXP-014-SYNTHESIS.md), [Validity Audit](experiments/EXP-014-VALIDITY-AUDIT.md), and [Post-Run Gate Disposition](experiments/EXP-014-POST-RUN-GATE-DISPOSITION.md)
- [EXP-015 Real Subprocess Mediation Protocol](experiments/EXP-015-real-subprocess-mediation.md)
- [EXP-015 Adapter Development Validation](experiments/EXP-015-ADAPTER-DEVELOPMENT-VALIDATION.md)

## Engineering

- [EXP-014 Filesystem Diligence Notes](engineering/EXP-014_FILESYSTEM_DILIGENCE_NOTES.md)
- [EXP-014 Pre-Corpus Freeze Audit](engineering/EXP-014_PRE_CORPUS_FREEZE_AUDIT.md)
- [EXP-015 Pre-Freeze Protocol and Authorization Quality Audit](engineering/EXP-015_PRE_FREEZE_PROTOCOL_AUTHORIZATION_AUDIT.md)
- [EXP-015 Process Adapter Diligence Notes](engineering/EXP-015_PROCESS_DILIGENCE_NOTES.md)
- [EXP-015 Pre-Corpus Implementation Freeze Audit](engineering/EXP-015_PRE_CORPUS_IMPLEMENTATION_FREEZE_AUDIT.md)
- [EXP-015 Frozen Corpus Ruff Disposition](engineering/EXP-015_FROZEN_CORPUS_RUFF_DISPOSITION.md)
- [EXP-015 Corpus@1 Validity Disposition](engineering/EXP-015_CORPUS_1_VALIDITY_DISPOSITION.md)
- [EXP-015 Pre-Run Test-Process Isolation Disposition](engineering/EXP-015_PRE_RUN_TEST_PROCESS_ISOLATION_DISPOSITION.md)
- [EXP-015 Pre-Run Gate Redisposition](engineering/EXP-015_PRE_RUN_GATE_REDISPOSITION.md)

## Strategy

- [OWASP GenAI and Agentic Coverage Plan](strategy/OWASP_GENAI_AGENTIC_COVERAGE_PLAN.md)
- [Build vs Claim Matrix](strategy/BUILD_VS_CLAIM_MATRIX.md)

## Architecture decisions

- [ADR-006 Real Filesystem Mediation Boundary](decisions/ADR-006-real-filesystem-mediation-boundary.md)
- [ADR-007 Argv-Native Subprocess Mediation Before Shell Mediation](decisions/ADR-007-argv-native-subprocess-before-shell.md)

See [`docs/decisions/`](decisions/) for numbered ADRs. Architecture changes require a new record rather than silent edits to prior decisions.

## Documentation validation

Before merge: verify relative links and filenames; check identifier formats and duplicate allocations; search unsupported certainty language; allow citation-verification placeholders only in related-work planning; confirm citations against primary sources before adding them; and inspect the final Git diff and tree.
