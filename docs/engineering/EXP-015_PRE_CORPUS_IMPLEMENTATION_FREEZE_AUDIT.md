# EXP-015 Pre-Corpus Implementation Freeze Audit

**Audit ID:** `EXP-015-PRE-CORPUS-FREEZE-AUDIT@1`

**Decision:** `PASS — APPROVED_FOR_PRE_CORPUS_IMPLEMENTATION_FREEZE`

**Evidence class:** contaminated development evidence; not held-out evidence or an
EXP-015 result

## Scientific boundary

This independent audit did not author or preview an EXP-015 corpus, create
`results/EXP-015`, tune an adapter against held-out cases, change a frozen success
criterion, add shell/network/AI mediation, or promote RTM or `CL-011`. It reviewed the
uncommitted PMED-L1 candidate and contaminated development fixtures only.

## Starting state

| Reference | Value |
|---|---|
| Audit-start `HEAD` and EXP-015 protocol freeze | `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` |
| EXP-014 protocol/design freeze | `7baf20293caa83d3fff6a200174c4f8840918607` |
| EXP-014 implementation freeze | `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c` |
| EXP-014 corpus freeze | `5ac7311bb8f086cca97f474069d068067ac73142` |
| EXP-014 raw-result freeze | `17a0f6b6409ac85a2ee1a2d49f36a5748e3ab310` |
| EXP-014 analysis freeze | `d1053c26cdfad781894f57ecedefb07a39d84ca7` |
| Python used for validation | CPython 3.11.16 |
| OS/kernel | Linux x86_64, Ubuntu kernel `6.8.0-138-generic` |
| SafetyBox | `0.0.0` |

Audit-start modified files were `CHANGELOG.md`, `docs/DOCUMENTATION_INDEX.md`,
`docs/architecture/POLICY_ENGINE.md`, `src/safetybox/authorization.py`, and
`src/safetybox/capabilities.py`. Untracked files were the EXP-015 development,
traceability, and diligence documents, all nine files then under
`src/safetybox/process/`, `tests/dev/test_exp015_process_adapter.py`, and
`tests/fixtures/process_helper.c`.

`experiments/EXP-015/corpus/` and `results/EXP-015/` were absent at audit start and remain
absent. The implementation-time edit to frozen `POLICY_ENGINE.md` was restored to the
protocol-freeze bytes; implementation facts remain in additive development/audit files.

## Protocol and predecessor integrity

`git diff` from the protocol freeze is empty for the frozen EXP-015 protocol, human
protocol, requirements, architecture, ADR, threat model, pre-freeze audit, and policy
architecture. Their SHA-256 values are:

| Frozen file | SHA-256 |
|---|---|
| `experiments/EXP-015/protocol.yaml` | `e4c4e97263b87fd8fc2612ca7678bbb609960353405e12a466827b0188cd87e7` |
| `docs/experiments/EXP-015-real-subprocess-mediation.md` | `942cb2d6e18c33e56478a1fa1c4281ceb1c64988681cd223fffd7f506fcca1e4` |
| `docs/research/REAL_SUBPROCESS_MEDIATION_REQUIREMENTS.md` | `21357b079bdc2076d30bddc204069c564626a8c7d4f538af01640707c2be8b85` |
| `docs/architecture/REAL_SUBPROCESS_MEDIATION.md` | `b955ff333089814027be9d25bc3a8a2e1f5d059b10a01a0357681f9d8aaf984c` |
| `docs/decisions/ADR-007-argv-native-subprocess-before-shell.md` | `d249727aa5015a74259415ae682e70bc013b44c03724e72210a862b22e5718c5` |
| `docs/threat-model/REAL_SUBPROCESS_THREATS.md` | `82e3f2fc9634b2fd817afddf67fa9739c4c28db87519bce6a7068f79b4dbc256` |
| `docs/engineering/EXP-015_PRE_FREEZE_PROTOCOL_AUTHORIZATION_AUDIT.md` | `20ab79694e7c9532a023773dd80813a9b6102ad4b60c8cfd229ce2b1285510a0` |
| `docs/architecture/POLICY_ENGINE.md` | `1e13bbfc7d3b7479d619ee3dcfed26f344d577d15a25b8c6a46e20a198d65b84` |

EXP-014 protocol/design and implementation-specific paths have no diff from their
freezes. Corpus and raw-result checksum manifests pass, as does the analysis checksum
manifest. Later append-only EXP-015 registry entries do not alter EXP-014 dispositions.

