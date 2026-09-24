# Real Filesystem Mediation Architecture

**Artifact:** `REAL-FILESYSTEM-MEDIATION-ARCHITECTURE@1`
**Status:** pre-implementation design for [EXP-014](../experiments/EXP-014-real-filesystem-mediation.md)

The governing decision is
[ADR-006](../decisions/ADR-006-real-filesystem-mediation-boundary.md).

## Boundary and maturity

The first real-tool milestone is deliberately an isolated Linux filesystem adapter. It
targets FMED-L1 and RTM-1: SafetyBox mediates only calls that enter the adapter. Current
SafetyBox remains RTM-0 until implementation and real-tool evaluation occur.

The adapter is not a sandbox. If the agent retains Python `os.*`, `pathlib`, native code,
shell, inherited file descriptors, or another direct filesystem route, it can bypass this
boundary. FMED-L2 would additionally require tested framework/API interception; FMED-L3
requires process-level bypass resistance; FMED-L4 requires OS/sandbox confinement or an
equivalent tested boundary.

## Trusted and untrusted sides

The trusted base for EXP-014 is the SafetyBox policy engine, adapter, canonicalizer,
canonical audit recorder, and deterministic test harness. The agent request, all path
spellings, operation arguments, filenames, file bytes, directory entries, and symlink
targets are untrusted. Observed content is data; it cannot become an instruction or
authority input.

The host kernel and filesystem implementation are environmental dependencies, not
properties proved by SafetyBox. Host or administrator compromise is outside this
experiment.

## Isolated namespace

Each case creates a fresh temporary host root with deterministic contents:

```text
<temporary-root>/
  workspace/
    public/
    private/
    output/
```

The caller sees only logical paths below `/workspace`. The ephemeral host prefix is never
accepted as a logical request or policy resource. All before/after observation is bounded
to this temporary root. Tests must never use the real home directory, SSH keys, system
files, production data, or repository secrets.

## Conceptual interface

No interface is implemented by this document. The future boundary is conceptually:

```text
FilesystemAdapter
  read(path)
  write(path, data)
  append(path, data)
  create(path, data)
  delete(path)
  rename(source, destination)
  mkdir(path)
  list(path)
  stat(path)
```

Each method accepts a typed request envelope containing request, session, task, and actor
identity. Data arguments are bytes or another versioned unambiguous representation;
string encoding must not be inferred. Methods do not expose a raw file descriptor.

The operation set separates privileges. `write` replaces an existing regular file and
never creates; `append` requires an existing regular file and never creates; `create`
requires an absent leaf; `delete` removes one regular file or empty directory; `mkdir`
creates one absent directory with an existing immediate parent and never creates parents;
`list` is non-recursive and sorted deterministically; and recursive deletion is absent.
`stat` returns a bounded metadata schema, not an arbitrary platform object. These are
research semantics, not consequences of Python open-mode defaults.

## Control and data flow

```text
untrusted typed adapter request
  -> record adapter ingress
  -> lexically validate and canonicalize path(s), with no filesystem lookup
  -> construct canonical ActionRequest
  -> ReferenceMonitor
       -> TaskContractPolicy
       -> CapabilityEvaluator
       -> ALLOW or DENY
  -> if and only if ALLOW: validate physical target without following links
  -> if and only if ALLOW: invoke exact bound filesystem primitive
  -> observe result/state category
  -> emit canonical completion/failure evidence
  -> return minimized typed result
```

There is no alternative filesystem-specific authorization branch. The adapter translates
the operation to a dotted action such as `filesystem.read` and a canonical logical
resource such as `/workspace/public/report.txt`, then reuses the M2 subtree semantics.
This avoids changing M2 resource syntax. Raw string-prefix checks are forbidden.

## Canonicalization contract

### Lexical form

