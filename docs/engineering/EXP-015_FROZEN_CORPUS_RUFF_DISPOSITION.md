# EXP-015 Frozen Corpus Ruff Disposition

**Disposition ID:** `EXP-015-FROZEN-CORPUS-RUFF-DISPOSITION@1`
**Additive gate disposition:** `EXP-015-PRE-RUN-ENVIRONMENT-GATE-DISPOSITION@1`
**Decision:** `READY_FOR_EXP_015_RUN_001`

## Issue and starting evidence

The historical `EXP-015-PRE-RUN-ENVIRONMENT-GATE@1` was `BLOCKED` solely because
repository-wide Ruff reported 36 findings in two checksum-covered frozen artifacts:
`experiments/EXP-015/corpus/build_corpus.py` and
`experiments/EXP-015/corpus/integrity_check.py`. Starting HEAD was
`ba150216cd71da6fbd7eb353de5edb24b1a716fb`; protocol, implementation, and corpus freezes
are `1b1d22eaded580e9b6f6311bf0e3a8145002e98d`,
`12c585a9830436d8a88d356cfecbdff132b55487`, and
`ba433ee21e66813ac30d966bf2f4880bb3897f53`. Both files are named in
`CHECKSUMS.sha256`, which passed before work. `results/EXP-015/` was absent.

## Exact Ruff debt

Ruff 0.16.8 ran with repository configuration and JSON output. Every item below records
`file:line:column | rule | message | autofix`; `yes` means applying the fix alters frozen
bytes, and every `no` also needs a byte-changing source edit to resolve.

```text
build_corpus.py:6:1 | I001 | Import block is un-sorted or un-formatted | yes
build_corpus.py:8:1 | E401 | Multiple imports on one line | yes
build_corpus.py:15:101 | E501 | Line too long (142 > 100) | no
build_corpus.py:17:101 | E501 | Line too long (103 > 100) | no
build_corpus.py:19:101 | E501 | Line too long (577 > 100) | no
build_corpus.py:20:101 | E501 | Line too long (378 > 100) | no
build_corpus.py:24:101 | E501 | Line too long (244 > 100) | no
build_corpus.py:26:101 | E501 | Line too long (224 > 100) | no
build_corpus.py:26:217 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:29:20 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:30:88 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:32:5 | B007 | Loop control variable `n` not used within loop body | no
build_corpus.py:33:101 | E501 | Line too long (128 > 100) | no
build_corpus.py:33:121 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:35:101 | E501 | Line too long (160 > 100) | no
build_corpus.py:37:95 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:37:101 | E501 | Line too long (102 > 100) | no
build_corpus.py:40:101 | E501 | Line too long (130 > 100) | no
build_corpus.py:40:123 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:42:83 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:43:5 | B007 | Loop control variable `n` not used within loop body | no
build_corpus.py:44:86 | E702 | Multiple statements on one line (semicolon) | no
build_corpus.py:46:101 | E501 | Line too long (828 > 100) | no
build_corpus.py:47:101 | E501 | Line too long (106 > 100) | no
build_corpus.py:49:101 | E501 | Line too long (122 > 100) | no
build_corpus.py:51:101 | E501 | Line too long (368 > 100) | no
build_corpus.py:52:101 | E501 | Line too long (288 > 100) | no
build_corpus.py:53:101 | E501 | Line too long (335 > 100) | no
build_corpus.py:54:101 | E501 | Line too long (396 > 100) | no
build_corpus.py:55:101 | E501 | Line too long (371 > 100) | no
build_corpus.py:56:101 | E501 | Line too long (217 > 100) | no
build_corpus.py:57:101 | E501 | Line too long (358 > 100) | no
build_corpus.py:58:10 | E701 | Multiple statements on one line (colon) | no
build_corpus.py:61:52 | E701 | Multiple statements on one line (colon) | no
build_corpus.py:61:101 | E501 | Line too long (112 > 100) | no
integrity_check.py:2:1 | I001 | Import block is un-sorted or un-formatted | yes
```

| Rule | Count | Classification | Why ignore is acceptable |
|---|---:|---|---|
| I001 | 2 | STYLE_ONLY | Import ordering cannot alter corpus semantics. |
| E401 | 1 | STYLE_ONLY | Import layout cannot alter corpus semantics. |
| E501 | 21 | STYLE_ONLY | Line wrapping cannot alter corpus semantics. |
| E701 | 2 | STYLE_ONLY | Single-line suite layout cannot alter corpus semantics. |
| E702 | 8 | STYLE_ONLY | Statement layout only; no control-flow defect is reported. |
| B007 | 2 | MAINTAINABILITY | Intentional repeated loops use their range count while not using `n`; no correctness or security defect is reported. |