## Freeze-blocking findings corrected

| Finding | Why it blocked freeze | Narrow correction | Regression evidence |
|---|---|---|---|
| Every real `Popen` `OSError` was classified `SPAWN_ERROR_NOT_CREATED`. | POSIX `Popen` may raise after fork/failed exec, so the primitive did not prove no child. | Real `Popen` `OSError` is `FAIL_INDETERMINATE_EXECUTION_POSSIBLE`, preserves `child_created=None`, and carries a per-attempt token. Injected proven-no-child failures retain `SPAWN_ERROR_NOT_CREATED`. | Direct real failure and injected primitive tests. |
| Required audit failure could erase an already completed compound decision from `ProcessResult`. | Authorization is a historical fact and cannot be rewritten by later audit outcome. | Audit and unexpected-failure branches now retain the captured `ALLOW` or `DENY`. | Allowed- and denied-audit-failure tests. |
| Overlapping matching capabilities selected provenance by `frozenset` iteration. | The decision stayed correct but its authority explanation could vary by hash order. | Matching provenance is selected by deterministic resource ordering and recursively immutable. | Generic M2 provenance test. |
| Compound subdecision dictionaries were mutable below a shallow mapping proxy. | Callers could mutate recorded component evidence after authorization. | Compound records and nested metadata are recursively frozen. | Direct compound-evidence mutation test. |
| The helper omitted frozen cwd/non-UTF-8 fixture capabilities and accepted path-bearing marker names. | REQ-059 traceability was overstated and the controlled helper could write outside its supplied cwd. | Added bounded cwd/non-UTF-8 modes and rejected marker names containing `/`, empty, `.` or `..`. | Real-child cwd/byte tests and traversal rejection. |

No success criterion, policy scope, or adapter permission was relaxed by these fixes.

## Production-source scope audit

| Production file | Classification | Reason |
|---|---|---|
| `src/safetybox/process/__init__.py` | `NEW_PROCESS_IMPLEMENTATION` | Public typed PMED-L1 API exports. |
| `process/adapter.py` | `NEW_PROCESS_IMPLEMENTATION` | Orchestrates canonicalization, compound authorization, reference monitor, validation, primitive, and result. |
| `process/audit.py` | `AUDIT_EXTENSION` | M3 bridge and post-allow/pre-spawn lifecycle boundary. |
| `process/canonicalization.py` | `NEW_PROCESS_IMPLEMENTATION` | Pure lexical executable/cwd handling and argv commitments. |
| `process/errors.py` | `NEW_PROCESS_IMPLEMENTATION` | Stable process error taxonomy. |
| `process/models.py` | `NEW_PROCESS_IMPLEMENTATION` | Immutable request/result/evidence models. |
| `process/primitive.py` | `NEW_PROCESS_IMPLEMENTATION` | Sole protected real subprocess creation and observation site. |
| `process/validation.py` | `NEW_PROCESS_IMPLEMENTATION` | Post-allow executable and cwd physical validation. |
| `process/versions.py` | `NEW_PROCESS_IMPLEMENTATION` | Frozen candidate identifiers. |
| `src/safetybox/authorization.py` | `GENERIC_AUTHORIZATION_EXTENSION` | Distinct-action ordered composition required by REQ-040; delegates all authority and owns no process rule. |
| `src/safetybox/capabilities.py` | `GENERIC_CAPABILITY_EXTENSION` | Adds matched/absent TaskContract provenance needed by REQ-056; decision rules and resource matching are unchanged. |

There is no `UNRELATED_CHANGE`. The capability change adds metadata to returned policy
decisions, so full dataclass equality observes the additive metadata; authorization
decision, rule, reason, matching, defaults, and hash/equality behavior of `Capability`
itself are unchanged. Legacy tests pass.

## Authorization-core uniqueness and compound quality

The complete authoritative route is:

```text
ProcessRequest
-> pure canonical executable/cwd and argv commitments
-> ActionRequest(process.exec, canonical executable)
-> CompoundActionAuthorizer
   -> TaskContractPolicy(process.exec)
   -> TaskContractPolicy(process.cwd, canonical logical cwd)
-> one aggregate decision with both ordered component records
-> ReferenceMonitor explicit-ALLOW branch
-> post-allow validation and committed EXECUTION_STARTED
-> ProcessExecutionBoundary
-> RealProcessPrimitive
```

