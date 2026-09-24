# B4 Bounded Context Trajectory Monitor

## Purpose and separation

`B4-BOUNDED-CONTEXT-TRAJECTORY@1` is a deterministic observational monitor for ordered
relationships that frozen `B2-SINGLE-OBSERVATION@1` cannot retain. B2 remains the
history-free comparator, and frozen M5.1-C remains unchanged. B4 is a separate package,
schema, configuration, state machine, finding type, and rule namespace.

B4 consumes one `CompletedActionObservation`, its frozen M5.1-B interpretation, the
immutable `TaskContext`, and [`B4-HISTORY-CONTEXT@1`](B4_HISTORY_CONTEXT.md). It can
emit findings only. It cannot authorize, deny, execute, quarantine, change capabilities,
mutate trusted context, terminate a task, or alter the `ReferenceMonitor` path.

## Fixed configuration and bounded state

`B4-CONFIG@1` is validated as an untunable value:

| Setting | Value |
|---|---|
| Raw state key | `(session_id, task_id)` |
| Raw window | newest 16 observations |
| Retained findings | newest 32 per key |
| Active keys | 128 |
| Ordering | strict increasing sequence per session; gaps accepted |
| Rules | `B4TRJ-001` through `B4TRJ-004` |
| Missing context | emit and deduplicate `INSUFFICIENT_CONTEXT` |
| Destination transitions | disabled and not implemented |

Active-key exhaustion raises `B4CapacityError`; another task is never evicted.
Duplicate or decreasing sequence numbers raise `B4OrderingError`. Task or history
context replacement raises `B4ContextChangedError`. The finding-retention policy
deterministically removes the oldest retained output after 32 while the new finding is
returned on ingest; snapshots expose a `finding_retention_truncated` marker so this is
not silent. Findings are outputs and never rule inputs.

All role, phase, finalization, and fallback state is recomputed from the current raw
window. No semantic summary survives eviction. A boolean only records that an unknown
prefix exists; it can force abstention but cannot preserve any evicted role, phase,
event, candidate, count, or finalization fact. `close()` removes the key and its state.

## Semantic state

Executed observations contribute only resource/data roles matched by trusted M5.1-B
declarations while a declared aggregation scope is open. Denied or unexecuted
observations never contribute collection roles. Role groups are derived only from
trusted finite membership declarations. At the declared outcome, the accumulated sets
are projected to the constraint's finite universes and compared by exact set equality.

Semantic-event bindings map structured observation/evaluation fields to opaque event
IDs. Events mapped to the same phase continue that phase. The first mapped event must
belong to the unique declared initial phase, and every phase change must use a declared
directed edge. Action names and phase names have no inferred semantics.

A finalization event records its declared outcome and closed phases only while that raw
event remains in the window. A later event in a closed phase is inconsistent unless its
event ID is explicitly excepted. This is semantic interpretation, not session or tool
termination.

Fallback attempts are denied, unexecuted observations already matched by M5.1-B to the
linked fallback behavior. B4 resolves candidate identity from the declared scope and
role, then tracks candidate order, attempt count, termination, restart, and cycle state
inside the raw window. It is not a generic workflow engine.

## Fixed rules

- `B4TRJ-001` emits `SUSPICIOUS` only at a declared outcome when sufficient retained
  role history projects to a combination absent from the trusted allow-list.
- `B4TRJ-002` emits `SUSPICIOUS` for an undeclared initial phase or directed phase
  transition. Same-phase continuation is allowed.
- `B4TRJ-003` emits `SUSPICIOUS` when a retained finalization event closed a phase and a
  later event re-enters it without an exact exception.
- `B4TRJ-004` emits `SUSPICIOUS` for an undeclared candidate edge, forbidden cycle,
  forbidden post-termination restart, or exceeded episode maximum.

Each rule instead emits `INSUFFICIENT_CONTEXT` when its required declaration, unique
binding, compatible TaskContext revision, or necessary retained prefix is unavailable.
No finding means the dimension was explicitly not applicable or sufficient witnessed
state contained no violation.

## Findings, provenance, and determinism

`B4TrajectoryFinding` is frozen and contains deterministic SHA-256-derived identity;
monitor/config versions; rule, type, and bounded classification; session/task and
ordered request/event IDs; first/detection sequence; structured historical state;
expected and observed relations; declaration IDs; ordered sources and reason IDs;
context sufficiency and missing dimensions; lineage availability; and conservative
explanation. Exact evidence and relations participate in identity, so unchanged evidence
deduplicates while later distinct evidence can emit.

Snapshots are immutable copies containing retained findings, raw-window sequence IDs,
the current M5.1-B result and semantic event, active phase, accumulated roles/groups,
finalization IDs/outcomes/establishing sequences/sources/re-entry exceptions, fallback
episodes and termination provenance, and machine-readable version information.

## Development evidence and limitations

Development-only contaminated probes establish B2-matched discrimination for exact
role combinations/cross-source grouping, phase order, closed-phase re-entry, fallback
candidate order, and post-termination restart. They establish code-path expressivity,
not held-out accuracy or generalization. No EXP-013 corpus or result is part of B4.

B4 does not inspect payloads, infer lineage, parse natural language, infer intent,
authenticate declarations, detect internally consistent real-world staleness, recover
dependencies beyond 16 observations, or implement destination-transition history. Its
permitted claim is that declared roles were observed before an operation in a declared
scope—not that bytes moved between them.
