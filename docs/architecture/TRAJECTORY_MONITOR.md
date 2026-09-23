# Trajectory Monitor

## Implemented in M5: minimal deterministic observational monitor

M5 uses these terms precisely: an **action** is one requested tool/resource operation; an **event** is one M3 audit record for action processing; a **trajectory** is an ordered sequence of relevant events/actions within a session and task; a **trajectory rule** is a deterministic predicate over bounded trajectory state; and a **finding** is structured evidence that a rule matched. A finding is not the primitive “attack detected”; interpretation and containment remain later policy concerns.

M5 consumes the canonical M3 `SafetyBoxEvent` stream and derives a compact `CompletedActionObservation` only from terminal `EXECUTION_SUCCEEDED` and `AUTHORIZATION_DENIED` events. The observation retains session/task/request identity, action/resource, decision/execution state, authoritative sequence number, and canonical event ID; it is not a second telemetry format or source of truth. Successful execution is required for the collection-to-egress rule, while explicit denied attempts are used for probing.

`TrajectoryMonitor` maintains a configurable bounded deque per `(session_id, task_id)` (default: eight completed observations). Session sequence numbers are checked on every canonical event: duplicate or decreasing values raise `TrajectoryOrderingError`; gaps are accepted without reordering because a filtered delivery stream may omit events. The bound is an M5 implementation choice, not a calibrated scientific value: smaller windows can miss longer patterns and larger windows increase memory and incidental matches.

M5 is strictly observational. It cannot invoke tools, authorize requests, change `TaskContract` authority, mutate capabilities, or block `ReferenceMonitor` execution. Findings are immutable evidence for later policy/containment research.

M5 is frozen as the EXP-012 sequence-only baseline. M5.1-C lives separately in
`safetybox.context_trajectory`; see [Context-Aware Trajectory Monitor](CONTEXT_AWARE_TRAJECTORY_MONITOR.md).
No `TRJ-001` or `TRJ-002` behavior is upgraded in place.

| Rule | Exact initial logic | Observation semantics |
|---|---|---|
| `TRJ-001` | Within one bounded session/task history, two consecutive executed `filesystem.read` actions followed by an executed `database.query` and executed `network.send`. | Allowed and successfully executed terminal actions. |
| `TRJ-002` | Within one bounded session/task history, three denied requests for the same action across three distinct resources. | Explicit authorization-denied terminal actions. |

A `TrajectoryFinding` contains a deterministic ID, session/task and rule IDs, finding type, uncalibrated `INFO` or `SUSPICIOUS` classification, first/last evidence sequence numbers, detection sequence number, related request IDs, canonical event IDs and matched actions/resources in immutable evidence, and an explanation. Matches deduplicate by `(session_id, rule_id, related_request_ids)`.

## Purpose

The trajectory monitor evaluates ordered event history to detect patterns not visible in a single authorized action: staged collection and exfiltration, repeated boundary probing, escalating privilege attempts, or unusual request sequences. It consumes committed canonical events and emits explainable signals; it does not grant authority or execute actions.

## Candidate rule forms

- bounded counts/rates over event windows;
- temporal sequences and forbidden transitions;
- cumulative bytes, rows, destinations, or resource breadth;
- divergence from contract-declared expected phases;
- correlations across child tool calls and delegated agents;
- repeated near-boundary requests following denials.

Rules must declare window semantics, state storage, reset behavior, late-event handling, task applicability, and false-positive rationale. Deterministic rules use sequence numbers rather than arrival timing where possible.

## Evaluation concerns

Trajectory detection can add early warning but may also punish legitimate retries, exploration, or long-running tasks. EXP-009 will compare action-only and trajectory-aware policies on matched sequences. Ablations should separate count, order, resource-breadth, and state-transition signals. Detection claims require pre-execution evidence; retrospective labeling alone is insufficient for prevention claims.

Cross-session and multi-agent correlation remain open problems because identity, delegation, and causal ordering may be incomplete.
