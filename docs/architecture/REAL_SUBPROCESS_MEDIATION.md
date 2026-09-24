# Real Subprocess Mediation

**Artifact:** `REAL-SUBPROCESS-MEDIATION-ARCHITECTURE@1`
**Status:** pre-implementation design for [EXP-015](../experiments/EXP-015-real-subprocess-mediation.md)
**Decision:** [ADR-007](../decisions/ADR-007-argv-native-subprocess-before-shell.md)

## Boundary and maturity

EXP-015 targets **PMED-L1**, adapter-routed direct-child subprocess execution. No process
adapter exists yet. The maturity ladder is:

| Level | Meaning |
|---|---|
| PMED-L0 | Simulated process tool with no real child process. |
| PMED-L1 | Calls routed through a real subprocess adapter are mediated. |
| PMED-L2 | Declared framework or process API interception routes have tested coverage. |
| PMED-L3 | Process-level route enforcement has tested bypass resistance. |
| PMED-L4 | OS, container, or sandbox enforcement constrains process behavior. |

PMED and FMED are separate axes. EXP-014 established bounded FMED-L1 evidence; it did
not establish process control. EXP-015 design does not upgrade RTM-1. A future successful
real-tool evaluation could contribute toward RTM-2, but only a later evidence review may
change maturity.

## Direct invocation is not shell interpretation

The v1 request is direct invocation:

```text
absolute executable identity + ordered argv tuple + logical cwd + timeout
                            -> shell=False-equivalent spawn
```

It is not a shell command string. The adapter never turns argv back into a shell line.
Characters such as `;`, `&&`, `|`, `>`, `$()`, backticks, wildcards, whitespace, and
quotes remain literal argument bytes.

Shell interpretation is a different control surface. `shell=True`, `/bin/sh -c`, shell
builtins, pipelines, redirection, substitution, subshells, globbing, expansion,
operators, and background syntax introduce a grammar, multiple commands and effects,
implicit executable resolution, and shell-specific state. They require a later explicit
shell-mediation protocol and cannot be smuggled into PMED-L1 argv execution.

## Request model

The conceptual immutable request is:

```text
ProcessExecRequest
  request_id, session_id, task_id, actor
  executable: Unicode absolute POSIX path
  argv: ordered tuple[Unicode string]
  cwd: canonicalizable logical /workspace path
  timeout_ms: integer in [50, 2000]
```

V1 has no caller environment and no stdin. The executable is not argv element zero in
the API: the primitive receives the canonical executable followed by the declared argv.
This avoids two competing executable identities.

The canonical `ActionRequest` uses action `process.exec`, resource equal to the
canonical absolute executable path, and immutable argument commitments. Cwd receives a
second ordinary capability decision using action `process.cwd` and its canonical logical
resource. Existing exact-resource syntax is sufficient; a new `proc://` URI is not
introduced.

## Trust boundary

Trusted components are the SafetyBox authorizer, future adapter, executable/cwd
canonicalizers and mapper, narrow process primitive, canonical audit recorder, and test
harness. The executable request string, argv, cwd, agent description, subprocess output,
and any future environment/stdin data are untrusted.

The process primitive is trusted to report whether its one direct child was created and
to expose direct-child completion. The child is not trusted. An allowed executable may
ignore the agent's description, access unexpected resources, emit hostile bytes, or
spawn descendants.

## Executable canonicalization

V1 intentionally avoids ambient executable resolution:

1. Require a Unicode absolute POSIX path; reject empty, bytes, NUL, and relative forms.
2. Normalize duplicate separators, `.` and lexical `..` into one absolute path.
3. Bind that canonical path as the `process.exec` authorization resource.
4. Only after complete compound allow, inspect every existing path component without
   following symlinks.
5. Require the terminal object to exist, be a regular native executable, have execute
   permission for the experiment user, and not be a shebang/wrapper script.
6. Supply that exact canonical path to the primitive.

Frozen EXP-015 contracts use exact `process.exec` resources; executable subtrees and raw
string prefixes are not corpus authority. Component-aware generic resource matching still
governs cwd scopes. Before both authorization components complete, executable and cwd
handling is purely lexical: no `stat`, `lstat`, `exists`, filesystem-resolving
`realpath`/`resolve`, `readlink`, `access`, `which`, PATH lookup, or `open` may inspect
target-dependent host state.

