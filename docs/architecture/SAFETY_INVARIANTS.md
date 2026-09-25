# Safety Invariants

These are **desired invariants**, not verified properties beyond the scope named in their status. Status is `DESIRED` until implementation, tests, and deployment assumptions support a stronger classification.

| ID | Desired invariant | Verification direction | Status |
|---|---|---|---|
| INV-001 | No tool action may execute before authorization is complete. | Controller/adapter ordering and crash-point tests. | Implemented and covered by unit tests in M1 and through `TaskContractPolicy` in M2 for the in-process `ReferenceMonitor` API. |
| INV-002 | A denied action must never be forwarded to the protected tool. | End-to-end denial and adapter-spy tests. | Implemented and covered by unit tests in M1 and M2 for the in-process `ReferenceMonitor` API. |
| INV-003 | The monitored agent must not be able to directly modify SafetyBox policy. | Process/identity isolation and adversarial write tests. | DESIRED |
| INV-004 | Audit records for enforcement decisions must include the responsible policy/rule identifiers. | Schema validation and replay tests. | Implemented and unit-tested for `ReferenceMonitor` authorization events in M3's single-process in-memory audit model. |
| INV-005 | Capabilities must not silently expand during a session. | Monotonic-authority property tests and grant-event audit. | Implemented and covered by unit tests in M2 only for immutable in-process `TaskContract` capability collections; no runtime attenuation, delegation, or OS-level confinement is implemented. |
| INV-006 | A quarantined session cannot perform privileged external actions. | State-machine and concurrency tests. | DESIRED |
| INV-007 | Every external action must be attributable to a session and task. | Adapter identity validation and orphan-action detection. | DESIRED |
| INV-008 | Policy evaluation failure defaults to a defined safe behavior. | Fault injection for each operation class. | Implemented and covered by a unit test in M1 for authorizer failure: `AuthorizationFailure` is raised and the in-process protected tool is not invoked. |
| INV-009 | Optional semantic or LLM signals cannot override a deterministic hard denial or maximum-privilege ceiling. | Decision-composition tests. | DESIRED |
| INV-010 | Authorization for one normalized request cannot be replayed for a different request, resource, session, or expired state. | Binding/replay and TOCTOU tests. | DESIRED |
| INV-011 | Within a session, emitted SafetyBox audit events have unique monotonically increasing sequence numbers. | Sequence and session-independence tests. | Implemented and unit-tested in M3's single-process, non-concurrent audit model. |
| INV-012 | M5 trajectory findings are derived only from supplied ordered canonical observations within their session/task boundary and cannot directly execute protected tools. | Ordering, session/task-isolation, and monitor-boundary unit tests. | Implemented and unit-tested for the in-process M5 monitor; it does not establish complete detection. |
| INV-013 | Context semantics must not grant authority absent from `TaskContract`. | Bidirectional authorization/context separation tests. | Implemented and unit-tested for the M5.1-A value model and M5.1-B evaluator: `TaskContext` is not accepted by the authorization path, evaluation copies rather than changes the prior decision/execution outcome, and context consistency cannot turn an M2 denial into authority. |
| INV-014 | Context-aware trajectory findings cannot grant authority or execute protected actions. | Interface-boundary, authorization-preservation, and absence-of-execution-path tests. | Implemented and unit-tested for the in-process M5.1-C monitor; this does not establish complete mediation or detection correctness. |
| INV-015 | B4 historical semantic state and findings cannot grant authorization or execute protected actions. | Interface-boundary, authority-preservation, immutable-context, and absence-of-execution-path tests. | Implemented and unit-tested for `B4-BOUNDED-CONTEXT-TRAJECTORY@1`; this does not establish complete mediation, declaration correctness, or detection accuracy. |
| INV-016 | A denied adapter-routed real filesystem mutation must neither invoke the protected mutation primitive nor change protected filesystem state. | Primitive-spy evidence plus operation-appropriate before/after state digests on the frozen real-tool corpus. | DESIRED repository-wide; scoped EXP-014 evidence is attached below. |
| INV-017 | A denied adapter-routed filesystem read, list, or stat must not invoke the protected retrieval primitive or return protected bytes, names, or metadata. | Primitive-spy and caller-result nondisclosure tests on the frozen real-tool corpus. | DESIRED repository-wide; scoped EXP-014 evidence is attached below. |
| INV-018 | Filesystem canonicalization must not expand capability scope, and the canonical resource authorized must identify the exact path supplied to the protected primitive. | Traversal, prefix, Unicode, symlink, hard-link, rename, and argument-binding tests. | DESIRED repository-wide; scoped static-path evidence is attached below and TOCTOU remains not established. |
| INV-019 | A required control or audit failure before filesystem execution must prevent the protected operation; a failure after primitive start must not be reported as denial or proven rollback. | Fault injection at every lifecycle boundary with invocation and post-state evidence. | DESIRED repository-wide; scoped EXP-014 failure-semantics evidence is attached below. |
| INV-020 | A denied adapter-routed subprocess request must not invoke the protected process-spawn primitive or create an adapter child. | Primitive-spy count, child-created state, and absence of PID/output/terminal child fields for every denied case. | DESIRED; EXP-015 Level 0 design only. |
| INV-021 | Complete executable and cwd authorization, required validation, and committed pre-spawn audit must precede process-spawn primitive invocation. | Canonical sequence evidence plus primitive-boundary ordering and fault injection. | DESIRED; EXP-015 Level 0 design only. |
| INV-022 | On the shell-false route, each declared argv element must reach the direct child as exactly one element without shell reinterpretation. | Controlled-helper tuple comparison over registered metacharacter, whitespace, quote, wildcard, empty, and Unicode cases. | DESIRED; EXP-015 Level 0 design only. |
| INV-023 | A required audit failure before spawn must prevent process creation; an audit failure after spawn must not be reported as denial, not executed, or rolled back. | Pre/post-spawn audit fault injection with primitive invocation, child-created state, and terminal truthfulness checks. | DESIRED; EXP-015 Level 0 design only. |
| INV-024 | `NO_UNAUTHORIZED_PROTECTED_EFFECT`: every occurred protected effect in a declared surface must be covered by valid authority for its subject, task, action, resource, constraints, and time. | Independent authority and effect oracles over an enumerated mediator/primitive surface. | DESIRED; no repository-wide unauthorized-effect experiment exists. |
| INV-025 | `NO_CROSS_TASK_AUTHORITY_REUSE`: authority bound to one task cannot authorize or be replayed for another task. | Counterfactual task-binding, cache/replay, session, and delegated-lineage tests. | DESIRED repository-wide; bounded logical authorization evidence does not establish authenticated identity or complete mediation. |
| INV-026 | `NO_AGENT_SELF_AUTHORITY_EXPANSION`: agent output, self-issued metadata, or an agent-controlled state transition cannot create, replace, or enlarge authority. | Issuer authentication, negative construction tests, mutation attempts, and trust-boundary review. | DESIRED; no authenticated issuer or Authority V2 implementation exists. |
| INV-027 | `NO_AUTHORITY_AMPLIFICATION`: derived, compiled, approved, or delegated authority cannot exceed its valid authority source across any constrained dimension. | Formal subset verification plus property, boundary, and malformed-chain tests. | DESIRED; bounded specification-level AUTH-COVERAGE-001 checks do not establish runtime delegation semantics. |
| INV-028 | `AI_CONTEXT_CANNOT_GRANT_AUTHORITY`: model output, prompt text, memory, retrieved context, trajectory findings, or suspiciousness/innocence assessments cannot create authority or override deterministic denial. | Interface/type separation and bidirectional noninterference tests across compiler, policy, and monitor boundaries. | DESIRED program-wide; INV-013 through INV-015 provide bounded in-process evidence for existing context paths only. |
| INV-029 | `DENIED_ACTION_NEVER_REACHES_PROTECTED_PRIMITIVE`: a deterministically denied action cannot be forwarded to any in-scope protected primitive. | Per-route primitive spies, direct controls, concurrency/failure injection, and independent effect observation. | DESIRED across protected surfaces; INV-002, EXP-014, and EXP-015 support only named bounded routes. |
| INV-030 | `EVERY_PROTECTED_EFFECT_HAS_AUTHORITY_PROVENANCE`: every occurred protected effect has an immutable, reconstructable link to the responsible request and either the exact valid authority or a verified `NO_VALID_AUTHORITY` violation disposition, including issuer and delegation/approval lineage where applicable. | Independent effect inventory joined to durable provenance with orphan, ambiguity, loss, and tamper tests. | DESIRED; current audit is in-process and non-durable. |
| INV-031 | `AMBIGUOUS_AUTHORITY_NEVER_SILENTLY_ALLOWS`: missing, conflicting, unverifiable, or semantically ambiguous authority cannot produce an unqualified allow. | Malformed/conflict/property tests with explicit deny, abstain, or external-approval outcomes. | DESIRED; a complete ambiguity and abstention model is not implemented. |
| INV-032 | `DELEGATED_AUTHORITY_IS_SUBSET_OF_PARENT`: every child authority is no broader than every required valid parent across principal/task, action, resource, constraints, time, usage, destination, and delegation depth. | Formal partial-order proof, chain validation, adversarial composition, and concurrency tests. | DESIRED; delegation is not implemented. |
| INV-033 | `REVOKED_OR_EXPIRED_AUTHORITY_CANNOT_AUTHORIZE_NEW_EFFECTS`: after the specified revocation/expiry commit point, that authority and affected descendants cannot authorize a new protected effect. | Clock/revocation-state semantics, cached-decision invalidation, child propagation, race, and in-flight boundary tests. | DESIRED; revocation and expiry semantics are specification work. |

