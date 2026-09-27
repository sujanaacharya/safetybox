# SafetyBox

SafetyBox is a research project investigating an external, deterministic runtime safety and control architecture for autonomous AI agents. The protected agent is not trusted to enforce its own constraints: proposed controls sit between the agent and privileged tools or resources.

> **Status:** SafetyBox Gateway v0.1 is the first deployable product surface.
> It is a scoped mediation library/CLI, not an OS sandbox. Research artifacts
> remain separately governed; see `SAFETYBOX_SECURITY_BOUNDARY.md` before use.

## Problem statement

The project asks whether an external runtime can detect, prevent, and contain unauthorized or task-deviating agent behavior without depending primarily on another language model as the safety judge. The intended system uses task contracts, scoped capabilities, deterministic policies, observable events, trajectory signals, and auditable enforcement decisions.

## Architecture at a glance

```text
User -> Task Contract -> Agent -> SafetyBox reference monitor -> Tools/resources
                                  | policy and authorization
                                  | trajectory and risk state
                                  | audit and provenance
                                  + allow / restrict / escalate / contain
```

The logical design is documented in [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md). SafetyBox is intended to remain model-provider-neutral and adaptable across agent frameworks.

## Research questions

The study covers deterministic authorization, pre-execution deviation detection, graduated capability restriction, overhead, framework generalization, comparisons with LLM monitors, limitations of deterministic signals, trajectory monitoring, blast-radius reduction, and monitor evasion. See the canonical [Research Questions](docs/research/RESEARCH_QUESTIONS.md) and [Hypotheses](docs/research/HYPOTHESES.md).

## Repository map

- `docs/research/`: proposal, questions, hypotheses, related-work plan, and claims ledger.
- `docs/architecture/`: conceptual system and enforcement semantics.
- `docs/threat-model/`: assets, attackers, boundaries, and threat scenarios.
- `docs/experiments/`: evaluation protocol, metrics, baselines, and reproducibility.
- `docs/decisions/`: architecture decision records (ADRs).
- `src/`, `tests/`: reserved for later implementation and verification.
- `benchmarks/`, `experiments/`, `configs/`, `datasets/`, `results/`: future research artifacts governed by [Project Governance](docs/PROJECT_GOVERNANCE.md).

Start with the [Documentation Index](docs/DOCUMENTATION_INDEX.md).

## Current milestones

M0, the research specification, is in progress. Implementation begins only after its exit criteria are met. The staged plan is in [ROADMAP.md](ROADMAP.md).

## Development and citation

Contributions must follow [CONTRIBUTING.md](CONTRIBUTING.md). Cite this evolving software artifact using [CITATION.cff](CITATION.cff); publication-specific citation details will be added only when available.

Licensed under the [MIT License](LICENSE).
