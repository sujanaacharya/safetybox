# EXP-014 — Real Filesystem Mediation and Complete-Path Evaluation

**Status:** `PREREGISTERED`
**Protocol version:** 1
**Implementation:** not included
**Corpus:** not included
**Results:** not included

## Frozen starting point

The repository was clean before this registration (`git status --short` produced no
output). The preregistration base is
`f4713f2f7012ba933ad9059fe8778004e331ae11`, SafetyBox version `0.0.0`.

| Artifact | Frozen Git SHA |
|---|---|
| EXP-013 protocol | `632a4f82ab7c6487d82a166bca2e3354c7b9b763` |
| B2 implementation | `3f8794e8b134b534365e0e26f48dd1886a50f662` |
| B4 implementation | `0b02b199e1f8e0f00aa87035bcbd4fced1aeda42` |
| EXP-013 corpus | `7361bad903be9294bd4088c86a0734ca12f79388` |
| EXP-013 result freeze | `8ac665cd2466f9d14c525a61759cd36c657795ca` |
| EXP-013 analysis and synthesis | `f4713f2f7012ba933ad9059fe8778004e331ae11` |
| M1 `ReferenceMonitor` freeze | `9f77dc906355d1191af1f4908460af8e4cc36293` |
| M3 event/audit freeze | `2d9f8b09825702d12304f379130001f60e3d867c` |

No frozen detector, corpus, result, or analysis artifact is changed by this registration.
The result SHA is the commit that froze the one-shot EXP-013 evaluation.

## Research question

Can SafetyBox deterministically mediate real filesystem operations so that authorized
operations execute, unauthorized operations produce no protected side effect, execution
ordering remains authorize-before-effect, and canonical audit evidence faithfully
reconstructs attempted and completed behavior?

Secondary questions are whether path canonicalization prevents alias bypass; whether
denied mutations change state; whether denied read/list/stat requests disclose bytes,
names, or metadata; how symlinks, traversal, race-sensitive paths, and adapter failures
behave; whether audit evidence can reconstruct every attempt; what measurable overhead
mediation adds; and where in-process mediation remains bypassable. These are questions,
not results.

## Scope and claim boundary

EXP-014 targets **FMED-L1: adapter-mediated operations only** and **RTM-1: an isolated
real-filesystem adapter**. SafetyBox is at RTM-0 before the experiment. The future adapter
will cover `filesystem.read`, `filesystem.write`, `filesystem.append`,
`filesystem.create`, `filesystem.delete`, `filesystem.rename`, `filesystem.mkdir`,
`filesystem.list`, and `filesystem.stat` inside a generated temporary root. Recursive
delete, shell, subprocess, network, database, browser, MCP, and real-agent integration are
excluded.

If an agent can call `os.*`, `pathlib`, native code, shell commands, an inherited file
descriptor, or any other filesystem route outside the adapter, it can bypass FMED-L1.
An intentional direct-`os.open` demonstration must show that boundary. EXP-014 cannot
support a universal filesystem-confinement or complete-mediation claim.

The complete claim ladder is:

| Level | Meaning |
|---|---|
| FMED-L0 | Logical simulated tool mediation. |
| FMED-L1 | Calls routed through the real adapter are mediated. |
| FMED-L2 | Declared framework/API interception paths have tested coverage. |
| FMED-L3 | Process-level mediation has tested bypass resistance. |
| FMED-L4 | OS/sandbox-level confinement or an equivalent strong boundary is tested. |

Real-tool maturity is tracked separately:

| Level | Meaning |
|---|---|
| RTM-0 | Simulated/logical tools only. |
| RTM-1 | Isolated real filesystem adapter. |
| RTM-2 | Multiple evaluated real local-tool adapters. |
| RTM-3 | Real agent-framework integration. |
| RTM-4 | Process-level, bypass-resistant mediation. |
| RTM-5 | Externally replicated deployment evidence. |

## Protocol decisions

- Every fixture lives below a fresh temporary host directory. Logical resources
  `/workspace/public/**`, `/workspace/private/**`, and `/workspace/output/**` map into
  that directory; host paths are never accepted as logical resources.