The following v1 outcomes are fixed:

| Input/object | Outcome before spawn |
|---|---|
| Absolute native executable, no symlink components | Eligible after allow and validation. |
| Relative path or bare name | Canonicalization failure; no authorization or spawn. |
| Ambient `PATH` lookup | Prohibited. |
| Symlinked executable or ancestor | Validation rejection after allow. |
| Missing executable | Validation rejection after allow. |
| Directory or non-regular file | Validation rejection after allow. |
| Regular file without execute permission | Validation rejection after allow. |
| Shebang/wrapper script | Validation rejection in v1. |

Rejecting symlinks and scripts narrows identity ambiguity but does not bind the checked
object to the later exec. Rename/replacement races remain unsolved. Executable metadata
validation is deliberately after authorization so denied requests do not probe whether
the named executable exists.

## PATH and environment

There is no `PATH` search. The adapter neither invokes `which` nor permits current-
directory shadowing. The child receives a new environment containing only:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
```

The parent environment is not inherited and `PATH` is absent. V1 has no caller-provided
variables. This makes secret inheritance and PATH poisoning mechanically testable while
deferring environment-specific authority to later research.

Environment is not an agent-controlled authority dimension in v1. Arbitrary future
environment values—especially secrets, loader variables, runtime tokens, and PATH-like
values—may need their own reviewed resource/capability model.

## Argument boundary

The adapter accepts up to 64 Unicode argv elements, each at most 4,096 UTF-8 bytes and
16,384 bytes in aggregate. NUL is rejected. It does not perform shell quoting, token
splitting, interpolation, expansion, or rendering. A future controlled helper observes
the exact argv tuple, allowing byte-for-byte comparison for registered Unicode inputs.

Authorization binds a canonical tuple digest and per-element commitments; the primitive
adapter verifies that the values passed to spawn are the same bound tuple. Authorization
does not attempt to understand executable-specific flags or code embedded in arguments.
Thus allowing an interpreter or powerful executable can grant broad behavior even when
argv boundaries are perfect. V1's native-helper-only evaluation does not remove this
architectural limitation.

Argv is operation data, not authorization authority. A literal argument such as
`"; rm -rf x"` is not denied merely because it resembles shell text. Under the v1
shell-false route it remains one argument when executable, cwd, task, and capability
authority are valid. This establishes boundary preservation, not malicious-injection
detection.

## Cwd and compound authorization

Cwd is mandatory. It is expressed as a logical `/workspace` resource and uses the frozen
EXP-014 lexical normalization and logical-to-temporary-root mapping semantics. Host paths
and relative cwd are invalid. After complete allow, the mapper/validator requires an
existing non-symlink directory below the isolated root.

One request therefore has two authorization dimensions:

| Order | Action | Resource |
|---:|---|---|
| 1 | `process.exec` | canonical executable absolute path |
| 2 | `process.cwd` | canonical logical `/workspace/...` cwd |

Both use the existing task-bound capability evaluator and both subdecisions are recorded,
even when the first denies. Any deny or exception closes the route. This is compound
authorization, not a process-specific allowlist. V1 does not separately authorize argv,
child-opened files, descendants, output, or network destinations.

All four component combinations are required evidence: allow/allow, allow/deny,
deny/allow, and deny/deny. Every component is evaluated and attributed without denial
short-circuiting; only allow/allow can reach validation. The current generic
`CompoundAuthorizer` composes multiple resources under one unchanged action, which is
sufficient for EXP-014 rename but not for `process.exec` plus `process.cwd`. Before the
process adapter, the shared authorization layer therefore needs a reviewed generic
ordered-`ActionRequest` composition extension. It must delegate both ordinary requests
to `TaskContractPolicy`; no process package may own a shadow allowlist.

Task authority is bound by `TaskContract.task_id`. Session ID is preserved across both
component requests and audit records, and the future harness must bind one trusted
contract instance to that session. Current M2 does not authenticate or store session ID
inside `TaskContract`, so cross-process session identity remains a schema/deployment gap
to resolve and test before implementation freeze.

## Authorization, behavior, AI, and approval boundaries

Hard authorization answers one question: **does explicit authority exist?** It is a
deterministic function of the trusted task contract, action, canonical resource, and
applicable capability rules. Physical validity, child success, suspiciousness, and
semantic intent are different questions.

B4 findings, context inconsistency, trajectory rules, risk/anomaly scores, and AI output
must not silently convert an otherwise authorized process request into `DENY`, grant
authority, expand a `TaskContract`, or override a hard denial. A separately governed
future behavior policy may attenuate or contain authority through explicit state
transitions, but its decision and provenance remain distinct from the EXP-015 capability
decision.

AI may propose capabilities, task scopes, executable roles, or cwd roles to a trusted
reviewer. It may not issue them. The boundary remains: **AI for understanding;
determinism for authority.**

`REQUIRE_APPROVAL` is a future authority-expansion state, not an EXP-015 result or
terminal class. `DENY` means authority is absent now. A trusted external actor could
later approve and issue a new versioned contract/capability; the agent, AI, or an anomaly
score cannot self-approve or mutate the original decision.

## Explanation, attenuation, and schema gaps

Every future component decision must explain its decision, subject/session, task,
action, canonical resource, matched or absent capability, rule ID, authority-source
contract reference/version/hash, compound-component identity, and deterministic reason.
“Not permitted” or a risk score alone is insufficient.

At the current immutable action/resource-set level, `process.exec` and `process.cwd` are
naturally attenuable by constructing a new task contract containing a strict subset of
the parent's capabilities. Delegation is not implemented. Missing schema and enforcement
include authenticated parent/child, actor and session binding, issuer/derivation
provenance, constraint-subset proofs, revocation/expiry, and confused-deputy protection.
These are future authorization milestones, not EXP-015 claims.

## Required lifecycle

```text
request
  -> canonicalize executable, argv commitments, and cwd
  -> authorize process.exec
  -> authorize process.cwd
  -> validate executable and cwd after complete allow
  -> commit required pre-execution audit
  -> invoke one spawn primitive
  -> capture/reap or terminate direct child
  -> commit terminal audit
