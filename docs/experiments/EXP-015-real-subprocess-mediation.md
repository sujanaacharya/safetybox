# EXP-015 — Real Subprocess Mediation and Command Execution Control

**Status:** `PREREGISTERED`
**Protocol version:** 1
**Evidence level:** Level 0 / design only
**Implementation:** not included
**Held-out corpus:** not included
**Results:** not included

## Frozen starting point

The repository was clean before registration (`git status --short` produced no output).
The preregistration base is `d1053c26cdfad781894f57ecedefb07a39d84ca7`, SafetyBox
version `0.0.0`, with current maturity RTM-1.

| EXP-014 artifact | Frozen Git SHA |
|---|---|
| Protocol/design | `7baf20293caa83d3fff6a200174c4f8840918607` |
| Implementation | `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c` |
| Held-out corpus | `5ac7311bb8f086cca97f474069d068067ac73142` |
| Raw results | `17a0f6b6409ac85a2ee1a2d49f36a5748e3ab310` |
| Analysis and bounded synthesis | `d1053c26cdfad781894f57ecedefb07a39d84ca7` |

At registration, the frozen EXP-014 protocol/design paths, adapter and development-freeze
paths, corpus directory, and raw-result manifest paths have no diff from their respective
freeze commits. The later additive analysis artifacts are not raw-result mutations.

Repository search found only `EXP-001` through `EXP-014`; the canonical registry makes
`EXP-015` the next valid allocation. Global namespaces likewise allocate `REQ-033`
through `REQ-062`, `INV-020` through `INV-023`, `ADR-007`, and `CL-011` only after
searching existing records.

## Primary research question

Can SafetyBox mediate real subprocess execution so that authorized commands execute,
denied commands create no child process or side effect, argument boundaries are preserved
without shell reinterpretation, execution ordering is authorize-before-spawn, and audit
evidence truthfully reconstructs process attempts and outcomes?

## Secondary questions

- Can command and argument canonicalization avoid shell-token confusion?
- Can environment-variable scope be controlled without secret inheritance?
- Can cwd be represented and scoped safely?
- Can executable paths be canonicalized without ambient PATH ambiguity?
- Can denied requests be shown to create zero child process?
- Can spawn, exit, timeout, signal, audit, and partial-effect failures be classified
  truthfully?
- What are the bypass limits of an in-process subprocess adapter?
- What materially changes when `shell=True` or explicit shell syntax enters the model?

These are preregistered questions, not findings.

## Mediation and claim boundary

EXP-015 targets **PMED-L1**, meaning only direct process requests routed through the
future adapter. The ladder is:

| Level | Meaning |
|---|---|
| PMED-L0 | Simulated process tool. |
| PMED-L1 | Adapter-routed real subprocess execution. |
| PMED-L2 | Tested framework or process-API interception. |
| PMED-L3 | Process-level route enforcement and bypass resistance. |
| PMED-L4 | OS/container/sandbox enforcement. |

The study will not establish universal process confinement, complete mediation,
descendant control, TOCTOU or concurrency safety, real-agent deployment, production
readiness, or automatic RTM-2 promotion.

## V1 execution model

V1 registers one operation: `process.exec`. The request is one absolute executable path,
an ordered argv tuple, a logical `/workspace` cwd, and a timeout between 50 and 2,000 ms.
Execution is equivalent to `shell=False`.

Explicit exclusions are `shell=True`, command strings, `/bin/sh -c`, pipes,
redirections, command substitution, subshells, globbing, variable expansion, operators,
builtins, background processes, daemonization, process groups, interactive TTY/PTY,
caller stdin, caller environment, inherited descriptors, privilege escalation, and
unbounded resource workloads.

## Shell boundary

Direct invocation selects one executable and passes ordered arguments. Shell invocation
passes text to a language interpreter that may resolve several commands and effects.
Accordingly, shell metacharacters in v1 are literal argv data and cannot be interpreted
by an adapter-created shell because no shell is created.

