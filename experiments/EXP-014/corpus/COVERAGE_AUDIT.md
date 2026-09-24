# EXP-014 Corpus Coverage Audit

All counts are scenario/session units. Events, audit records, endpoint subdecisions, and
primitive calls are not independent examples. `VR` means post-allow target-validation
rejection; `FC` excludes those validation rejections; `FI` means fail-indeterminate; and
`BYP` is the expected direct FMED-L1 control.

## Operation × terminal outcome

| Operation | Allow | Policy deny | VR | Tool error | FC | FI | BYP | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| append | 5 | 3 | 2 | 0 | 1 | 1 | 0 | 12 |
| create | 3 | 2 | 1 | 2 | 0 | 0 | 0 | 8 |
| delete | 4 | 2 | 1 | 1 | 0 | 0 | 0 | 8 |
| list | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 6 |
| mkdir | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| read | 6 | 3 | 3 | 2 | 0 | 0 | 0 | 14 |
| rename | 2 | 9 | 4 | 0 | 1 | 0 | 0 | 16 |
| stat | 5 | 4 | 3 | 0 | 2 | 0 | 0 | 14 |
| write | 7 | 2 | 2 | 1 | 1 | 1 | 2 | 16 |
| **Total** | **36** | **28** | **17** | **6** | **5** | **2** | **2** | **96** |

Every frozen operation has at least one successful authorized case and one policy denial.
The corpus supplies 19 denied mutation units and nine denied retrieval units: read 3,
list 2, and stat 4.

## Requirement × scenarios

| Requirement | Coverage |
|---|---|
| REQ-001 | `FSH-014-091/092` delimit FMED-L1; direct routes are excluded from adapter correctness. |
| REQ-002 | Every fixture is a logical namespace mapped only into a fresh temporary root. |
| REQ-003 | All nine operations; operation-specific request schema tests reject invalid records. |
| REQ-004 | `019-022` and all per-operation matched pairs prevent action implication. |
| REQ-005 | Every path/name/content/request remains untrusted fixture data; the TCB is unchanged. |
| REQ-006 | `002`, `016`, `018`, `020`, `028`, `030` plus label-sentinel isolation checks. |
| REQ-007 | All 94 adapter-route scenarios require the canonical policy/monitor route; no corpus allow path exists. |
| REQ-008 | Bound request fields in all cases; rename and byte-bearing examples emphasize argument identity. |
| REQ-009 | 91 authorization-metric members cover grants, missing action, resource mismatch, and task mismatch. |
| REQ-010 | Policy-denial, post-allow validation, pre-audit, and post-start pairs expose ordering. |
| REQ-011 | Relative, absolute logical, dot, separator, trailing, and Unicode request spellings. |
| REQ-012 | `003-008`, `023-030`, `079/080`, and `095/096`. |
| REQ-013 | Host mapping remains a future-runner lexical step for every adapter route; `096` rejects host namespace. |
| REQ-014 | Absent create/mkdir leaves, missing parent, existing create target, and rename destinations. |
| REQ-015 | `033-066`: ten symlink rejections and seven hard-link rejection operations. |
| REQ-016 | State scopes are required for every mutation and both rename endpoints/parents. |
| REQ-017 | All 19 denied mutation units require unchanged state and zero requested primitive calls. |
| REQ-018 | Read/list/stat denial denominators are 3/2/4 with corpus-only sentinels/names/sizes. |
| REQ-019 | 16 rename units cover allow/allow, allow/deny, deny/allow, deny/deny, links, and failures. |
| REQ-020 | File/empty-dir delete, non-empty delete error, mkdir, root/nested list, and directory rename. |
| REQ-021 | Frozen result categories plus richer validation/direct-control classification are explicit. |
| REQ-022 | `080`, `082`, `084`, `086`, `096` cover lexical, authorization, validation, and pre-audit closure. |
| REQ-023 | `078`, `087-090` cover definitely pre-effect error, partial effect, and post-effect audit loss. |
| REQ-024 | Every adapter attempt requires reconstruction; compound rename cases require two subdecisions. |
| REQ-025 | Runtime contents never enter labels; future audit checks raw content/name/metadata absence. |
| REQ-026 | Traversal, host path, prefix, Unicode, links, rename escape, nested/missing parents, and direct routes. |
| REQ-027 | `091/092`; `091` is the specifically required direct `os.open`-style demonstration. |
| REQ-028 | Task mismatch `021/022`, unique session/task/request binding, and repeated denied rename `093`. |
| REQ-029 | Deterministic fixture hashes/materialization plus repeated allow `001` and deny `093`. |
| REQ-030 | Future runner records adapter/authorization/audit timing for all 94 adapter routes; no threshold. |
| REQ-031 | Freeze order, contamination inventory, source isolation, checksums, and no prediction execution. |
| REQ-032 | Every scenario declares Linux/local case-sensitive assumptions; link support is explicit. |

REQ-005, REQ-007, REQ-013, REQ-016, REQ-024, REQ-025, REQ-030, REQ-031, and
REQ-032 have architectural or runner components in addition to scenario evidence. They are
not falsely represented as reducible to one labeled request.

## Invariant × scenarios

