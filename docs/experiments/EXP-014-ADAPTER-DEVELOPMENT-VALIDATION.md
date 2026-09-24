# EXP-014 Adapter Development Validation

> **DEVELOPMENT / CONTAMINATED / NOT HELD-OUT EVIDENCE**
>
> This is not an EXP-014 run or result. It cannot establish RTM-1, experimental success,
> production readiness, complete mediation, or an FMED-L2/3/4 claim.

## Baseline and environment

- Protocol/design freeze: `7baf20293caa83d3fff6a200174c4f8840918607`
- M1: `9f77dc906355d1191af1f4908460af8e4cc36293`
- M2: `5c55917bb9adb5728f12d26faf6da9e29d2402b2`
- M3: `2d9f8b09825702d12304f379130001f60e3d867c`
- EXP-013 analysis/synthesis: `f4713f2f7012ba933ad9059fe8778004e331ae11`
- Implementation starting HEAD: `7baf20293caa83d3fff6a200174c4f8840918607`
- Development interpreter: CPython 3.11.16 from the repository virtual environment
- Host observed at the pre-implementation gate: Linux 6.8.0-138-generic, x86_64
- Assumptions: local case-sensitive filesystem, process-owned temporary roots,
  same-filesystem rename, sequential deterministic mediation

## Development checks

Real temporary-filesystem success paths exercised read, write, append, create, file
delete, empty-directory delete, file and empty-directory rename, mkdir, non-recursive
list, and minimized stat. Each used a real standard-library filesystem primitive below a
fresh `TemporaryDirectory` root.

The contaminated suite also checks:

- relative/absolute logical paths, dot and dot-dot processing, repeated/trailing
  separators, NFC normalization, empty/NUL/bytes inputs, root escape, host/other absolute
  paths, and workspace-prefix collisions;
- terminal, parent, relative, absolute, chained, and dangling symlinks, plus symlinked
  create/mkdir/rename parents;
- multi-link regular-file rejection for read/write/append/delete/stat, rename source, and
  existing rename destination when hard links are supported;
- all per-operation policy denials with zero requested primitive calls, independent
  before/after digests for mutations, and no protected return for read/list/stat;
- source/destination/both rename denial, compound authorization exception, cross-scope
  destination, destination prefix collision, and both-decision evidence;
- authorization, canonicalization, physical validation, state observation, required
  pre-execution audit, permission-like primitive, definitely unchanged write, simulated
  partial write, unexpected post-start, and terminal audit failures;
- session/task attribution, normalized semantic determinism, event ordering, and
  machine-checkable envelope completeness; and
- direct `os.open` mutation below the temporary root as
  `EXPECTED_FMED_L1_BYPASS`.

The required ordering was observed as adapter ingress, canonicalization, M3 action and
authorization, post-allow target validation, committed `EXECUTION_STARTED`, requested
primitive call, and terminal M3 event. Denials had no validation or execution event.
Both rename subdecisions preceded validation and execution.

## Development fixture contamination record

The following fixture families and semantic combinations are contaminated and must not be
reused verbatim by the future held-out corpus:

- `DEV-FS-LEXICAL-001` through `DEV-FS-LEXICAL-009`: the documented relative,
  absolute, dot, dot-dot, separator, trailing separator, NFC, root, and in-root collapse
  spellings used in the unit table;
- `DEV-FS-SYMLINK-TERMINAL`, `DEV-FS-SYMLINK-PARENT`,
  `DEV-FS-SYMLINK-ABSOLUTE`, `DEV-FS-SYMLINK-CHAIN`, and
  `DEV-FS-SYMLINK-DANGLING`, including their `link.bin`, `chain-a`, `chain-b`,
  `linked-parent`, and `secret.bin` topology;
- `DEV-FS-OP-*`, `DEV-FS-RENAME-*`, `DEV-FS-CREATE-SYMLINKED-PARENT`,
  `DEV-FS-MKDIR-SYMLINKED-PARENT`, `DEV-FS-ROOT-CREATE-REJECT`, and
  `DEV-FS-SESSION-*` operation/path/authority arrangements;
- `DEV-FS-PRIMITIVE-FAILURE-WRITE` and
  `DEV-FS-PRIMITIVE-FAILURE-PERMISSION` failure combinations; and
- audit failures injected at adapter ingress, canonicalization failure/success,
  `EXECUTION_STARTED`, post-effect state observation, and terminal success, including the
  development payloads and paths in `tests/dev/test_exp014_filesystem_adapter.py`;
- hostile direct mapper inputs using dotted, repeated-separator, escaping, and NFD forms;
  governed hashing of an invalid absolute host-path sentinel;
  semantic state-digest content/child-create/rename/delete mutations and equivalent
  fixtures under two host roots; and
- the normalized legacy-M3 allow flow in `tests/test_audit_events.py`.

Generic requests using the default `DEV-FS-REQUEST-001` identifier are also contaminated.
The future corpus must use different path/name tuples, bytes, authority arrangements, and
failure combinations, not merely different IDs.

## Known limitations

The adapter uses post-allow `lstat` validation followed by pathname-based primitives.
Name-to-object TOCTOU and symlink swap remain **NOT_SOLVED**. Link-count observation is
race-sensitive and is not inode confinement. The in-memory recorder is not durable,
tamper-evident, cross-process, distributed, or concurrency-safe. Direct `os.*`, pathlib,
native, shell, or inherited-descriptor routes bypass FMED-L1. The suite is Linux-only,
sequential, development-authored, and contaminated. No shell interception, real agent,
corpus, held-out run, performance acceptance claim, or production deployment exists.

## Reproduction snapshot

The initial candidate reported 87 targeted and 271 full-repository passed tests. The
pre-corpus freeze audit added mapper, state-digest, post-effect truthfulness, sensitive
logging, and normalized legacy-M3 regressions. The final audit snapshot reports 91
targeted tests, 276 full-repository tests, 96% aggregate `safetybox` statement coverage,
and 98% aggregate filesystem/compound/monitor coverage. Ruff, strict mypy, and
`git diff --check` passed. These are development engineering checks, not EXP-014 metrics
or results.

```text
.venv/bin/pytest -q tests/dev/test_exp014_filesystem_adapter.py
.venv/bin/pytest --cov=safetybox --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/mypy src
git diff --check
```
