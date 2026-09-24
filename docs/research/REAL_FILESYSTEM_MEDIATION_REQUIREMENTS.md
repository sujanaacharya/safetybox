# Real Filesystem Mediation Requirements

**Artifact:** `REAL-FILESYSTEM-MEDIATION-REQUIREMENTS@1`
**Status:** preregistered design requirements; not implemented
**Experiment:** [EXP-014](../experiments/EXP-014-real-filesystem-mediation.md)

## Purpose and language

These requirements define what SafetyBox must prove before making a bounded claim about
real filesystem mediation. “Must” is a future implementation/evaluation requirement, not
a statement of current behavior. Repository governance specifies the global `REQ-NNN`
format; `REQ-001` through `REQ-032` are allocated here after confirming that no canonical
global requirement record was already allocated. Historical `REQ-CTX-*` identifiers are
not changed.

The experiment targets FMED-L1 only: calls routed through one adapter in an isolated test
root. Requirements do not imply complete mediation, OS confinement, production readiness,
or real-agent integration.

## Scope and functional requirements

### REQ-001 — Bounded mediation claim

Evaluation must report only adapter-routed behavior at FMED-L1. It must not describe the
adapter as universal filesystem mediation or confinement.

### REQ-002 — Isolated temporary root

Every test must create a fresh temporary host root and map the logical `/workspace`
namespace into it. No operation may target a real home directory, SSH material, system
file, production data, repository secret, or path outside that root.

### REQ-003 — Closed operation set

V1 must expose only `filesystem.read`, `filesystem.write`, `filesystem.append`,
`filesystem.create`, `filesystem.delete`, `filesystem.rename`, `filesystem.mkdir`,
`filesystem.list`, and `filesystem.stat`. Each operation must have typed arguments and the
semantics stated in the protocol. Recursive list, recursive delete, implicit parent
creation, shell, network, database, browser, and MCP operations are excluded.

`create` requires an absent leaf. `write` and `append` require an existing regular file
and never create a missing file. `mkdir` requires an absent leaf and an existing immediate
directory parent. These rules, rather than language-library open modes, define behavior.

### REQ-004 — Operation distinctions

Action names must retain privilege distinctions. In particular, write must not imply
append, create, delete, rename, or mkdir, and read must not imply list or stat unless an
explicit existing policy deliberately grants each action.

### REQ-005 — Trusted computing base declaration

The evaluated trusted base must be limited to the policy engine, adapter,
canonicalization logic, canonical audit recorder, and deterministic test harness. Agent
requests, paths, path aliases, names, contents, symlink targets, and user-controlled
arguments must be treated as untrusted.

### REQ-006 — File content is data

No bytes read from a file, filename, metadata value, or directory entry may become a
SafetyBox instruction, capability, authorization rule, or trusted context merely because
the adapter observed it.

### REQ-007 — Reuse canonical authorization

The adapter must translate a typed operation into the existing `ActionRequest` action and
resource model and use `TaskContract`, `Capability`, `TaskContractPolicy`, and
`ReferenceMonitor`. It must not introduce a filesystem-specific allow path or make an
authorization decision from corpus identifiers.

### REQ-008 — One operation, one bound request

The action, canonical source resource, canonical destination when applicable, session,
task, actor, arguments digest, and request/correlation identifier must be bound before
authorization. Values used by the primitive must equal the authorized values.

### REQ-009 — Explicit task and capability match

An operation must execute only after an explicit action/resource capability matches the
same task-bound request. Missing capability, task mismatch, unsupported action, and
resource mismatch must deny or safely reject before primitive invocation.

### REQ-010 — Authorize before effect

Canonical sequence evidence must show `AUTHORIZATION_ALLOWED` before physical target
validation and `EXECUTION_STARTED`, and the caller-requested primitive may be invoked only
after both. Physical validation uses trusted, non-disclosing no-follow metadata checks and
must not run for a policy-denied path. A denied operation must have neither target probe,
`EXECUTION_STARTED`, nor caller-requested primitive invocation.

