# EXP-013 B4 Pre-Corpus Addendum

## 1. Registration and authority

| Field | Value |
|---|---|
| Addendum ID | `EXP-013-B4-ADDENDUM@1` |
| Addendum version | `1` |
| Status | `PRE-CORPUS DESIGN; UNFROZEN UNTIL COMMITTED` |
| Parent experiment | `EXP-013` protocol v1 |
| Activated condition | `B4` |
| Candidate implementation ID | `B4-BOUNDED-CONTEXT-TRAJECTORY@1` |
| Primary analysis condition after implementation freeze | `B4` |
| Results | None |

This addendum activates the B4 condition reserved by the frozen
[EXP-013 protocol](EXP-013-counterfactual-multistep-context-evaluation.md). It does not
rewrite that protocol. It narrows the permitted B4 design before implementation and
before any EXP-013 held-out corpus is authored. The frozen
[M5.1-C capability audit](EXP-013-M5_1-CAPABILITY-AUDIT.md) is the development-only
rationale: five of six registered primary families are not expressible by frozen
M5.1-C, while its partial support for the sixth is limited to bounded numeric fallback
counting.

The two addendum representations are this document and
`experiments/EXP-013/b4_addendum.yaml`. The commit that first contains both is the
canonical addendum freeze. No implementation, corpus, evaluation, result, hypothesis
change, success-criterion change, or supported claim is part of this addendum.

## 2. Frozen starting state

The addendum began from a clean working tree. A component SHA is the commit that
introduced or completed the frozen component. The capability-audit SHA is the commit
that first contains both audit representations.

| Frozen item | Git SHA |
|---|---|
| EXP-013 protocol v1 | `632a4f82ab7c6487d82a166bca2e3354c7b9b763` |
| B2 `B2-SINGLE-OBSERVATION@1` | `3f8794e8b134b534365e0e26f48dd1886a50f662` |
| M5 sequence-only baseline | `6dc4a6eac7db315a06d9b165234eb1388ee89529` |
| M5.1-A trusted `TaskContext` | `7dd4de167e8b997479da051cc412ac70feed7702` |
| M5.1-B `ContextEvaluator` | `f75f29552681f5b471b4009992a2100610bdf18c` |
| M5.1-C context-aware trajectory monitor | `bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71` |
| EXP-013 M5.1 capability audit | `b8f026d71ec1a08e64b09b62398d75da7ed11d64` |
| Addendum starting `HEAD` | `b8f026d71ec1a08e64b09b62398d75da7ed11d64` |

The original protocol, B2 architecture, M5.1-C architecture, TaskContext architecture,
ContextEvaluation architecture, failure modes, and safety invariants remain unchanged.

## 3. Why B4 is required

Frozen B2 classifies each observation only from its M5.1-B aggregate status and reduces
scenario predictions without order or multiplicity. Frozen M5.1-C retains an eight-item
deque, but `CTXTRJ-001` primarily gates a current observation-local mismatch on whether
an earlier access exists. `CTXTRJ-002` supplies genuine but narrow history semantics:
same-action fallback attempts can be counted against `maximum_attempts` within the
deque. Neither the current trusted schema nor the rules define accumulated role
combinations, grouping, phase transitions, finalization, or structured fallback
progression.

Consequently, frozen M5.1-C cannot make five registered history-required families
testable as defined. B4 is activated to supply only the bounded deterministic semantic
primitives needed for those families. B1, B2, and B3 remain frozen reported
comparators.

## 4. B4 role and non-role

B4 is a **bounded deterministic multi-step contextual trajectory monitor**. Its purpose
is to evaluate whether ordered trajectory state adds discriminative information beyond
B2. It consumes completed observations, their M5.1-B interpretations, and immutable
trusted historical declarations, then emits structured findings.

B4 is not an LLM, intent classifier, taint engine, containment mechanism, unrestricted
rule engine, or replacement for `TaskContract` authorization. It performs no natural-
language interpretation, learned similarity, payload inspection, or causal lineage
inference.

## 5. Observational boundary

B4 may emit immutable findings only. It may not grant capability authority, authorize
or deny execution, terminate a session, quarantine, mutate `TaskContract`, mutate
`TaskContext`, alter tool execution, or feed an implicit enforcement path. Prior policy
decisions and execution outcomes are evidence only.

