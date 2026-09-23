# Project Governance

## Purpose and principles

SafetyBox exists to produce research-grade evidence and, if supported by that evidence, a production-quality external runtime control system for autonomous agents. Development is research-first: questions and safety properties precede implementation; experiments precede claims; evidence remains reproducible and auditable.

The project distinguishes five categories:

1. **Design goals** describe intended properties.
2. **Hypotheses** are falsifiable expectations.
3. **Implementation** is what a version actually does.
4. **Experimental evidence** is observation under a recorded protocol.
5. **Conclusions** are bounded interpretations supported by evidence.

No document may collapse these categories. Observable behavior is preferred over agent-reported intent, core enforcement should be deterministic where feasible, and any semantic model is auxiliary rather than a prerequisite for fundamental authorization.

## Branches and commits

- `main` is the reviewable integration branch and should remain releasable as a research artifact.
- Working branches use `docs/`, `feature/`, `fix/`, `experiment/`, `benchmark/`, or `chore/` followed by a short kebab-case description.
- Experiment branches should include the ID, for example `experiment/exp-001-static-authorization`.
- Commits use Conventional Commits: `type(scope): imperative summary`. Reference stable IDs in the body when relevant.
- Rebase or merge policy may be formalized when collaboration infrastructure exists; history must retain meaningful decision and experiment provenance.

## Pull requests

Pull requests require a bounded rationale, linked IDs, validation evidence, compatibility and documentation impact, limitations, and any effect on claims. Architecture-changing decisions require an accepted or concurrently reviewed ADR. Experimental claims must reference experiment IDs. Review must check that the protected agent cannot bypass newly introduced controls.

## Architecture decisions

Fundamental choices and changes to trust boundaries, enforcement semantics, event ordering, policy behavior, contract/capability meaning, or reproducibility guarantees require an ADR. ADRs are immutable historical records except for spelling or link corrections. A changed decision is documented by a new ADR that states which prior ADR it supersedes.

## Identifier and naming policy

Use the formats in [Naming Conventions](NAMING_CONVENTIONS.md): `RQ-NN`, `H-NN`, `EXP-NNN`, `BM-NNN`, `TS-NNN`, `ADR-NNN`, `REQ-NNN`, `INV-NNN`, and `POL-NNN`. IDs are never recycled. Experiment directories should use `EXP-NNN-short-slug`; benchmark directories use `BM-NNN-short-slug`.

## Experiments and results

- Register every experiment before execution with its question, hypotheses, protocol, metrics, baselines, and stopping rule.
- Store executable experiment definitions under `experiments/EXP-NNN-short-slug/` and reusable benchmark definitions under `benchmarks/BM-NNN-short-slug/`.
- Raw outputs belong under `results/EXP-NNN/run-.../` during execution. Large raw outputs normally live in approved artifact storage and are represented by checksummed manifests.
- A finalized experiment must include metadata, environment details, logs or references, analysis version, and checksums.
- **Finalized result files are immutable.** Corrections produce a new result version or experiment with explicit linkage; they never overwrite the original.
- Summary tables small enough for review may be versioned. Generated bulk output and scratch files must not be committed.
- Any paper claim must cite one or more finalized experiment IDs in the claims ledger.

## Datasets

Each dataset requires provenance, version, license or usage authority, collection/generation method, schema, checksums, sensitive-data assessment, and train/evaluation contamination notes. Do not commit secrets, personal data without documented ethical/legal authority, or third-party data whose license prohibits redistribution. Large data must use external immutable storage with a retrieval manifest.

## Generated files

Generated artifacts must state their generator, source inputs, tool version, and reproduction command. Commit generated files only when review or distribution requires them; otherwise ignore them. A generated file must not be hand-edited.

## Notebooks and experimental scripts

- Notebooks are for exploration and communication, not the sole implementation of a reported result. Clear outputs before commit unless outputs are intentionally reviewed evidence.
- Promoted analyses must have deterministic scripts or documented execution order, explicit inputs, and tests where practical.
- Experimental scripts live inside an identified experiment or under `scripts/` when genuinely reusable. They must not become undeclared production runtime paths.
- Seeds must be recorded when available; nondeterministic sources and provider limitations must be disclosed.

## Repository hygiene

Only project-wide entry points and conventional configuration belong at repository root. New prose belongs in the appropriate `docs/` area; code in `src/`; tests in `tests/`; configurations in `configs/`; examples in `examples/`; and artifacts in their governed directories. Random notes, downloads, logs, local outputs, and one-off scripts must not be placed at root.

Secrets are never committed. Dependencies must be minimal, justified, and provider-neutral in the core. Duplicate definitions are avoided by designating a canonical document and linking to it.