Every required audit emission through `EXECUTION_STARTED` must be accepted before the
protected primitive is called. A required audit failure at any earlier point prevents the
primitive. Rename completes and records both authorization evaluations before target
probing, audit of execution start, or mutation; no filesystem mutation may occur between
its source and destination decisions.

## Canonicalization and alias requirements

### REQ-011 — Canonical logical resource

Policy must receive a normalized logical absolute POSIX path below `/workspace`, using the
existing M2 path-resource syntax. The ephemeral host prefix must not become a policy
resource or caller-visible path.

### REQ-012 — Deterministic lexical normalization

The canonicalizer must reject bytes paths and NUL, normalize Unicode to NFC, collapse
duplicate `/`, remove `.`, collapse `..` without escape above `/workspace`, resolve
relative inputs from `/workspace`, strip non-root trailing separators, preserve case, and
reject absolute paths outside the logical namespace. Authorization by raw string prefix is
prohibited; subtree checks must be component-aware.

The empty string is rejected; empty components introduced by repeated separators are
removed. Unicode normalization applies to the complete input before segments are
processed. `..` is processed left-to-right and rejects immediately if it would cross
above `/workspace`. `/workspace` canonicalizes to itself, and `/workspace2` is unrelated.
Specifically, `/workspace/public/**` does not match
`/workspace/public-report.txt`. Authorized `list` and `stat` may target `/workspace`;
all other v1 operations reject the logical root after authorization without invoking the
requested primitive.

### REQ-013 — Exact logical-to-host mapping

Exactly one host path below the temporary root must be derived lexically from each
accepted canonical logical path without probing filesystem state before authorization.
After allow, physical validation must verify containment and entry types by path
components. Execution must use that derived path, not the original spelling.

Before authorization, neither canonicalization nor mapping may call `stat`, `lstat`, a
filesystem-resolving `realpath`, `exists`, `is_file`, `is_dir`, `readlink`, or directory
enumeration on the requested target. The pre-authorization phase is purely syntactic and
must not reveal target existence, type, metadata, link target, or child names.

### REQ-014 — Nonexistent destination handling

For create, mkdir, rename destination, and other permitted missing targets, post-allow
target validation must inspect the closest existing ancestor without following symlinks,
validate the already-normalized remaining components, and enforce the operation-specific
parent-existence rule. A nonexistent leaf must not disable scope checking.

After allow, a missing target required by read, write, append, delete, list, stat, or
rename source is `TOOL_ERROR`. A missing immediate parent for create, mkdir, or rename
destination is also `TOOL_ERROR`. Create and mkdir fail with `TOOL_ERROR` when the leaf
already exists. Rename may use an absent destination or replace an existing compatible
regular file or empty directory after destination validation.

### REQ-015 — Reject-all symlink policy

V1 must reject any existing symlink in an intermediate or final component, including
relative, absolute, chained, dangling, and symlinked-parent forms. A capability cannot
override this adapter safety rule. Race resistance beyond this check must be reported
separately under the TOCTOU boundary.

For create and mkdir, every existing ancestor through the immediate parent must satisfy
the no-symlink rule. Rename separately validates every source component including its
terminal entry, every destination-parent component, and the terminal destination when it
exists. Relative, absolute, chained, and dangling links all receive the same rejection.

V1 must also reject an observed link count above one for existing terminal regular files
used by read, write, append, delete, stat, rename source, or an existing rename
destination. It does not apply that rule to directories, directory ancestors, a list
directory, or absent create/mkdir leaves. The adapter exposes no hard-link creation
operation. An `st_nlink` observation is race-sensitive, cannot prove that no alias exists
at execution time, is not inode confinement, and is not a TOCTOU solution.

## Safety and side-effect requirements

### REQ-016 — Mechanical state observation

Tests must take operation-appropriate before/after snapshots using existence, type,
content SHA-256, size, selected metadata/mode, and sorted directory entries. The snapshot
domain must include every source, destination, protected root, and alias relevant to the
case.

