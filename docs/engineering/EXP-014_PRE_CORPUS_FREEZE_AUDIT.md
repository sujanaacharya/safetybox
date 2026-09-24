# EXP-014 Pre-Corpus Implementation Freeze Audit

**Audit ID:** `EXP-014-PRE-CORPUS-FREEZE-AUDIT@1`

**Scope:** implementation freeze, M1/M3 backward compatibility, and technical diligence

**Evidence class:** contaminated development evidence; not held-out evidence or an EXP-014 result
**Decision:** `PASS — APPROVED_FOR_PRE_CORPUS_IMPLEMENTATION_FREEZE`

## Scientific boundary

This audit did not author or preview an EXP-014 corpus, run EXP-014, create
`results/EXP-014`, tune against held-out cases, or change the frozen protocol. It reviews
only the pre-corpus implementation candidate and contaminated development fixtures.
SafetyBox remains RTM-0. FMED-L1 means only calls routed through this adapter.

## Starting state

| Reference | SHA |
|---|---|
| EXP-014 protocol/design freeze and starting `HEAD` | `7baf20293caa83d3fff6a200174c4f8840918607` |
| M1 `ReferenceMonitor` freeze | `9f77dc906355d1191af1f4908460af8e4cc36293` |
| M2 task-scoped capability freeze | `5c55917bb9adb5728f12d26faf6da9e29d2402b2` |
| M3 event/audit freeze | `2d9f8b09825702d12304f379130001f60e3d867c` |
| EXP-013 analysis/synthesis | `f4713f2f7012ba933ad9059fe8778004e331ae11` |

At audit start, modified files were `CHANGELOG.md`, `docs/DOCUMENTATION_INDEX.md`,
`docs/architecture/REAL_FILESYSTEM_MEDIATION.md`, `docs/research/RESEARCH_PROGRESS.md`,
`docs/strategy/BUILD_VS_CLAIM_MATRIX.md`,
`docs/strategy/OWASP_GENAI_AGENTIC_COVERAGE_PLAN.md`, `src/safetybox/audit.py`,
`src/safetybox/events.py`, `src/safetybox/exceptions.py`, `src/safetybox/monitor.py`, and
`src/safetybox/protocols.py`. Untracked files were the three EXP-014 development,
traceability, and diligence documents, `src/safetybox/authorization.py`, all eleven files
then present below `src/safetybox/filesystem/`, and
`tests/dev/test_exp014_filesystem_adapter.py`.

`experiments/EXP-014/` contained only `protocol.yaml`. `results/EXP-014` did not exist.

The architecture document had implementation-status edits at audit start. Because it is
part of the frozen design commit, those edits were removed and implementation facts were
kept in additive development/audit documents. Its final bytes again match `7baf202…`.

## Requirement completeness

`docs/research/EXP-014_REQUIREMENT_TRACEABILITY.md` contains one disposition for every
identifier from REQ-001 through REQ-032. Mechanical checks found 32 unique rows, no gaps,
no duplicates, no held-out-validated status, and no orphan security behavior. REQ-030 is
explicitly evaluation-only at this stage: protocol v1 defines descriptive performance
measurement with no acceptance threshold, so it has no implementation behavior to test
before corpus authorship. All 31 implementation-applicable requirements have production
and concrete contaminated-development evidence references. The frozen success and
failure gates were not weakened.

## M1 additive-change audit

| File and symbol | EXP-014 reason | Legacy/default effect | Authorization influence |
|---|---|---|---|
| `monitor.py:ReferenceMonitor.lifecycle_hook` | Run post-allow validation and collect minimized terminal evidence inside the existing execution branch. | `None` by default; old callers do not enter it. | Cannot grant allow; invoked only after `AUTHORIZATION_ALLOWED`. |
| `monitor.py:ReferenceMonitor.execute` keyword-only parent/metadata arguments | Join adapter ingress to the canonical M3 lifecycle. | Both default to `None`; normalized legacy flow is unchanged. | Metadata and parentage do not select a decision. |
| `protocols.py:ExecutionLifecycleHook` | Typed generic hook contract. | Additive protocol only. | No authorization method exists on the hook. |
| `exceptions.py:AuditFailure` failure-stage attributes | Distinguish pre-effect fail-closed from post-start indeterminate. | Defaults preserve old construction and message behavior. | Cannot allow execution. |
| `authorization.py:CompoundAuthorizer` | REQ-019 requires two ordinary evaluations for rename. | New opt-in component; no existing caller uses it. | Aggregates the injected authorizer; it has no filesystem policy logic and allows only when all subdecisions allow. |

