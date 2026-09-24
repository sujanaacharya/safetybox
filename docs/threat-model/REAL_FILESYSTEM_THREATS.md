# Real Filesystem Threat Extension

**Status:** additive pre-implementation threat analysis for
[EXP-014](../experiments/EXP-014-real-filesystem-mediation.md)

This document extends the existing threat model without rewriting frozen scenarios. It
defines the threats the first real-filesystem protocol must test and the boundary it must
report. No mitigation listed here is currently implemented.

## Boundary

The protected object is a deterministic temporary filesystem fixture mapped to logical
`/workspace`. The adapter, canonicalizer, policy engine, audit recorder, and harness are
trusted. Agent requests, all requested paths and arguments, filenames, file contents, and
symlink targets are untrusted. File content is data and cannot grant authority.

FMED-L1 assumes calls enter the adapter. Direct Python filesystem APIs, native code,
shells, inherited descriptors, or other unwrapped routes remain bypasses. EXP-014 must
demonstrate one such direct route rather than conceal it.

## Threats and required evidence

| Threat | Attack | Required future control/evidence | Residual boundary |
|---|---|---|---|
| Path traversal | `..`, duplicate separators, or relative paths escape scope. | Deterministic normalization; containment and counterfactual tests. | TOCTOU remains separate. |
| Prefix collision | `/workspace/public-report.txt` is mistaken for `/workspace/public/**`. | Component-aware scope matching and hard negatives. | Depends on canonical M2 semantics. |
| Host/logical confusion | Caller supplies the temporary host path or another absolute path. | Accept only logical `/workspace`; never authorize ephemeral host prefixes. | Host access outside adapter remains possible at FMED-L1. |
| Unicode/path confusion | Equivalent or lookalike spellings receive inconsistent policy. | NFC policy, exact executed mapping, Unicode hard negatives, platform manifest. | Confusable characters are distinct; non-Linux platforms untested. |
| Symlink escape | Authorized spelling resolves to a denied file or parent. | Reject all existing symlinks without following; exercise relative, absolute, chained, dangling, and parent links. | Swap race not solved by a pre-check. |
| TOCTOU/symlink swap | Checked entry is replaced before use. | Classify honestly; later descriptor-relative/OS binding and race tests if implemented. | `NOT_SOLVED` before implementation. |
| Hard-link alias | Authorized path names an inode also reachable under a denied path. | V1 rejects post-allow `st_nlink > 1` on existing terminal regular files for read/write/append/delete/stat and rename source/existing destination; exercise platform-permitted aliases. | One observation cannot prove no alias exists at execution time; the check is race-sensitive and not inode confinement. |
| Rename escape | Authorized source moves to denied destination, or denied source enters allowed namespace. | Canonicalize and authorize both endpoints; bind both to one primitive. | Atomicity limited to recorded filesystem semantics. |
| Delete overbreadth | Write authority or recursive behavior removes undeclared entries. | Separate delete action; no recursive delete; parent snapshots. | Empty-directory deletion only in v1. |
| Protected-read disclosure | Denied read/list/stat returns bytes, names, metadata, or error details. | Result inspection plus primitive spy; nondisclosure metric. | Side channels and external caches excluded. |
| Partial write | Failure leaves changed bytes or temporary entries. | Fault injection and broad post-state snapshot; indeterminate outcome when needed. | Rollback is not assumed. |
| Audit loss before effect | Side effect occurs without required pre-execution evidence. | Required audit failure closes before primitive; invocation spy and state snapshot. | Audit durability remains outside M3. |
| Audit loss after effect | Operation happens but terminal evidence is unavailable. | Report `FAIL_INDETERMINATE`; never report denial/rollback. | Full reconstruction may fail and therefore fail EXP-014. |
| Context mismatch | Session/task decision is reused across another context. | Bound IDs, task mismatch denial, per-session sequencing and isolation tests. | Authenticated cross-process identity is not provided at FMED-L1. |
| Direct API bypass | Agent calls `os.open`, `pathlib`, native code, shell, or reused descriptor. | Explicit boundary demonstration and no complete-mediation claim. | Requires FMED-L2/3/4 architecture to mitigate. |
| Corpus overfitting | Adapter recognizes test names or expected outcomes. | Freeze before held-out authoring; prohibit corpus branches; inspect code. | Finite corpus cannot prove exhaustive correctness. |

Pre-authorization lexical processing is an information boundary, not a physical
validation phase. It must not use `stat`, `lstat`, filesystem-resolving `realpath`,
`exists`, `is_file`, `is_dir`, `readlink`, or directory enumeration on the requested
target. Otherwise a denied read/list/stat could disclose existence, type, link, metadata,
or membership information before policy runs.

Bypass scoring distinguishes control failure from scope. Escaping traversal, host paths,
prefix collision, symlink escape, and rename escape are `ADAPTER_SHOULD_BLOCK`.
Hard-link fixture creation is `PLATFORM_DEPENDENT`, with blocking required once created.
Direct `os.open`, direct `pathlib` I/O, shell redirection, and inherited-descriptor I/O are
`EXPECTED_FMED_L1_BYPASS`; they delimit FMED-L1 and are not detector failures. Valid
absolute logical paths are normal inputs, and external/non-Linux filesystem behavior is
`NOT_IN_SCOPE`.

## Abuse cases

The held-out plan must include matched cases in which only one security-relevant property
changes: a path crosses the root, a source or destination capability is removed, a normal
component becomes a symlink, a task ID changes, or a similar prefix replaces a descendant.
Legitimate hard negatives include nested authorized directories, dotted and Unicode
filenames, in-scope renames, and nonexistent in-scope files. These cases distinguish safe
normalization from blanket rejection.

## Impact statements

A denied mutation that changes any protected state is a critical invariant violation. A
denied read that returns protected content is a disclosure even if state is unchanged.
An execution-start event before allow is a control-order violation even if the primitive
later fails. A missing completion record after a known effect is an audit failure, not
proof that the effect did not occur.

## Relationship to existing threats

This extension operationalizes existing resource-aliasing, interception-bypass,
adapter/TOCTOU, audit-loss, and cross-task concerns for one filesystem adapter. It does
not change `TS-001` through `TS-015`, establish new threat outcomes, or bring kernel and
administrator compromise into scope.