State uses `EXP014-STATE-DIGEST@1`: canonical UTF-8 JSON with sorted keys and no
insignificant whitespace, then SHA-256. An absent path is `{ "type": "ABSENT" }`; a
regular-file record contains type, byte size, and content SHA-256; a directory record
contains type and child NFC names/types sorted by Unicode code point. A snapshot manifest
sorts canonical-logical-path/node-record pairs and covers endpoints, affected parents,
protected roots, and registered aliases. Temporary host prefixes, access/change/
modification times, and inode numbers are excluded. Selected stable mode bits may appear
only when the frozen corpus schema requires them.

### REQ-017 — Denied mutation has no side effect

Every denied mutating adapter request must leave the protected snapshot unchanged and
must not invoke its protected primitive. This is an all-cases gate, not an average-risk
target.

### REQ-018 — Denied read/list/stat has no disclosure

A denied read, list, or stat request must return no protected file bytes, entry names, or
protected metadata. Where the architecture exposes an invocation spy, the corresponding
read-like primitive must not be invoked. Nondisclosure is distinct from non-mutation.

The metric and test evidence must report all three mappings separately: read to protected
bytes, list to directory-entry names, and stat to approved metadata. Every denominator is
all denied cases of that operation; every target is 100%.

### REQ-019 — Two-resource rename authorization

Rename must canonicalize and independently authorize both source and destination under
their appropriate scopes before a single rename primitive begins. Source-only or
destination-only authorization is insufficient. Argument substitution after either
decision is prohibited. Because current M2 evaluates one resource, implementation is
gated on a reviewed, frozen generic compound authorizer that reuses two ordinary
`TaskContractPolicy` evaluations and preserves both subdecisions.

The deterministic evaluation order is source then destination, but both subdecisions
must be recorded even when source denies. The compound result is fail-closed if either
endpoint denies or either evaluation fails. Execution begins only after two explicit
allows and successful required pre-execution audit; there is no source-only fallback,
filesystem-specific authorizer, or mutation between decisions.

### REQ-020 — Delete and directory semantics

Delete requires explicit `filesystem.delete` authority. V1 may delete a regular file or
an empty directory only; recursive delete is excluded. `mkdir` creates one directory with
an existing authorized parent, `list` returns one level, and directory rename still
requires source and destination authorization.

Deleting a non-empty directory is `TOOL_ERROR` after authorization and must not become a
recursive operation. A missing mkdir parent is likewise `TOOL_ERROR` after authorization;
v1 has no `parents=True` equivalent. List returns NFC, case-preserved immediate child
names sorted by Unicode code point and never relies on filesystem iteration order.

## Failure requirements

### REQ-021 — Typed outcome categories

Every attempt must end in one truthful category: `ALLOW` plus success, `DENY`,
`FAIL_CLOSED`, `TOOL_ERROR`, or `FAIL_INDETERMINATE`. Policy and canonicalization errors
must not be misreported as tool denials; tool errors must not be misreported as policy
decisions.

### REQ-022 — Pre-effect failure closes the path

Authorization exceptions, invalid/canonicalization exceptions, unsupported inputs,
unexpected exceptions before primitive invocation, and required pre-execution audit
failure must be `FAIL_CLOSED`: no protected primitive and no protected effect.

### REQ-023 — Post-start failure remains truthful

File-not-found, permission, read, and definitely unchanged write failures after allow are
`TOOL_ERROR`. A partial write, unexpected failure after primitive start, or terminal audit
failure after an effect is `FAIL_INDETERMINATE` unless measured state proves a narrower
result. The system must not claim denial, rollback, or unchanged state without evidence.

## Audit requirements

### REQ-024 — Reconstruct every attempted action

Canonical evidence must reconstruct session, task, request, correlation, requested
logical path or governed identifier, canonical path, rename destination, action, rule,
decision, execution attempted, execution succeeded, tool error, applicable pre/post state
digests, sequence numbers, and adapter/policy/contract versions. Parent/correlation links
must form one lifecycle without relying on timestamps for order.

M3's existing lifecycle types and pre/post audit-failure semantics are retained. Because
M3 cannot represent adapter ingress, pre-`ActionRequest` canonicalization, physical
validation, rename subdecisions, or state digests, the future adapter requires one
additive M3-compatible canonical envelope/schema extension. A parallel audit model is
prohibited and the schema change must complete repository architecture review before
implementation.