There is one authoritative forwarding branch: `ReferenceMonitor.execute` invokes
`protected_tool.execute` only after its selected `Authorizer` returns `Decision.ALLOW`
and required pre-execution audit/hook work succeeds. `FilesystemAdapter` never invokes a
requested primitive directly. The lifecycle hook can reject or fail closed; it cannot
change a denial to allow. The focused frozen-era M1/M2 suite passes independently.

## M3 additive-change and compatibility audit

| Change | Classification | Compatibility result |
|---|---|---|
| Seven adapter/canonicalization/validation `EventType` members | `ADDITIVE_EVENT_TYPE` | Existing event values and old flows are unchanged. |
| `AuditRecorder.last_sequence_number` | `ADDITIVE_METADATA` inspection | Read-only; allocation still occurs only in `emit` after sink acceptance. |
| Optional parent and filesystem metadata in `ReferenceMonitor.execute` | `ADDITIVE_METADATA` | Absent for old callers; old metadata remains exactly `{}` where it was empty. |
| Optional lifecycle hook | `ADDITIVE_EVENT_TYPE` orchestration | Absent by default; existing sinks see the original five-event allow flow or three-event deny/failure flow. |
| `AuditFailure.execution_may_have_started` and `failed_event_type` | `ADDITIVE_FAILURE_DETAIL` | Old exception type/message behavior remains. |
| Extended failure `executed` status | `ADDITIVE_FAILURE_DETAIL` | Applies only to opt-in extended lifecycle; legacy tool-failure events retain `executed=False`. |

`SafetyBoxEvent` remains frozen, recursively freezes metadata, and retains the same field
layout. Sequence numbers remain session-local and sink-commit-based. A normalized
regression excludes UUID/timestamp values and proves the original allow serialization,
metadata, parent chain, decision, execution flags, and result semantics. Existing
consumers may ignore new enum values and filesystem metadata; consumers that exhaustively
enumerate a closed enum still need normal forward-compatible handling for any additive
event registry.

## Authorization and operation paths

All operations share this path:

```text
FilesystemAdapter.execute
-> governed request identity
-> pure lexical canonicalization
-> ActionRequest binding
-> ReferenceMonitor.execute
-> injected Authorizer
-> AUTHORIZATION_ALLOWED
-> FilesystemExecutionBoundary.before_execution
-> PhysicalTargetValidator.validate
-> committed TARGET_VALIDATION_SUCCEEDED
-> committed EXECUTION_STARTED
-> FilesystemExecutionBoundary.execute
-> one RealFilesystemPrimitives method
-> terminal M3 event and FilesystemResult
```

The operation-specific terminal dispatch is:

| Operation | Post-allow validation | Requested primitive |
|---|---|---|
| read | existing single-link regular file | `read` |
| write | existing single-link regular file | `write` |
| append | existing single-link regular file | `append` |
| create | absent leaf and existing immediate parent | `create` |
| delete | existing single-link file or empty directory | `delete_file` or `delete_directory` |
| rename | validated source and compatible destination | `rename` |
| mkdir | absent leaf and existing immediate parent | `mkdir` |
| list | existing directory | `list_directory` |
| stat | existing directory or single-link regular file | `minimized_stat` |

Rename canonicalizes both endpoints before authorization. `CompoundAuthorizer` evaluates
source then destination against the same bound request and immutable contract, including
the destination after a source denial. Only its aggregate allow reaches the monitor's
post-allow validation. No probe or mutation occurs between decisions. The component is
generic over an `Authorizer` and ordered resources, so it is reusable later without
generalizing it further now.

Source review and call-site search found no production route from `FilesystemAdapter` to
a requested primitive that bypasses the monitor allow branch.

## Primitive reachability