A later shell experiment must separately define tokenization, pipes, redirections,
substitutions, subshells, globbing, variables, operators, builtins, backgrounding, and
multi-process audit. EXP-015 results may not be generalized to those semantics.

## Canonical request and executable rules

The executable and ordered argv tuple are distinct. Authorization never uses a
pretty-printed command string. V1 requires a Unicode absolute POSIX executable path and
performs lexical normalization before authorization. Relative paths and bare names fail
before authorization. Ambient `PATH` search, `which`, and current-directory lookup are
prohibited.

Frozen v1 contracts use exact `process.exec` resources; raw prefixes and executable
subtrees are not authority. Before complete compound authorization, processing is purely
lexical: no `stat`, `lstat`, `exists`, filesystem-resolving `realpath`/`resolve`,
`readlink`, `access`, `which`, PATH search, or `open` may inspect executable or cwd host
state.

After complete allow, validation rejects a missing executable, directory, non-regular
file, non-executable file, any symlink component, and shebang/wrapper script. The exact
canonical path authorized is the path supplied to the primitive. This does not solve the
validation-to-exec race and does not establish object-identity confinement.

## Argv policy

Argv is an immutable ordered tuple of at most 64 strings, 4,096 UTF-8 bytes each and
16,384 bytes total. NUL is rejected. Empty arguments and the strings `;`, `&&`, `|`, `>`,
`$()`, backticks, wildcards, spaces, and quotes remain individual literal arguments.
The adapter must not concatenate, quote, split, expand, or shell-render them.

V1 authorizes executable identity, not executable-specific flag meaning. A powerful
allowed executable can still interpret argv as code or instructions; controlled native
helpers are used so the initial evidence measures mediation rather than interpreter
semantics.

Argv is operation data, not authority. Dangerous-looking shell text does not become a
hard authorization denial; for example, `"; rm -rf x"` remains one literal argument when
the executable, cwd, task, and capabilities are authorized. EXP-015 tests boundary
preservation, not malicious shell-injection detection.

## Environment, cwd, and stdin

The child receives a newly constructed environment containing only `LANG=C.UTF-8` and
`LC_ALL=C.UTF-8`. It receives no inherited `PATH`, credentials, secret-like variables,
or caller values. Environment-resource authorization is deferred.

Environment is not agent-controlled authority in v1. Future arbitrary variables,
secrets, loader controls, and PATH-like values may require their own reviewed
resource/capability model.

Cwd is mandatory, canonicalized under logical `/workspace`, mapped into a fresh
temporary root using EXP-014 filesystem semantics, and independently authorized with
`process.cwd`. Relative, host, missing, symlinked, non-directory, or out-of-workspace cwd
cannot spawn.

Stdin is closed/empty. No caller input or interactive mode is supported.

## Authorization model

No independent process allowlist is introduced. V1 reuses `TaskContract`, `Capability`,
`TaskContractPolicy`, and `ReferenceMonitor` with two bound decisions:

1. `process.exec` on the canonical absolute executable; then
2. `process.cwd` on the canonical logical cwd.

Both subdecisions are recorded even if one denies. Any missing capability, wrong
executable resource, unauthorized cwd, wrong task, or authorization exception prevents
all validation and spawn. Argv, child filesystem/network behavior, and descendants are
not separate v1 authorization dimensions.

All four component outcomes are required: allow/allow, allow/deny, deny/allow, and
deny/deny. Both components are evaluated and attributed without denial short-circuiting;
only allow/allow reaches validation. The existing generic `CompoundAuthorizer` supports
same-action resource tuples, so before adapter implementation the shared authorization
layer requires a reviewed generic extension for ordered ordinary `ActionRequest`
components with distinct actions. Both components still delegate to
`TaskContractPolicy`; no subprocess package may contain a shadow allowlist.

