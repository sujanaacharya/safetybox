# Real Subprocess Mediation Requirements

**Artifact:** `REAL-SUBPROCESS-MEDIATION-REQUIREMENTS@1`
**Status:** preregistered design requirements; not implemented
**Experiment:** [EXP-015](../experiments/EXP-015-real-subprocess-mediation.md)

## Purpose and language

These requirements define the design and future evidence gate for adapter-routed real
process execution. “Must” describes a future implementation or evaluation obligation,
not current behavior. The global requirement namespace was searched before allocation;
`REQ-001` through `REQ-032` belong to real-filesystem mediation, so this artifact
allocates `REQ-033` through `REQ-062`.

The target is PMED-L1 only. It is not complete process mediation, shell mediation,
process-tree confinement, concurrency or TOCTOU resistance, real-agent deployment, or
production readiness.

## Boundary, request, and trust requirements

### REQ-033 — Bounded PMED-L1 claim

Evaluation must describe only requests routed through the future subprocess adapter.
Direct `subprocess`, `os.system`, explicit shells, native execution, inherited process
handles, and other routes remain outside PMED-L1. Success must not be described as
universal process control or confinement.

### REQ-034 — Typed direct-execution request

V1 must expose only `process.exec` with a typed request containing an executable string,
ordered immutable argv tuple, logical cwd, and bounded timeout. The executable is not
duplicated in argv: argv contains only arguments passed after the executable. A single
shell command string is prohibited.

### REQ-035 — Trusted computing base and untrusted data

The trusted base is the SafetyBox authorizer, process adapter, executable and cwd
canonicalizers/mappers, process primitive, audit recorder, and deterministic harness.
Executable text, argv, cwd, agent descriptions, subprocess output, and any future
environment or stdin values are untrusted. Command text and subprocess output never
become authority.

Hard authorization answers only whether explicit authority exists. Suspiciousness,
trajectory deviation, context inconsistency, and anomaly or AI scores are behavior-
analysis signals and must not silently become `ALLOW` or `DENY`. AI may propose a
capability, scope, executable role, or cwd role for review, but it may not grant a
capability, expand a `TaskContract`, override a denial, or become trusted authority.

## Executable and argument requirements

### REQ-036 — Absolute executable identity

V1 must accept only a Unicode absolute POSIX executable path without NUL. Lexical
normalization removes `.` and duplicate separators and resolves `..` without permitting a
relative result. The canonical absolute path is the `process.exec` resource passed to
the existing authorization model and the exact path later supplied to the spawn
primitive.

EXP-015 v1 contracts must grant `process.exec` to exact executable resources rather than
raw prefixes or executable subtrees. Near-neighbor names must not match. This is a
contract-fixture restriction evaluated by the existing exact-resource matcher, not a
process-specific allowlist or alternate policy engine.

Relative executable paths are rejected before authorization. A missing executable,
directory, non-regular file, non-executable file, symlink in any existing component, and
shebang/wrapper script are rejected after allow and before spawn. V1 supports controlled
native helper executables only; interpreter and wrapper behavior require a later design.
No claim of name-to-object binding or TOCTOU resistance follows.

Before complete authorization, executable handling is purely lexical. It must not call
`stat`, `lstat`, `exists`, filesystem-resolving `realpath`/`resolve`, `readlink`,
`access`, `which`, PATH search, or `open` on the requested target.

### REQ-037 — No ambient PATH lookup

V1 must not search `PATH`, invoke `which`, use the current directory as an executable
search location, or accept a bare program name. `PATH` is absent from the child
environment. This fixed rule prevents PATH poisoning and executable shadowing from being
silently environment-dependent.

### REQ-038 — Ordered argv integrity

Each argv element must remain one argv element. The adapter must never concatenate,
quote, split, or render argv into a shell string. Empty arguments, spaces, quotes,
wildcards, semicolons, `&&`, pipes, redirections, `$()`, and backticks remain literal
data when accepted. NUL is rejected. V1 limits requests to 64 arguments, 4,096 UTF-8
bytes per argument, and 16,384 UTF-8 bytes in total.