| Production location | Calls | Classification |
|---|---|---|
| `filesystem/primitives.py:RealFilesystemPrimitives.lstat` | `os.lstat` | `POST_ALLOW_VALIDATION` |
| `directory_is_empty` | `os.scandir` | `POST_ALLOW_VALIDATION` |
| `read` | `os.open`, `os.read`, `os.close` | `PURE_EXECUTION` |
| `write` | `os.open`, `os.ftruncate`, `os.write`, `os.close` | `PURE_EXECUTION` |
| `append` | `os.open`, `os.write`, `os.close` | `PURE_EXECUTION` |
| `create` | `os.open`, `os.write`, `os.close` | `PURE_EXECUTION` |
| `delete_file` / `delete_directory` | `os.unlink` / `os.rmdir` | `PURE_EXECUTION` |
| `rename` / `mkdir` | `os.replace` / `os.mkdir` | `PURE_EXECUTION` |
| `list_directory` | `os.scandir` | `PURE_EXECUTION` |
| `minimized_stat` | `os.lstat` | `PURE_EXECUTION` |
| `state_digest.py` | `os.open/read/close`, `os.lstat`, `os.scandir` | `STATE_DIGEST` |

All other real calls in the development module are `TEST_ONLY`, including the explicit
direct `os.open` bypass. No production occurrence was classified `OTHER`.

## Pre-authorization information boundary

Before policy evaluation, the adapter uses type checks, NFC normalization, POSIX
component processing, hashing of caller-supplied arguments, object construction, and
audit emission. Neither canonicalization nor request preparation calls `stat`, `lstat`,
`exists`, `resolve`, `realpath`, `readlink`, `open`, or enumeration. Mapping is not used
until the post-allow validator and now revalidates exact canonical form syntactically.
Denied-path spies show zero validation probes.

Public errors are stable messages/codes. Ordinary caller-supplied logical spelling is
governed audit identity; NUL/malformed payloads are replaced by a non-reversible SHA-256
identifier. Raw OS messages, host paths, read bytes, write/append payloads, and protected
directory contents are absent from public results and audit metadata.

## Denial, links, and mapping

- All six mutating denial types have zero requested primitive calls and equal independent
  pre/post `EXP014-STATE-DIGEST@1` observations on real temporary filesystems.
- Denied read, list, and stat return `None`, perform zero target probes/requested calls,
  and disclose no protected bytes, names, or approved metadata.
- Real terminal, intermediate/parent, relative, absolute, chained, dangling, create or
  mkdir parent, rename source, and rename destination-parent symlinks reject after allow
  and before `EXECUTION_STARTED`.
- Linux hard-link tests cover read, write, append, delete, stat, rename source, and an
  existing rename destination. The rule is explicitly a race-sensitive `st_nlink`
  observation, not inode confinement.
- Deterministic canonicalization tests cover equivalent relative/absolute/dot/repeated
  separator forms, left-to-right traversal rejection, NFC, logical root, and prefix
  collision. `LogicalHostMapper` rejects hostile noncanonical strings even when called
  directly; `commonpath` remains a defense-in-depth syntactic root check.

## Failure truth table

| Condition | Public result | Primitive invoked | Effect possible | State claim | Classification |
|---|---|---:|---:|---|---|
| Policy denied | value omitted, decision `DENY` | no | no | independent denied-mutation equality where applicable | `DENY` |
| Canonicalization failed | safe error, no canonical target | no | no | unchanged by construction | `FAIL_CLOSED` |
| Safety validation rejected | decision remains `ALLOW`, safe validation code | no | no | unchanged | `FAIL_CLOSED` |
| Operational precondition failed after allow | safe tool code | no requested primitive | no | unchanged | `TOOL_ERROR` |
| Primitive failed before effect | safe tool code | yes | no | observed post-state where mutating | `TOOL_ERROR` |
| Primitive partially affected state | no value, pre/post evidence when observable | yes | yes | no rollback claim | `FAIL_INDETERMINATE` |
| Primitive succeeded | typed minimized value/effect | yes | yes/observed | success evidence | `ALLOW` |
| Required pre-execution audit failed | safe audit code | no | no | unchanged | `FAIL_CLOSED` |
| Post-effect lifecycle or terminal audit failed | no success claim | yes | yes | effect retained; success/rollback not overclaimed | `FAIL_INDETERMINATE` |

Injected truncation covers a partial write. A post-effect lifecycle-metadata failure now
records the primitive as executed, while the public result remains indeterminate. A
terminal sink failure leaves the real effect observable and likewise returns
`FAIL_INDETERMINATE`.