Hard authorization asks only whether explicit authority exists. Validation asks whether
the host object satisfies execution constraints. Behavior analysis asks whether activity
looks suspicious. Validation rejection, exit 1, timeout, signal, B4 findings, context
inconsistency, anomaly/risk scores, and AI output do not rewrite the capability decision.
A separately governed future containment policy may intervene, but it must emit its own
decision and provenance.

Task authority is bound to `TaskContract.task_id`; session ID is preserved in every
component and audit record. The future harness must bind the trusted contract instance to
that session. Current M2 lacks authenticated session binding in `TaskContract`, which is
an explicit implementation-freeze schema/deployment gap.

AI may propose capabilities, scopes, and executable/cwd roles for trusted review, but it
cannot grant or expand authority, override denial, self-approve, or turn an anomaly score
into hard authorization. `REQUIRE_APPROVAL` is a future authority-expansion state, not an
EXP-015 outcome: a trusted external actor would issue a new versioned authority object.
At the current action/resource-set level, process capabilities can be attenuated by a
strict-subset child contract, but delegation, parent/child and actor/session binding,
derivation provenance, constraint-subset proof, revocation, and expiry are not
implemented.

## Ordering and denied-spawn invariants

Required allowed sequence:

```text
request
-> canonicalize and bind executable/argv/cwd
-> executable authorization
-> cwd authorization
-> post-allow executable/cwd validation
-> required pre-execution audit committed
-> protected spawn primitive
-> direct-child completion/termination
-> terminal audit
```

Denied sequence:

```text
request -> canonicalize -> both authorization decisions -> DENY -> no validation -> no spawn
```

Mechanically tested order is:

```text
both ALLOW < validation success < pre-execution audit committed < spawn primitive
```

The proposed invariants are `INV-020` denied requests never invoke spawn, `INV-021`
authorization and required audit precede spawn, `INV-022` argv boundaries are preserved,
and `INV-023` pre-spawn audit failure prevents spawn while post-spawn failure remains
truthful. All remain `DESIRED`.

## Protected primitive

Future implementation must centralize one spawn route behind a narrow primitive rather
than scatter `Popen`, `run`, `posix_spawn`, or exec-like calls. The primitive exposes
invocation count, bound values, order, child-created state, PID, wait/termination outcome,
and injectable failures. No primitive or adapter is part of this registration.

## Effects and process-tree boundary

An execution effect includes primitive invocation, child creation, executable invocation,
stdout/stderr, exit/signal outcome, and child-caused filesystem, network, or descendant
activity. The strongest immediately measurable denied property is zero primitive
invocation and zero adapter-created direct child. Controlled marker fixtures may inspect
selected downstream effects.

Only the direct child is observed. An allowed process may spawn descendants. V1 does not
control process groups or claim descendant termination. Cgroups, namespaces, seccomp,
containers, MAC, ptrace/eBPF/LSM mechanisms, and non-Linux job controls remain future
work.

## Frozen terminal taxonomy

| Terminal class | Broad family | Meaning |
|---|---|---|
| `POLICY_DENY_NOT_SPAWNED` | `DENY` | Policy denied and primitive was not invoked. |
| `FAIL_CLOSED_NOT_SPAWNED` | `FAIL_CLOSED` | Pre-spawn control failure and primitive was not invoked. |
| `VALIDATION_REJECT_NOT_SPAWNED` | `TOOL_ERROR` | Allowed request failed executable/cwd validation. |
| `SPAWN_ERROR_NOT_CREATED` | `TOOL_ERROR` | Primitive confirms no child was created. |
| `PROCESS_EXIT_0` | `ALLOW_SUCCESS` | Direct child exited zero; effects may have occurred. |
| `PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE` | `TOOL_ERROR` | Direct child exited nonzero after execution. |
| `PROCESS_TIMEOUT_EFFECT_POSSIBLE` | `TOOL_ERROR` | Timeout termination path; effects may remain. |
| `PROCESS_SIGNALED_EFFECT_POSSIBLE` | `TOOL_ERROR` | Signal terminated the direct child; effects may remain. |
| `FAIL_INDETERMINATE_EXECUTION_POSSIBLE` | `FAIL_INDETERMINATE` | Execution/effect cannot be stated more narrowly. |