## Status policy

Future statuses and evidence criteria require an ADR or verification plan. Unit tests alone cannot establish invariants that depend on OS isolation, deployment topology, or complete mediation. M1/M2 evidence does not establish complete mediation or capability confinement for operating systems, subprocesses, agent frameworks, malicious Python code, direct tool references, or alternate resource paths. Any claimed verification must name the version, environment, assumptions, and evidence artifact.

INV-024 through INV-033 are the coherent unauthorized-effect and authority-lifecycle
family. They strengthen and organize existing narrower invariants without retroactively
changing the meaning or evidence status of INV-001 through INV-023. In particular,
authorization correctness cannot establish INV-024 without real-effect and mediation
evidence, and a passed adapter test cannot establish INV-029 outside its registered route.

M4 supplies deterministic regression scenarios that exercise the existing in-process evidence for INV-001, INV-002, INV-004, INV-005, and INV-011. It does not strengthen their stated status or establish any deployment-wide property.

Direct filesystem access outside the future adapter is not assigned an invariant ID:
it is an explicit FMED-L1 exclusion. An agent with `os.*`, `pathlib`, shell, native code,
or another unwrapped route can bypass adapter-level mediation. EXP-014 requires this
boundary to be demonstrated and reported.

Direct process execution outside a future subprocess adapter is likewise not assigned a
universal prevention invariant. `INV-020` through `INV-023` apply only to the proposed
PMED-L1 adapter route. Direct `subprocess`, `os.system`, shell, native process APIs,
allowed-child descendants, and allowed-child filesystem/network activity remain explicit
boundaries. No implementation or evidence is attached to these proposed invariants.