## State digest and reconstruction

`EXP014-STATE-DIGEST@1` uses sorted compact UTF-8 JSON and SHA-256. Tests establish
repeat stability, input-order independence, content mutation, child creation, rename and
deletion changes, identical digests for equivalent fixtures under different host roots,
and exclusion of timestamps, inode numbers, host prefixes, and symlink targets.

The successful-operation matrix reconstructs all nine operations (including both delete
forms) from evidence alone: session, task, request/correlation, requested/canonical
resource, action, rename destination, all authorization decisions/rules, validation,
execution attempted/outcome, category/error, applicable state digests, all four schema
versions, parent chain, and exact session sequence range. Development reconstruction
completeness is 10/10 successful operation shapes (100%); denial and injected-failure
tests additionally verify their minimized terminal fields. This is development evidence
only.

## Threat-to-implementation traceability

| Registered threat | Mitigation and development test | Remaining limitation |
|---|---|---|
| Path traversal | lexical stack; `test_lexical_rejections_do_not_depend_on_host_state` | no non-Linux claim |
| Prefix collision | M2 components; `test_component_prefix_collisions_are_denied_without_probe` | depends on M2 semantics |
| Host/logical confusion | canonicalizer/mapper; mapper and lexical rejection tests | direct host APIs bypass FMED-L1 |
| Unicode/path confusion | whole-input NFC; lexical and equivalent-root tests | visual confusables remain distinct |
| Symlink escape | post-allow component `lstat`; symlink category/parent/rename tests | swap race remains |
| TOCTOU/symlink swap | honest `NOT_SOLVED` classification | pathname validation/execution gap |
| Hard-link alias | terminal `st_nlink`; registered-operation and rename tests | race-sensitive, not inode confinement |
| Rename escape | two decisions and bound destination; rename decision/prefix tests | pathname race and platform atomicity boundary |
| Delete overbreadth | distinct action and nonrecursive primitives; denial/nonempty tests | empty directories only |
| Protected-read disclosure | deny before validation; denied retrieval sentinel test | external side channels excluded |
| Partial write | effect flag plus post-state; partial-write injection | no rollback guarantee |
| Audit loss before effect | required sink commit; pre-execution failure test | in-memory audit is not durable |
| Audit loss after effect | indeterminate outcome; terminal and lifecycle failure tests | terminal record may be unavailable |
| Context mismatch | immutable IDs/M2 contract/session sequence; isolation test | no authenticated cross-process identity |
| Direct API bypass | explicit temp-root `os.open` demonstration | expected until FMED-L2/3/4 |
| Corpus overfitting | no source fixture/label branches; pre-corpus freeze and source search | finite future corpus remains limited |

INV-016 maps to denied mutation/digest and rename-denial tests; INV-017 to the denied
read/list/stat sentinel matrix; INV-018 to lexical, mapper, prefix, symlink, hard-link,
argument-binding, and two-endpoint rename tests; INV-019 to authorization,
canonicalization, validation, state-observation, audit, partial-write, and post-effect
failure injection. Their canonical statuses remain `DESIRED`.

## Configuration, API, portability, and isolation

The public boundary (`FilesystemRequest`, `FilesystemResult`, `FilesystemAdapter`) is
independent of the experimental runner and can be called by a future Python SDK, local
gateway, or MCP interceptor. Those integrations would still need authenticated identity,
serialization/version negotiation, quotas, durable audit, cancellation, concurrency,
and actual interception; none is implied here.

Host root, authorizer/policy object, policy reference, recorder/sink, and optional
primitive boundary are constructor dependencies. Logical base and security/version
semantics are immutable module constants. There is no security-critical mutable module
global or singleton. Runtime dependencies added by EXP-014: none; production code uses
the standard library and existing SafetyBox types.

The recorder owns mutable per-instance sequence state and is explicitly single-process,
sequential, and not concurrency-safe. No global mutable request state was found. Initial
evidence assumes Linux, a local case-sensitive filesystem, process-owned temporary roots,
and same-filesystem rename. Every real filesystem development case uses a
`TemporaryDirectory`; `/etc/passwd` appears only as a rejected logical input string. No
home, root, SSH, service, repository, or production path is touched.

