# EXP-013 M5.1-C Capability Audit

## 1. Audit purpose

**Audit ID:** `EXP-013-M5_1-CAPABILITY-AUDIT@1`

**Decision:** frozen M5.1-C is not sufficient for a meaningful evaluation across the
preregistered EXP-013 history-required families. B4 is required before held-out corpus
authorship, subject to the protocol's pre-corpus addendum and freeze requirements.

This is development-only implementation-readiness evidence. It asks whether frozen
M5.1-C can produce a scenario-level interpretation unavailable to frozen B2 when the
members are matched on observation-local evidence and differ only in bounded history.
It does not ask merely whether M5.1-C accepts a long trace. No EXP-013 corpus case was
authored or run, no experiment result was created, and no research claim was changed.

## 2. Frozen references

The audit began from a clean `git status --short` at current `HEAD`. A component's SHA is
the commit that introduced or completed the frozen component, not a hash inferred from
its intended architecture.

| Frozen item | Git SHA | Resolution |
|---|---|---|
| EXP-013 protocol v1 | `632a4f82ab7c6487d82a166bca2e3354c7b9b763` | First commit containing both protocol representations |
| B2 `B2-SINGLE-OBSERVATION@1` | `3f8794e8b134b534365e0e26f48dd1886a50f662` | B2 implementation freeze/current starting HEAD |
| M5 sequence-only baseline | `6dc4a6eac7db315a06d9b165234eb1388ee89529` | Frozen M5 implementation |
| M5.1-A trusted `TaskContext` | `7dd4de167e8b997479da051cc412ac70feed7702` | Commit introducing the trusted context model |
| M5.1-B `ContextEvaluator` | `f75f29552681f5b471b4009992a2100610bdf18c` | Commit completing the evaluator and its tests |
| M5.1-C context trajectory monitor | `bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71` | Frozen monitor/rules implementation |
| Audit starting HEAD | `3f8794e8b134b534365e0e26f48dd1886a50f662` | Clean worktree before audit files |

The EXP-013 YAML's `protocol_freeze_git_sha` remains the preregistered placeholder, while
the companion protocol document defines the canonical freeze as the first commit that
contains both representations. Repository history resolves that commit to `632a4f8...`.
The preregistration base remains `465a711ed3edc2654d1cb2fe4b37a2f965feaad9`.

Sources reviewed were both EXP-013 protocol representations, the B2 architecture/source/
tests, the M5.1-C architecture/source/tests, M5.1-B and its context schema, frozen M5, and
the EXP-012 adversarial analysis. In particular, EXP-012 found that history only gated
emission for all 40 positives: an observation-local `CONTEXT_MISMATCH` separated every
positive from every negative.

## 3. B2 capability boundary

B2 calls `ContextEvaluator` for one observation and maps aggregate status as follows:
`CONTEXT_MISMATCH -> POSITIVE`, `INSUFFICIENT_CONTEXT -> ABSTAIN`, and all other statuses
to `NEGATIVE` (`single_observation.py:74-117,147-153`). Its scenario reducer converts
results to a `frozenset` and applies `POSITIVE > ABSTAIN > NEGATIVE`
(`single_observation.py:119-145`). The reduction is commutative and ignores order and
prediction multiplicity.

B2 copies sequence number, action/resource, matched roles, destination IDs, reasons, and
provenance into an immutable result. Those fields are evidence, not scenario reduction
inputs. It has no retained observations, counts, role accumulation, phase state,
transition state, or cross-observation grouping. Thus equal sets of observation-level
prediction categories necessarily give the same B2 scenario prediction.

This is narrower than the analytical B0 input allowance: executable B2 ultimately
classifies solely from aggregate `ContextEvaluation.status` and reduces solely from the
presence of observation predictions.

## 4. M5.1-C state inventory

The inventory below describes the frozen code, including state that is retained but not
used to classify.