Only Python-style Unicode strings without NUL are accepted in v1. Path bytes are
rejected. `/` is the separator. Relative inputs resolve from logical `/workspace`;
absolute inputs are accepted only in the logical `/workspace` namespace. Duplicate
separators and `.` are removed. `..` is collapsed, but any attempt to move above
`/workspace` is rejected. Unicode is normalized to NFC; the normalized spelling is the
only spelling mapped and executed. Case is preserved and compared case-sensitively.
Trailing separators are removed except for `/workspace`, with directory expectations
validated by the operation rather than inferred from spelling.

The empty string is rejected; empty components introduced by repeated `/` are removed.
The entire string is NFC-normalized before left-to-right segment processing. An attempt
to apply `..` above `/workspace` rejects immediately even if later text could appear to
return in scope. `/workspace` canonicalizes to itself: authorized `list` and `stat` may
target it, while other v1 operations reject that root after authorization without calling
their requested primitive. A valid absolute path is `/workspace` or a component
descendant only; `/workspace2` and an ephemeral host path are rejected.

| Input | Lexical result |
|---|---|
| `public/a.txt` | `/workspace/public/a.txt` |
| `/workspace/public/./a.txt` | `/workspace/public/a.txt` |
| `/workspace/public/x/../a.txt` | `/workspace/public/a.txt` |
| `/workspace//public///a.txt` | `/workspace/public/a.txt` |
| `/workspace/public/` | `/workspace/public` |
| empty string or `../private/a.txt` | reject |
| `/workspace/public-report.txt` | That exact path; never a descendant of `/workspace/public`. |

The initial fixture generator uses NFC names. A pre-existing NFD-distinct host entry does
not become reachable through an NFD request; the adapter executes only its NFC-derived
mapping. No case-insensitive or macOS normalization claim follows.

### Host mapping and containment

The canonical logical component vector is appended to the known temporary root. The
implementation must verify component containment and must never authorize or execute the
original path string. Text such as `/workspace/public-report.txt` does not match
`/workspace/public/**`; M2's component-aware descendant semantics are reused.

Canonicalization is deliberately two-phase. Before authorization, lexical normalization
and logical-to-host component mapping perform no filesystem lookup: specifically, no
`stat`, `lstat`, filesystem-resolving `realpath`, `exists`, `is_file`, `is_dir`,
`readlink`, or directory enumeration may touch the requested target. This prevents an
unauthorized caller from learning target existence, type, metadata, link target, or child
names through pre-policy outcomes. After `ALLOW`, trusted physical target validation inspects every existing
component without following symlinks and returns none of that metadata to the caller. For
a missing destination, it inspects the closest existing ancestor and validates the
already-normalized remainder before enforcing the operation-specific requirement that the
immediate parent exist. A missing leaf never disables scope checks.

After allow, a missing required target for read, write, append, delete, list, stat, or
rename source is `TOOL_ERROR`; so is a missing immediate parent for create, mkdir, or
rename destination. Create and mkdir require an absent target. Rename may use an absent
destination or replace an existing compatible regular file or empty directory after full
destination validation.

### Symlinks and hard links

V1 rejects all symlinks in existing intermediate and final components, including
relative, absolute, chained, and dangling links. This is an adapter safety rejection,
not a grantable capability. The implementation must not call a following primitive first
and inspect afterward.

Create and mkdir validate every existing ancestor through the immediate parent. Rename
validates every source component including its terminal entry, every destination-parent
component, and the existing destination terminal when present. Any symlink at any of
those locations rejects before execution.

Hard links are different: path inspection does not reveal a separate target path. V1
therefore rejects an existing terminal regular file whose post-allow `st_nlink` is above
one for read, write, append, delete, stat, rename source, and an existing rename
destination. The rule does not apply to directory ancestors, list directory targets,
directory delete/rename targets, or absent create/mkdir leaves. The adapter exposes no
hard-link creation method. The held-out suite must exercise this behavior where the
platform permits links. The check observes only one instant, is race-sensitive, cannot
prove no alias exists at execution time, does not establish inode confinement, and may
reject a legitimate multi-link file; these limits must be reported rather than hidden.