This preserves `INV-013`: context cannot grant authority absent from `TaskContract`.
It also preserves and extends the boundary of `INV-014`: B4 findings cannot grant
authority or execute protected actions. Implementing B4 must add explicit separation
tests without changing either invariant's frozen text or status.

## 6. Inputs and trust boundary

B4 may consume only:

- one ordered `CompletedActionObservation` at a time;
- the corresponding immutable M5.1-B `ContextEvaluation`;
- the immutable M5.1-A `TaskContext` bound to the same task;
- the immutable `B4-HISTORY-CONTEXT@1` companion defined below; and
- canonical sequence, request, and event provenance already carried by those values.

It must not consume labels, pair membership, family/scenario/experiment/corpus metadata,
future observations, or evaluator outputs. `ObservationContext` may affect B4 only
through the frozen `ContextEvaluation`; it cannot define or override B4 declarations.

All history-relevant declarations and semantic event bindings must carry a trusted
`ContextSource`. The accepted authority set remains `TASK_CONTRACT`, `SYSTEM_POLICY`,
`RESOURCE_REGISTRY`, `TOOL_ADAPTER`, and `DEPLOYMENT_CONFIGURATION`.
`AGENT_SELF_REPORT` must be rejected and cannot create or override phase definitions,
role combinations, grouping scopes, fallback progression, or finalization semantics.

## 7. Trusted historical-context extension

No field is added to or silently inferred for frozen `TaskContext` schema version `1`.
B4 implementation requires a separate frozen, immutable companion value named
`B4HistoricalConstraints` with schema identifier `B4-HISTORY-CONTEXT@1`. It is trusted
task context, is bound to exactly one `task_id` and immutable TaskContext reference, and
has no authorization meaning.

The required top-level fields are:

- `schema_version`, `constraints_id`, `task_id`, and `task_context_reference`;
- `dimension_applicability`, with an explicit `REQUIRED` or `NOT_APPLICABLE` entry for
  `ROLE_COMBINATION`, `PHASE_TRANSITION`, `FINALIZATION`, and
  `FALLBACK_PROGRESSION`;
- `role_groups`, `aggregation_scopes`, and `role_combination_constraints`;
- `semantic_event_bindings`, `phase_definitions`, and `permitted_phase_transitions`;
- `finalization_constraints`;
- `fallback_progression_constraints`; and
- trusted provenance on every declaration.

An omitted applicability entry is invalid. `REQUIRED` with an absent, incomplete,
ambiguous, untrusted, or incompatible declaration is `INSUFFICIENT_CONTEXT`.
`NOT_APPLICABLE` is an explicit trusted statement, not an inference from absence.

Identifiers are opaque structured data. Detector code must not branch on their spelling.
Bindings use a small conjunction of controlled fields already available from an
observation/evaluation: exact action ID and optional resource-role, data-role,
destination, action-purpose, or outcome IDs. A binding that matches more than one
semantic event is invalid rather than resolved by precedence.

## 8. Allowed and excluded state dimensions

The following dimensions are allowed in B4 v1 and no others:

| Dimension | Bounded representation | Justification |
|---|---|---|
| Accumulated resource-role sets | Set projected from executed observations in one declared aggregation scope inside the window | Required by MS-A and MS-B. |
| Accumulated data-role sets | Same scope and bound as resource roles | Required when a trusted declaration expresses the combination through data roles. |
| Cross-source role grouping | Declared role-group IDs accumulated in one declared scope | Required by MS-B without asserting payload lineage. |
| Ordered task-phase transitions | Current declared phase plus transitions witnessed in the window | Required by MS-C and MS-F. |
| Outcome/finalization state | Declared finalization event and closed-phase set witnessed in the window | Required by MS-D and phase re-entry cases in MS-F. |
| Fallback progression | Last candidate, attempt count, termination marker, restart/cycle state within the window | Required by MS-E and extends current count-only support. |
| Bounded repetition/count | Counts recomputed from the same fixed window and declared episode boundary | Required by MS-E. |

Destination identifiers may participate in trusted semantic event matching and finding
evidence, but **destination-transition history is excluded from B4 v1**. No registered
primary family requires a standalone destination-change predicate; adding one would
expand the treatment beyond the audited gap. A future destination-transition rule would
require a new pre-corpus addendum/version and cannot be enabled as configuration.

No arbitrary historical predicate, user-supplied expression, temporal-logic language,
callback rule, or dynamically loaded rule is permitted.