| State or derived feature | Local / historical | Count | Order | Role accumulation | Phase | Destination transition | Grouping | Actual rule use |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Current `CompletedActionObservation` | local | no | current position | no | no | no | no | Both rules inspect action, decision, execution, resource, or current position |
| Current `ContextEvaluation` | local | no | current position | no | no | no | no | Both rules consume aggregate status or matched fallback ID; CTXTRJ-001 checks destination applicability |
| Current supplied `ObservationContext` | local | no | current position | no | no | no | no | Only logical-flow presence affects CTXTRJ-001 finding wording/evidence |
| `_histories[(session, task)]` bounded deque | historical, maximum 8 | indirectly | yes | available per item, not semantic state | no | IDs available per item, not compared | no | Tuple passed to each stateless rule |
| Earlier matched resource roles | historical | existence only in CTXTRJ-001 | only earlier/current split | collected only for emitted evidence | no | no | no | Any one earlier executed matched role satisfies the CTXTRJ-001 gate |
| Earlier evaluations/reasons | historical | no general count | retained | no | no | no | no | CTXTRJ-001 ignores prior statuses/reasons; CTXTRJ-002 reads statuses and fallback IDs for selected denials |
| Same-action denied observations | historical | yes, within window | last three selected | no | no | no | grouped only by action | CTXTRJ-002 threshold, distinct-resource, consistency, and bound checks |
| Matched fallback behavior IDs | local values compared across history | matching attempts counted | last three plus bounded-window total | no | no | no | same behavior ID required | CTXTRJ-002 only |
| `_last_sequence_by_session` | historical | no | strict monotonic validation | no | no | no | no | Rejects duplicate/decreasing sequence; magnitude/gaps do not classify |
| `_processed_counts[(session, task)]` | historical | total count | no | no | no | no | no | Snapshot metadata only; rules never read it |
| `_contexts[(session, task)]` | fixed static context | no | no | declarations only | no phase declarations exist | static destinations only | no | Rejects context replacement; supplied to rules |
| `_findings` and `_deduplication_keys` | historical outputs | findings retained | evidence tuple participates in dedup | evidence only | no | no | exact request tuple only | Prevent duplicate output; neither is input to rule semantics |
| Request/event IDs and sequence positions | historical provenance | no semantic count | preserved | no | no | no | exact evidence tuple | Finding identity, deduplication, and audit output only |

`ContextualizedObservation` retains the complete observation, evaluation, and supplied
context (`models.py:24-30`). The snapshot exposes recent observations, evaluations, total
processed count, findings, and rule IDs (`monitor.py:112-126`). Availability is not
capability: neither rule implements phase/stage state, an accumulated role-set predicate,
a destination transition, or a grouping key.

The trusted `TaskContext` schema contains outcomes, data/resource roles, static
destinations, logical-flow constraints, expected action purposes, and fallback patterns
(`context/models.py:301-340`). It has no declaration type for phases, ordered transitions,
role-combination constraints, finalization, grouping, or destination-change policies.

## 5. CTXTRJ-001 analysis

### Dependencies

| Element | Frozen behavior |
|---|---|
| Trigger observation | Newest item has an applicable destination dimension |
| Historical prerequisite | At least one earlier item is executed and has a matched resource role |
| Context prerequisite | M5.1-B can evaluate the destination dimension; static context is fixed per session/task |
| Suspicious signal | Current aggregate status is `CONTEXT_MISMATCH` |
| Abstention signal | Current aggregate status is `INSUFFICIENT_CONTEXT` |
| Consistent current observation | Always returns no finding |
| Historical semantic comparison | None: prior statuses, role combinations, grouping, and destination history are ignored |

The decisive branches are `rules.py:130-162`: earlier history supplies only an existence
gate, while the current evaluation supplies the full classification. Helpers accumulate
roles, reasons, and sources into the finding at `rules.py:61-103,282-309`, after a match;
that accumulation does not trigger or classify the match.