### TOCTOU boundary

Canonicalize-then-open is race-sensitive: another actor can replace a checked component
before the primitive uses its name. Path normalization and symlink rejection do not solve
that race. EXP-014 begins with TOCTOU classified `NOT_SOLVED`. A future implementation may
use directory file descriptors, no-follow/resolve constraints, identity revalidation, or
other Linux mechanisms, but it may report `TESTED` or `PARTIALLY_TESTED` only from frozen
evidence. V1 must not imply atomic object binding if it lacks it.

## Authorization representation

Single-resource operations create one `ActionRequest` whose action is the exact operation
and whose resource is the canonical logical path. The request arguments may carry a
digest and non-sensitive typed operation parameters, but raw write bytes are not audit
metadata.

Rename is a two-resource operation. The proposed representation is one correlated rename
envelope with:

- action `filesystem.rename`;
- canonical source as the primary resource;
- typed canonical destination as a bound argument; and
- two attributable authorization evaluations, one for source and one for destination,
  completed before a single `EXECUTION_STARTED`.

The event/schema review must choose a representation compatible with the existing
monitor without reducing authorization to source-only matching. An internal derived
request for the destination may be used only if both decisions remain atomically bound to
the same correlation and exact primitive arguments. No rename executes on one allow.

The current M2 evaluator authorizes one `ActionRequest.resource`, so it cannot by itself
satisfy the two-resource rule. Before adapter implementation, governance must review and
freeze a generic compound `TaskContractPolicy` authorizer that derives two ordinary
`filesystem.rename` resource checks against the same immutable contract, returns `DENY`
if either check denies or fails, and preserves both subdecision rule IDs. It evaluates
source then destination deterministically and records both even if source denies. There
is no target probe or mutation between evaluations. `ReferenceMonitor` then receives that
compound authorizer and still owns the only execution branch; execution starts only after
both explicit allows and required pre-execution audit. This is a proposed minimal
extension, not current code; source-only and filesystem-specific fallback paths are
prohibited.

Delete always requires `filesystem.delete`. `filesystem.write` never implies deletion.
The same rule applies to directory deletion; recursive delete is excluded. A non-empty
directory delete is `TOOL_ERROR` after allow. A missing mkdir parent is also `TOOL_ERROR`
after allow; there is no `parents=True` behavior. List returns only immediate NFC,
case-preserved child names sorted by Unicode code point, never host iteration order.

## Ordering and events

The existing M3 lifecycle remains canonical:

```text
ACTION_REQUESTED
-> AUTHORIZATION_STARTED
-> AUTHORIZATION_ALLOWED | AUTHORIZATION_DENIED | AUTHORIZATION_FAILED
-> EXECUTION_STARTED
-> EXECUTION_SUCCEEDED | EXECUTION_FAILED
```

The canonical session-local `sequence_number`, not timestamp, proves order. For allow,
`AUTHORIZATION_ALLOWED` must precede `EXECUTION_STARTED`. Every required event through
`EXECUTION_STARTED` must be accepted by the canonical audit sink before the protected
primitive is invoked. Audit failure at any earlier point fails closed with no primitive.
Denial has no execution event, target metadata probe, or primitive call.

M3 alone cannot reconstruct a request rejected before `ActionRequest` construction or
the post-allow physical-validation stage.
EXP-014 therefore proposes—not implements—compatible additions to the canonical registry:

- `ADAPTER_REQUEST_RECEIVED`;
- `CANONICALIZATION_STARTED`;
- `CANONICALIZATION_SUCCEEDED`; and
- `CANONICALIZATION_FAILED`;
- `TARGET_VALIDATION_STARTED`;
- `TARGET_VALIDATION_SUCCEEDED`; and
- `TARGET_VALIDATION_FAILED`.