## 9. Role accumulation and role-combination semantics

An executed observation may contribute the resource role and data role that M5.1-B
matched from trusted declarations. B4 never derives a role from a resource name,
filename, payload, action description, or agent explanation. Denied or unexecuted
observations do not accumulate collection roles.

For each declared `aggregation_scope`, B4 maintains projected immutable sets such as:

```text
observed_resource_roles = {
    SOURCE_MATERIAL,
    CONFIGURATION,
    GENERATED_ARTIFACT,
}
```

The identifiers above are illustrative values, not identifiers recognized by detector
logic. A scope declares its opening phase/event, closing outcome/finalization event, and
the role groups it tracks. State resets on its declared close; no detector branch
guesses a boundary.

A `role_group` gives a generic group ID and a non-empty set of resource-role and/or
data-role IDs. A `role_combination_constraint` contains:

- its declaration ID and aggregation-scope ID;
- the outcome semantic-event ID at which it is checked;
- the finite tracked resource-role, data-role, and role-group universes; and
- a finite set of allowed exact projected combinations for that outcome.

At the outcome event, B4 projects the observed sets onto those tracked universes and
compares the resulting tuple of sets with the declared allow-list. Detector code does
not hard-code combinations. Empty allow-lists are invalid; absence under a required
dimension abstains.

This is historical context only. B4 may say “roles A and B were observed in the declared
scope before outcome C” and that their combination was or was not declared. It may not
say “data from A and B was transferred through C” without separate lineage evidence.

## 10. Phase and order semantics

A `phase_definition` has an opaque phase ID, optional `initial` and `terminal` flags,
and the semantic-event IDs associated with that phase. Terms such as `COLLECT`,
`TRANSFORM`, `FINALIZE`, or `DELIVER` may be declaration values, but no such identifier
is embedded in rule logic.

`permitted_phase_transitions` is a finite set of directed `(from_phase_id,
to_phase_id)` pairs. Consecutive events mapped to the same phase are continuation and do
not require a self-edge. The first mapped event must belong to a declared initial phase.
A change of phase is permitted only when its directed edge is declared. Reverse edges,
re-entry, skipping, and interleaving are not inferred from a forward edge.

If an observation should participate according to the applicable semantic-event
bindings but has no unique phase, phase evaluation is `INSUFFICIENT_CONTEXT`. Events
explicitly outside phase applicability do not move phase state. There is no generic
temporal logic, pattern language, or inference from action/phase names.

## 11. Finalization semantics

A `finalization_constraint` declares:

- a finalization ID and outcome ID;
- the trusted semantic-event ID that establishes finalization;
- the phase IDs closed by that event; and
- the semantic-event IDs, if any, explicitly permitted after finalization.

When the bound event is observed, B4 records the declared outcome as finalized and the
listed phases as closed. A later event mapped to a closed phase is inconsistent unless
it is explicitly included in the post-finalization allow-list. The transition is
evaluated from structured IDs only. Filenames, action names, descriptions, and position
as the last observation cannot imply finalization.

Finalization state exists only while the establishing event remains inside the fixed
window. If a relevant later event is observed but the window cannot establish whether a
prior finalization or scope boundary was evicted, B4 abstains with
`INSUFFICIENT_CONTEXT`; it does not assume the phase is open.

## 12. Cross-source aggregation semantics

Cross-source aggregation is represented only as role history inside a declared
aggregation scope. Multiple resources can map through trusted M5.1-A declarations to
different roles, and those roles can map through `role_groups` to source-group IDs.
`B4TRJ-001` compares the accumulated group/role combination at a declared outcome event
with the corresponding allow-list.

There is no full data-lineage graph, byte propagation, payload equivalence, or causal
claim. An explicit current-observation `LogicalDataFlow` may remain M5.1-B evidence, but
B4 does not fabricate one from prior accesses or use order as proof of transfer.

## 13. Fallback progression semantics

A `fallback_progression_constraint` extends, but does not mutate, one existing
M5.1-A `FallbackPattern`. It contains:

- the linked fallback behavior/declaration ID;
- a finite ordered tuple of candidate IDs, each bound to a declared candidate scope and
  role;
- a finite set of allowed directed candidate transitions;
- `maximum_attempts` for one declared progression episode;
- an optional termination-condition ID plus its trusted semantic-event binding;
- `restart_policy`, exactly `FORBIDDEN` or `AFTER_DECLARED_TERMINATION`; and
- `cycle_policy`, exactly `FORBIDDEN` or `DECLARED_TRANSITIONS_ONLY`.

