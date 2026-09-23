# Contributing to SafetyBox

SafetyBox is research software. Contributions must preserve traceability between design decisions, requirements, experiments, evidence, and claims.

## Before contributing

1. Read [Project Governance](docs/PROJECT_GOVERNANCE.md), [Naming Conventions](docs/NAMING_CONVENTIONS.md), and the relevant canonical document.
2. Open or reference an issue describing scope and motivation.
3. For architecture-changing work, add an ADR before or with the change.
4. For experimental work, allocate an experiment ID and identify its research questions and hypotheses.

## Development workflow

- Branch from `main` using `type/short-description`, such as `docs/task-contract` or `experiment/exp-001`.
- Keep commits focused and use the Conventional Commits form described in governance.
- Do not mix research results, architecture changes, and unrelated cleanup in one pull request.
- Add or update tests when implementation behavior changes.
- Update documentation and the changelog when the public behavior or research protocol changes.
- Never commit credentials, private datasets, unreviewed large artifacts, or generated caches.

## Pull requests

A pull request must state:

- purpose and bounded scope;
- linked issue, requirement, ADR, experiment, or threat scenario IDs;
- validation performed;
- documentation and compatibility impact;
- research-claim impact, including claim IDs when applicable;
- known limitations and follow-up work.

Reviewers should reject unsupported claims, silent scope expansion, non-reproducible experiments, and code paths that bypass the intended reference monitor. Approval requirements may become stricter as maintainers and CI policies are established.

## Research integrity

- Label proposed behavior as design, hypotheses as hypotheses, and observed results as evidence.
- Do not promote a claim in the claims ledger without referenced finalized experiments.
- Do not alter finalized result artifacts. Corrections require a new immutable result set with provenance.
- Do not invent citations. Mark unverified literature entries as citation-verification placeholders.

## Local checks

Once implementation begins, the expected baseline commands are:

```bash
ruff check .
mypy src
pytest
```

Documentation-only changes must also pass the repository validation procedure in [Documentation Index](docs/DOCUMENTATION_INDEX.md).