Authorization must not depend on a pretty-printed shell reconstruction. Exact ordered
argv commitments are bound into the request before authorization and checked against the
values passed to the process primitive.

Argv is operation data, not authority. In v1, dangerous-looking text—including
`"; rm -rf x"`—does not itself cause an authorization denial; under the shell-false route
it remains one literal argument if executable, cwd, task, and capabilities authorize the
request. Executable-specific argument meaning and future behavior analysis are separate
from hard authorization.

## Cwd and environment requirements

### REQ-039 — Canonical logical cwd

Cwd is mandatory and uses the frozen EXP-014 logical `/workspace` syntax and mapping
semantics inside a fresh temporary root. It is lexically canonicalized before
authorization and physically validated only after the complete compound allow. Relative
cwd, host cwd, missing cwd, non-directory cwd, symlinked cwd or ancestor, and cwd outside
`/workspace` are rejected without spawn.

No cwd existence, type, link, or host-mapping probe may occur before authorization.
Logical canonicalization must preserve component boundaries and must not widen cwd
authority through raw-prefix or alternate-representation matching.

### REQ-040 — Compound executable and cwd authorization

V1 requires two ordinary task-bound capability decisions under one request:
`process.exec` on the canonical executable and `process.cwd` on the canonical logical
cwd. The existing `TaskContract`, `Capability`, `TaskContractPolicy`, and
`ReferenceMonitor` semantics remain authoritative; a separate process allowlist is
prohibited.

Evaluation order is executable then cwd. Both subdecisions must be recorded even if one
denies. Any deny or authorization exception prevents validation and spawn. No argv value
or child behavior is separately authorized in v1; that limitation must be reported.

The four compound combinations—allow/allow, allow/deny, deny/allow, and deny/deny—must
all be independently observable. Only allow/allow can reach validation or spawn. The
existing `CompoundAuthorizer` supports ordered same-action resource tuples; EXP-015
requires a reviewed generic extension that composes ordered ordinary `ActionRequest`
components with distinct actions. That extension must remain in the shared authorization
layer, delegate every component to `TaskContractPolicy`, avoid denial short-circuiting,
and freeze before the process adapter and held-out corpus. The adapter may not implement
its own allowlist or decision logic.

Task authority remains bound to the `TaskContract.task_id`. Session ID must be preserved
in every component and audit record, and the future implementation/harness must bind one
trusted contract instance to the evaluated session so a decision cannot be replayed
across sessions. Current M2 has no authenticated session field in `TaskContract`; this is
an explicit schema/deployment gap rather than an implemented guarantee.

### REQ-041 — Fixed minimal environment

V1 accepts no caller-supplied environment mapping. The child receives a new fixed minimal
environment containing only `LANG=C.UTF-8` and `LC_ALL=C.UTF-8`; the parent environment
is not inherited, and `PATH` is absent. Secret-like parent variables, credentials,
runtime tokens, and locale variation must not silently flow to the child. Future
environment resources such as `ENV_SECRET`, `ENV_RUNTIME`, or `ENV_PATH` require a new
protocol and are not allocated here.

Environment is therefore not an agent-controlled authorization dimension in EXP-015.
Future arbitrary variables, secrets, loader controls, or PATH-like values may require
their own reviewed capability/resource model rather than being hidden in argv or adapter
configuration.

## Ordering and primitive requirements

### REQ-042 — Authorize, validate, audit, then spawn

The required order is request ingress, command/cwd canonicalization, complete compound
authorization, executable and cwd validation, committed pre-execution audit, one process
primitive invocation, direct-child completion or termination, and terminal audit.
Session-local sequence evidence, not timestamps, determines ordering.

A denied route ends after both authorization subdecisions and emits no validation,
pre-execution, output, PID, exit, signal, timeout, or spawn event.

### REQ-043 — Denied requests invoke no spawn primitive

