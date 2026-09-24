# EXP-015 Pre-Run Environment / Integrity Gate

**Gate ID:** `EXP-015-PRE-RUN-ENVIRONMENT-GATE@1`

**Decision:** `BLOCKED`

**Scope:** validation-environment and frozen-artifact integrity only. This gate did not
execute `ProcessAdapter` against an EXP-015 held-out scenario, create
`results/EXP-015`, inspect predictions, or modify the protocol, adapter, or corpus.

## Starting references and environment

| Item | Value |
|---|---|
| HEAD at gate start | `ba433ee21e66813ac30d966bf2f4880bb3897f53` |
| Protocol/design freeze | `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` |
| Implementation freeze | `12c585a9830436d8a88d356cfecbdff132b55487` |
| Corpus freeze | `ba433ee21e66813ac30d966bf2f4880bb3897f53` |
| SafetyBox | `0.0.0` |
| Platform | Linux x86_64; kernel `6.8.0-138-generic` |

The active shell had no `python` on `PATH`, which explains the missing-tool report at
corpus freeze. The repository project environment already existed at `.venv`, with
prompt `safetybox`, CPython `3.11.16`, and `uv 0.12.9` provenance. This is the canonical
environment supported by the prior EXP-014 development record, which invokes
`.venv/bin/pytest`, `.venv/bin/ruff`, and `.venv/bin/mypy`. The system `python3` is
3.10.12 and was not used.

`pyproject.toml` declares Python `>=3.11` and the `dev` extra (`pytest`, `pytest-cov`,
`ruff`, and `mypy`). There are no requirements or dependency lock files. No environment
mutation or installation was performed.

| Tool | Gate environment version | Availability classification |
|---|---|---|
| pytest | `9.1.1` | `AVAILABLE_IN_EXISTING_PROJECT_VENV` |
| pytest-cov | `7.1.0` | `AVAILABLE_IN_EXISTING_PROJECT_VENV` |
| coverage | `7.16.1` | `AVAILABLE_IN_EXISTING_PROJECT_VENV` |
| Ruff | `0.16.8` | `AVAILABLE_IN_EXISTING_PROJECT_VENV` |
| mypy | `2.3.1` | `AVAILABLE_IN_EXISTING_PROJECT_VENV` |

The prior EXP-015 development audit records CPython 3.11.16, 375 passing tests, 95%
coverage, and 64 source files, but not exact tool versions. The tool versions above are
therefore version drift within the declared lower-bound dependencies, not a comparison
against an established exact prior version.

## Integrity and non-execution checks

- `experiments/EXP-015/corpus/CHECKSUMS.sha256`: pass before and after validation.
- Frozen EXP-015 protocol/design files: no diff from the protocol freeze.
- Frozen process implementation and its frozen authorization/capability dependencies:
  no diff from the implementation freeze.
- EXP-014 corpus, raw-result, and analysis checksum manifests: pass.
- The static corpus integrity script passed: 120 scenarios and labels, labels isolated,
  and adapter deliberately not imported.
- `results/EXP-015/` remains absent. No prediction cache or EXP-015 result/log artifact
  exists. Held-out `ProcessAdapter.execute` invocations: **0**.

## Validation results

| Check | Result |
|---|---|
| EXP-015 DEV-PROC suite | 82 passed |
| Legacy `Capability`, `TaskContractPolicy`, and `ReferenceMonitor` regression selection | 26 passed |
| Full pytest | 375 passed |
| Coverage | 95% (4,833 statements, 221 missed) |
| Strict mypy | pass; 64 source files |
| `git diff --check` | pass |

Ruff did not pass. `ruff check .` reports 36 violations, all in frozen corpus files
`experiments/EXP-015/corpus/build_corpus.py` and
`experiments/EXP-015/corpus/integrity_check.py`. The files are checksum-covered frozen
corpus artifacts. They were not changed, and this gate does not authorize changing them.
This is a lifecycle/governance blocker for the canonical one-shot run, not an adapter or
corpus-integrity failure.

## Reproducibility assessment

The existing project `.venv` is suitable to repeat the non-held-out validation commands
and matches the prior validated Python minor version. Recreating its exact package set is
not fully reproducible from the repository alone because the dev dependencies have lower
bounds but no lock file or documented installation command. No install was necessary for
this gate. Canonical `EXP-015-RUN-001` remains blocked until the frozen-corpus Ruff
disposition is governed and the environment reproducibility gap is explicitly accepted
or remedied without changing frozen EXP-015 semantic artifacts.