Candidate tuple order is audit metadata and a deterministic default progression only
when the declaration explicitly selects `ORDERED`; otherwise the explicit transition
set is authoritative. B4 does not invent lexical or scope order. Attempts are denied,
unexecuted observations that M5.1-B matched to the linked fallback behavior. A new
episode can start only as declared. Exceeding the bound, taking an undeclared edge,
cycling when forbidden, continuing after termination, or restarting without the
required termination event is inconsistent.

Missing candidate identity, an unknown termination state, an incomplete episode due to
window truncation, or a required progression declaration that is absent yields
`INSUFFICIENT_CONTEXT` rather than a benign interpretation.

## 14. Preregistered B4 rule families

Only these rules are enabled in `B4-BOUNDED-CONTEXT-TRAJECTORY@1`:

| Rule | Generic predicate | EXP-013 families | Why architecturally general |
|---|---|---|---|
| `B4TRJ-001` | At a declared outcome event, the accumulated projected resource/data/role-group combination is not in the trusted allow-list. | MS-A, MS-B | Operates on declaration IDs and sets, independent of task category, resource spelling, or corpus family. |
| `B4TRJ-002` | An observed change between declared phases is not a permitted directed transition, including undeclared re-entry/interleaving. | MS-C, MS-F | Implements one finite transition relation for arbitrary opaque phase IDs. |
| `B4TRJ-003` | After a trusted finalization event, an observation re-enters a closed phase without an explicit post-finalization exception. | MS-D, MS-F | Separates terminal-state semantics from any particular “collection” action or filename. |
| `B4TRJ-004` | Fallback attempts violate the declared candidate transition, episode bound, termination, restart, or cycle policy. | MS-E | Applies the same finite progression semantics to any declared fallback candidates. |

These are reusable semantic primitives, not one rule per future family: two rules each
cover two families, and the family ID is neither input nor branch condition.

### 14.1 Why B2 cannot express them

| Rule | History B2 lacks |
|---|---|
| `B4TRJ-001` | Prior accumulated role/group sets and an outcome-scoped combination comparison. |
| `B4TRJ-002` | Observation order, current phase, and directed transition history. |
| `B4TRJ-003` | Prior finalization state and closed-phase re-entry. |
| `B4TRJ-004` | Multiplicity, candidate order, attempt count, episode, termination, restart, and cycle state. |

B2's commutative idempotent reducer cannot recover any of these properties.

### 14.2 Difference from M5.1-C

| Primitive | M5.1-C relationship |
|---|---|
| Accumulated role/group combination | Entirely new semantic predicate. M5.1-C retains matched roles but uses earlier roles only as an existence gate/evidence. |
| Declared phase transition | Entirely new. M5.1-C has no phase declarations or phase state. |
| Finalization and closed-phase state | Entirely new. M5.1-C has no terminal/finalization primitive. |
| Fallback attempt count | Existing narrow primitive is extended in a separate B4 implementation. |
| Candidate progression, termination, restart, and cycle state | Entirely new semantics layered on the existing fallback identity; M5.1-C remains unchanged. |

B4 is a separate implementation and version. It does not redefine `CTXTRJ-001`,
`CTXTRJ-002`, M5.1-C state, or M5.1-A/B objects.

## 15. Partial, missing, and stale context

Every rule has three semantic outcomes: `SUSPICIOUS`, `INSUFFICIENT_CONTEXT`, or no
finding. No finding is permitted only after the rule is either explicitly
`NOT_APPLICABLE` or has sufficient declarations and witnessed state with no violation.

`INSUFFICIENT_CONTEXT` is required when, for an applicable dimension:

- the declaration or applicability entry is missing;
- a matcher is ambiguous or a required event/role/candidate cannot be resolved;
- phase definitions or permitted edges are incomplete;
- role-combination or aggregation-scope constraints are absent/incomplete;
- fallback progression/termination state is missing or incompatible;
- the active `TaskContext` reference differs from the companion binding; or
- an evicted observation may contain the necessary opening, finalization, termination,
  restart, or prior-attempt state.

Abstention is not benign evidence and does not count as a detected primary positive.
Duplicate insufficient findings use the same deterministic evidence-key policy as
suspicious findings.