Every policy-denied request must have zero invocations of the protected process-spawn
primitive and therefore no adapter-created child PID, stdout, stderr, exit code, signal,
or child-caused downstream effect. This is an all-denied-cases gate with target 1.0.

### REQ-044 — Narrow process primitive boundary

Future implementation must place the one v1 spawn operation behind a narrow replaceable
primitive abstraction. `Popen`, `run`, `posix_spawn`, and exec-like calls must not be
scattered through adapter code. The abstraction must support call counting, ordered
evidence, failure injection, and a definitive `child_created` observation when the
platform can provide it.

### REQ-045 — Required pre-spawn audit is fail closed

Every required record through `EXECUTION_START_COMMITTED` must be accepted by the
canonical audit sink before primitive invocation. Failure at or before that boundary is
`FAIL_CLOSED_NOT_SPAWNED`, with zero primitive calls.

## Shell, process tree, and effects

### REQ-046 — Shell-language exclusion

V1 uses direct executable invocation equivalent to `shell=False`. It does not mediate
arbitrary shell grammar, command strings, shell builtins, pipelines, redirections,
substitutions, subshells, globbing, expansions, operators, backgrounding, or explicit
`/bin/sh -c`. A future shell experiment must define and evaluate those semantics
separately.

### REQ-047 — Direct-child-only observation

PMED-L1 v1 observes and controls only the adapter's direct spawn. An allowed child may
spawn descendants, daemonize, change process groups, or use native routes not confined
by this adapter. No descendant-control or process-tree-confinement claim is permitted.

### REQ-048 — Process side-effect definition

Process execution effects include child creation, executable invocation, stdout/stderr,
an exit status or signal outcome, and child-caused filesystem, network, or descendant
effects. The core denied invariant measures the strongest immediate boundary: zero spawn
primitive invocation and zero adapter-created direct child. Controlled fixtures may
inspect downstream marker files but cannot prove absence of every external effect.

## Terminal and failure requirements

### REQ-049 — Frozen terminal taxonomy

Every attempt must end in exactly one of:

- `POLICY_DENY_NOT_SPAWNED`;
- `FAIL_CLOSED_NOT_SPAWNED`;
- `VALIDATION_REJECT_NOT_SPAWNED`;
- `SPAWN_ERROR_NOT_CREATED`;
- `PROCESS_EXIT_0`;
- `PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE`;
- `PROCESS_TIMEOUT_EFFECT_POSSIBLE`;
- `PROCESS_SIGNALED_EFFECT_POSSIBLE`; or
- `FAIL_INDETERMINATE_EXECUTION_POSSIBLE`.

The result separately records a broad outcome family (`ALLOW_SUCCESS`, `DENY`,
`FAIL_CLOSED`, `TOOL_ERROR`, or `FAIL_INDETERMINATE`), exact terminal class, policy
decision, primitive invocation, child-created state, and effect uncertainty. Validation
rejection, spawn error, nonzero exit, timeout, and signal are distinct terminal classes
within the broad `TOOL_ERROR` family; they must not collapse into one generic error.

### REQ-050 — Pre-spawn and spawn-failure truthfulness

Canonicalization error, authorization exception, invalid request, required pre-spawn
audit failure, and unexpected pre-primitive exception are
`FAIL_CLOSED_NOT_SPAWNED`. Executable or cwd precondition failure after allow is
`VALIDATION_REJECT_NOT_SPAWNED`. A primitive error is `SPAWN_ERROR_NOT_CREATED` only when
the primitive establishes that no child was created; otherwise it is indeterminate.

### REQ-051 — Post-spawn truthfulness and partial effects

After child creation, nonzero exit, timeout, signal termination, capture failure,
unexpected exception, or terminal-audit failure must never be reported as denied, not
executed, rolled back, or side-effect-free. If the exact outcome cannot be preserved, the
terminal result is `FAIL_INDETERMINATE_EXECUTION_POSSIBLE`. Exit zero means command
completion, not absence or safety of side effects.

