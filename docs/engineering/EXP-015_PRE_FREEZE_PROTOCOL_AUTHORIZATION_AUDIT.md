# EXP-015 Pre-Freeze Protocol and Authorization Quality Audit

**Audit ID:** `EXP-015-PRE-FREEZE-AUTHORIZATION-AUDIT@1`
**Decision:** `PASS_WITH_LIMITATION — FREEZE READY`
**Scope:** protocol/design and shared authorization architecture only
**Evidence class:** Level 0 design audit; no implementation, corpus, subprocess run, or result

## Starting state

The audit began from HEAD `d1053c26cdfad781894f57ecedefb07a39d84ca7` with the
uncommitted EXP-015 preregistration package as the candidate freeze set. SafetyBox is
version `0.0.0` and remains RTM-1.

| EXP-014 artifact | Frozen Git SHA |
|---|---|
| Protocol/design | `7baf20293caa83d3fff6a200174c4f8840918607` |
| Implementation | `b49a5cd0ff28a38eb8314291f51c106d2df9bd7c` |
| Corpus | `5ac7311bb8f086cca97f474069d068067ac73142` |
| Raw result | `17a0f6b6409ac85a2ee1a2d49f36a5748e3ab310` |
| Analysis/synthesis | `d1053c26cdfad781894f57ecedefb07a39d84ca7` |

EXP-014 protocol/design, implementation, corpus, and raw-result frozen paths have no diff
from their freeze commits. Corpus, raw-result, and analysis checksum manifests pass.

## Identifier governance

Repository-at-HEAD searches, excluding the uncommitted EXP-015 candidate, establish:

| Namespace | Result |
|---|---|
| Experiment | `EXP-001` through `EXP-014` were allocated; `EXP-015` is next. |
| Requirements | `REQ-001` through `REQ-032` were allocated; `REQ-033` through `REQ-062` were unused. |
| Invariants | `INV-001` through `INV-019` were allocated; `INV-020` through `INV-023` were next. |
| ADR | `ADR-001` through `ADR-006` existed; `ADR-007` was unused. |
| Claim | `CL-001` through `CL-010` existed; `CL-011` was next. |

Candidate cross-references resolve consistently after allocation; no collision required
renumbering.

## Protocol/document parity

The machine protocol, human protocol, requirements, architecture, threat extension, and
ADR agree on the following freeze values:

| Dimension | Frozen value | Result |
|---|---|---|
| Boundary | PMED-L1 adapter-routed direct child only | PASS |
| Shell | shell-false equivalent; shell grammar excluded | PASS |
| Executable | absolute lexical identity, exact v1 contract resource, post-allow native-object validation | PASS |
| PATH | no PATH, `which`, cwd, relative, or bare-name search | PASS |
| Argv | ordered literal data; no shell reconstruction or semantic authorization | PASS |
| Cwd | logical `/workspace`, separate capability, post-allow host validation | PASS |
| Environment | fixed `LANG`/`LC_ALL`; no PATH, inheritance, or caller values | PASS |
| Authorization | one TaskContract/Capability/TaskContractPolicy core | PASS |
| Compound decision | exec then cwd; all four combinations observed; no short circuit | PASS |
| Ordering | complete allow, validation, committed audit, then one spawn boundary | PASS |
| Output | untrusted bytes; 65,536-byte retention per stream; hash/count/truncation audit | PASS |
| Timeout/signals | 50–2,000 ms; TERM, 250 ms, KILL; effects may remain | PASS |
| Failure | exact terminal classes plus broad truthful families | PASS |
| Bypasses | direct process and shell routes explicit | PASS |
| Process tree | direct child only; descendants uncontrolled | PASS |
| Filesystem/network | allowed child activity is not confined by filesystem/network mediators | PASS |
| Metrics/gates | original strict gates plus zero authorization false allow/deny | PASS |
| Claim | bounded CL-011 wording only | PASS |
| Workflow | design freeze before implementation; implementation freeze before corpus | PASS |

Strict YAML parsing with duplicate-key rejection, required-field checks, and a parity
matrix over these values are freeze gates. Markdown-link and stable-ID validation are
also required.

## Authorization architecture finding

SafetyBox retains one authoritative authorization system:

```text
TaskContract
  -> Capability
  -> TaskContractPolicy
  -> shared compound authorization
  -> ReferenceMonitor
  -> one protected spawn boundary
```

No subprocess-specific allowlist, suspicious-string deny list, B4 decision, AI judge, or
adapter-local permission branch is permitted.

The important limitation is concrete: today's generic `CompoundAuthorizer` evaluates an
ordered resource tuple while keeping one action unchanged. EXP-015 needs two ordinary
actions, `process.exec` and `process.cwd`. Before adapter work, the shared authorization
layer must gain and freeze a generic ordered-`ActionRequest` composition that delegates
both components to the existing policy. This is a reusable authorization-core evolution,
not process-specific permission logic, so it does not block protocol freeze.

## Authorization decision discipline

Hard authorization answers only whether authority exists. Validation decides whether an
allowed host object satisfies execution constraints. Tool outcome reports what happened
after spawn. Behavior analysis reports suspiciousness. These classifications do not
rewrite one another.