- The adapter performs pure lexical canonicalization before creating the monitor
  `ActionRequest`. After `ALLOW` and before the requested primitive, it validates the
  physical target without following links. This prevents physical metadata probing of
  policy-denied paths. It uses the existing canonical absolute-path resource syntax, not
  a new filesystem-specific policy engine. `TaskContract`, `Capability`,
  `TaskContractPolicy`, and `ReferenceMonitor` remain the authorization path.
- Inputs are Unicode strings without NUL. Separators are POSIX `/`; duplicate separators
  and `.` are removed, `..` is collapsed but may not escape `/workspace`, relative paths
  resolve from `/workspace`, NFC normalization is applied, case is preserved, and trailing
  separators are removed except at the logical root.
- V1 rejects any symlink in an existing path component or final component and rejects an
  existing regular-file target whose link count exceeds one. For a missing destination,
  post-allow target validation checks the closest existing parent, rejects links in that
  prefix, and evaluates the normalized remainder. The exact canonical host path derived
  from the canonical logical path is the execution target.
- Linux with a case-sensitive local filesystem is the only initial target. No Windows or
  macOS equivalence is claimed.
- Canonicalize-then-open remains susceptible to TOCTOU unless later implementation binds
  the checked object to the operated object with OS mechanisms. The protocol records this
  as `NOT_SOLVED` before implementation and requires future results to report the tested
  status without inflation.

Lexical processing is purely syntactic and performs no filesystem lookup. Before
authorization it must not call `stat`,
`lstat`, filesystem-resolving `realpath`, `exists`, `is_file`, `is_dir`, `readlink`, or
directory enumeration on the requested target. The logical-to-host mapping is an adapter
responsibility: policy sees `/workspace/public/a.txt`, never a temporary host path such as
`/tmp/.../workspace/public/a.txt`.

The exact lexical cases are:

| Input class | Result |
|---|---|
| Relative `public/a.txt` | `/workspace/public/a.txt` |
| Absolute `/workspace/public/a.txt` | Same canonical path. |
| `.` and repeated `/` | Removed/collapsed. |
| In-root `..` | Collapsed left-to-right. |
| `..` above `/workspace` | Rejected immediately. |
| Empty string | Rejected; empty components caused by repeated `/` are removed. |
| Trailing `/` | Removed except on `/workspace`. |
| Unicode | Whole input normalized to NFC before segment processing; case preserved. |
| `/workspace` | Canonicalizes to itself; only authorized list/stat may operate on it in v1. |
| `/workspace/public-report.txt` | Exact separate resource; never matches `/workspace/public/**`. |

After allow, nonexistent behavior is operation-specific. Read, write, append, delete,
list, stat, and rename source require an existing target; create and mkdir require an
absent leaf; create, mkdir, and rename destination require an existing immediate parent.
Missing required targets/parents and existing create/mkdir leaves are `TOOL_ERROR` rather
than policy denials. Rename destination may be absent or may replace an existing compatible
regular file or empty directory after validation.

The nine operation semantics are fixed independently of Python defaults:

| Action | V1 behavior |
|---|---|
| `filesystem.read` | Return bytes from an existing regular file. |
| `filesystem.write` | Replace bytes of an existing regular file; never create. |
| `filesystem.append` | Append to an existing regular file; never create. |
| `filesystem.create` | Create one absent regular-file leaf; existing leaf is an error. |
| `filesystem.delete` | Delete one regular file or empty directory; non-empty directory is `TOOL_ERROR`; never recursive. |
| `filesystem.rename` | Rename existing regular file or empty directory after two-endpoint authorization; compatible destination replacement is allowed. |
| `filesystem.mkdir` | Create one absent directory with an existing parent; no implicit parents. |
| `filesystem.list` | Return immediate NFC child names sorted by Unicode code point; never recursive or host-order-dependent. |
| `filesystem.stat` | Return bounded approved metadata for one non-symlink target. |