### REQ-025 — Evidence minimization

Canonical audit must default to logical path identifiers, hashes, sizes, selected
metadata, and result categories. It must not store raw file contents or arbitrary request
payloads. Any raw synthetic fixture assertion must remain outside the canonical audit and
be explicitly justified.

## Bypass and isolation requirements

### REQ-026 — Registered adapter-bypass suite

The held-out suite must exercise traversal, logical/host absolute paths, prefix collision,
alternate normalization, symlink escape, symlinked parent, create-symlink-then-access,
rename escape, cross-root move, hard links where supported, `pathlib`/string spelling,
nested paths, nonexistent parents, and relevant descriptor reuse. Every adapter-routed
escape must fail safely.

The freeze-time classification is: traversal escape, host absolute paths, prefix
collision, symlink escape, and rename escape are `ADAPTER_SHOULD_BLOCK`; hard-link fixture
creation is `PLATFORM_DEPENDENT` but a created multi-link regular target must be blocked;
direct `os.open`, direct `pathlib` I/O, shell redirection, and inherited-descriptor I/O are
`EXPECTED_FMED_L1_BYPASS`; valid absolute logical paths are supported inputs rather than
bypasses; and external/non-Linux filesystem semantics are `NOT_IN_SCOPE`. Passing a
supported string representation derived from `pathlib` into the adapter receives normal
adapter enforcement and is distinct from direct `pathlib` I/O.

### REQ-027 — Honest direct-route demonstration

At least one test must use direct `os.open` outside the adapter in the isolated root to
demonstrate that FMED-L1 is bypassable. This expected boundary demonstration is not an
adapter failure and must never be omitted from reporting or reframed as confinement.

### REQ-028 — Session and task isolation

Requests, authorization, sequencing, audit, and fixture observations must remain bound to
their session and task. A task mismatch must deny without mutation or disclosure; one
session must not consume another's decision, sequence state, canonicalization result, or
authorization token.

## Reproducibility, performance, and platform requirements

### REQ-029 — Deterministic fixtures and semantics

Fixture creation must be deterministic and record initial-state digests. Equivalent
inputs under the same platform, policy, adapter, and fixture version must produce
semantically equivalent decisions, events, and final filesystem states. UUIDs and
timestamps may differ and must be excluded from semantic equivalence.

### REQ-030 — Secondary overhead measurement

Adapter, authorization, and audit overhead must be measured separately where feasible.
Report sample count, minimum, median, mean, p95, and p99 only when volume supports the
percentiles. No correctness requirement may be relaxed to improve latency.

### REQ-031 — Freeze and held-out corpus order

The protocol and design must freeze before implementation; adapter and event semantics
must freeze before held-out corpus authorship. The corpus must contain at least 20
authorized, 20 unauthorized, 10 canonicalization/bypass, and 10 failure/error cases and
prefer counterfactual pairs. No corpus is part of this design stage.

Implementation may use recorded `DEV-FS-*` fixtures for lexical rules, symlinks,
primitive failures, and audit failures. At adapter freeze, their identifiers and semantic
cases become a contamination record. A held-out case must not repeat a development
fixture verbatim (path/name tuple, bytes, authority arrangement, and failure-injection
combination), and the adapter must not be tuned after held-out cases are viewed.

### REQ-032 — Linux-only initial evidence

Initial evidence must name Linux, local case-sensitive filesystem behavior, process
ownership/permission assumptions, symlink semantics, and same-filesystem rename
assumptions. Results must not be generalized to Windows, macOS, remote, overlay, or
network filesystems without new testing.

## Verification gates

The frozen corpus must meet 100% authorization correctness, denied-mutation prevention,
denied read/list/stat nondisclosure, authorize-before-effect ordering, required audit
reconstruction,
tool-error classification, and registered canonicalization correctness. All
adapter-routed bypass cases must fail safely; the direct-route demonstration must show the
FMED-L1 boundary. Any critical violation fails EXP-014 and is retained in its evidence.

These requirements define a research gate. They do not authorize implementation in this
change and do not update the claims ledger.