## EXP-014 scoped evidence attachment

Repository-wide status remains `DESIRED` for INV-016 through INV-019 because the current
status vocabulary has no evidence-qualified scoped state and none of these properties is
established across deployment routes. `EXP-014-ANALYSIS-001` attaches the following
bounded evidence without changing those global statuses:

| Invariant | Scoped evidence | Interpretation |
|---|---|---|
| INV-016 | 19/19 policy-denied adapter-routed mutations had no wrapped primitive invocation and no independently observed state change. | `SUPPORTED_WITHIN_EXP_014_FMED_L1`; strong within the tested sequential temporary-filesystem scope. |
| INV-017 | 9/9 policy-denied read/list/stat cases had no protected primitive call or protected result in evaluated channels. | `SUPPORTED_WITHIN_EXP_014_FMED_L1`; process/debug channels were not captured. |
| INV-018 | A separate protocol-derived canonicalizer matched 70/70 registered cases; static symlink/hard-link and compound-rename outcomes matched. | `SUPPORTED_WITHIN_EXP_014_FMED_L1_STATIC_PATH_STATE_ONLY`; TOCTOU remains not established. |
| INV-019 | 5/5 registered pre-effect fail-closed cases and 2/2 registered indeterminate cases had the expected outcome. | `SUPPORTED_WITHIN_EXP_014_FMED_L1`; small denominators and mostly injected failures limit strength. |

The evidence source is the frozen `EXP-014-RUN-001` plus
[`EXP-014-VALIDITY-AUDIT.md`](../experiments/EXP-014-VALIDITY-AUDIT.md). It does not extend
to direct routes, races, concurrency, durable audit, non-Linux filesystems, or production
deployment.
