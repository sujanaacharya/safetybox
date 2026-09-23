# Safety Invariants

These are **desired invariants**, not verified properties. Status is `DESIRED` until implementation, tests, and deployment assumptions support a stronger classification.

| ID | Desired invariant | Verification direction | Status |
|---|---|---|---|
| INV-001 | No tool action may execute before authorization is complete. | Controller/adapter ordering and crash-point tests. | DESIRED |
| INV-002 | A denied action must never be forwarded to the protected tool. | End-to-end denial and adapter-spy tests. | DESIRED |
| INV-003 | The monitored agent must not be able to directly modify SafetyBox policy. | Process/identity isolation and adversarial write tests. | DESIRED |
| INV-004 | Audit records for enforcement decisions must include the responsible policy/rule identifiers. | Schema validation and replay tests. | DESIRED |
| INV-005 | Capabilities must not silently expand during a session. | Monotonic-authority property tests and grant-event audit. | DESIRED |
| INV-006 | A quarantined session cannot perform privileged external actions. | State-machine and concurrency tests. | DESIRED |
| INV-007 | Every external action must be attributable to a session and task. | Adapter identity validation and orphan-action detection. | DESIRED |
| INV-008 | Policy evaluation failure defaults to a defined safe behavior. | Fault injection for each operation class. | DESIRED |
| INV-009 | Optional semantic or LLM signals cannot override a deterministic hard denial or maximum-privilege ceiling. | Decision-composition tests. | DESIRED |
| INV-010 | Authorization for one normalized request cannot be replayed for a different request, resource, session, or expired state. | Binding/replay and TOCTOU tests. | DESIRED |

## Status policy

Future statuses and evidence criteria require an ADR or verification plan. Unit tests alone cannot establish invariants that depend on OS isolation, deployment topology, or complete mediation. Any claimed verification must name the version, environment, assumptions, and evidence artifact.
