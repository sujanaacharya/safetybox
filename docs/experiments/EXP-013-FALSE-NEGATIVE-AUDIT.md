# EXP-013 False-Negative Audit

Analysis ID: `EXP-013-ANALYSIS-001`  
Frozen run: `EXP-013-RUN-001` at `8ac665cd2466f9d14c525a61759cd36c657795ca`

## Scope

The frozen B4 condition has exactly two primary false negatives, both in `MS-E`
fallback progression. This catalog explains the frozen behavior; it does not change the
detector, context representation, corpus, or labels.

| Scenario | Pair | Expected distinction | B4 outcome | Classification of cause |
|---|---|---|---|---|
| `HX-013-033-B` | `CF-013-033` | after declared termination, a new episode begins at `candidate_3`, which the ground truth treats as unable to start an ordered episode | `NO_FINDING` | `RULE_SEMANTIC_LIMIT`, `CONTEXT_REPRESENTATION_LIMIT`, `STATE_MACHINE_LIMIT`, `GROUND_TRUTH_RULE_MISMATCH`, `EXPECTED_FROZEN_BEHAVIOR` |
| `HX-013-034-B` | `CF-013-034` | after declared termination, a new episode begins at `candidate_4`, which the ground truth treats as unable to start the explicitly directed episode | `NO_FINDING` | `RULE_SEMANTIC_LIMIT`, `CONTEXT_REPRESENTATION_LIMIT`, `STATE_MACHINE_LIMIT`, `GROUND_TRUTH_RULE_MISMATCH`, `EXPECTED_FROZEN_BEHAVIOR` |

Neither miss is a window limit: both traces have 6 or 7 observations, the window is 16,
`prefix_evicted` is false, and all relevant events remain retained. Neither is an event
binding failure: each attempt and termination marker resolves to its intended semantic
event. No evidence establishes an implementation defect relative to the frozen rule as
documented: B4TRJ-004 registers forbidden restart, undeclared candidate edge, forbidden
cycle, and maximum-attempt violations, but does not register an allowed episode-start set.

## `HX-013-033-B`

Family: `MS-E`; shape: `six_step_restart`; pair negative: `HX-013-033-A`.

### Declaration

- Mode: `ORDERED`.
- Ordered candidates: `candidate_1`, `candidate_2`, `candidate_3`.
- Derived allowed edges: `candidate_1 -> candidate_2` and
  `candidate_2 -> candidate_3`.
- Maximum attempts per episode: 3.
- Termination event: `semantic_termination`.
- Restart policy: `AFTER_DECLARED_TERMINATION`.
- Cycle policy: `FORBIDDEN`.
- No field declares which candidates may start a restarted episode.

### Trace and state evolution

| Seq. | Observation | B2 | B4 episode after observation | Finding |
|---:|---|---|---|---|
| 1 | denied `candidate_1` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | `[candidate_1]`, attempts 1, restart 0, open | none |
| 2 | denied `candidate_2` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | `[candidate_1, candidate_2]`, attempts 2, restart 0, open | none |
| 3 | `semantic_termination` | `NEGATIVE` / `CONTEXT_CONSISTENT` | same candidates, terminated at 3 | none |
| 4 | denied `candidate_3` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | reset to `[candidate_3]`, attempts 1, restart 1, open | none |
| 5 | receipt | `NEGATIVE` / `CONTEXT_CONSISTENT` | unchanged | none |
| 6 | archive | `NEGATIVE` / `CONTEXT_CONSISTENT` | unchanged | none |

At sequence 4 the termination satisfies the only restart prerequisite. The frozen rule
therefore resets the episode before considering an edge. Because the new episode has no
prior candidate, no transition exists to test; one attempt is below the maximum; no
candidate repeats; and restart itself is permitted. The final B4 state is a one-attempt
episode starting at `candidate_3`, with `restart_count=1` and no finding.

The matched negative executes `candidate_1 -> candidate_2 -> candidate_3`, then
terminates. Its local evidence multiset and all B2 statuses match, but it does not restart.
The intended pair distinction is real at the authored ground-truth level; the frozen
declaration/rule contract does not encode the additional proposition that only
`candidate_1` may begin an episode.

## `HX-013-034-B`

Family: `MS-E`; shape: `seven_step_episode`; pair negative: `HX-013-034-A`.

### Declaration

- Mode: `EXPLICIT_TRANSITIONS`.
- Candidates: `candidate_1` through `candidate_4`.
- Allowed edges: `candidate_1 -> candidate_2`, `candidate_2 -> candidate_3`, and
  `candidate_3 -> candidate_4`.
- Maximum attempts per episode: 4.
- Termination event: `semantic_termination`.
- Restart policy: `AFTER_DECLARED_TERMINATION`.
- Cycle policy: `FORBIDDEN`.
- The graph has no explicit initial-node or allowed-restart-start declaration. Inferring
  an initial node from graph indegree is not part of frozen B4 semantics.

### Trace and state evolution

| Seq. | Observation | B2 | B4 episode after observation | Finding |
|---:|---|---|---|---|
| 1 | denied `candidate_1` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | `[candidate_1]`, attempts 1, restart 0, open | none |
| 2 | denied `candidate_2` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | `[candidate_1, candidate_2]`, attempts 2 | none |
| 3 | denied `candidate_3` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | `[candidate_1, candidate_2, candidate_3]`, attempts 3 | none |
| 4 | `semantic_termination` | `NEGATIVE` / `CONTEXT_CONSISTENT` | same candidates, terminated at 4 | none |
| 5 | denied `candidate_4` lookup | `NEGATIVE` / `CONTEXT_CONSISTENT` | reset to `[candidate_4]`, attempts 1, restart 1, open | none |
| 6 | receipt | `NEGATIVE` / `CONTEXT_CONSISTENT` | unchanged | none |
| 7 | archive | `NEGATIVE` / `CONTEXT_CONSISTENT` | unchanged | none |

As in pair 033, sequence 5 starts a fresh episode after a permitted termination. The
rule checks edges only when an episode already contains a candidate, so `candidate_4`
has no predecessor to compare. It is neither a cycle nor an attempt-count violation.
The matched negative follows all four edges in one episode before termination.

## Context sufficiency and expressibility

Both cases are `SUFFICIENT_CONTEXT` under the frozen schema: references match, bindings
are unique, the fallback behavior is linked, the termination is retained, and no prefix
was evicted. That is not the same as sufficient semantic vocabulary for the authored
ground truth. The schema represents restart permission but not the set of valid episode
starts. The intended distinction is therefore not currently expressible without either
adding a trusted start-candidate relation or defining a new inference over ordering/graph
structure. Neither change is made here.

These misses motivate future research on explicit fallback state-machine entry semantics
and on agreement between corpus ground truth and the exact trusted relation exposed to a
detector. They do not justify an immediate patch or post-result tuning.