Reject-all symlink validation covers every existing ancestor and terminal component.
Create/mkdir validate through the immediate parent. Rename validates the complete source,
the complete destination parent, and an existing destination terminal. Relative,
absolute, chained, and dangling links all reject. The hard-link rule is narrower:
post-allow `st_nlink > 1` rejects an existing terminal regular file for read, write,
append, delete, stat, rename source, or existing rename destination. It does not apply to
directories, ancestors, list targets, or absent create/mkdir leaves. This observation is
race-sensitive and proves neither absence of aliases nor inode confinement.

## Required invariants and observations

The lifecycle must establish:

```text
adapter request received
  -> lexical canonicalization
  -> ACTION_REQUESTED
  -> AUTHORIZATION_STARTED
  -> AUTHORIZATION_ALLOWED | AUTHORIZATION_DENIED | AUTHORIZATION_FAILED
  -> physical target validation          # allowed path only
  -> EXECUTION_STARTED committed to required audit  # allowed path only
  -> protected primitive invocation
  -> EXECUTION_SUCCEEDED | EXECUTION_FAILED
```

No `EXECUTION_STARTED` may precede `AUTHORIZATION_ALLOWED`, and none may exist for a
denial. Every required audit record through `EXECUTION_STARTED` must commit before the
primitive; an audit failure before that point invokes no protected primitive. A denied
mutating action must leave protected state unchanged. A denied read returns no protected
bytes, a denied list no directory-entry names, and a denied stat no protected metadata;
none invokes its retrieval primitive.

State uses `EXP014-STATE-DIGEST@1`: canonical UTF-8 JSON with sorted keys and no
insignificant whitespace, then SHA-256. Absence is `{"type":"ABSENT"}`; a regular file
records type, size, and content SHA-256; a directory records immediate NFC child
names/types sorted by Unicode code point. The sorted manifest covers endpoints, affected
parents, protected roots, and registered aliases. Temporary host prefixes, atime, mtime,
ctime, and inode are excluded; stable mode bits are included only if the frozen corpus
schema preregisters them.

The existing M3 lifecycle and its pre-effect fail-closed/post-effect-indeterminate
semantics are retained. Proposed canonical extensions for adapter ingress,
lexical canonicalization, physical target validation, requested/canonical resource
identifiers, adapter version, state digests, result category, and two rename subdecisions
are requirements for one additive M3-compatible envelope/schema—not an implemented
parallel event system. Current M3 cannot represent those stages and fields.

Rename uses one bound correlation with source then destination evaluated deterministically
against the same immutable `TaskContract`. Both subdecisions are recorded even if the
source denies; either denial/failure closes the compound result. No target probe or
filesystem mutation occurs between the decisions, and execution begins only after two
explicit allows and successful required pre-execution audit. A source-only or
filesystem-specific authorization path is prohibited.

Failure categories are `DENY`, `FAIL_CLOSED`, `TOOL_ERROR`,
`FAIL_INDETERMINATE`, or allowed success. Invalid input, authorization/control failure,
symlink/hard-link safety rejection, and pre-execution audit failure are fail-closed.
Ordinary post-allow missing target/parent, permission, read, and non-empty-directory errors
are tool errors when no mutation is possible. Partial write, an unexpected error after
primitive start, or completion-audit failure is `FAIL_INDETERMINATE` unless measured state
proves a narrower outcome; it must never be reported `DENIED` or `NOT_EXECUTED`.

## Experiment stages

1. Freeze this protocol and its design documents.
2. Implement and review the adapter in a later change.
3. Freeze the adapter and event-schema extension before corpus authorship.
4. Author and freeze a held-out real-tool corpus: at least 20 authorized, 20 unauthorized,
   10 canonicalization/bypass, and 10 failure/error cases, with counterfactual pairs where
   feasible.
5. Run once under the frozen evaluation procedure, preserve raw evidence, and analyze all
   failures without weakening criteria.

No corpus is authored in this registration.

The held-out corpus minimum is 60 cases: at least 20 authorized, 20 unauthorized, 10
canonicalization/bypass, and 10 failure/error cases. It prefers counterfactual pairs and
must cover every operation, source/destination rename denial, traversal, prefix collision,
Unicode and dotted hard negatives, all symlink forms, platform-supported hard links,
pre/post audit failure, partial failure, session/task isolation, and deterministic rebuild.