B4 cannot discover that internally valid trusted context is outdated relative to an
unrepresented real-world task. A structurally detectable revision/reference mismatch
abstains. Otherwise, B4 evaluates the supplied stale declaration deterministically,
preserves its provenance, and reports declaration consistency separately from current
ground-truth task safety in the EXP-013 stale-context controls. It must never silently
claim that declaration consistency proves freshness or safety.

## 16. Finding schema

Every emitted `B4TrajectoryFinding` must be frozen and contain:

- deterministic finding ID, B4 implementation/config version, rule ID, finding type,
  and classification;
- session ID, task ID, first evidence sequence, detection sequence, ordered request IDs,
  and ordered canonical event IDs;
- relevant historical state, including the bounded role sets, phases, finalization
  state, or fallback episode fields used by that rule;
- expected trusted relation and observed relation as structured values;
- every declaration ID and ordered trusted `ContextSource` used;
- an explicit context-sufficiency status and missing dimensions;
- logical-lineage availability; and
- a deterministic conservative explanation.

The only classifications are `SUSPICIOUS` and `INSUFFICIENT_CONTEXT`. There is no
opaque score, probability, inferred maliciousness, or safety verdict. Finding identity
and deduplication must include the rule, session/task, exact evidence request IDs, and
expected/observed relation so later distinct violations remain eligible.

## 17. Determinism and ordering

Equivalent ordered traces, TaskContext values, and `B4HistoricalConstraints` values
must produce equivalent normalized semantic findings. The implementation must use no
timestamps for semantics, randomness, learned model, external mutable cache, iteration-
order dependence, or nondeterministic explanation text.

Canonical sequence numbers must strictly increase per session. Duplicate/decreasing
values are integrity errors; gaps are accepted without reordering and do not themselves
classify a trace. No future observation may influence a current finding. A context or
historical-constraint replacement for an active `(session_id, task_id)` is an explicit
error, not a state reset.

## 18. Fixed B4 v1 configuration and state bounds

The implementation must freeze exactly this configuration before corpus authorship:

| Setting | Fixed value |
|---|---|
| Configuration ID | `B4-CONFIG@1` |
| State key | `(session_id, task_id)` |
| Raw completed-observation window | `16` |
| Enabled rules | `B4TRJ-001`, `B4TRJ-002`, `B4TRJ-003`, `B4TRJ-004` |
| Role accumulation | Executed, trusted matched roles; declaration-scoped exact projection |
| Phase behavior | Declared initial phase; same-phase continuation; explicit directed cross-phase edges |
| Finalization behavior | Trusted event closes declared phases; no name/position inference |
| Fallback behavior | Declared candidate edges, per-episode maximum, termination, restart, and cycle policy |
| Missing-context policy | Emit/deduplicate `INSUFFICIENT_CONTEXT`; never coerce to benign or suspicious |
| Ordering | Strictly increasing session sequence; gaps accepted; no reorder |
| Destination-transition rule | Disabled and not implemented |
| Raw observation retention | Last `16` per active key only |
| Internal finding retention | Last `32` per active key for snapshots; findings are also returned on ingest |
| Maximum active keys | `128`; capacity exhaustion is explicit, never silent eviction |
| Lifecycle | Explicit session/task close removes that key; no semantic state survives close |

All semantic state is recomputed from or directly bounded by the 16 retained
observations and finite declarations. No role set, phase, finalization bit, fallback
count, episode, or transition summary persists after the supporting observation is
evicted. If eviction makes the needed prefix unknowable, the applicable rule abstains.
The last-sequence integrity marker and immutable context binding may persist while the
key is active but cannot classify. Findings retained outside B4 by an audit consumer are
outputs, not detector state.

No window size, rule set, transition behavior, accumulation policy, fallback policy, or
missing-context behavior may be tuned after corpus authoring begins.

## 19. Explicitly forbidden features

B4 must not use:

- scenario, experiment, family, corpus, pair, or ground-truth label IDs;
- task-category-specific detector branches or corpus-specific purpose IDs;
- static-label shortcuts, trace length alone, sequence-number magnitude, or final
  position as a label proxy;
- natural-language keyword inference, regular expressions over descriptions, LLM
  output, embeddings, prompts, hidden reasoning, or model confidence;
- payload inspection, inferred byte lineage, taint propagation, or event order as proof
  of causal data flow;
- future observations, unbounded history, unbounded counters, arbitrary predicates,
  user code, or a generic workflow/temporal-logic language; or