There are no `POTENTIAL_CORRECTNESS` or `POTENTIAL_SECURITY` findings. Non-held-out corpus
integrity execution passed (120 scenarios and labels, labels isolated, adapter not imported),
so no listed finding plausibly invalidates construction or integrity.

## Provenance and runtime-role audit

`git archive ba433ee21e66813ac30d966bf2f4880bb3897f53 experiments/EXP-015/corpus` was extracted
to a temporary directory. Ruff on the extracted Python files produced the same 36 findings
at the same locations and distribution. No-output `git diff --no-index` comparisons of
each current file to its extracted object confirmed byte identity. This is
`PRE_EXISTING_FROZEN_DEBT`, not a post-freeze change.

| Question | `build_corpus.py` | `integrity_check.py` |
|---|---|---|
| Used to author frozen corpus? | Yes; historical materializer. | No; static verifier. |
| Required by canonical execution or evaluation runner? | No. | No; pre-run integrity only. |
| Imported by ProcessAdapter or production SafetyBox? | No. | No. |
| Used only for corpus generation/integrity? | Yes. | Yes. |
| Checksum-covered? | Yes. | Yes. |

They are research artifacts, not production enforcement or runtime authorization code.

## Governance and technical resolution

Frozen scientific artifacts are immutable after freeze. A post-freeze lint requirement must
not silently rewrite a checksum-covered artifact merely to make a quality gate green:
preserve bytes and checksums, document pre-existing debt, use the narrowest machine-enforced
baseline, and retain normal Ruff enforcement for mutable and new code.

The existing Ruff configuration supports exact per-file ignores, and its only exception is:

```toml
[tool.ruff.lint.per-file-ignores]
"experiments/EXP-015/corpus/build_corpus.py" = ["B007", "E401", "E501", "E701", "E702", "I001"]
"experiments/EXP-015/corpus/integrity_check.py" = ["I001"]
```

Every code is justified above: it existed before freeze, resolving it changes frozen bytes,
and its classification does not invalidate the corpus. There is no directory-wide or
`experiments/` exclusion, no global ignore or wildcard EXP ID, and no production,
authorization, or process-adapter source exclusion. Equivalent mutable code remains under
normal Ruff enforcement.

No Ruff autofix, manual formatting, `noqa`, regeneration, or new corpus freeze was used.
The corpus remains the held-out corpus frozen before adapter execution; preserving that
scientific chronology outranks cosmetic cleanup.

## Gate re-disposition, non-execution, and limitation

This document does not rewrite the historical blocked gate. It additively supersedes its
decision as `EXP-015-PRE-RUN-ENVIRONMENT-GATE-DISPOSITION@1` after final validation passes.
No frozen bytes changed; checksums are reverified. Held-out `ProcessAdapter.execute`
invocations remain **0**; `results/EXP-015/` remains absent; no prediction logs, caches, or
adapter-mediated helper execution were created.

`ENVIRONMENT_REPRODUCIBILITY_LIMITATION` remains: the intact validated `.venv` used
CPython 3.11.16 with uv provenance 0.12.9, while dev dependencies have lower bounds and
no lockfile. No dependency or lockfile change is made here. The recorded environment is
usable for the one scientific run, but exact recreation should be improved afterward.

Before future protocol, implementation, corpus, or result freezes, mutable artifacts that
will participate in static-analysis gates should pass them before freeze. This exceptional
baseline is not a recommended workflow. The residual limitation is unchanged historical
generator readability/maintainability; it preserves provenance without masking lint debt
in other code.

## Final validation record

After this disposition, rerun DEV-PROC, legacy authorization, full pytest, coverage,
repository Ruff, `mypy src`, `git diff --check`, corpus checksums, EXP-014 manifests, and
EXP-015 protocol, implementation, and corpus integrity without executing a held-out
scenario. Results are appended only after all checks pass.

| Check | Observed result |
|---|---|
| EXP-015 DEV-PROC | 82 passed |
| Legacy authorization regression | 26 passed |
| Full pytest | 375 passed |
| Coverage | 95% (4,833 statements; 221 missed) |
| Repository Ruff | pass |
| Strict mypy | pass; 64 source files |
| `git diff --check` | pass |
| EXP-014 corpus, raw-result, and analysis manifests | pass |
| EXP-015 corpus checksums and integrity checker | pass |
| EXP-015 protocol integrity | byte-identical to protocol freeze |
| EXP-015 implementation integrity | `src/` byte-identical to implementation freeze |
| EXP-015 corpus integrity | every corpus file Git object hash equals its corpus-freeze object |

The configuration was mechanically inspected: it has exactly two literal paths, seven
rule-specific ignores, no global `ignore`, and no directory, wildcard, production,
authorization, or process-adapter exclusion. A temporary mutable file containing
`import os, sys` still failed Ruff with E401, I001, and F401, demonstrating that the
exception does not weaken normal enforcement outside these frozen paths.