Authorization exception, canonicalization failure, invalid request, pre-execution audit
failure, and unexpected pre-primitive exception fail closed. Missing executable,
permission, directory, symlink, script, and invalid cwd are validation rejections after
allow. A spawn exception is no-child only when the primitive proves it. Post-spawn audit
or capture failure cannot become denial or not-executed.

## Output, timeout, and signal semantics

Stdout and stderr are captured as untrusted bytes. The caller receives no more than
65,536 bytes per stream with total counts, full-stream digest when safely drained, and
truncation status. Audit stores only count, digest, truncation, and capture status—never
raw output. Denied and pre-spawn routes have no child output.

Timeout begins after confirmed spawn. On expiration the adapter sends `SIGTERM`, waits
250 ms, and sends `SIGKILL` if the direct child remains, then reaps it when possible.
Timeout does not roll back existing effects or prove descendants stopped. A Linux signal
outcome records the signal number. No cross-platform signal equivalence is claimed.

## Audit model and minimization

The canonical envelope must reconstruct, without runner-private state:

- session, task, actor, request, correlation, sequence, action, and versions;
- requested/canonical executable and cwd;
- argv count, tuple digest, and ordered index/byte-length/SHA-256 commitments;
- environment profile and timeout;
- both normalized action/resource components, matched or absent capabilities, decisions,
  rules, deterministic reasons, authority-source contract reference/version/hash,
  validation outcomes, and ordering;
- spawn attempted, primitive invoked, child created, stable child token, optional PID;
- exit code, signal, timeout/termination, output counts/hashes/truncation;
- terminal class, effect uncertainty, and error category.

Raw argv may contain secrets and is not in canonical audit. Raw environment and child
output are also excluded. PID is ephemeral diagnostics; the child token is the stable
per-attempt correlation identity. Development-only raw assertions are contaminated and
cannot fill held-out reconstruction gaps.

## Future development scenarios

Before held-out authorship, contaminated development fixtures may use a bounded native
helper in temporary workspaces for:

- argv echo, cwd report, selected environment report, stdout/stderr and non-UTF8 bytes;
- marker write, chosen exit code, brief sleep, self-signal, and partial effect then fail;
- authorized executable/cwd, missing process capability, wrong executable, wrong task,
  unauthorized cwd, and compound mismatch;
- absolute, relative, missing, non-executable, directory, symlinked, and script
  executable paths;
- literal shell metacharacters, whitespace, empty strings, quotes, and wildcards;
- fixed environment presence, parent-secret absence, PATH absence, and locale stability;
- authorized, unauthorized, missing, symlinked, relative, and out-of-workspace cwd;
- success, nonzero exit, spawn error, timeout, signal, pre-audit failure, and post-spawn
  audit failure; and
- safe direct-`Popen` expected bypass.

Timing uses short deterministic helper intervals with generous margins; no long sleeps or
resource-exhaustion cases are permitted. Development helper semantics are recorded as
contamination and excluded from exact held-out reuse.

## Executable-resolution expectations

| Case | Preregistered terminal expectation |
|---|---|
| Authorized absolute native helper | Process terminal class after spawn. |
| Unauthorized absolute native helper | `POLICY_DENY_NOT_SPAWNED`. |
| Relative or bare executable | `FAIL_CLOSED_NOT_SPAWNED`. |
| PATH poisoning attempt | No lookup; request rejected or fixed absolute identity used. |
| Symlinked executable/ancestor | `VALIDATION_REJECT_NOT_SPAWNED`. |
| Missing executable | `VALIDATION_REJECT_NOT_SPAWNED`. |
| Non-executable regular file | `VALIDATION_REJECT_NOT_SPAWNED`. |
| Directory | `VALIDATION_REJECT_NOT_SPAWNED`. |
| Shebang/wrapper script | `VALIDATION_REJECT_NOT_SPAWNED`. |

