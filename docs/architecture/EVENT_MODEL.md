# Event Model

## Canonical event

A SafetyBox event is an immutable logical record of an observed request, decision, state transition, or result. The schema below is conceptual and will be versioned before implementation.

| Field | Purpose |
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

## Initial event types

`SESSION_STARTED`, `TASK_REGISTERED`, `MODEL_OUTPUT`, `TOOL_REQUESTED`, `TOOL_ALLOWED`, `TOOL_DENIED`, `FILE_READ`, `FILE_WRITE`, `NETWORK_REQUEST`, `SHELL_EXECUTION`, `DATABASE_QUERY`, `CAPABILITY_GRANTED`, `CAPABILITY_REVOKED`, `POLICY_VIOLATION`, `RISK_CHANGED`, `APPROVAL_REQUESTED`, `SESSION_PAUSED`, `SESSION_QUARANTINED`, and `SESSION_TERMINATED`.

Execution-attempt and execution-result distinctions may require additional types in the first schema ADR; an allowed request is not proof that a tool executed successfully.

## Ordering requirements

Within a session, committed sequence numbers are unique and strictly increasing. Authorization events precede tool invocation; result events follow the corresponding invocation; state transitions become visible in commit order. Wall-clock timestamps cannot establish order because clocks can jump, collide, or differ across hosts. Monotonic sequence numbers support deterministic replay, trajectory windows, race analysis, and audit completeness.

Cross-session order is partial unless a trusted coordinator defines it. Distributed producers require an ingestion/commit protocol; producer-supplied numbers or timestamps are not authoritative. Gaps, duplicates, late events, and correlation mismatches must generate explicit integrity failures rather than silent repair.

## Data handling

Events minimize sensitive content. Summaries use structured redaction; full payloads, when necessary, live in access-controlled storage referenced by content hash. Unknown schema fields must follow declared compatibility rules, and event schema/version is recorded in every stream or record.