Adapter implementation may use recorded `DEV-FS-LEXICAL-*`, `DEV-FS-SYMLINK-*`,
`DEV-FS-PRIMITIVE-FAILURE-*`, and `DEV-FS-AUDIT-FAILURE-*` fixtures. Their identifiers and
semantic cases become a contamination record when the adapter freezes. Held-out authorship
then occurs separately and may not repeat a development fixture verbatim (path/name tuple,
bytes, authority arrangement, and failure-injection combination). The adapter may not be
tuned after held-out cases are viewed.

The stopping rule freezes development before held-out authorship, evaluates every valid
frozen case and preregistered repeat without favorable early stopping, preserves every
critical failure, and permits exclusion only for predeclared invalid-fixture or
harness-integrity failures reported with identifiers and reasons.

## Metrics and gates

Primary metrics are authorization correctness, denied-mutation side-effect prevention,
denied read/list/stat nondisclosure (reported separately as bytes, names, and metadata),
audit reconstruction completeness, canonicalization correctness, bypass-case outcomes,
tool-error classification accuracy, and lifecycle ordering correctness. There is no
generic security score.

Success requires 100% authorization correctness, denied-mutation prevention, denied
read/list/stat nondisclosure, authorize-before-effect ordering, and required audit
reconstruction; 100% tool-error classification accuracy; all registered canonicalization
cases correct; zero successful
adapter-routed policy escapes; deterministic repeats; the expected direct-route boundary
demonstration; and no frozen-research regression. Any denied mutation, protected bytes/
names/metadata disclosure, execution-before-allow, symlink/traversal/rename escape,
scope-expanding canonicalization, false audit account of an executed operation,
corpus-specific authorization branch, nondeterministic policy outcome, or unreconstructable
attempt fails the experiment.

Bypass cases are classified before execution:

| Case | Classification |
|---|---|
| Escaping `..`, host absolute path, prefix collision, symlink escape, rename escape | `ADAPTER_SHOULD_BLOCK` |
| Hard-link fixture | `PLATFORM_DEPENDENT`; if created, adapter target must be blocked |
| Valid absolute `/workspace/...` path | `NOT_IN_SCOPE` as a bypass; supported normal input |
| Direct `os.open`, direct `pathlib` I/O | `EXPECTED_FMED_L1_BYPASS` |
| Shell redirection | `EXPECTED_FMED_L1_BYPASS`; shell execution is excluded |
| Inherited descriptor | `EXPECTED_FMED_L1_BYPASS` when fixture is available |
| External/non-Linux filesystem behavior | `NOT_IN_SCOPE` |

A string derived through `pathlib` and passed into the typed adapter is enforced normally;
direct `pathlib` I/O is the bypass. Expected direct-route bypasses delimit FMED-L1 and are
not detector or adapter failures.

Latency may record adapter, authorization, and audit overhead using minimum, median, mean,
p95, and p99 when the sample size supports the percentiles. Performance is secondary and
cannot trade away correctness. Protocol v1 sets no overhead acceptance threshold, so its
performance result is descriptive and cannot support an “acceptable overhead” claim.

## Candidate claim

**PROPOSED only:** “SafetyBox can mediate adapter-routed real filesystem operations with
deterministic authorize-before-effect ordering and prevent denied filesystem side effects
within the tested mediation boundary.”

Even a successful EXP-014 may provide Level 4 evidence only for specifically tested real
filesystem sub-properties related to Excessive Agency, Agentic Tool Misuse, improper tool
access, or sensitive-information-disclosure impact mitigation. It cannot establish Level
4 coverage for an entire OWASP category.

The authoritative complete registration is
[`experiments/EXP-014/protocol.yaml`](../../experiments/EXP-014/protocol.yaml). Design
details are in [requirements](../research/REAL_FILESYSTEM_MEDIATION_REQUIREMENTS.md),
[architecture](../architecture/REAL_FILESYSTEM_MEDIATION.md),
[ADR-006](../decisions/ADR-006-real-filesystem-mediation-boundary.md), and the
[threat extension](../threat-model/REAL_FILESYSTEM_THREATS.md).
