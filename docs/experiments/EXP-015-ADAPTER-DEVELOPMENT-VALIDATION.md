# EXP-015 Adapter Development Validation

> **DEVELOPMENT / CONTAMINATED / NOT HELD-OUT EVIDENCE**
>
> This is not an EXP-015 run or result. It does not establish protocol success, RTM-2,
> production readiness, complete mediation, or support for `CL-011`.

## Identity and Phase 0 gate

- Protocol/design freeze: `1b1d22eaded580e9b6f6311bf0e3a8145002e98d`
- Immediate pre-design baseline: `d1053c2`
- Adapter: `PROC-ADAPTER@1`
- Canonicalization: `PROC-CANONICALIZATION@1`
- Audit envelope: `PROC-AUDIT-ENVELOPE@1`
- Environment profile: `PROC-ENV-MINIMAL@1`

The baseline-to-freeze diff contains no production source or test change. The reported
policy-engine modification is only an additive section in
`docs/architecture/POLICY_ENGINE.md`; it introduced no symbol, caller, runtime behavior,
authorization behavior, or subprocess implementation. Phase 0 therefore passed as
`DOCUMENTATION_ONLY`.

## Development results

The contaminated suite executes real repository-controlled native children from fresh
pytest temporary roots. It exercises exact executable and cwd capabilities, all four
compound combinations, task mismatch, exact-name neighbors, lexical rejection,
post-allow target rejection, output, environment, timeouts, signals, partial effects,
audit failures, and direct bypass.

| Authority fixture | Exec | Cwd | Compound | Validation | Spawn | Development label |
|---|---|---|---|---|---|---|
| DEV-PROC-AUTH-AA | ALLOW | ALLOW | ALLOW | succeeds | 1 | authority-positive |
| DEV-PROC-AUTH-AD | ALLOW | DENY | DENY | not attempted | 0 | authority-negative |
| DEV-PROC-AUTH-DA | DENY | ALLOW | DENY | not attempted | 0 | authority-negative |
| DEV-PROC-AUTH-DD | DENY | DENY | DENY | not attempted | 0 | authority-negative |

The four-row table is the explicit compound-combination subset. Independent source-
fixture enumeration over every adapter call that reached a compound decision found 31
authority-positive and 10 authority-negative cases. Development authorization false
allows were **0/10** and false denies were **0/31**. These are contaminated engineering
checks, not held-out rates. Pre-authorization aborts and an injected authorizer exception
have no compound decision and are excluded. A post-allow missing/symlink/type rejection
remains authorization-positive and is not counted as a false denial.

The native helper round-tripped literal `;`, `&&`, `|`, `>`, `$()`, backticks, wildcard,
quotes, spaces, an empty element, and Unicode without authorization overblocking or shell
interpretation. The child environment was exactly `LANG=C.UTF-8` and `LC_ALL=C.UTF-8`;
`PATH` and a parent secret sentinel were absent.

Denied requests invoked no primitive and exposed no PID, child token, stdout, stderr,
exit, signal, timeout, target probe, or marker side effect. Required audit failures
through `EXECUTION_STARTED` also had zero primitive calls and retained any already-
completed authorization decision. A terminal-audit failure after a real child was
reported `FAIL_INDETERMINATE_EXECUTION_POSSIBLE`. An injected primitive that explicitly
proved no child remained `SPAWN_ERROR_NOT_CREATED`; a real `Popen` `OSError`, which does
not prove whether a fork occurred, remained indeterminate with an attempt token.

Real outcomes covered exit zero, mapped-cwd observation, non-UTF-8 bytes, marker
creation, marker then exit 7, self-`SIGUSR1`, timeout with `SIGTERM`, and timeout
escalation to `SIGKILL` after 250 ms. These outcomes retain the frozen distinction
between authorization, validation, tool outcome, and effect uncertainty.

Output capture incrementally drains both streams, hashes and counts complete captured
streams, returns at most 65,536 bytes per stream, and emits no raw output to canonical
M3 events. A development sentinel verified that raw argv and child output did not appear
in audit metadata. The envelope-only reconstruction test used no harness-private data.

## Contamination inventory

All cases in `tests/dev/test_exp015_process_adapter.py`, its native helper operations, and
the following families are contaminated and must not be copied verbatim into a future
held-out corpus:

- `DEV-PROC-AUTH-AA`, `DEV-PROC-AUTH-AD`, `DEV-PROC-AUTH-DA`, and
  `DEV-PROC-AUTH-DD`;
- `DEV-PROC-REQUEST-*`, `DEV-PROC-IDENTITY-*`, exact helper paths and
  `/workspace/allowed`, `/workspace/other`, `/workspace/missing`,
  `/workspace/file`, and `/workspace/symlink` arrangements;
- native helper modes `argv`, `env`, `cwd`, `nonutf8`, `marker`, `marker-fail`, `exit`,
  `sleep`, `ignore-term-sleep`, `signal`, and `streams`, including their concrete
  payloads and the rejected path-bearing marker case;
- the literal argv tuple, parent-secret sentinel, output sizes, marker names, exit codes,
  signals, timeout durations, and audit-failure event placements; and
- the direct-`Popen` `outside-adapter.txt` boundary control.

Future corpus cases must differ semantically, not merely by identifier.

## Bypass and limitations

The direct `subprocess.Popen` control creates a safe marker beneath its temporary cwd and
is classified `EXPECTED_PMED_L1_BYPASS`, not adapter failure. A child marker write does
not pass through `FS-ADAPTER@1`. An authorized child can directly use filesystem,
network, native, shell, or descendant routes because PMED-L1 does not confine syscalls.
No network call was made in development.

Validation is pathname inspection followed by pathname spawn; replacement/rename TOCTOU
is **NOT_SOLVED**. Only the direct child is signaled, waited, and observed. Descendants
are not confined or claimed terminated. The implementation is Linux/ELF/POSIX oriented,
sequential, and not claimed concurrency-safe. M3 is in-memory and non-durable.
`TaskContract.task_id` binds task authority, and all audit records preserve session ID,
but the current contract schema does not authenticate contract-to-session binding. No
identity infrastructure was invented.

## Development validation summary

The targeted suite contains 82 tests. Process-package statement coverage is 99% in the
targeted run; canonicalization, validation, primitive, audit, models, and errors are at
100%, while adapter orchestration is at 97%. The full repository reports 375 passing
tests and 95% aggregate statement coverage; Ruff, strict mypy, and `git diff --check`
pass. These figures are development engineering checks, not experiment metrics.
