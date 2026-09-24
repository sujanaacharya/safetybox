# Real Subprocess Threat Model

**Artifact:** `REAL-SUBPROCESS-THREAT-MODEL@1`
**Status:** preregistered design extension; no implementation or evidence
**Experiment:** [EXP-015](../experiments/EXP-015-real-subprocess-mediation.md)

## Assets and security objective

Assets are task-scoped process authority, executable and cwd identity, argv boundaries,
parent secrets, isolated test state, audit truthfulness, and the absence of a child for a
denied request. The v1 objective is narrow: correctly mediate one adapter-routed direct
child at PMED-L1. It is not to make an allowed process safe or confined.

## Attacker and trust assumptions

The agent controls executable text, argv, cwd, timeout request, and descriptive command
text. Child stdout/stderr are adversarial data. The authorizer, future adapter,
canonicalizers, primitive, audit recorder, and harness are trusted for the experiment.
The test runs sequentially as a normal Linux user in a fresh temporary workspace.

Kernel compromise, SafetyBox administrator compromise, harness mutation, sudo/setuid
exploitation, hostile concurrent mutation, and production resources are excluded.

## Threat register

| Threat | V1 treatment | Residual boundary |
|---|---|---|
| Command injection through shell metacharacters | Evaluated as literal argv under `shell=False`; no string reconstruction. | Executable-specific interpretation of an argument is not shell-boundary proof. |
| Shell reinterpretation | Shell grammar is excluded and direct shell routes are explicit bypasses. | Requires a separate shell experiment. |
| PATH poisoning | Ambient PATH lookup and child `PATH` are prohibited. | Alternate direct routes may still search PATH. |
| Working-directory executable shadowing | Relative/bare executables are rejected. | Allowed child may perform its own searches. |
| Executable substitution | Absolute identity, post-allow no-symlink validation, exact primitive binding. | Validation-to-exec TOCTOU remains unsolved. |
| Symlinked executable | Reject any symlink component after allow. | Races and bind-mount/namespace behavior are untested. |
| Missing, directory, non-executable object | Registered validation rejection with no spawn. | Platform-specific loader failures remain possible. |
| Wrapper/shebang interpreter behavior | Wrapper/shebang executable is excluded in v1. | Interpreters explicitly allowed as native binaries remain powerful. |
| Argument boundary loss | Exact helper-observed tuple comparison; hashes and lengths in audit. | Child-specific option parsing is outside policy. |
| Cwd manipulation | Logical canonical cwd plus independent `process.cwd` authorization and post-allow validation. | Child can later `chdir`; OS filesystem scope is not confined. |
| Environment poisoning | New fixed minimal environment; no inheritance, caller variables, or PATH. | Loader/platform variables outside the explicit environment require validation. |
| Secret inheritance | Parent variables and inherited descriptors are excluded. | Process memory, OS services, and alternate routes are not addressed. |
| Unauthorized child process | Deny must cause zero protected primitive calls and no adapter-created child. | Direct subprocess APIs bypass PMED-L1. |
| Shadow process allowlist | Prohibited; `process.exec` and `process.cwd` must use the shared task/capability authorization core. | Shared compound layer needs a distinct-action extension before adapter work. |
| Authorization over-denial | Hard benign and matched authority counterfactuals measure false denies separately from validation/tool failure. | Finite held-out cases cannot establish universal low false-denial behavior. |
| Behavior signal becomes authority | B4/context/risk/AI signals cannot silently grant or deny hard authority. | Future containment policy needs separate governance and evidence. |
| Descendant process spawning | First-class limitation; not treated as direct-child success evidence. | Needs process groups, cgroups, namespaces, sandboxing, or equivalent. |
| Timeout partial effects | Timeout classified effect-possible; TERM then KILL direct child. | Descendants and completed side effects may remain. |
| Nonzero exit or signal | Classified as execution with possible effects. | No rollback or broad state inventory. |
| Audit loss before spawn | Fail closed; no primitive call. | Audit infrastructure remains in process and non-durable. |
| Audit loss after spawn | Indeterminate execution-possible result. | Complete reconstruction may be lost and fails the experiment. |
| Direct subprocess bypass | Safe direct `Popen` boundary control expected to bypass. | PMED-L2/3/4 work is needed to reduce bypass. |
| Shell bypass | `os.system`, `shell=True`, and explicit shells are outside v1. | Separate routing/interception and grammar policy needed. |
| Process-tree escape/daemonization | Excluded and disclosed. | Requires OS-level lifecycle confinement. |
| Filesystem effects by child | Marker fixtures may observe selected effects. | `FS-ADAPTER@1` does not intercept child syscalls. |
| Network activity by child | Prohibited in fixtures, not technically confined. | Needs network namespace/firewall/proxy mediation. |
| Signals | Direct-child signal terminal cases may be tested on Linux. | Signal races, groups, and cross-platform semantics are excluded. |
| Resource exhaustion/fork bomb | Dangerous cases prohibited. | CPU, memory, process, output and time budgets remain future work. |
| Privilege transition/setuid | Tests run normal-user and reject privilege research. | No privilege-boundary evidence. |
| Native execution bypass | Direct native APIs remain PMED-L1 bypasses. | Needs process/OS enforcement. |

## Shell attack-surface expansion

A shell converts untrusted text into a program. It can select multiple executables,
perform redirections before a command body, substitute output into new tokens, expand
variables and globs, invoke builtins without a child matching the apparent command, and
create pipelines/subshells/background jobs. Consequently, executable-plus-argv policy
cannot be extrapolated to a shell string. Shell support requires its own grammar,
canonicalization, compound-effect, audit, and bypass design.

## Process and filesystem boundary

Process authorization answers whether one executable may be started from one cwd. It
does not authorize or mediate every operation performed after start. In particular, an
allowed child can call filesystem APIs without entering `FS-ADAPTER@1`. This means
filesystem and subprocess mediation are complementary but not transitively composed.

A future containment architecture may need namespaces, seccomp, cgroups, containers,
mandatory access control, filesystem confinement, and network confinement. None is
implemented or evaluated by this design.

## Test safety

Future helpers and direct-route controls must remain inside temporary roots and avoid the
real home, SSH material, repository changes, production resources, external network,
privilege changes, long waits, fork bombs, and unbounded output. Signal and timeout cases
use short deterministic helpers with generous margins and direct-child cleanup.

## OWASP relevance

The design is architecturally relevant to narrow sub-properties of Excessive Agency,
Agentic Tool Misuse, Unexpected Code Execution, and Improper Output Handling where model
output reaches execution. Later bounded CPU/memory/process/time governance may be
relevant to Unbounded Consumption. This Level 0 threat model establishes no prevention
evidence and no whole-category coverage.