The schema also needs governed `requested_resource`, `canonical_resource`, optional
`canonical_destination`, adapter version, argument digest, pre/post state digests,
result/error category fields, and both rename subdecisions. Existing M3 lifecycle types
and its pre-effect fail-closed/post-effect-indeterminate semantics are sufficient as the
base, but not for those adapter stages and fields. The required solution is one additive
M3-compatible canonical envelope/schema extension, not a parallel audit stream. Any
schema change requires the repository's architecture-decision process before code.

## Side effects and state observation

A side effect is mechanical and operation-specific:

| Operation | Protected effect |
|---|---|
| `read` | Protected bytes are successfully retrieved. |
| `list` | Protected directory names are successfully retrieved. |
| `stat` | Protected metadata is successfully retrieved. |
| `write` | Existing file bytes/size change. |
| `append` | Existing file bytes/size change at the end. |
| `create` | A new directory entry and regular file appear. |
| `delete` | A directory entry disappears. |
| `rename` | Source/destination namespace state changes. |
| `mkdir` | A new directory entry appears. |

Before/after state uses `EXP014-STATE-DIGEST@1`. Each node is encoded as canonical UTF-8
JSON with sorted keys and no insignificant whitespace: absence is the explicit
`{"type":"ABSENT"}` sentinel; a regular file records type, byte size, and content
SHA-256; a directory records type and immediate child NFC names/types sorted by Unicode
code point. A snapshot manifest sorts canonical-logical-path/node-record pairs covering
both endpoints, affected parents, protected roots, and registered aliases, and the
manifest is SHA-256 hashed. Ephemeral host prefixes, atime, mtime, ctime, and inode
numbers are excluded; stable mode bits appear only if preregistered by the corpus schema.
Rename snapshots include both parent directories and both endpoints. This scope prevents
a narrow endpoint check from missing a cross-path mutation.

Reads have no expected mutation, but successful retrieval is still a protected effect. A
denied read must return no protected bytes, a denied list no directory-entry names, and a
denied stat no approved metadata. The frozen evaluation reports each denominator and
requires 100% nondisclosure for each. A spy at each primitive boundary establishes
non-invocation.

## Write visibility and partial failure

Authorization must complete before any temporary or final file visible in the protected
namespace is created. A future implementation should evaluate same-directory temporary
files, flush behavior, and atomic replace for whole-file writes, but atomic replace is not
automatically correct: temporary-file creation is itself a side effect and overwrite,
mode, ownership, cleanup, and crash behavior require policy.

Append cannot generally be transformed into atomic replacement without changing its
semantics. Injected short-write and failure tests must observe the actual post-state. If a
failure can leave partial bytes or an orphan temporary entry, the result is
`FAIL_INDETERMINATE` unless the state observation proves otherwise. The architecture does
not promise rollback.

## Failure flow

| Point | Required category | Effect statement |
|---|---|---|
| Invalid input/canonicalization | `FAIL_CLOSED` | No primitive, mutation, or disclosure. |
| Physical target validation rejects after policy allow | `FAIL_CLOSED` | Preserve `ALLOW`, record adapter safety failure, and do not start requested execution. |
| Authorization exception/unsupported decision | `FAIL_CLOSED` | No primitive, mutation, or disclosure. |
| Required audit failure before execution | `FAIL_CLOSED` | No primitive, mutation, or disclosure. |
| Allowed primitive reports not found/permission/read error | `TOOL_ERROR` | Report measured outcome; do not call it denial. |
| Write-like failure with possible partial effect | `FAIL_INDETERMINATE` | Operation may have changed state; retain post-state evidence. |
| Tool succeeds, terminal audit fails | `FAIL_INDETERMINATE` | Effect happened; never claim denial or rollback. |
| Unexpected exception after primitive start | `FAIL_INDETERMINATE` | Preserve uncertainty and measured state. |