### Can it distinguish matched local evidence by order?

Yes, narrowly. `DEV-MS-A` uses the same three normalized observations. In `A -> B -> C`,
`B` is an outbound `CONTEXT_MISMATCH` after a consistent matched-role access, so
CTXTRJ-001 emits `SUSPICIOUS`. In `B -> A -> C`, the same outbound mismatch occurs before
any access, so no finding is ever emitted. B2 returns `POSITIVE` for both and the status/
reason multiset is identical.

This proves order sensitivity in the emission gate. It does **not** prove that CTXTRJ-001
extracts new semantic classification from otherwise acceptable actions: the entire
suspicious signal remains the current outbound mismatch. When all observations are
`CONTEXT_CONSISTENT`, reordering roles or moving an allowed outbound action cannot make
CTXTRJ-001 emit. This is why the result does not satisfy the preregistered MS-C definition
of individually acceptable A and B whose order changes contextual meaning.

## 6. CTXTRJ-002 analysis

### Dependencies

| Element | Frozen behavior |
|---|---|
| Trigger observation | Current decision is `DENY` |
| Historical prerequisites | At least three same-action denials in the bounded window; the last three use three distinct resources |
| Context prerequisites | Last three evaluations supply fallback statuses/behavior IDs; a common ID is resolved in static `TaskContext` |
| Insufficient path | Any of the selected three is `INSUFFICIENT_CONTEXT` |
| No-finding path | All three share one fallback behavior and bounded-window matching count is within `maximum_attempts`, or no numeric maximum exists |
| Suspicious path | Mixed/unmatched fallback evidence, a mismatch, or matching count exceeds the declared numeric maximum |

The selection and threshold are at `rules.py:202-217`; status and behavior comparison at
`rules.py:219-248`; and bound-exceeded classification at `rules.py:249-279`.

`DEV-MS-C` demonstrates genuine B2-indistinguishable count history. Every denied attempt
is `CONTEXT_CONSISTENT` with the identical reason pattern `CTX-RESOURCE-MATCH`,
`CTX-ACTION-PURPOSE-MATCH`, `CTX-FALLBACK-MATCH`. Three attempts remain within the bound
and produce no finding; a fourth exceeds `maximum_attempts=3` and is suspicious. B2 is
`NEGATIVE` for both because repetition does not affect its reduction.

The support is narrow. CTXTRJ-002 has no ordered candidate list, progression index,
cycle/re-entry declaration, or termination-condition evaluation. It filters same-action
denials, takes the last three, and tests distinct resource strings and common fallback
membership. Reordering an equivalent same-count candidate set has no declared progression
semantics to violate. Counts are limited to the eight-item deque even though the snapshot
has an unbounded processed count; the rule never reads that total.

## 7. EXP-013 family capability matrix

| Family | Classification | Exact code-path evidence |
|---|---|---|
| MS-A — role accumulation before outbound | `NOT_EXPRESSIBLE` | CTXTRJ-001 checks only that *some* earlier executed item has a matched role (`rules.py:135-142`). `_resource_roles` accumulates IDs only while building an already-triggered finding (`rules.py:79-88,308`). No allowed/forbidden role-set relation exists in `TaskContext`. |
| MS-B — cross-source aggregation | `NOT_EXPRESSIBLE` | No grouping identifier or aggregate state exists. `DataFlowConstraint` is evaluated only from a supplied current-observation `LogicalDataFlow`; M5.1-B explicitly does not infer flow from order. CTXTRJ-001 never compares its earlier roles with that declaration. |
| MS-C — order-dependent purpose violation | `NOT_EXPRESSIBLE` | The only generic order gate is “earlier access exists” before a destination-bearing current mismatch. A current `CONTEXT_CONSISTENT` observation returns no finding (`rules.py:143-150`). No ordered purpose/transition declaration exists. |
| MS-D — collection after finalization | `NOT_EXPRESSIBLE` | Neither `TaskContext` nor monitor state represents finalization or a closed phase; no rule recognizes a finalization action or rejects later collection. |
| MS-E — repeated fallback progression | `PARTIALLY_SUPPORTED` | CTXTRJ-002 counts bounded-window matching attempts against `maximum_attempts` and requires the selected three to share a fallback behavior. It does not represent candidate order, legal progression, cycles, termination-condition satisfaction, or total count beyond the deque. |
| MS-F — cross-phase behavior | `NOT_EXPRESSIBLE` | No phase/stage field, state machine, transition table, close/re-entry state, or cross-phase interleaving rule exists. Sequence monotonicity is validation, not phase semantics. |

