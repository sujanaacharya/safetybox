# Context-Aware Trajectory Monitor

## Purpose and boundary

M5.1-C combines ordered M5 `CompletedActionObservation` values, frozen M5.1-B
`ContextEvaluation` values, and bounded deterministic state. It is a separate
observational implementation; frozen M5 `TrajectoryMonitor`, `TRJ-001`, and `TRJ-002`
remain the sequence-only EXP-012 baseline.

`ContextAwareTrajectoryMonitor.ingest` accepts one completed observation, its trusted
`TaskContext`, and optional structured `ObservationContext`. It invokes
`ContextEvaluator` rather than duplicating resource, destination, outcome,
action-purpose, data-role, logical-flow, or fallback membership checks. It never accepts
free-form intent and never parses descriptions, resource names, or payloads.

The monitor does not authorize, block, execute, quarantine, attenuate capabilities, or
modify a `TaskContract`. Findings describe post-authorization observations only.

## State and ordering

State is keyed by `(session_id, task_id)` and held in a bounded deque. The default
window is eight completed observations, reusing M5's development default because the
EXP-012 protocol registers no different M5.1 window. This is an explicit implementation
bound, not an empirically calibrated value.

Canonical `sequence_number` values must increase strictly per session. Duplicate or
decreasing values raise `ContextTrajectoryOrderingError`; gaps are accepted without
reordering. A trusted context is fixed for each active session/task key; replacement
raises `TaskContextChangedError`. Snapshots copy the bounded observations, evaluations,
findings, processed count, and rule IDs into frozen tuple-based values.

## Finding schema

`ContextAwareTrajectoryFinding` is frozen and contains deterministic identity; session,
task, rule, type, classification, and sequence positions; aligned request and canonical
event IDs; M5.1-B reason IDs and trusted provenance; matched roles; expected and observed
context; logical-lineage availability; and a conservative explanation.

The only emitted classifications are `SUSPICIOUS` and `INSUFFICIENT_CONTEXT`.
`NO_FINDING` is represented by no emitted finding. `INSUFFICIENT_CONTEXT` is an
abstention, never benign evidence and never a suspicious detection. Deduplication uses
session, task, finding type, and exact matched request IDs, so distinct later evidence
remains eligible.

## Rules

### `CTXTRJ-001` — access then outbound context interpretation

The current observation must have an applicable destination dimension according to
M5.1-B. At least one earlier, executed observation in bounded state must have a trusted
matched resource role. The rule does not require M5's exact
`read -> read -> query -> send` shape.

- `CONTEXT_CONSISTENT`: no finding.
- `CONTEXT_MISMATCH`: `SUSPICIOUS`, preserving mismatch reasons and sources.
- `INSUFFICIENT_CONTEXT`: a distinct insufficient-context finding.
- otherwise: no finding.

Supplied data-role, action-purpose, and logical-flow metadata are evaluated by
`ContextEvaluator`. Event order alone is not converted into an assertion that accessed
data was sent. Without explicit logical flow, wording says only that outbound action
occurred after access to declared roles and that lineage was unavailable.

### `CTXTRJ-002` — repeated denied action with fallback context

The rule considers three denied requests for the same action across three distinct
resources within bounded state, preserving M5's development repetition count while
changing interpretation rather than tuning the threshold.

- If all three M5.1-B evaluations match one trusted fallback behavior and total
  same-action denied attempts remain within its declared `maximum_attempts` (or no
  numeric maximum is declared), repetition alone emits no finding.
- If any required fallback evaluation is `INSUFFICIENT_CONTEXT`, the rule emits an
  insufficient-context finding.
- Otherwise, uncovered, purpose-conflicting, mixed, or bound-exceeding repetition emits
  a suspicious finding.

M5.1-B owns fallback membership. The trajectory rule only counts ordered results and
checks the bound belonging to the matched trusted declaration. Agent explanations
cannot supply or override a fallback declaration.

## Development evidence and research status

Contaminated development tests demonstrate that an identical four-action trace can
produce a destination-mismatch finding under one trusted context and no finding under a
compatible declared-delivery context. A three-action
`filesystem.read -> database.query -> network.send` trace is also detected when its
outbound evaluation mismatches context. Paired denial tests distinguish a declared
bounded fallback from equally repeated attempts outside that declaration. These are
development regressions only; they are not EXP-012 results and establish no
generalization claim. No EXP-012 held-out corpus has been authored or run.

## Interpretation limits

Context consistency means only consistency with trusted declarations. It does not prove
that the task is safe, the declarations are correct, the payload is safe, the external
system is safe, or the action is authorized. Trusted context may be wrong or incomplete;
roles may be too coarse; declarations impose configuration burden; and a bounded window
can omit relevant history. The monitor performs no payload inspection, byte lineage,
taint tracking, natural-language inference, hidden-reasoning inference, or real
data-flow proof.