- any path that grants authority, changes execution, or mutates trusted context.

Source review for these prohibitions remains part of the unchanged EXP-013 success
criteria.

## 20. Development-data policy

B4 may be designed and implemented using only:

- the development-only probes from `EXP-013-M5_1-CAPABILITY-AUDIT@1`;
- new clearly named `DEV-MS-*` probes authored and recorded before held-out corpus
  authoring; and
- contaminated EXP-009/EXP-012 material for explicitly labeled regression work.

Every new development probe, including variants and identifiers, is contaminated and
prohibited from EXP-013 held-out reuse. No future held-out scenario, preview prediction,
label, or minimally renamed held-out template may inform implementation.

## 21. Pre-corpus freeze workflow

The mandatory sequence is:

1. Freeze this addendum in the commit that first contains both representations.
2. Implement only `B4-BOUNDED-CONTEXT-TRAJECTORY@1`, its trusted companion schema, and
   tests using development-only material.
3. Freeze B4 source, schema, configuration, tests, and implementation SHA.
4. Only then author or independently review the new EXP-013 held-out corpus.
5. Freeze the candidate corpus and labels only after static-separability, B2,
   history-required, and matched-status audits pass without detector-output preview.
6. Run B1, B2, B3, and B4 once under the original stopping/repeat rules.
7. Freeze raw results/checksums and analyze afterward.

If B4 cannot be implemented within this addendum, revise the protocol/addendum before
corpus authorship. After corpus authorship begins, changing B4 requires a new protocol
version and new held-out corpus.

## 22. Unchanged hypotheses, metrics, and criteria

H-MS-01 through H-MS-05 are incorporated unchanged from EXP-013 protocol v1. B4 makes
them testable; it does not rewrite them. The original corpus targets, family coverage,
history-required qualification, matched-status and static-separability audits,
determinism requirement, stopping rule, and all success/failure criteria remain in
force.

In particular, full success still requires recall at least `0.80`, FPR at most `0.10`,
FPR at least `0.15` lower than B1, pair accuracy at least `0.75`, balanced accuracy and
pair accuracy each at least `0.20` above B2, at least one correctly discriminated pair
per positive family, and `100%` normalized semantic agreement on designated repeats.
B4 becomes the primary trajectory monitor only after its pre-corpus implementation
freeze; B3 remains a reported comparator. No metric target is weakened or declared
inapplicable by this addendum.

## 23. Future run provenance

Every future EXP-013 run must record at least:

- EXP-013 protocol commit SHA and file hashes;
- B4 addendum commit SHA and both file hashes;
- frozen B2 commit/source hashes;
- frozen B4 implementation commit/source hashes;
- frozen M5 and M5.1-A/B/C references;
- `TaskContext`, `ContextEvaluation`, and `B4-HISTORY-CONTEXT@1` schema versions;
- corpus commit/version and manifest, label, pair-map, and audit hashes;
- raw result and summary/analysis hashes;
- enabled B4 rule IDs/versions and `B4-CONFIG@1` serialized hash; and
- exact commands, environment, immutable context sources, and independence record.

## 24. B4-specific threats to validity

- The trusted history schema or fine-grained role groups may encode the intended answer
  too directly and make task-context authoring resemble labeling.
- Phase/finalization declarations may be cleaner or less ambiguous than realistic
  workflows.
- Enumerating allowed role combinations may be manually burdensome and may increase
  abstention or configuration error.
- The 16-observation bound may miss longer dependencies; abstention limits coverage but
  does not recover the missing evidence.
- Role history and grouping do not establish causal payload lineage.
- White-box development probes may shape declarations and rules toward known structures.
- External corpus authors can still understand the public protocol and mirror its rule
  vocabulary even without seeing implementation branches.
- Explicit `NOT_APPLICABLE` declarations can be misconfigured and hide a relevant
  dimension; provenance and corpus review mitigate but cannot eliminate this risk.
- A stale but internally consistent trusted declaration may produce confident
  declaration-relative output that is wrong about the current task.

## 25. Strict non-goals of this addendum

This addendum does not implement B4 or its schema, author or preview the EXP-013 corpus,
run EXP-013 or any detector, create a result, modify B2/M5/M5.1/EXP-012, change an
existing source/test file, update a claim, or assert that B4 will meet the frozen
criteria. Those are separate gated tasks.