### REQ-052 — Timeout and termination semantics

Each request carries an integer timeout from 50 through 2,000 milliseconds. On timeout,
the adapter sends `SIGTERM` to the direct child, waits a fixed 250-millisecond grace
period, then sends `SIGKILL` if the direct child remains. Timeout starts after confirmed
spawn and ends only when the direct child is reaped or outcome becomes indeterminate.
Timeout never implies rollback and does not establish descendant termination.

### REQ-053 — Exit and signal semantics

Exit code zero is `PROCESS_EXIT_0`; a positive/nonzero normal exit is
`PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE`; termination observed as a POSIX signal is
`PROCESS_SIGNALED_EFFECT_POSSIBLE` with the signal number. The initial platform is Linux;
portable Windows termination semantics are not claimed.

## I/O and evidence requirements

### REQ-054 — Captured output is untrusted and bounded

V1 captures stdout and stderr as bytes. The caller may receive at most 65,536 bytes per
stream plus total-byte counts, SHA-256 digests of the complete drained streams when
available, and truncation flags. The adapter must continue draining without retaining
unbounded data. Canonical audit stores no raw output, only counts, digests, truncation,
and capture status. Denied and pre-spawn failures expose no child output because no child
exists.

### REQ-055 — No stdin or interactive execution

V1 supplies an immediate closed/empty stdin and accepts no caller stdin. Interactive TTY,
password prompts, pipes between commands, inherited descriptors, and PTY semantics are
excluded.

### REQ-056 — Reconstructable minimized audit

Canonical evidence must reconstruct session, task, actor, request, correlation, action,
requested and canonical executable, ordered argv commitments, argv count, requested and
canonical cwd, fixed environment profile, timeout, both authorization subdecisions and
rules, validation outcomes, whether spawn was attempted, child-created state, terminal
class, effect uncertainty, output handling, adapter/primitive/policy/contract versions,
and event order without runner-private state.

Each executable and cwd subdecision must additionally identify the authority source:
`TaskContract` reference/version or hash, matched or absent `Capability` action and
resource, normalized request action/resource, rule ID, task/session, compound component,
decision, and deterministic reason. “Not permitted” without these structured facts is
insufficient, and a risk score is not a hard-authorization explanation.

### REQ-057 — Argument, output, and PID minimization

Canonical audit records the ordered index, UTF-8 byte length, and SHA-256 of each argv
element plus a digest of the canonical argv tuple; raw argv is excluded. Raw stdout,
stderr, parent environment, and secrets are excluded. A post-spawn record may contain an
ephemeral PID and must contain a per-attempt child identity token. PID is diagnostic only,
never stable identity or authority. Any raw development assertion stays outside canonical
audit and is marked contaminated.

## Bypass, safety, and experimental requirements

### REQ-058 — Explicit direct-route and filesystem boundaries

A safe direct `subprocess.Popen` control outside the adapter must demonstrate expected
PMED-L1 bypass in an isolated fixture. Direct `os.system`, `shell=True`, explicit shells,
and native execution are also outside the guarantee but need not be executed in v1.
Filesystem operations of an authorized child do not pass through `FS-ADAPTER@1`; process
launch authorization and child filesystem confinement are separate control surfaces.

An authorized child may likewise perform network activity outside a future SafetyBox
network mediator unless an OS/process sandbox or network control constrains it. PMED-L1
does not imply network observation or confinement.

### REQ-059 — Isolated controlled fixtures

All future tests run as a normal user in fresh temporary workspaces with no external
network, real home, SSH, production, or repository mutation. Development uses a bounded
repository-controlled native helper capable of reporting argv, selected environment,
cwd, marker writes, chosen exit, short sleep, stderr, self-signal, and partial effect then
failure. Helper fixtures are contaminated and may not be exactly reused in held-out
cases. No helper is part of this design change.

### REQ-060 — Frozen workflow and deterministic gates