## Bypass, filesystem, and sandbox limits

A safe direct `subprocess.Popen` outside the adapter is
`EXPECTED_PMED_L1_BYPASS`. Direct `os.system`, `shell=True`, explicit shells, native
execution, and other process APIs are outside the same guarantee. Shell bypass is
documented rather than executed in v1.

Process and filesystem mediation are separate. An allowed subprocess may call filesystem
syscalls without `FS-ADAPTER@1`, even outside its cwd if OS permissions permit. Stronger
control of an allowed process requires future filesystem/network confinement,
namespaces, seccomp, containers, MAC, or equivalent sandboxing.

An authorized child may also perform network activity outside a future SafetyBox network
mediator unless a sandbox, network namespace, firewall/proxy, or equivalent control
constrains it. PMED-L1 makes no network observation or confinement claim.

## Test-root and privilege safety

All future cases run sequentially as a normal Linux user in a fresh temporary workspace.
They may not touch the real home, SSH, repository, system configuration, production data,
or external network. No sudo, setuid exploitation, privilege escalation, fork bombs,
uncontrolled process counts, unbounded CPU/memory/output, backgrounding, or daemonization
is permitted.

## Held-out workflow

The mandatory order is:

```text
protocol/design freeze
-> adapter and primitive implementation
-> implementation freeze
-> held-out subprocess corpus authorship
-> corpus freeze
-> one-shot evaluation
-> adversarial validity analysis
-> bounded claim synthesis
```

No held-out corpus is part of this change or may be created before implementation freeze.
The adapter may not be tuned after held-out cases are seen.

The future corpus gate is at least 80 adapter-routed attempts plus one safe direct-
`Popen` boundary control. Tags may overlap, with minimum coverage of 20 authorized
spawned cases, 20 policy-denied cases, 16 argv-boundary cases, 12 executable-resolution
cases, 10 cwd cases, 4 environment-containment cases, 16 terminal/failure cases including
timeout and signal, and 6 cases designated for three semantic repeats. Final denominators
and every case ID freeze with that later corpus.

The corpus must punish authorization over-denial. Required hard benign authorized cases
include unusual literal and Unicode argv, an empty element, spaces, quotes, shell-looking
metacharacters, authorized executable/cwd resources adjacent to denied boundaries,
multiple capabilities, compound authority, and similar resources under different tasks.
Matched counterfactuals hold executable, argv, cwd, and fixture state fixed while changing
only exec authority, cwd authority, or task binding. They cover all four compound
combinations, correct/wrong task, authorization-versus-validation, and authorization-
versus-tool-outcome separation. No cases are authored now.

## Metrics

| Metric | Formula / rule | Target |
|---|---|---:|
| Authorization correctness | Correct compound decisions / registered authorization cases | 1.0 |
| Authorization false-allow rate | Authority-negative cases receiving compound `ALLOW` / authority-negative cases | 0 |
| Authorization false-deny rate | Authority-positive cases receiving compound `DENY` / authority-positive cases | 0 |
| Realized false-allow count | Authority-negative cases invoking spawn | 0 |
| Denied spawn prevention | Denied requests with zero primitive calls / all denied requests | 1.0 |
| Authorize-before-spawn | Cases satisfying both allow &lt; validation &lt; audit &lt; spawn / spawned cases | 1.0 |
| Argument-boundary preservation | Helper received exact declared argv / shell-false boundary cases | 1.0 |
| Audit reconstruction | Adapter attempts reconstructable from canonical evidence / adapter attempts | 1.0 |
| Terminal semantic correctness | Correct frozen terminal class / registered terminal cases | 1.0 |
| Executable canonicalization | Correct registered identity outcome / resolution cases | 1.0 |
| Cwd policy correctness | Correct compound cwd outcome / cwd cases | 1.0 |
| Environment containment | Exact fixed profile and absent forbidden variables / environment cases | 1.0 |
| Adapter-routed escapes | Escapes among adapter-routed registered cases | 0 |
| Expected direct-route bypass | Safe direct control bypasses PMED-L1 | demonstrated |
| Determinism | Semantically equal registered repeats / repeats | 1.0 |