There is one authority mechanism. The process package has no manual executable or cwd
allowlist, path-permission special case, `DEV-PROC` check, argv rule, risk score, AI
decision, hard-coded task, or direct `TaskContract` inspection. `ProcessAdapter` requires
the existing `TaskContractPolicy`; `ReferenceMonitor` remains the only forwarding gate.

All four component combinations retain two records in executable-then-cwd order. Only
allow/allow reaches validation. There is no probe or spawn between decisions and no
denial short-circuit. A component cannot overwrite another because aggregate allow is
the conjunction of all component decisions. Exceptions retain attempted component
provenance and fail closed. Records are immutable and preserve session, task, action,
resource, capability, rule, reason, decision, authority source, and component identity.

Generic compound-authorizer quality: **PASS**. It is reusable for distinct actions
beyond subprocess and intentionally does not implement policy priorities, delegation,
or attenuation itself.

## Development authorization audit

Ground truth was derived from each source fixture's `TaskContract`, capabilities,
request action/resource, and task ID. Adapter output was then compared to that derivation.
Only calls that completed a compound decision enter the authorization table;
canonicalization/pre-authorization audit aborts and the injected evaluator exception do
not.

| Ground truth | Count | Compound `ALLOW` | Compound `DENY` | Error |
|---|---:|---:|---:|---:|
| Authority-positive | 31 | 31 | 0 | 0 |
| Authority-negative | 10 | 0 | 10 | 0 |
| Total | 41 | 31 | 10 | 0 |

- False allows: **0/10 (0%)**.
- False denies: **0/31 (0%)**.
- True allows: **31**.
- True denies: **10**.

Five malformed/canonicalization adapter calls, two positive requests stopped by audit
before policy evaluation, and one injected evaluator exception have no compound decision
and are not relabeled as authorization errors.

The explicit allow/allow, allow/deny, deny/allow, and deny/deny fixtures share the
session-scoped executable, argv, logical cwd, request identity, and equivalent fresh
workspace shape; only exec/cwd capabilities change. The task-mismatch case shares the
same executable, argv, cwd, capabilities, and session with correct-task cases; only task
binding changes. Pytest supplies separate fresh host-root instances across parameter
members, so they are equivalent rather than literally the same inode fixture; host roots
are not visible to authorization and no pre-allow mapping/probe occurs. Near-name cases
change the requested resource and are resource-boundary tests, not authority-only pairs.
An audit-time same-inode-fixture rerun held executable, argv, cwd, session, request, and
marker state fixed: the three negative capability combinations each denied with zero
primitive calls/marker, allow/allow invoked once, and changing only task ID changed
`ALLOW` to `DENY`.

Benign shell-looking argv (`;`, `&&`, `|`, `>`, `$()`, backticks, `*`, quotes, spaces,
empty, and Unicode) receives `ALLOW` and arrives as exact elements. Of 31 positive
adapter cases, 5 are `TRIVIAL`, 25 are `EDGE_CASE`, and 1 combined literal-argv case is
`HARD_BENIGN`. This is modest contaminated coverage; held-out cases must be stronger.

## Authorization, validation, execution, and binding separation

- Missing, directory, non-executable, script, and symlink executable cases receive two
  allows and then executable validation rejection. Missing, file, and symlink cwd cases
  receive two allows and then cwd validation rejection. None is a false deny.
- Exit 7, signal, timeout, spawn/capture error, and terminal-audit loss preserve the
  historical `ALLOW`; none becomes `DENY` or an authorization failure.
- Task A capabilities do not authorize task B. Both exec and cwd independently return
  `POL-M2-TASK-MISMATCH`; same session, executable, cwd, or resource similarity provides
  no fallback.
- Session ID is preserved in requests, both component records, M3 events, and the result
  envelope. It is provenance only: `TaskContract` has no authenticated session/actor,
  issuer, deployment binding, replay prevention, or contract-reference verification.
  That unresolved identity gap is not solved or claimed by EXP-015.

## Canonicalization, information boundary, and exact binding

An independent stack-based table derived from the frozen protocol, without importing the
production algorithm, matched production for unchanged absolute paths, repeated
separators, dot removal, lexical `..`, above-root behavior, `/`, and repeated-root
spelling. Empty, relative, bare, and NUL-containing inputs rejected. The protocol does
not require NFC normalization for executable paths; cwd inherits EXP-014 NFC behavior.
There were zero mismatches.