## Technical debt and reviewability

No `TODO`, `FIXME`, `XXX`, `HACK`, `pass`, `NotImplementedError`, deprecated shim, or
temporary security branch occurs in the new production code. No path allowlist,
`/public`/`/private` permission branch, development fixture ID, scenario, label, or task
category occurs in production filesystem authorization.

`FilesystemAdapter.execute` is the only unusually large new function. It is orchestration
heavy, but canonicalization, compound authorization, validation, primitives, state
observation, and event bridging remain separate inspectable modules. Refactoring it only
for line count before freeze would add change risk; its stage boundaries and single
monitor call remain explicit. The sensitive validator and primitive methods are small.

The development contamination inventory is the complete set in
`EXP-014-ADAPTER-DEVELOPMENT-VALIDATION.md`, augmented by the audit-time hostile mapper,
semantic digest mutation/equivalent-root, post-effect lifecycle failure, and normalized
legacy-M3 cases. Future held-out authors must avoid exact or renamed-template duplicates
of their paths, bytes, authority arrangements, and injection combinations.

## Acquirer-quality technical asset assessment

| Dimension | Result | Rationale |
|---|---|---|
| Modularity | `PASS` | Adapter core has no experimental-runner dependency. |
| Testability | `PASS` | Policy, root mapping, audit sink, and primitives are injected. |
| Explainability | `PASS` | Decisions, rules, resources, stages, and sequence links are reconstructable. |
| Failure honesty | `PASS` | Possible effects are indeterminate; rollback is never implied. |
| Claim discipline | `PASS` | FMED-L1 direct-route bypass and RTM-0 status are prominent. |
| Reuse | `PASS_WITH_LIMITATION` | Typed core suits later SDK/gateway/MCP wrapping; integration controls are absent. |
| Portability boundary | `PASS_WITH_LIMITATION` | Linux/local-filesystem assumptions are explicit; other platforms are untested. |
| Security reviewability | `PASS_WITH_LIMITATION` | Stage modules are small; top-level orchestration remains comparatively large. |

## Final validation and freeze record

| Gate | Result |
|---|---|
| Targeted filesystem suite | 91 passed |
| Full `pytest` | 276 passed |
| Full statement coverage | 96% (3,722 statements, 136 missed) |
| Filesystem/compound/monitor coverage | 98% (871 statements, 14 missed) |
| Frozen-era M1/M2 suites | 18 passed independently |
| Frozen-era M3/threat suites | 21 passed independently; one additive normalized-compatibility regression also passed |
| Ruff | pass |
| strict mypy | pass, 54 source files |
| `git diff --check` | pass |
| Markdown links | pass |
| JSON / YAML parsing | pass, 20 JSON and 12 YAML files |
| Requirement dispositions | 32/32, with REQ-030 explicitly evaluation-only |
| Development reconstruction | 10/10 successful operation shapes (100%) |
| EXP-014 corpus / results | absent / absent |

Frozen file SHA-256 values are:

| File | SHA-256 |
|---|---|
| `experiments/EXP-014/protocol.yaml` | `fd41816e6a3178e1d632f8f82ce10f7c70e488b06701b7be8f5615c5be333ade` |
| `docs/experiments/EXP-014-real-filesystem-mediation.md` | `704be16f851619708d009707e423a14b52351a69493cb62a33b05e895c5bff36` |
| `docs/research/REAL_FILESYSTEM_MEDIATION_REQUIREMENTS.md` | `9690b19019bf3e01d2237e6f9f179397a16d3c4958f30495ee25571eaa93fc5b` |
| `docs/architecture/REAL_FILESYSTEM_MEDIATION.md` | `09d4cd4ca7616ce2d185599a2499a19880d0c76478975e57314980ced7fb5283` |
| `docs/threat-model/REAL_FILESYSTEM_THREATS.md` | `cef7bc59239bdb472cc12af98ac3947834c889abfb1458964cb65ba8fa1352ad` |
| `docs/architecture/SAFETY_INVARIANTS.md` | `bd83bfd80f687515b1098a432992a2bedcc414c5e465c31032fc2d5dd0d5eaba` |

The implementation freeze SHA and push/clean-status evidence are recorded in the final
handoff because a commit cannot contain its own SHA.
