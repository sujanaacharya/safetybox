# EXP-016 pre-corpus freeze audit

**Audit ID:** `EXP-016-PRE-CORPUS-FREEZE-AUDIT@1`

**Protocol:** `EXP-016-PROTOCOL@1`

**Decision:** `FREEZE_READY`

**Scope:** protocol, native fixture, independent reachability, development proofs, and
scoring infrastructure only

## Starting state and predecessor integrity

Work began at clean `main`/`origin/main` commit
`71cb87b771978f3fc55edac7bf2a0f45809c9d55`. This is the frozen EXP-015 adversarial
analysis commit. The EXP-015 raw-result tree remains identical to
`65d047de0fe3b484eaed64bd2adc8562a5835eea`; its `SHA256SUMS` manifest passes. No
working-tree path beneath `experiments/EXP-015/` or `results/EXP-015/`, and no EXP-015
analysis or claims-ledger path, was changed.

EXP-015 was not rerun, repaired, or reinterpreted. Its 0-child result and
`CORPUS_FIXTURE_DESIGN_FAILURE` conclusion remain frozen.

## Native helper provenance and reachability

| Check | Frozen observation | Result |
|---|---|---|
| Source language | C11 | PASS |
| Source SHA-256 | `363992ed2834bd1aee2449cb49317730d80f5de50cd4e165e28f4742e3d4d41e` | PASS |
| Compiler | `cc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0` | PASS |
| Flags | `-std=c11 -O2 -Wall -Wextra -Werror -fno-ident -Wl,--build-id=none` | PASS |
| Binary SHA-256 | `f9e3c8908cb7bd99e5e23f5844bdaddfc41efd5409d3c94d8807b7c8ab0f5503` | PASS |
| ELF magic | `7f454c46` | PASS |
| ELF | 64-bit little-endian PIE `ET_DYN` | PASS |
| Architecture | host x86_64 / `EM_X86_64` 62 | PASS |
| Linkage | dynamic | PASS |
| Loader | `/lib64/ld-linux-x86-64.so.2` | PASS |
| Link policy | one link | PASS |
| Rebuild | identical binary and provenance hashes | PASS |
| Direct loadability | native child exits with declared status | PASS |

The independent oracle contains no import from `safetybox.process`, the production
validator, or `ProcessAdapter`. It distinguishes every frozen executable and cwd state.
The direct smoke proof passed argv, environment, cwd, stdout, stderr, both streams, exit,
sleep, self-signal, marker, marker-then-sleep, and marker-then-exit modes.

## Development-only adapter proofs

All concrete proof operands are registered as contaminated and prohibited from exact
held-out reuse. The proofs created real native children for:

- byte-exact length-framed argv including empty, Unicode, and shell-looking literals;
- exact child environment with absent parent sentinels;
- physical cwd observation and selected marker effect;
- empty, below-limit, exact-limit, above-limit, and comfortably-above-limit output;
- normal exits 1, 7, and 23;
- self-`SIGUSR1`;
- timeout completed by TERM and timeout escalated to KILL; and
- independent ordering and audit-truth comparisons around the actual spawn primitive.

The known-ALLOW plus valid-ELF proof reached cwd rejection. A bounded DENY proof reached
neither validation nor spawn. `DIRECT_CONTROL` used the independent runner while an
accidental `ProcessAdapter.execute` route was made fatal.

Supported injections reached all registered prerequisites:

- preexecution audit rejection occurred after both validations and before primitive
  invocation;
- confirmed-no-child spawn failure occurred after committed `EXECUTION_STARTED`;
- injected capture failure carried an observation from a real created and reaped child;
- successful-terminal audit failure occurred after a real exit-zero child; and
- failure-terminal audit failure occurred after a real exit-7 child.

A distinct post-spawn/pre-completion audit seam does not exist in the synchronous frozen
adapter and is prohibited rather than simulated.

## Scoring and governance audit

| Gate | Result |
|---|---|
| One canonical family registry | PASS |
| Registry and reachability matrix family equality | PASS |
| Held-out instance count | 0 |
| Runtime held-out scenario files | ABSENT |
| Held-out label/prediction files | ABSENT |
| Raw-first label isolation contract | PASS |
| Machine-readable edge/hard/control/family fields | PASS |
| Machine-readable REQ-033–062 subset mapping | PASS |
| Machine-readable tested-threat/boundary mapping | PASS |
| Executable stage-funnel counter | PASS |
| Machine-checked route agreement | PASS |
| Zero-denominator result | `NOT_EXERCISED` — PASS |
| Repeat normalization | named ephemeral top-level fields only — PASS |
| Semantic-output normalization | PROHIBITED |
| Candidate claim status | all `PROPOSED` |
| Automatic RTM-2 promotion | not preregistered |

## Validation record

| Check | Result |
|---|---|
| EXP-016 focused pytest | 30 passed |
| Post-run-applicable repository pytest | 647 passed, 2 exact frozen EXP-015 pre-run lifecycle nodes deselected |
| Unqualified repository pytest diagnostic | 647 passed; 2 established EXP-015 post-run lifecycle-only failures retained |
| Coverage | 95% total; EXP-016 reachability module 87% |
| Ruff | PASS |
| mypy strict `src` | PASS |
| `git diff --check` | PASS |
| EXP-015 raw `SHA256SUMS` | PASS |
| EXP-016 helper `CHECKSUMS.sha256` | PASS |

The two deselected nodes are the frozen EXP-015 pre-run assertions that
`results/EXP-015/` is absent and that no earlier shared-interpreter test imported process
code. The frozen analysis already records them as expected after the raw result exists.
They are not modified or represented as passing. All tests applicable to the current
post-run repository state pass.

## Freeze decision

Every EXP-016 infrastructure freeze condition is satisfied. The helper is a genuine
compatible ELF with recorded provenance; smoke, executable/cwd oracle, seam, route,
repeat, family, mapping, no-vacuity, and scorer gates pass; and no held-out case or future
prediction exists. EXP-016 pre-corpus infrastructure is therefore freeze-ready.

This decision provides no held-out execution result and promotes no claim.

## Exactly one next task

Author the EXP-016 held-out native-process corpus using only the frozen
reachability/scoring contracts, independently verify every intended-valid fixture reaches
the required stage without using ProcessAdapter predictions, then perform contamination,
determinism, family-count, requirement, threat, and reachability audits before corpus
freeze.
