# ADR-007: Argv-Native Subprocess Mediation Before Shell Mediation

Status: Accepted

Date: 2026-09-24

## Context

SafetyBox has held-out evidence for adapter-routed filesystem mediation at FMED-L1 but no
real subprocess, shell, process-tree, or sandbox control. Filesystem control alone cannot
prevent an agent from launching a program that performs direct filesystem or network
operations outside `FS-ADAPTER@1`.

A direct process invocation and a shell command are materially different interfaces. A
direct invocation selects one executable and passes an ordered argv vector. A shell
interprets a command language containing tokenization, expansion, substitutions,
operators, redirection, pipelines, builtins, subshells, and potentially multiple process
launches. Treating these as one primitive would make identity, authorization, argument
integrity, and effects ambiguous before any evidence exists.

Repository governance requires an ADR because the new design affects trust boundaries,
compound authorization, event ordering, failure semantics, and audit minimization.

## Decision

Design EXP-015 v1 around argv-native direct executable invocation at PMED-L1, equivalent
to `shell=False`. Use one canonical absolute executable identity, one ordered argv tuple,
a separately authorized logical cwd, a fixed minimal non-inherited environment, bounded
timeout/output, empty stdin, and one narrow direct-child spawn primitive.

V1 will:

- reuse `TaskContract`, `Capability`, `TaskContractPolicy`, and `ReferenceMonitor`;
- authorize `process.exec` on the canonical executable and `process.cwd` on cwd;
- compose those distinct ordinary requests through a reviewed generic authorization-core
  extension, never a process-specific allowlist;
- keep capability authority separate from validation, tool outcome, behavior findings,
  risk/anomaly scores, and AI proposals;
- disallow ambient `PATH` lookup, relative executables, symlinked executables, and
  shebang/wrapper scripts;
- preserve argv element boundaries without shell reconstruction;
- require complete authorization, post-allow validation, and committed audit before
  spawn;
- classify nonzero exit, timeout, signal, and post-spawn failure as possibly effectful;
- observe only the direct child; and
- retain direct subprocess and shell routes as explicit PMED-L1 bypass boundaries.

Arbitrary shell command mediation is deferred to a separate future experiment. Process
tree and child-resource confinement are deferred to stronger OS or sandbox boundaries.

## Alternatives considered

- Mediate `shell=True` and `shell=False` through one command-string interface.
- Authorize a pretty-printed shell command reconstructed from argv.
- Permit ambient `PATH` search or parent-environment inheritance.
- Authorize only the executable and accept arbitrary cwd.
- Treat an allowed child as transitively confined.
- Implement OS/container confinement before an adapter-level experiment.

## Consequences

### Positive

- Executable identity and argv boundaries are deterministic and mechanically testable.
- PATH poisoning and shell-metacharacter reinterpretation are excluded by construction.
- Existing task/capability authority remains the canonical authorization path.
- False-allow and false-deny analysis can use authority labels without conflating
  validation rejection or child failure.
- Denied-spawn prevention and authorize-before-spawn ordering have a narrow primitive
  boundary suitable for spies and fault injection.
- Failure and audit semantics can distinguish no-child failures from possibly effectful
  post-spawn outcomes.

### Negative

- Common coding-agent shell workflows are not supported by v1.
- Executable flags and code passed as argv are not semantically authorized.
- An allowed direct child can spawn descendants or perform direct filesystem/network
  effects.
- Rejecting symlinked executables and scripts narrows practical compatibility.
- A fixed minimal environment and no stdin exclude legitimate programs.
- The current same-action `CompoundAuthorizer` needs a generic distinct-action extension
  before process-adapter implementation.

### Risks

- Validation-to-spawn replacement races remain unsolved.
- Powerful allowed executables can interpret dangerous argv without violating argument
  boundaries.
- Timeout or signal termination may leave direct or descendant side effects.
- Direct process APIs bypass PMED-L1 unless integration enforces routing.
- Audit minimization prevents plaintext argv reconstruction by design; evidence relies on
  ordered commitments and request-side verification.

## Research impact

This decision governs EXP-015 protocol version 1 at Level 0. It permits protocol/design
freeze before any process adapter, helper, held-out corpus, or subprocess experiment. It
does not support CL-011, RTM-2, a production claim, complete mediation, or any whole OWASP
category.