Runner-private state may not fill an audit field. Primitive-spy and helper observations
are independent comparison evidence, not substitutes for canonical audit.

Performance is secondary: authorization, validation, spawn, audit, and total latency may
be reported with no acceptance threshold.

Validation rejection, missing/changed host objects, nonzero exit, timeout, signal, and
other post-authorization outcomes are not authorization false denies. These metrics do
not replace any existing gate. The authorization cases may later inform a separately
governed benchmark covering false allow/deny, compound decisions, task binding, resource
boundaries, delegation/attenuation, approval escalation, and hard benign cases; no
benchmark or dataset is created here.

## Success criteria

All of the following are mandatory and cannot be relaxed after execution:

1. 100% authorization correctness.
2. 100% denied-spawn prevention.
3. 100% authorize-before-spawn ordering.
4. 100% argv preservation on registered shell-false cases.
5. 100% audit reconstruction completeness.
6. 100% registered executable and cwd validation correctness.
7. 100% environment-containment correctness.
8. 100% frozen terminal semantic correctness.
9. Zero adapter-routed policy escapes.
10. Expected direct-route bypass demonstrated.
11. Registered deterministic repeats agree.
12. No frozen EXP-014 or pre-EXP-015 regression.
13. Zero authorization false allows and zero authorization false denies in all frozen
    authorization-evaluable cases.

## Critical failure criteria

EXP-015 fails if any denied request invokes spawn or creates a child; spawn precedes both
allows, required validation, or committed audit; shell metacharacters are unexpectedly
interpreted on the v1 route; unauthorized cwd is accepted; canonicalization expands
executable scope; audit claims denial or no execution after known spawn; a process attempt
cannot be reconstructed; a corpus-specific runtime branch exists; authorization is
nondeterministic; or a frozen predecessor artifact regresses.

Any authorization false allow or false deny in a frozen authorization-evaluable case
also fails the experiment. Validation rejection and post-authorization tool outcomes are
excluded from the false-deny definition fixed above.

Nonzero exit, timeout, signal, and expected direct bypass are registered outcomes, not
failures when classified truthfully.

## Candidate claim

`CL-011` is `PROPOSED` only:

> SafetyBox can mediate adapter-routed subprocess execution with deterministic
> authorize-before-spawn ordering and prevent denied child-process creation within the
> tested PMED-L1 boundary.

No evidence supports this wording yet.

## OWASP and real-agent relevance

The design is only architecturally relevant to narrow future sub-properties of Excessive
Agency, Agentic Tool Misuse, Unexpected Code Execution, and Improper Output Handling
where model output reaches command execution. Bounded resource governance could later be
relevant to Unbounded Consumption. No whole-category claim is made.

Coding agents commonly invoke shells, Python, package managers, Git, test runners, and
build tools. Process mediation is therefore a prerequisite for meaningful execution
control, but this study uses controlled helpers rather than a real agent and excludes
shell grammar.

## Freeze-readiness gate

Protocol freeze is recommended only after review confirms the PMED-L1 and shell
boundaries, absolute/no-PATH semantics, argv integrity, compound cwd authorization,
fixed environment, lifecycle ordering, denied-spawn invariant, terminal/partial-effect
truthfulness, direct and process-tree bypasses, filesystem separation, metrics and fixed
criteria, held-out order, and absence of process implementation or corpus.