Mechanical source tracing and a denial test that replaces `lstat`, `access`, `open`, and
the mapper with failing spies show no target-dependent probe before complete compound
allow. Pre-allow work is type/lexical processing, hashing, object creation, and audit.

The exact canonical executable is used as the policy resource, stored in validated
targets, and supplied unchanged as both the `Popen` first sequence element and explicit
`executable=` argument. `tool`, `tool2`, `tool-old`, and `tools/tool` do not prefix-match.
There is no alternate host substitution or PATH resolution.

Cwd authorization sees only canonical logical `/workspace/...`. Mapping to the injected
host root begins after both allows. Direct mapper probes accepted only exact canonical
`/workspace` resources and rejected repeated separators, dot traversal, root escape,
prefix collision, and relative input, independently preventing lexical host-root escape.

## Primitive, environment, argv, and shell

The sole new production process creation call is
`src/safetybox/process/primitive.py:subprocess.Popen`. No production `subprocess.run`,
`os.system`, `os.exec*`, `os.posix_spawn*`, explicit shell, `shlex`, or command-string
reconstruction exists. Test-only calls compile the helper and demonstrate the expected
direct-`Popen` PMED-L1 bypass.

`Popen` receives `(executable, *argv)`, the exact authorized executable, mapped cwd,
`shell=False`, `stdin=DEVNULL`, captured byte pipes, `close_fds=True`, and a newly
constructed environment. An independent real `/usr/bin/env -0` observation under a
parent with poisoned `PATH`, `HOME`, and a secret sentinel produced exactly:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
```

The sentinel, `PATH`, `HOME`, and all other parent variables were absent. Every
registered literal argv value round-tripped through the native helper with no joining,
splitting, escaping, reconstruction, interpolation, expansion, or normalization.

## Denial, ordering, failure, and cleanup

Every authority-negative adapter case had zero primitive calls. Denied evidence has
`child_created=false` and no token, PID, stdout, stderr, exit code, signal, or timeout.
The target-probe spy remained untouched and a requested marker was absent.

Ordering is:

```text
exec decision < cwd decision < executable validation < cwd validation
< committed EXECUTION_STARTED < primitive entry < Popen
```

The evidence classification is **MIXED**: component order comes from immutable indexed
compound records, while an independently wrapped primitive captured the committed audit
events present at its invocation boundary. Both validations and `EXECUTION_STARTED`
preceded the real primitive call. Failure of any required event through
`EXECUTION_STARTED` produced `FAIL_CLOSED_NOT_SPAWNED`, zero primitive calls, no marker,
and preserved any authorization already completed.

An injected `ProcessSpawnError` is `SPAWN_ERROR_NOT_CREATED` only because that test
primitive explicitly supplies `child_created=false`. Real `Popen` `OSError` is
indeterminate. Unknown post-invocation and capture failures are also indeterminate.
Nonzero exit retains `ALLOW`, child/token/PID, exit code, effect-possible state, and the
observed partial marker.

Timeout accepts only integer 50–2,000 ms. After child creation, expiration sends SIGTERM,
waits 250 ms, sends SIGKILL only if still live, and waits/reaps the direct child. Tests
cover TERM completion and TERM-ignoring/KILL escalation. Signal termination uses Linux
negative-return-code semantics and records the positive signal number. No cross-platform
equivalence is claimed. The primitive synchronously waits every real development child;
a direct known-PID `waitpid(..., WNOHANG)` audit returned `ChildProcessError`, confirming
that representative child was already reaped. No unrelated process was scanned or
killed.

## Output and sensitive data

Separate drain threads prevent stdout/stderr pipe deadlock. Each collector retains at
most 65,536 bytes while continuing to count and SHA-256 the complete stream. The
over-limit two-stream case produced exact complete counts/hashes and independent
truncation flags; non-UTF-8 bytes remain bytes.

A controlled sentinel was returned in `ProcessResult.stdout` as permitted. It was absent
from canonical events, authorization evidence, safe errors, and logs. Canonical audit
contains only byte count, hash, truncation, and capture status for output. Raw argv is
replaced by ordered index/UTF-8-length/hash commitments and one tuple digest.

## Boundaries and limitations

- **Process tree:** only the direct child is signaled, waited, and observed. Descendants
  may survive timeout or direct-child exit. There is no process-group, cgroup, namespace,
  seccomp, daemon, or process-tree security claim.
- **Filesystem:** a real allowed marker write occurs through the child OS syscall, not
  `FS-ADAPTER@1`. Launch authority does not constrain child syscalls.
- **Network:** no development test made an external network request and the adapter has
  no network interception. An authorized child may use the network directly.
- **TOCTOU:** component `lstat`/mode/header validation and later pathname `Popen` are not
  inode/fd bound. Executable or cwd replacement/rename races remain possible; static
  symlink rejection is not race safety.
- **Resources:** retained output and request timeout are bounded, but output rate, CPU,
  memory, process count, descendants, and privilege transitions are not OS-confined.
- **Concurrency:** development evidence is sequential/single-process. Audit sequencing,
  mutable primitive observations, simultaneous `Popen`, cleanup races, and cwd target
  replacement are not claimed concurrent-safe.

## Audit completeness, independence, and truthfulness

Allowed and denied component evidence contains session, task, normalized action/resource,
matched or absent capability, rule, contract reference, component, decision, and
deterministic reason. It uses no risk score. Envelope and M3 reconstruction cover all
frozen attempt fields and session-local sequence order.

Reconstruction independence is **SCHEMA_COUPLED**, not independent: reconstruction tests
consume producer event/envelope models and field names. Field completeness passes, but
that does not by itself prove semantic truth. Semantic checks are mixed: primitive-entry
instrumentation, helper-observed argv/environment/output, OS marker files, known exit and
signal fixtures, complete hashes/counts, and audit-failure injection provide partial
independence. No mismatch was found for spawn attempt, child state, exit, signal, timeout,
output, or selected marker effects.

## State, isolation, and helper review

Requests, results, evidence, component declarations, and component records are immutable.
`ProcessAdapter` creates request-specific decision capture and execution-boundary objects
per call. It has no global authority cache or retained mutable request authority. The
per-instance recorder sequence map and primitive invocation list are mutable evidence
state and are explicitly not claimed concurrency-safe.

Every real development child uses a pytest temporary cwd. The native helper is compiled
to temporary storage; it does not mutate the repository, home, SSH, packages, services,
or system configuration and makes no network call. It has no shell/command execution,
fork, privilege change, or uncontrolled allocation. Operations are bounded: literal argv
and selected environment reporting, fixed-buffer cwd reporting, six non-UTF-8 bytes,
exclusive seven-byte basename marker writes, numeric exit/signal, bounded-count streams,
and adapter-bounded sleep. Path-bearing marker names reject.

The complete contaminated inventory is every case in
`tests/dev/test_exp015_process_adapter.py`: helper modes `argv`, `env`, `cwd`, `nonutf8`,
`marker`, `marker-fail`, `exit`, `sleep`, `ignore-term-sleep`, `signal`, and `streams`;
all literal argv, helper and near-name paths, logical cwd shapes, capability combinations,
task/session IDs, marker names, output sizes, exits/signals/timeouts, failure injections,
and audit event placements. Future corpus authors must avoid exact or renamed-template
reuse.

## Requirement, invariant, and threat traceability

`EXP-015_REQUIREMENT_TRACEABILITY.md` has exactly one row for every REQ-033 through
REQ-062: 27 implementation/development dispositions, REQ-060 explicitly not yet held-out
validated, and REQ-061/REQ-062 architectural-only limitations. No implementation-
applicable requirement is orphaned and no architectural limitation is called empirically
established.

INV-020 maps to compound/task/resource denial plus no-probe/no-marker tests; INV-021 to
primitive-boundary ordering and pre-spawn audit faults; INV-022 to native-helper exact
argv; INV-023 to pre- and post-spawn audit faults. Global status remains `DESIRED`; there
is no held-out support.

| Threat family | Disposition before corpus |
|---|---|
| Shell metacharacters, PATH/cwd shadowing, argv reinterpretation, exact executable/cwd, symlink/type rejection, environment/secret inheritance, denied child, timeout/signal, audit loss, direct bypass | `DEVELOPMENT_TESTED` |
| One authorization core, behavior/AI separation, fixed shell-false boundary, validation separation, direct-child-only design | `ARCHITECTURALLY_ADDRESSED` |
| TOCTOU, descendants, filesystem/network child syscalls, shell/native bypass, resource quotas, durable audit, concurrency | `EXPECTED_BOUNDARY` |
| External network activity, privilege transitions, hostile concurrency, actual descendant confinement/survival, CPU/memory/process quotas, cross-platform behavior, real-agent integration | `NOT_EVALUATED` |

## Technical diligence and reuse assessment

| Dimension | Assessment | Limitation |
|---|---|---|
| Authorization core reuse | `PASS` | Generic composition depends only on ordinary requests and an `Authorizer`. |
| Exact resource authority | `PASS` | EXP-015 contracts use exact exec/cwd resources; generic subtree capability syntax still exists outside this fixture rule. |
| False-allow observability | `PASS` | Ground truth and compound decision are externally separable. |
| False-deny observability | `PASS` | Validation/tool failures remain separate from authorization. |
| Task binding | `PASS` | No authenticated session/actor binding. |
| Compound authorization | `PASS` | No priority/delegation semantics are implemented. |
| Validation separation | `PASS` | Path validation remains TOCTOU-prone. |
| Argv integrity | `PASS` | Executable-specific argv meaning is not authorized. |
| Primitive centralization | `PASS` | Direct external APIs remain expected PMED-L1 bypasses. |
| Audit explainability | `PASS_WITH_LIMITATION` | Reconstruction is schema-coupled and audit is in-memory/non-durable. |
| Failure honesty | `PASS` | Unknown child state is conservatively indeterminate. |
| SDK/gateway reuse | `PASS_WITH_LIMITATION` | Identity, serialization, durability, quotas, cancellation, and interception are future work. |
| PMED-L1 boundary | `PASS_WITH_LIMITATION` | Adapter-routed direct child only. |
| Session binding gap | `PASS_WITH_LIMITATION` | Session provenance is not authenticated authority binding. |
| TOCTOU gap | `PASS_WITH_LIMITATION` | Path validation is not fd/inode-bound execution. |
| Descendant gap | `PASS_WITH_LIMITATION` | No process-tree control. |
| Network/filesystem child gap | `PASS_WITH_LIMITATION` | Child syscalls bypass SafetyBox adapters. |

Another engineer can use `TaskContract`, `Capability`, `TaskContractPolicy`,
`CompoundActionAuthorizer`, and `ReferenceMonitor` for filesystem, a future network
adapter, or future MCP actions without understanding subprocess internals. Decisions are
deterministic and explainable, authority denial is distinguishable from later validation,
and false allow/deny can be measured outside the adapter. Strict-subset capabilities fit
the model without rewriting `ProcessAdapter`. Architectural blockers are authenticated
contract/session/actor/issuer identity, delegation proofs, revocation/expiry, durable
audit, integration serialization, and actual route interception—not subprocess policy.

## Final validation

| Gate | Result |
|---|---|
| Process-specific suite | 82 passed |
| Legacy authorization/M1/M2/M3 suite | 37 passed independently |
| Legacy filesystem plus authorization suite | 128 passed independently |
| Full pytest | 375 passed |
| Full statement coverage | 95% (4,833 statements, 221 missed) |
| Process-package coverage | 99% (688 statements, 5 missed) |
| Process adapter | 97% |
| Process canonicalization/validation/primitive/audit/models/errors | 100% |
| Ruff | pass |
| strict mypy | pass, 64 source files |
| `git diff --check` | pass |
| YAML/JSON parsing | pass |
| Markdown links | pass |
| REQ-033–REQ-062 / INV-020–INV-023 identity checks | pass |
| EXP-014 corpus/raw/analysis checksums | pass |
| EXP-015 frozen protocol/design diff | none |
| EXP-015 corpus / results | absent / absent |

## Freeze decision

After the narrow corrections above, every implementation-freeze gate passes: one
authorization core, additive regression-safe generic infrastructure, zero development
false allows/denies, authorization/validation/outcome separation, task binding, all four
compound combinations, no pre-allow probe, exact executable and logical-cwd binding,
minimal environment, exact argv, no shell, one spawn primitive, zero denied spawns,
correct ordering, pre-audit fail closure, truthful post-spawn states, synchronous direct-
child cleanup, bounded minimized output, complete traceability, full validation, frozen
protocol bytes, and no held-out corpus/results.

The implementation freeze commit SHA is recorded in the final handoff because a commit
cannot contain its own SHA.

## Exactly one next task

Author and independently audit EXP-015-CORPUS@1 as a held-out real-subprocess corpus,
emphasizing false-allow/false-deny measurement, benign hard negatives, matched
authorization counterfactuals, argv-boundary cases, compound authorization, and failure
truthfulness, without modifying the frozen PMED-L1 adapter.