The matrix is intentionally stricter than “the history contains enough raw fields.” A
family is supported only where frozen declarations and a frozen rule can assign meaning
to those fields.

## 8. Development probes

The executable probes live in
`tests/dev/test_exp013_m5_1_capability_audit.py`. They use only `DEV-MS-*` identifiers,
are synthetic development checks, and are not imported into any corpus or evaluator.

| Probe | Pair construction | Local evidence parity | B2 (+ / -) | M5.1-C (+ / -) | Interpretation |
|---|---|---|---|---|---|
| `DEV-MS-A` order reversal | Same A/B/C; `A -> B -> C` versus `B -> A -> C`; B is outbound mismatch | Same normalized observation/status/reason multiset | `POSITIVE / POSITIVE` | `SUSPICIOUS / NO_FINDING` | CTXTRJ-001 order-sensitive mismatch gate; not new consistent-action semantics |
| `DEV-MS-B` role accumulation | Role A and B precede allowed outbound versus B occurring after outbound | Exact same normalized multiset; all consistent | `NEGATIVE / NEGATIVE` | `NO_FINDING / NO_FINDING` | Accumulated role combination is not a trigger |
| `DEV-MS-C` fallback count | Four equivalent declared denials versus first three, bound 3 | Same local status/reason type on every attempt; multiplicity intentionally differs | `NEGATIVE / NEGATIVE` | `SUSPICIOUS / NO_FINDING` | Genuine count/bound history |
| `DEV-MS-D` phase order | Phase-named A/C/B versus A/B/C under the same schema | Exact same normalized multiset; all consistent | `NEGATIVE / NEGATIVE` | `NO_FINDING / NO_FINDING` | Names cannot create absent machine-readable phase state |

Probe D deliberately uses controlled identifiers that a future schema could bind. Frozen
code treats them only as ordinary resource-role identifiers and performs no natural-
language inference.

## 9. B2 parity verification

All four development pairs are mechanically B2-parity-valid:

- A: `POSITIVE == POSITIVE`;
- B: `NEGATIVE == NEGATIVE`;
- C: `NEGATIVE == NEGATIVE`; and
- D: `NEGATIVE == NEGATIVE`.

The tests also compare normalized status/reason evidence. A, B, and D have equal
multisets. C intentionally differs only by one repeated instance of the same consistent
evidence type, which is the permitted independent variable. No pair differs in static
context. No positive obtains a unique mismatch/insufficient status: A contains the same
mismatch in both members, while B/C/D contain only consistent evaluations.

## 10. M5.1-C outcomes

M5.1-C produces different scenario outcomes on 2 of 4 B2-parity-valid pairs:

- A differs because the current observation-local mismatch is conditionally emitted only
  after any matched-role access.
- C differs because the fourth same-behavior attempt exceeds a numeric fallback bound.
- B and D remain identical because there is no role-combination or phase-order predicate.

Only C demonstrates new semantic evidence derived from history with every observation
locally consistent. A demonstrates historical gating of already-discriminative local
evidence. Therefore the frozen monitor shows one narrow genuine history dimension, not
coverage of several preregistered family types.

## 11. Expressible history dimensions

Frozen M5.1-C can express:

- strict arrival-order validation per session;
- whether any matched-role executed access precedes the current destination-bearing
  mismatch or insufficient evaluation;
- a three-denial/same-action/three-distinct-resource threshold within the current window;
- whether the selected denials share one matched fallback behavior;
- matching-attempt count within the current window versus a numeric fallback bound; and
- bounded evidence ordering and finding provenance.

Of these, only numeric fallback-bound comparison supplies label-relevant semantic
information not already present in an individual evaluation in the all-consistent probe.

## 12. Non-expressible history dimensions

Frozen M5.1-C cannot express:

- allowed or forbidden accumulated resource/data-role combinations;
- cross-source grouping/aggregation derived from prior observations;
- declared A-before-B purpose or logical-outcome transitions;
- finalization, closed phases, phase re-entry, or cross-phase interleaving;
- destination transitions or allowed destination-change sequences;
- ordered fallback candidate progression, cycle policy, or termination-condition state;
- grouping boundaries linking selected accesses to a later action; or
- counts outside the bounded deque through the otherwise retained processed total.

Matched roles, destinations, reasons, and request history are present in raw bounded
state, but no frozen predicate assigns the missing semantics. Intended architecture or
available evidence fields cannot substitute for an implemented rule and declaration.

## 13. B4 necessity assessment

**`b4_required: true`.**

The decision follows the preregistered criteria:

1. All-consistent role-accumulation and phase-order pairs produce identical B2 and M5.1-C
   outcomes.
2. CTXTRJ-001's only order discrimination depends on an observation-local mismatch; the
   prior trace merely gates emission.
3. Five of six primary families are not expressible as defined.
4. CTXTRJ-002 supplies only narrow fallback membership/count behavior and no structured
   progression semantics.
5. The monitor therefore does not discriminate several valid B2-matched family types,
   including more than trivial repetition count.

This assessment does not activate B4 by itself and does not authorize detector changes
under this audit task.

### Minimal deterministic B4 design gap

A pre-corpus B4 design should add only bounded, structured primitives needed by the
registered families:

- trusted role-combination declarations plus an accumulated accessed-role set scoped to
  an explicit group or task stage;
- a finite phase/stage state machine with allowed transitions, final/closed states, and
  explicit re-entry/interleaving rules;
- declared ordered action-purpose or logical-outcome transitions;
- destination-transition declarations and prior matched-destination state;
- structured fallback progression with ordered candidate steps, cycle/retry policy,
  termination state, and a count whose scope is explicit; and
- explicit grouping/correlation identifiers where cross-source aggregation is claimed.

Each primitive should emit the declaration ID, prior/current state, relevant canonical
positions, and violated transition/bound. It must not infer intent from names, infer byte
flow from event order, or use scenario/family IDs. The context schema, implementation,
tests, and analysis mapping must freeze before independent corpus authorship as required
by the EXP-013 addendum rule.

## 14. Recommended next step

Create and freeze the pre-corpus EXP-013 B4 protocol addendum and bounded deterministic
B4 design/implementation using development-only cases, preserving B3 as the frozen
comparator. Do not begin held-out corpus authorship until that addendum and implementation
freeze are complete.

## 15. Validity limitations

- These are four minimal white-box development pairs, not sampled data and not held-out
  evidence. They establish reachability/non-reachability of code paths, not accuracy or
  generalization.
- Probe A shows scenario-level output discrimination but retains an observation-local
  mismatch in both members. It is evidence of an order gate, not evidence that the
  monitor understands a new order-dependent semantic violation.
- Probe C changes trace length by one equivalent attempt. That is appropriate for count
  expressivity but does not test same-length candidate progression.
- Absence claims are bounded to the frozen default rules and schema reviewed at the
  recorded SHAs. Custom rule injection is an extension point, not capability of the
  frozen default M5.1-C condition.
- The default window of eight limits conclusions about longer traces and total counts.
- Ground-truth labels were not assigned and no EXP-013 evaluation metric was computed.
