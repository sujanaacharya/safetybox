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
| INV-016 | A denied adapter-routed real filesystem mutation must neither invoke the protected mutation primitive nor change protected filesystem state. | Primitive-spy evidence plus operation-appropriate before/after state digests on the frozen real-tool corpus. | DESIRED for EXP-014; no real filesystem adapter or evidence exists. |
| INV-017 | A denied adapter-routed filesystem read, list, or stat must not invoke the protected retrieval primitive or return protected bytes, names, or metadata. | Primitive-spy and caller-result nondisclosure tests on the frozen real-tool corpus. | DESIRED for EXP-014; no real filesystem adapter or evidence exists. |
| INV-018 | Filesystem canonicalization must not expand capability scope, and the canonical resource authorized must identify the exact path supplied to the protected primitive. | Traversal, prefix, Unicode, symlink, hard-link, rename, and argument-binding tests. | DESIRED for EXP-014; TOCTOU is explicitly `NOT_SOLVED` before implementation. |
| INV-019 | A required control or audit failure before filesystem execution must prevent the protected operation; a failure after primitive start must not be reported as denial or proven rollback. | Fault injection at every lifecycle boundary with invocation and post-state evidence. | DESIRED for EXP-014; M3 supplies only the in-process logical precursor semantics. |

## Status policy

Future statuses and evidence criteria require an ADR or verification plan. Unit tests alone cannot establish invariants that depend on OS isolation, deployment topology, or complete mediation. M1/M2 evidence does not establish complete mediation or capability confinement for operating systems, subprocesses, agent frameworks, malicious Python code, direct tool references, or alternate resource paths. Any claimed verification must name the version, environment, assumptions, and evidence artifact.

M4 supplies deterministic regression scenarios that exercise the existing in-process evidence for INV-001, INV-002, INV-004, INV-005, and INV-011. It does not strengthen their stated status or establish any deployment-wide property.

Direct filesystem access outside the future adapter is not assigned an invariant ID:
it is an explicit FMED-L1 exclusion. An agent with `os.*`, `pathlib`, shell, native code,
or another unwrapped route can bypass adapter-level mediation. EXP-014 requires this
boundary to be demonstrated and reported.