The order is protocol/design freeze, adapter and primitive implementation, implementation
freeze, held-out corpus authorship, corpus freeze, one-shot evaluation, and adversarial
analysis. No held-out case may be authored before implementation freeze. Repeated
registered cases must agree semantically apart from declared ephemeral fields.

The future corpus must contain at least 80 adapter-routed attempts plus one isolated
direct-`Popen` boundary control. Tags may overlap, but coverage must include at least 20
authorized spawned cases, 20 policy-denied cases, 16 argv-boundary cases, 12 executable-
resolution cases, 10 cwd cases, 4 environment-containment cases, 16 terminal/failure
cases including timeout and signal, and 6 cases designated for three semantic repeats.

Authorization-evaluable cases must include hard benign authorized examples with unusual
literal argv, Unicode, an empty element, spaces, quotes, shell-looking metacharacters,
authorized cwd and executable near denied component boundaries, multiple capabilities,
compound executable/cwd authority, and similar resources across different tasks. They
must also include matched counterfactual pairs holding executable, argv, cwd, and fixture
state constant while changing only `process.exec`, `process.cwd`, or task authority; all
four compound decision combinations; correct-task/wrong-task pairs; authorization-versus-
validation pairs; and authorization-versus-tool-outcome pairs. These cases must punish
over-denial and are not authored at the design stage.

Success requires 100% authorization correctness, denied-spawn prevention,
authorize-before-spawn ordering, registered argv-boundary preservation, audit
reconstruction, executable/cwd validation, environment containment, terminal taxonomy,
zero adapter-routed policy escapes, an expected direct-route bypass, deterministic
repeats, and no frozen regression. Criteria may not be relaxed after the run.

The future analysis must also derive:

- `authorization_false_allow_rate` = authority-negative cases receiving compound
  `ALLOW` / all authority-negative cases; target 0;
- `authorization_false_deny_rate` = authority-positive cases receiving compound `DENY` /
  all authority-positive cases; target 0; and
- `realized_false_allow_count` = authority-negative cases invoking spawn; target 0.

Validation rejection, missing/changed host objects, nonzero exit, timeout, signal, and
other post-authorization tool outcomes are not authorization false denies. These metrics
supplement rather than replace the existing authorization and denied-spawn metrics.

EXP-015 authorization cases may later contribute to a separately governed authorization
benchmark covering false allow/deny, compound decisions, task binding, resource
boundaries, attenuation/delegation, approval escalation, and hard benign cases. This
requirement creates no benchmark or dataset now.

### REQ-061 — Secondary performance only

Future evaluation may report authorization, canonicalization/validation, spawn, audit,
and total adapter latency with sample counts and appropriate summaries. V1 has no
performance acceptance threshold, and correctness may not be traded for latency.

### REQ-062 — Platform, privilege, resource, and maturity limits

Initial evidence is Linux-only, normal-user, sequential, and non-concurrent. Sudo,
setuid, privilege escalation, fork bombs, uncontrolled CPU/memory/process/output loads,
background processes, daemonization, and production resources are excluded. Process
count, CPU, memory, output, network, and broader timeout budgets remain future bounded
resource-governance work. A successful EXP-015 may contribute evidence toward RTM-2 but
does not preregister automatic promotion.

`process.exec` and `process.cwd` capabilities are naturally attenuable at the current
action/resource-set level by issuing a new contract containing a strict subset. No
delegation mechanism is implemented. Current schema gaps include authenticated parent/
child and session/actor binding, issuer and derivation provenance, constraint-subset
proofs, revocation/expiry, and prevention of confused-deputy reuse.

`REQUIRE_APPROVAL` is a future authority-expansion state, not an EXP-015 terminal or
enforcement outcome. `DENY` means current authority is absent; a trusted external actor
may later issue a new versioned contract/capability after approval. The requesting agent,
AI output, or anomaly score cannot self-approve or mutate the current decision.

## Verification disposition

These are Level 0 design requirements. They authorize no implementation, corpus,
experiment execution, maturity upgrade, candidate-claim promotion, or OWASP category
claim.