| Invariant | Coverage |
|---|---|
| INV-016 | 19 denied mutations; authorization/validation/pre-audit failures; before/after state domains include endpoints, parents, roots, and aliases. |
| INV-017 | Denied read/list/stat denominators 3/2/4 with caller result, error, audit, serialized event, and primitive-spy checks preregistered. |
| INV-018 | Lexical aliases, prefix collisions, Unicode, ten symlink topologies, seven hard-link operations, and 16 rename cases. |
| INV-019 | Authorization exception, lexical rejection, validator exception, pre-audit rejection, partial write, and post-effect audit rejection. |

## Threat × scenarios or disposition

| Threat | Scenarios/disposition |
|---|---|
| Path traversal | `007/008`, `079/080` |
| Prefix collision | `023-030`, `095` |
| Host/logical confusion | `096` |
| Unicode/path confusion | `003/004`, `015/016` |
| Symlink escape | `033-052` |
| TOCTOU/symlink swap | `NOT_EVALUATED`: frozen protocol says `NOT_SOLVED`; no race harness. |
| Hard-link alias | `053-066`; unsupported link creation is reported, not passed. |
| Rename escape | all 16 rename units |
| Delete overbreadth | `009/010`, `025/026`, `075/076` |
| Protected-read disclosure | denied retrievals `002`, `016`, `018`, `020`, `028`, `030` plus link-denial retrievals |
| Partial write | `087/088` |
| Audit loss before effect | `085/086` |
| Audit loss after effect | `089/090` |
| Context mismatch | `021/022`; unique session/task identities throughout |
| Direct API bypass | `091/092` |
| Inherited descriptor bypass | `NOT_EVALUATED`: no platform descriptor fixture supplied. |
| Corpus overfitting | Freeze chronology, opaque IDs, import audit, contamination audit, and no prediction run. |

## Success-criterion measurability

| Frozen criterion | Corpus/runner measurement |
|---|---|
| Authorization correctness | 91 cases with explicit expected decisions; join labels after canonical records. |
| Denied mutation prevention | 19 denied mutation scenarios; primitive spy and identical pre/post state digest. |
| Read nondisclosure | 3 policy-denied reads; sentinel absent from result/error/audit/events and zero read primitive. |
| List nondisclosure | 2 policy-denied lists; child names absent from result/error/audit/events and zero list primitive. |
| Stat nondisclosure | 4 policy-denied stats; protected type/size absent and zero stat primitive. |
| Ordering | Session-local sequence checks on all 94 adapter-route attempts. |
| Audit reconstruction | Required envelope/provenance fields on every adapter attempt; two subdecisions for rename. |
| Canonicalization correctness | Valid aliases have expected identity; root escape/host path reject; policy/physical pairs isolate later stages. |
| Adapter-routed bypass prevention | Prefix, traversal, symlink, hard-link, rename, and host-logical groups. |
| FMED-L1 boundary | Two separately reported direct controls; excluded from adapter denominator. |
| Determinism | Rebuild every fixture twice; repeat `001` and `093`; exclude timestamps/UUIDs. |
| Frozen regression | Future run invokes the frozen repository regression suite as a separate no-tuning gate. |

REQ-030 timing is also measurable for all adapter routes: sample count, minimum, median,
mean, p95, and p99 are reported only where sample volume is sufficient, with no acceptance
threshold.

## Catastrophic failure-criterion detectability

| Failure criterion | Detecting corpus evidence |
|---|---|
| Denied mutation executes | 19 denied mutation state/primitive checks. |
| Denied retrieval discloses | Separate read/list/stat sentinels, names, and sizes. |
| Execution before allow / execution event on deny | All adapter lifecycles; especially matched authorization-before-validation pairs. |
| Symlink escape | Ten distinct authorized-then-rejected topologies. |
| Traversal escape / scope expansion | Root escape, in-root cancellation, repeated separator, Unicode, prefix, host path. |
| Rename escape | Source/destination decision matrix plus link and prefix endpoints. |
| False audit account | Partial-write and post-effect audit pairs with measured post-state. |
| Corpus-specific branch | Production-source identifier scan and loader import isolation. |
| Nondeterminism | Two explicit repeated sessions plus deterministic fixture rebuild. |
| Unreconstructable attempt | Every adapter route requires ingress-to-terminal reconstruction fields. |

## Family detail

- Canonicalization: relative/absolute logical forms, dot, nested dot-dot cancellation,
  repeated/trailing separators, NFC normalization, root boundary, root escape, host
  absolute namespace, and four component-prefix adversaries.
- Symlinks: terminal relative/absolute, intermediate relative/absolute, chain, dangling
  final/intermediate, rename source, rename destination parent, and create ancestor.
- Hard links: read, write, append, delete-file, stat-file, rename source, and existing
  rename destination, with ordinary single-link controls and environment gating.
- Failures: missing required file, missing parent, wrong type, existing create target,
  non-empty delete target, permission-like pre-effect primitive error, authorization
  exception, canonicalization rejection, physical-validator exception, pre-execution audit
  rejection, partial write, and post-effect audit rejection.
- Nondisclosure: protected read bytes, list child names, and stat type/size are distinct and
  never copied into scoring metadata.

**Coverage decision: PASS for corpus freeze.** Empirically testable requirements and all
four new invariants have scenario coverage; inherently architectural gates remain explicit
runner/source audits rather than invented per-scenario labels.