```

For denial:

```text
request -> canonicalize -> both authorization subdecisions -> DENY -> no validation -> no spawn
```

The ordering proof uses canonical session-local sequence numbers and primitive-spy
evidence. The critical relation is:

```text
both ALLOW < validation success < pre-execution audit committed < primitive invoked
```

## Narrow primitive

Future implementation centralizes the equivalent of `Popen`/`posix_spawn` behind one
`ProcessPrimitive` interface. No production process module is created by this design.
The primitive must expose invocation count, argument snapshot, child-created state,
ephemeral PID, direct-child wait/termination outcome, and injectable failures.

Centralization supports mechanical denied-spawn tests, order checks, fault injection,
and later replacement with a stronger sandbox. It does not intercept direct calls made
outside the adapter.

## Output, stdin, timeout, and signal behavior

Stdout and stderr are byte streams and untrusted data. The adapter returns at most
65,536 bytes from each, plus complete-stream byte count/digest when safely drained and a
truncation flag. Canonical audit contains only counts, hashes, truncation, and capture
status. It never stores raw child output.

Stdin is immediately closed/empty. Interactive TTY, PTY, command pipelines, inherited
descriptors, and caller-supplied input are excluded.

Timeout is per request, bounded from 50 to 2,000 ms. It begins after confirmed direct-
child creation. The adapter sends `SIGTERM`, waits 250 ms, then uses `SIGKILL` if the
direct child remains. It reaps the direct child when possible. Timeout and signal
termination mean execution occurred and effects may remain; neither is rollback.

## Terminal semantics

| Terminal class | Broad family | Spawn/effect interpretation |
|---|---|---|
| `POLICY_DENY_NOT_SPAWNED` | `DENY` | Policy denied; primitive not invoked. |
| `FAIL_CLOSED_NOT_SPAWNED` | `FAIL_CLOSED` | Control failed before primitive; primitive not invoked. |
| `VALIDATION_REJECT_NOT_SPAWNED` | `TOOL_ERROR` | Allowed identity failed a registered precondition. |
| `SPAWN_ERROR_NOT_CREATED` | `TOOL_ERROR` | Primitive invoked but affirmatively created no child. |
| `PROCESS_EXIT_0` | `ALLOW_SUCCESS` | Direct child exited zero; child effects may have occurred. |
| `PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE` | `TOOL_ERROR` | Direct child exited nonzero; effects may remain. |
| `PROCESS_TIMEOUT_EFFECT_POSSIBLE` | `TOOL_ERROR` | Timeout path used; child effects may remain. |
| `PROCESS_SIGNALED_EFFECT_POSSIBLE` | `TOOL_ERROR` | Direct child ended by signal; effects may remain. |
| `FAIL_INDETERMINATE_EXECUTION_POSSIBLE` | `FAIL_INDETERMINATE` | Child creation/effect or terminal evidence cannot be stated more narrowly. |

An authorization exception, canonicalization error, invalid request, pre-execution audit
failure, or unexpected pre-primitive failure closes before spawn. Post-spawn audit or
capture failures are indeterminate when the truthful narrower child outcome cannot be
durably represented.

## Audit envelope

The future canonical process envelope extends the M3-compatible lifecycle rather than
creating a parallel authorization log. It must contain:

- session, task, actor, request, correlation, action, sequence, and versions;
- requested/canonical executable and requested/canonical cwd;
- argv count, ordered per-argument index/length/SHA-256, and tuple digest;
- fixed environment profile and bounded timeout;
- executable and cwd normalized actions/resources, matched or absent capability facts,
  authorization rule IDs, decisions, deterministic reasons, authority-source contract
  reference/version/hash, and compound-component identities;
- validation categories and order relative to the spawn primitive;
- whether spawn was attempted and whether a child was confirmed;
- a stable per-attempt child token and optional ephemeral PID;
- exit status, signal, timeout/termination path, and effect-uncertainty state;
- stdout/stderr counts, digests, truncation, and capture status; and
- terminal class and error category.

Raw argv, parent environment, stdout, stderr, and secrets are excluded. Ordered hashes
reconstruct the committed argument structure and permit exact verification without
turning canonical audit into a secret store. PID is diagnostic, not long-term identity.

## Process-tree limitation

Only the adapter's direct child is observed. Once allowed, that child may create further
processes or escape the adapter's direct wait/termination logic. Process groups, cgroups,
seccomp, namespaces, container sandboxes, ptrace/eBPF/LSM enforcement, and equivalent
non-Linux job controls are future layers. No descendant confinement is inferred from a
direct-child result.

## Interaction with filesystem mediation

`FS-ADAPTER@1` and future process mediation are separate control surfaces. Blocking an
unauthorized process launch removes that launch route. Allowing a process does not route
its `open`, rename, or other filesystem syscalls through `FS-ADAPTER@1`. An authorized
child may modify files directly, including files outside its logical cwd if OS permission
allows.

Constraining the behavior of an allowed process requires stronger filesystem and network
confinement—such as namespaces, seccomp, containers, MAC, or another OS boundary—beyond
PMED-L1.

Likewise, an authorized child may make network connections outside any future SafetyBox
network mediator unless a sandbox, network namespace, firewall/proxy, or equivalent
control constrains it. Process authorization alone does not imply network observation or
confinement.

## Bypass and deployment boundary

A future isolated direct `subprocess.Popen` control must succeed outside the adapter and
is classified `EXPECTED_PMED_L1_BYPASS`. Direct `os.system`, `shell=True`, explicit shell
invocation, native extensions, and alternate process APIs share that boundary. They are
not adapter failures because PMED-L1 assumes routing.

This limitation matters for coding agents, which commonly invoke Python, shells, package
managers, Git, build tools, and test runners. Process mediation begins a broader execution
control plane, but real-agent value requires framework integration or a stronger route
enforcement layer plus sandboxing of allowed processes.

## Safety and future implementation fixtures

All future cases use fresh temporary workspaces, a normal user, no external network, and
no home, SSH, repository, system, or production mutation. A bounded native helper may
print argv/selected environment/cwd, write a marker, choose an exit code, sleep briefly,
emit stderr, self-signal, or create a partial effect before failure. No helper or adapter
is implemented in this design stage.

Fork bombs, uncontrolled output, CPU/memory/process exhaustion, privilege escalation,
setuid behavior, daemonization, background work, process groups, concurrency, and TOCTOU
attacks remain future bounded research.