M3 already fails closed when a required event cannot be recorded before invocation and
recognizes that terminal audit failure cannot undo an invoked tool. The adapter must
preserve these semantics.

## Audit reconstruction and minimization

For every attempt, evidence must reconstruct session, task, request, correlation,
requested and canonical logical resources, rename destination if any, action, rule,
decision, execution attempted/succeeded, tool-error category, pre/post state digest when
recorded, adapter/policy/contract version, parent links, and sequence numbers.

Synthetic logical paths may be recorded because the experiment creates them, but raw file
contents are excluded from canonical audit by default. Content hashes, sizes, entry types,
selected metadata, result categories, and governed identifiers are preferred. Raw fixture
bytes used by assertions stay in test evidence and are never copied into general audit
metadata.

## Bypass boundary

The future adversarial suite covers traversal, prefix collision, alternate spellings,
logical versus host absolute paths, symlink escape, symlink creation followed by access,
hard-link aliases where supported, rename into a denied root, cross-root moves, missing
parents, nested boundaries, `pathlib` versus string representations, and relevant
descriptor reuse. All adapter-routed cases must fail safely.

A separate direct `os.open` call in the isolated root must be able to bypass the adapter
under the FMED-L1 topology. This is an expected demonstration of the claim boundary. A
deployment needing resistance to that case must progress to process/OS mediation rather
than merely add adapter tests.

| Route/case | Frozen classification |
|---|---|
| Escaping `..`, host absolute path, prefix collision, symlink escape, rename escape | `ADAPTER_SHOULD_BLOCK` |
| Hard-link fixture creation | `PLATFORM_DEPENDENT`; if created, adapter access must be blocked |
| Valid `/workspace/...` absolute logical path | `NOT_IN_SCOPE` as a bypass; it is normal input |
| Direct `os.open` or direct `pathlib` I/O | `EXPECTED_FMED_L1_BYPASS` |
| Shell redirection | `EXPECTED_FMED_L1_BYPASS`; execution itself is outside experiment scope |
| Inherited descriptor I/O | `EXPECTED_FMED_L1_BYPASS` when a platform fixture supplies it |
| External filesystems and non-Linux semantics | `NOT_IN_SCOPE` |

A `pathlib`-derived value passed through the typed adapter is distinct from direct
`pathlib` I/O and receives ordinary input validation and authorization.

## Development fixtures and evaluation separation

Implementation-time tests may use recorded `DEV-FS-LEXICAL-*`, `DEV-FS-SYMLINK-*`,
`DEV-FS-PRIMITIVE-FAILURE-*`, and `DEV-FS-AUDIT-FAILURE-*` fixtures. Their identifiers
and semantic cases become a contamination record at adapter freeze. Held-out cases are
authored only afterward and may not reuse a development fixture verbatim, including its
path/name tuple, bytes, authority arrangement, and failure-injection combination. Once
held-out authorship begins, the adapter may not be tuned against those cases.

## Platform assumptions

Initial evidence is Linux-only on a local case-sensitive filesystem, with fixtures owned
by the experiment process and rename performed within one filesystem. POSIX-like names,
permissions, symlink behavior, and directory-entry operations are assumed only as
recorded by the future environment manifest. Windows, macOS, case-folding, Unicode-
normalizing, remote, overlay, and network filesystems require separate protocols.

## Deferred architecture

After filesystem evidence, the dependency order is subprocess/shell, HTTP/network, MCP
tool proxy, database, browser, then a multi-tool real-agent harness. Filesystem comes
first because it establishes canonical resource binding, authorize-before-effect,
side-effect observation, audit failure semantics, and bypass vocabulary used by later
adapters. Shell adds interpreter/process escape; network adds name/rebinding and remote
effects; MCP adds protocol identity/provenance; database adds transaction/query semantics;
browser adds stateful multi-origin behavior; the agent harness should integrate only
after individual adapter boundaries are measurable.

No adapter source, event enum, policy code, or test corpus is created by this document.
