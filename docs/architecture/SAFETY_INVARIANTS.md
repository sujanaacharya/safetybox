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

## Status policy

Future statuses and evidence criteria require an ADR or verification plan. Unit tests alone cannot establish invariants that depend on OS isolation, deployment topology, or complete mediation. M1/M2 evidence does not establish complete mediation or capability confinement for operating systems, subprocesses, agent frameworks, malicious Python code, direct tool references, or alternate resource paths. Any claimed verification must name the version, environment, assumptions, and evidence artifact.
