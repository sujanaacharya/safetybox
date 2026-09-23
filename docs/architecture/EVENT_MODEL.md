# Event Model

## Implemented in M3: canonical event

A `SafetyBoxEvent` is an immutable logical record of one `ReferenceMonitor` request lifecycle observation. M3 emits unique `event_id`, session/task/request/correlation identifiers, session-local `sequence_number`, actor/action/resource, typed `event_type`, UTC `timestamp`, optional policy `decision`/`rule_id`, optional `executed` state, `parent_event_id`, and immutable metadata.

`sequence_number` is the authoritative ordering mechanism. `timestamp` is observational UTC metadata and must never be used to order events.

| Future conceptual extension | Purpose |
|---|---|
| `event_id` | Globally unique event identity. |
| `session_id` / `task_id` | Attribution to runtime session and declared task. |
| `timestamp` | SafetyBox-observed wall-clock time with source/precision; not the ordering authority. |
| `sequence_number` | Monotonically increasing session-local commit order. |
| `actor` | Authenticated source principal/component. |
| `event_type` | Canonical type from the versioned registry. |
| `action` / `resource` | Normalized operation and target, when applicable. |
| `arguments_summary` / `result_summary` | Redacted structured summaries plus hashes/references for governed details. |
| `policy_decision` | Outcome, reason, rule IDs, and policy version where applicable. |
| `risk_before` / `risk_after` | Experimental state around the event, not an assertion of intent. |
| `parent_event_id` | Direct causal predecessor where defined. |
| `correlation_id` | Groups request, authorization, execution, and result events. |
| `metadata` | Schema/engine/adapter versions, provenance, integrity, and extension fields. |

## Implemented event types

`ACTION_REQUESTED`, `AUTHORIZATION_STARTED`, `AUTHORIZATION_ALLOWED`, `AUTHORIZATION_DENIED`, `AUTHORIZATION_FAILED`, `EXECUTION_STARTED`, `EXECUTION_SUCCEEDED`, and `EXECUTION_FAILED` are a strongly typed enum. M3 does not implement session, risk, trajectory, quarantine, capability-lifecycle, or provider events.

Execution-attempt and execution-result distinctions may require additional types in the first schema ADR; an allowed request is not proof that a tool executed successfully.

## Ordering requirements

Within a session, accepted events have unique, strictly increasing sequence numbers beginning at 1. `AuditRecorder` assigns them only after its sink accepts the event; an audit failure does not consume a number in this single-process model. Independent sessions each begin at 1. This does not solve concurrent writers, multi-process ordering, distributed clocks, or cross-session causality.

For M3, all events for one `ActionRequest` use its `request_id` as their `correlation_id`; distinct request IDs therefore identify distinct traces. Each lifecycle event points to its direct predecessor with `parent_event_id`.

Cross-session order is partial unless a trusted coordinator defines it. Distributed producers require an ingestion/commit protocol; producer-supplied numbers or timestamps are not authoritative. Gaps, duplicates, late events, and correlation mismatches must generate explicit integrity failures rather than silent repair.

## Data handling

Events do not automatically copy arbitrary request arguments, tool results, or prompts. Metadata is recursively immutable but is not a general payload store. Secret-redaction guarantees, schema versioning, durable storage, and governed payload references are not implemented in M3.
