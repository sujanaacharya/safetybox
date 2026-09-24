# EXP-015 PMED-L1 Requirement Traceability

> **DEVELOPMENT / CONTAMINATED / NOT HELD-OUT EVIDENCE**
>
> This matrix records implementation and development tests only. It does not report an
> EXP-015 result, change frozen success criteria, or support a maturity/claim promotion.

Frozen protocol/design SHA: `1b1d22eaded580e9b6f6311bf0e3a8145002e98d`.

| Requirement | Implementation | Development test/evidence | Status | Notes |
|---|---|---|---|---|
| REQ-033 | `safetybox.process` PMED-L1 package | package boundary and bypass tests | DEVELOPMENT_VALIDATED | Direct-child adapter route only. |
| REQ-034 | `ProcessRequest`, `ProcessResult`, `ProcessAdapter.execute` | immutable request, real execution, result taxonomy | UNIT_TESTED | No caller environment or expected-label fields. |
| REQ-035 | injected mapper/authorizer/audit/primitive | denial, malformed input, output minimization | DEVELOPMENT_VALIDATED | Child and request data remain untrusted. |
| REQ-036 | `canonicalize_executable`, `ProcessTargetValidator` | lexical, missing/type/mode/script/symlink cases | DEVELOPMENT_VALIDATED | Native ELF on Linux; TOCTOU not solved. |
| REQ-037 | absolute executable binding and fixed environment | bare/relative rejection, absent child `PATH` | DEVELOPMENT_VALIDATED | No production lookup or `which`. |
| REQ-038 | immutable argv plus ordered commitments | literal metacharacters, empty, spaces, quotes, Unicode | DEVELOPMENT_VALIDATED | Primitive receives the original tuple. |
| REQ-039 | `canonicalize_process_cwd`, `LogicalHostMapper` reuse | boundary, missing, file, and symlink cwd cases | DEVELOPMENT_VALIDATED | Host mapping starts only after both allows. |
| REQ-040 | generic `CompoundActionAuthorizer` | four combinations, task mismatch, explanation | DEVELOPMENT_VALIDATED | Same `TaskContractPolicy` evaluates both actions. |
| REQ-041 | `FIXED_CHILD_ENVIRONMENT` | selected-variable helper plus full `env -0` audit | DEVELOPMENT_VALIDATED | Exact `LANG`/`LC_ALL` only; `PATH`, `HOME`, and parent sentinel absent. |
| REQ-042 | `ReferenceMonitor` plus `ProcessExecutionBoundary` | primitive-boundary event-order assertion | DEVELOPMENT_VALIDATED | Sequence numbers, not timestamps, carry order. |
| REQ-043 | denial branch before lifecycle hook | compound matrix plus denied target-probe/marker spy | DEVELOPMENT_VALIDATED | No probe, child fields, output, or marker on denial. |
| REQ-044 | `RealProcessPrimitive.spawn_and_wait` | spy, real child, and injected failures | UNIT_TESTED | Sole production `Popen` call for this package. |
| REQ-045 | M3 `EXECUTION_STARTED` before protected tool | audit-failure injection at multiple pre-spawn events | DEVELOPMENT_VALIDATED | Every injected pre-spawn failure had zero calls. |
| REQ-046 | `shell=False`, tuple argv | shell-looking literal round trip | DEVELOPMENT_VALIDATED | Shell grammar remains excluded. |
| REQ-047 | primitive waits/signals direct `Popen` child | timeout and signal fixtures | DEVELOPMENT_VALIDATED | Descendants are not controlled. |
| REQ-048 | terminal/effect fields and marker fixture | marker, marker-then-fail, denied no-spawn | DEVELOPMENT_VALIDATED | Filesystem effects bypass `FS-ADAPTER@1`. |
| REQ-049 | `ProcessTerminalClass`, `ProcessResultCategory` | deny, validation, spawn, exit, timeout, signal, indeterminate | DEVELOPMENT_VALIDATED | Exact frozen taxonomy represented. |
| REQ-050 | typed canonicalization/validation/spawn errors | invalid, audit, injected no-child, and real `Popen` failure cases | DEVELOPMENT_VALIDATED | Real `Popen` `OSError` is indeterminate, not false no-child evidence. |
| REQ-051 | effect-aware errors and audit handling | partial marker and terminal-audit failure | DEVELOPMENT_VALIDATED | Post-spawn uncertainty is never `NOT_EXECUTED`. |
| REQ-052 | timeout range and TERM/250ms/KILL flow | TERM success and TERM-ignoring helper | DEVELOPMENT_VALIDATED | Direct child is reaped; no descendant claim. |
| REQ-053 | return-code/signal interpretation | exit 0, exit 7, `SIGUSR1`, timeout signals | DEVELOPMENT_VALIDATED | Linux/POSIX only. |
| REQ-054 | incremental `_StreamCollector` | non-UTF-8 plus over-limit stdout/stderr count/hash/truncation | DEVELOPMENT_VALIDATED | Retains at most 65,536 bytes per stream. |
| REQ-055 | `stdin=DEVNULL`, no stdin API, `close_fds=True` | public-model and real-child tests | UNIT_TESTED | No TTY/interactive route. |
| REQ-056 | `ProcessAuditEnvelope` and M3 metadata | envelope-only reconstruction test | DEVELOPMENT_VALIDATED | In-memory audit is not durable. |
| REQ-057 | argument/output hashes and child token | sensitive argv/output absence from M3 events | DEVELOPMENT_VALIDATED | PID is diagnostic only. |
| REQ-058 | explicit adapter boundary | safe direct-`Popen` marker control | DEVELOPMENT_VALIDATED | Network and filesystem syscalls remain unmediated. |
| REQ-059 | native C helper under `tests/fixtures` | argv/env/cwd/output/effect/terminal modes and marker-path rejection | DEVELOPMENT_VALIDATED | All real children use temporary cwd roots; `DEV-PROC-*` cases are contaminated. |
| REQ-060 | no corpus/results implementation workflow | absence checks plus development table/report | NOT_YET_HELD_OUT_VALIDATED | Corpus authorship and one-shot evaluation remain future work. |
| REQ-061 | no performance gate in runtime | no benchmark or threshold implementation | ARCHITECTURAL_ONLY | Correctness was not traded for latency. |
| REQ-062 | explicit platform/maturity limits | diligence and validation limitation sections | ARCHITECTURAL_ONLY | Sequential Linux development only; authenticated session binding absent. |

## Invariant traceability

Repository status remains `DESIRED`; the following is contaminated development evidence,
not held-out support.

| Invariant | Development tests | Development disposition |
|---|---|---|
| INV-020 | compound/task/resource denials plus target-probe and marker spy | Denied adapter routes had zero probes, primitive invocations, children, output, or markers. |
| INV-021 | ordering spy and pre-spawn audit fault injection | Both decisions and both validations preceded committed execution-start audit and spawn. |
| INV-022 | native helper NUL-framed argv round trip | Registered literals arrived as distinct exact argv elements. |
| INV-023 | pre-spawn and terminal audit failure injection | Pre-spawn failures prevented spawn; post-spawn audit loss was indeterminate. |
