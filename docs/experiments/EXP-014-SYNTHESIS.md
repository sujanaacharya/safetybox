# EXP-014 Synthesis

## What changed from simulation to real-tool mediation?

Before EXP-014, SafetyBox's enforcement evidence stopped at logical protected-tool APIs
and synthetic worlds. EXP-014 exercised `FS-ADAPTER@1` against actual files,
directories, symlinks, hard links, renames, reads, writes, and partial effects in fresh
Linux temporary filesystems. The adapter bound canonical logical paths to real primitive
calls and emitted one in-process audit lifecycle around them.

This is a material evidence change: real side effects, object metadata, failure states,
and independent filesystem snapshots replaced a purely logical simulator. It is not a
change to a real agent deployment or process-confinement boundary.

## What did EXP-014 establish?

Within `EXP-014-CORPUS@1` and FMED-L1:

- 94/94 adapter-routed scenarios produced the registered terminal outcome;
- independently derived authorization matched 91/91 labels and adapter decisions;
- 19/19 policy-denied mutations invoked no protected primitive and left independently
  observed filesystem state unchanged;
- 9/9 policy-denied read/list/stat cases invoked no protected retrieval primitive and
  exposed no protected value in the evaluated result, safe-error, or serialized
  audit/event channels;
- a separate protocol-derived canonicalizer matched 70/70 registered scope cases;
- all tested audit records were field-reconstructable and semantically consistent with
  the harness's primitive/state observations; and
- real static symlink/hard-link fixtures and compound rename cases behaved as registered.

This supports RTM-1 and Level 4 evidence for these named real-filesystem sub-properties.
It does not raise the whole SafetyBox system or an OWASP category to Level 4.

## What did it not establish?

EXP-014 does not establish complete mediation, direct-API prevention, race safety,
concurrency safety, inode confinement, durable or tamper-evident audit, cross-platform
behavior, production performance, real-agent integration, or production readiness.

The perfect aggregate result also overstates uniform evidence quality. Most cases are
moderate rather than adversarial; only 11/48 pairs remain `STRONG` after post-run review;
injected failure enums and fixture types cue conformance outcomes; rare categories have
denominators as low as two; and protocol, implementation, and corpus came from the same
project process.

## Why is FMED-L1 useful?

FMED-L1 makes an important engineering property testable: if an integration routes a
filesystem call through the typed adapter, SafetyBox can bind task/action/resource
authority to a real effect, place authorization before validation/execution, report
failure uncertainty explicitly, and emit reconstructable evidence. That is substantially
stronger than simulated tool behavior.

It also exposes a reusable adapter architecture: typed request and result models,
logical-to-physical mapping, canonical authorization reuse, explicit failure semantics,
primitive instrumentation, and a canonical audit envelope.

## Why is FMED-L1 insufficient for universal enforcement?

FMED-L1 assumes the call enters the adapter. Direct `os.*`, `pathlib`, shell, native code,
inherited descriptors, or a compromised process can bypass it. The current validator
checks pathnames and later operates on pathnames, leaving TOCTOU windows. The evaluation
is sequential, same-process, and in-memory; it cannot support claims about races,
complete interception, audit durability, or hostile deployment.

The two direct-route controls make that limitation empirical rather than rhetorical.
SafetyBox becomes an enforcement boundary only when an integration or sandbox ensures
relevant effects cannot take an alternate route.

## Supported claim

> On `EXP-014-CORPUS@1`, frozen `FS-ADAPTER@1` correctly produced the registered terminal
> outcome in all 94 adapter-routed held-out scenarios in an isolated temporary Linux
> filesystem at FMED-L1. It prevented a wrapped primitive call and independently observed
> state change in 19/19 policy-denied mutations; returned no protected value and invoked
> no protected retrieval primitive in 9/9 policy-denied read/list/stat cases, with no
> sentinel found in evaluated result, safe-error, or serialized audit/event channels; and
> satisfied tested ordering, reconstruction-field, and truthfulness checks in 94/94
> adapter attempts.

## What should come next?

The strongest next implementation milestone is shell/subprocess mediation, followed by
HTTP/network mediation and an MCP proxy. Subprocess mediation is the next scientific
dependency and reuses the adapter's request binding, authorization, ordering, failure,
and audit architecture while addressing a major direct-effect route.

Process-level filesystem hardening remains important, particularly descriptor-bound
`openat`/`openat2`, `O_NOFOLLOW`, dirfd-relative resolution, race testing, and sandboxing,
but it should be treated as a distinct FMED-L2/3 hardening track rather than inferred from
the 20/20 static symlink result.