- An authorized symlinked executable is `ALLOW` followed by validation rejection, not an
  authorization false deny.
- An authorized cwd that disappears remains `ALLOW` followed by validation/tool error.
- Exit 1, timeout, signal, and post-spawn failure are not authorization failures.
- Shell-looking argv remains literal data and does not become a keyword-based denial.
- B4/context/risk/AI signals cannot silently grant or deny hard authority.

The derived authorization measures are:

- false-allow rate: authority-negative cases receiving compound `ALLOW` divided by all
  authority-negative cases, target 0;
- false-deny rate: authority-positive cases receiving compound `DENY` divided by all
  authority-positive cases, target 0; and
- realized false-allow count: authority-negative cases invoking spawn, target 0.

## Provenance and explanation

Every future component decision must identify subject/session, task, normalized action
and resource, matched or absent capability, rule ID, authority-source contract
reference/version/hash, compound component, decision, and deterministic reason. A vague
“not permitted” or risk score is insufficient.

Task ID binding exists in M2. Session is currently audit/request provenance rather than
an authenticated `TaskContract` field. The implementation/harness must establish and
test trusted contract-to-session binding before implementation freeze; no deployment-
wide session-isolation claim is made now.

## AI, approval, and attenuation

AI may propose capabilities and roles to a trusted reviewer but cannot issue, expand, or
override authority. `REQUIRE_APPROVAL` is future architecture, not an EXP-015 outcome: a
trusted external actor would issue a new versioned authority object after approval.

Process capabilities can be attenuated at the current action/resource-set level by
issuing a strict-subset contract. Delegation is not implemented. Parent/child, actor and
session binding, issuer/derivation provenance, constraint subset proofs, revocation,
expiry, and confused-deputy controls remain schema/enforcement gaps.

## Future corpus quality gate

No corpus was authored. The frozen protocol requires difficult benign authorized cases,
matched authority-only counterfactuals, all four compound combinations, task-confusion
pairs, near-boundary executable/cwd resources, and explicit authorization-versus-
validation/tool-outcome pairs. This enables false-deny measurement and punishes
keyword/path overblocking.

EXP-015 cases may later inform a separately registered authorization benchmark covering
false allow/deny, compound decisions, task/resource binding, attenuation/delegation,
approval escalation, and hard benign cases. No benchmark is created here.

## Technical diligence assessment

| Question | Assessment | Limitation |
|---|---|---|
| One authorization core? | PASS | None at design level. |
| Reusable compound authorization? | PASS_WITH_LIMITATION | Generic distinct-action composition must be added before the adapter. |
| Clear trust boundary? | PASS | Child, argv, output, cwd/executable input remain untrusted. |
| No process-specific shadow policy? | PASS | Must remain an implementation-freeze gate. |
| False allow/false deny explicit? | PASS | Evidence awaits held-out corpus. |
| Policy vs validation separated? | PASS | Implementation must preserve separate records. |
| Policy vs behavior separated? | PASS | Future containment composition remains undesigned. |
| Deterministic explanations? | PASS_WITH_LIMITATION | Current M2 lacks contract/capability stable identity/version fields. |
| Typed future API? | PASS | Request, result, and terminal semantics are fixed conceptually. |
| Injectable audit/process boundary? | PASS | No implementation exists yet. |
| Bypass boundaries explicit? | PASS | PMED-L1 remains route-dependent. |
| Extensible toward network/MCP? | PASS_WITH_LIMITATION | Boundaries are explicit; those adapters and shared identities remain future work. |

Overall assessment: `PASS_WITH_LIMITATION`. The limitations are explicit pre-
implementation gates and do not make the research question, metrics, or claim ambiguous.

## Validation record

- `pytest`: 292 passed.
- `pytest --cov=safetybox`: 292 passed; total coverage 95%.
- `ruff check .`: passed.
- `mypy src`: passed for 55 source files.
- `git diff --check`: passed.
- strict YAML parse with duplicate-key rejection: passed.
- protocol/document parity, stable-ID sequence, experiment registry, and Markdown links:
  passed.
- EXP-014 corpus, raw-result, and analysis checksum manifests: passed.
- EXP-014 frozen-path diff checks: no changes.
- process adapter/helper, EXP-015 corpus, and EXP-015 results: absent.

## Freeze gates and decision

The audit found no reason to weaken a success criterion or materially revise the
scientific question. Freeze is approved only with these immutable interpretations:

- one shared deterministic authorization core;
- zero authorization false allows and false denies on frozen evaluable cases;
- separate authorization, validation, behavior, and tool-outcome records;
- all four executable/cwd compound combinations with both subdecisions;
- argv as data, not authority;
- no target-dependent host probing before authorization;
- one narrow spawn primitive;
- truthful timeout/partial-effect semantics;
- explicit direct-route, descendant, filesystem, and network limitations; and
- implementation freeze before any held-out corpus authorship.

No process adapter, helper, corpus, result, benchmark, maturity upgrade, AI authorization,
or supported CL-011 claim is part of this freeze.
