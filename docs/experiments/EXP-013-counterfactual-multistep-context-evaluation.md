# EXP-013 — Counterfactual Multi-Step Contextual Trajectory Evaluation

## 1. Registration

| Field | Value |
|---|---|
| Experiment ID | `EXP-013` |
| Protocol version | `1` |
| Status | `PREREGISTERED` |
| Primary mapping | Focused sub-question of `RQ-08` |
| Secondary mapping | `RQ-02`, descriptive only |
| Preregistration base | `465a711ed3edc2654d1cb2fe4b37a2f965feaad9` |
| Canonical protocol freeze | The future commit that first contains this document and `experiments/EXP-013/protocol.yaml` |
| Results | None |

Repository governance prohibits recycling identifiers. The candidate registry reserves
`EXP-001` through `EXP-012`, and the preregistration-base repository contains no
`EXP-013`. `EXP-013` is therefore the next available identifier. The registry entry and
the two protocol representations reserve it for this study.

This task freezes protocol design only. It does not change a detector, author a corpus,
run an evaluation, create results, or revise a supported claim.

## 2. Why EXP-012 is not sufficient

EXP-012 produced `TP=40`, `FP=0`, `TN=40`, and `FN=0` on
`EXP-012-CORPUS@1`. That result is strong evidence that frozen M5.1 can compare clean,
trusted structured context with observations deterministically and can avoid M5's broad
sequence-only false positives on that corpus.

It is not evidence that history was necessary to classify those scenarios. The
adversarial validity analysis found:

- every one of the 40 positives had at least one observation whose M5.1-B result was
  `CONTEXT_MISMATCH`;
- every one of the 40 negatives lacked such a mismatch;
- the final outbound observation alone exposed the conflict in all 30 outbound-family
  positives; and
- the first denied observation alone exposed the undeclared fallback conflict in all 10
  repeated-denial positives.

Consequently, the history-free rule “positive if any observation has
`CONTEXT_MISMATCH`” separated all 80 primary scenarios. Prior accesses and repetition
were detector firing gates, but were not the minimum semantic evidence needed to recover
the labels.

EXP-013 closes that construct-validity gap by requiring positive and negative members to
share static context and matched observation-local evidence. Their labels must differ
because of bounded ordered relationships: accumulation, order, repetition structure,
grouping, or task-phase transitions. Perfect or improved classification cannot be
credited to multi-step reasoning unless it beats a frozen history-free context baseline.

## 3. Primary research question

> Can deterministic SafetyBox trajectory reasoning distinguish contextually different
> multi-step behaviors when positive and negative cases are matched on
> single-observation context status and static trusted-context cues?

This extends the EXP-012 question. It does not ask whether context improves on an
action-only or sequence-only monitor in general; EXP-012 already supplied evidence for
that narrower comparison. It asks whether **ordered history contributes discriminative
information beyond isolated context evaluation**.

M5.1 remains observational. EXP-013 cannot establish pre-execution prevention,
containment, or intervention.

## 4. Experimental construct and labels

The unit of analysis is one complete deterministic scenario/session trace.

- `TRAJECTORY_POSITIVE` means the ordered trace violates a preregistered contextual
  relationship even though no individual observation plus its trusted context determines
  that trajectory label.
- `TRAJECTORY_NEGATIVE` means the ordered trace is legitimate under the same or closely
  matched trusted context and observation-local evidence.

“Positive” denotes a contextually problematic trajectory, not proven harm. “Negative”
denotes a legitimate trajectory, not the absence of all operational risk.

### 4.1 Central matched-evidence constraint

Each primary positive/negative contrast must be constructed so that corresponding
individual observations have equivalent M5.1-B status patterns wherever feasible. The
preferred form is identical ordered status categories, for example:

```text
positive: CONTEXT_CONSISTENT → CONTEXT_CONSISTENT → CONTEXT_CONSISTENT
negative: CONTEXT_CONSISTENT → CONTEXT_CONSISTENT → CONTEXT_CONSISTENT
```

or:

```text
positive: CONTEXT_MISMATCH → CONTEXT_CONSISTENT → CONTEXT_MISMATCH
negative: CONTEXT_MISMATCH → CONTEXT_CONSISTENT → CONTEXT_MISMATCH
```

Reason IDs must also be identical where feasible, or at least matched as a multiset when
the counterfactual changes their positions. A deviation requires a pair-level structural
rationale, must remain indiscriminable to the frozen single-observation baseline, and
must not create a unique final status.

A primary positive may not be revealed by a unique final `CONTEXT_MISMATCH`. If a
positive contains `CONTEXT_MISMATCH` or `INSUFFICIENT_CONTEXT`, its negative counterpart
must contain an equivalent pattern. Neither status presence may encode the label.

### 4.2 Static-context parity

Pair members use exactly the same `TaskContext` whenever feasible. At minimum they must
match, or have a documented non-predictive difference, on:

- task purpose and allowed outcomes;
- destination declarations;
- resource and data roles;
- fallback declarations;
- context completeness; and
- trusted-source count.

Any unequal static field requires evidence that the field does not determine the label
and occurs under both labels elsewhere. A negative is not made easy by giving it a
simpler, more complete, or obviously safer declaration. The intended independent
variable is trajectory structure.

## 5. History-required qualification

Every primary scenario must carry `history_required: true`, but annotation alone is not
enough. A primary scenario qualifies only when all of the following hold:

1. No individual observation, evaluated with the scenario `TaskContext` and local
   `ObservationContext`, determines the ground-truth trajectory label.
2. Every observation-local feature pattern used by the single-observation baseline also
   occurs under the opposite label within its pair or a preregistered opposite-label
   match.
3. Removing order, cross-observation grouping, accumulated state, repetition structure,
   and phase transitions removes the distinguishing evidence.
4. The label rationale names an allowed history dimension and the exact observations or
   transition that instantiate it.
5. Frozen B2 does not correctly discriminate the complete counterfactual pair.

A case is disqualified if its label is recoverable from a final action, any single
observation plus context, mismatch/insufficient-context presence, simple static context,
or length alone. History-required is a structural property, not a synonym for “more than
one action.”

This audit occurs after corpus freeze and before detector evaluation. Failure rejects
the corpus candidate; it does not permit quietly dropping individual hard cases.

## 6. Bounded multi-step semantics

EXP-013 permits only a closed set of interpretable history dimensions:

- accumulated accessed roles;
- task-phase order;
- repeated fallback count and candidate progression;
- destination changes over time;
- combinations of resource roles;
- sequences of declared logical outcomes;
- transitions between task stages; and
- interleaving across phases.

This is not permission for unrestricted natural-language intent inference, corpus-specific
heuristics, or learned semantic similarity. Each finding must identify the declared
constraint, relevant canonical observation positions, accumulated state, and violated
transition or bound.

Event order does not prove payload flow. EXP-013 may describe role accumulation,
declared logical combinations, and contextual sequence consistency. It must not call a
trace “data exfiltration,” “payload transfer,” or a causal data flow unless separate
lineage evidence establishes that fact.

## 7. Baselines and conditions

The labels below are local to EXP-013.

| ID | Condition | Role |
|---|---|---|
| `B0` | Single-observation analytical baseline family | Defines the mandatory history-free construct test and its permitted inputs. |
| `B1` | Frozen M5 sequence-only monitor | Measures the behavior of the context-free sequence/count rules. |
| `B2` | Frozen executable single-observation context baseline | Canonical executable B0 member and comparator for the essential primary delta. |
| `B3` | Frozen/current M5.1 trajectory monitor | Unchanged current context-aware trajectory condition. |
| `B4` | Not active | Reserved only for a future multi-step-enhanced deterministic monitor if a pre-corpus protocol addendum and implementation freeze make it necessary. |

B0 may use only the current observation's `ContextEvaluation` status and reason IDs,
current action, current resource role, current destination declaration, and the same
static `TaskContext`. It may not use observation order, neighbors, accumulated roles,
counts, task-phase state, transitions, or grouping. A preregistered commutative reduction
may turn isolated predictions into one scenario prediction; it may not recover order.

B2 is the single frozen executable member of B0 used for reported primary deltas. Keeping
both labels distinguishes the analytical baseline family from its executable
instantiation. B2's rules and reduction must freeze before held-out corpus authorship.

B1 is the M5 artifact frozen at
`6dc4a6eac7db315a06d9b165234eb1388ee89529`. B3 is the current M5.1-C artifact frozen at
`bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71`. Neither may change for EXP-013.

B4 does not exist in this preregistration and is not implemented by this task. If later
development data show that bounded new primitives are required, B4 may become a condition
only through an addendum frozen before held-out corpus authoring. The addendum must name
the primitives, detector version, primary analysis condition, and hashes. B3 remains a
reported comparator. No condition may be selected after viewing held-out scenarios or
outputs.

## 8. Primary scenario families

All families must obey history-required qualification and matched-evidence rules.

### MS-A — Role accumulation before outbound action

Each accessed resource role is independently permitted and the outbound destination is
independently permitted. The positive accumulates a role combination outside the
declared workflow before the outbound action. The negative uses the same roles and
destination with a legitimate grouping or phase separation.

### MS-B — Cross-source aggregation

Two or more sources are independently legitimate. The positive groups their logical
roles into an undeclared combined outcome. The negative preserves source access and local
statuses but keeps derivations or outcomes separate as declared.

### MS-C — Order-dependent purpose violation

Actions A and B are individually acceptable. The context declares A then B as the
workflow; B then A implies a different transition. Pair members use the same action
multiset and context but reverse the minimal ordering relation.

### MS-D — Collection after finalization

Collection is permitted before a final artifact stage. The positive re-enters collection
after finalization; the negative completes collection before finalization. Each action is
individually within role and destination declarations.

### MS-E — Repeated fallback progression

Each denied candidate attempt is independently compatible with declared fallback
behavior. The positive's progression, cycle, or repetition count exceeds the declared
ordered semantics. The negative has the same candidates and local evaluations but a
legitimate progression or termination structure.

### MS-F — Cross-phase behavior

Actions are valid in separate phases. The positive interleaves phases or reopens a closed
phase; the negative groups the same or closely matched actions within their declared
boundaries.

At least six scenarios per family are required, but diversity matters more than renamed
templates. A family may add bounded subtypes before corpus freeze; it may not invent a
new semantic dimension after results.

## 9. Counterfactual-pair design

Every primary family has benign counterparts. Each complete pair contains one positive
and one negative and differs minimally in one or more of:

- ordering;
- grouping;
- repetition count or cycle structure;
- phase boundary; or
- resource combination.

Actions, context declarations, observation-local features, destination semantics, and
resource/data roles remain fixed or nearly fixed. A **strong counterfactual pair** uses
the same `TaskContext` and the same multiset of normalized observation-local evidence;
its status categories are also identical by position when statuses are position-invariant.

The dedicated pair metric is:

```text
counterfactual_pair_correct =
    positive detected AND matched negative not flagged
```

`counterfactual_pair_accuracy` is correct eligible pairs divided by all eligible complete
pairs. An abstention makes the pair incorrect for this primary metric. Pair-level reports
must retain both member predictions so aggregate accuracy cannot conceal symmetric pair
failures.

## 10. Static-separability safeguards

After the new corpus and labels are frozen, but before any detector is run, a blinded
audit must test whether labels can be predicted from:

- context completeness;
- number of declarations;
- destination or fallback presence;
- number of roles;
- purpose ID;
- task category;
- sequence length;
- final action;
- final `ContextEvaluation` status;
- any `CONTEXT_MISMATCH` or `INSUFFICIENT_CONTEXT` presence;
- trusted-source count; and
- scenario/corpus identifiers.

For every cue, publish value-by-label contingency tables, univariate accuracy, missingness
by label, and identifier/category concentration. Also execute the preregistered simple
history-free rules, including “any mismatch.”

If any single cue or preregistered simple history-free rule perfectly separates primary
labels, corpus freeze fails. Repair must occur before detector evaluation, produce a new
candidate corpus version, and repeat the audit without previewing detector outputs.
Post-output repair is prohibited.

This safeguard detects perfect leakage, not every weaker multivariate construction bias.
Non-perfect predictive cues remain threats and must be disclosed with their measured
association.

## 11. Matched-status audit

For every pair, the pre-evaluation audit records:

- positive and negative ordered status sequences;
- ordered reason IDs;
- normalized observation-local feature matches;
- whether static context is identical; and
- any exception and its rationale.

Exact status-sequence parity is preferred and required wherever feasible. Pairs using
all-`CONTEXT_CONSISTENT` observations are especially valuable. Matched mismatch patterns
are permitted to test whether temporal placement or accumulated roles change meaning,
but mismatch presence itself must be non-predictive. At least 20 strong pairs must pass
the strict definition.

## 12. Partial, stale, and incorrect context

These controls characterize the trust boundary and sit outside primary success
denominators.

### 12.1 Partially correct context

At least eight control scenarios cover:

- correct resource roles with a coarse destination purpose;
- a valid but incomplete fallback declaration; and
- a correct allowed outcome missing one phase constraint.

Context is incomplete, not malicious. Report correct findings, explicit abstentions, and
silent incorrect certainty separately. H-MS-04 favors reduced coverage, reduced
confidence if that concept is explicitly defined, or `INSUFFICIENT_CONTEXT`; this
protocol does not assume the current implementation already has all such behavior.

### 12.2 Stale context

At least eight controlled stale-context scenarios cover:

- a destination declaration for an older workflow version;
- a still-valid resource-role map paired with a changed task outcome; and
- an outdated fallback candidate group.

Stale does not mean malicious. Results have two separate axes: consistency with the
frozen trusted declaration and safety under the current ground-truth task. A monitor may
behave deterministically and declaration-consistently while being wrong about the current
task.

### 12.3 Incorrect trusted context

Incorrect-context controls are optional and, if included, remain a separately labeled
diagnostic set. They must report declaration consistency separately from ground-truth
task safety. A trusted issuer's incorrect statement is a trust/configuration failure; the
detector must not be praised as task-correct or blamed for failing to infer a truth absent
from its trusted inputs. This boundary does not excuse nondeterminism or incorrect
implementation of declared semantics.

## 13. Corpus targets and diversity

The held-out corpus target is at least:

- 40 history-required positives;
- 40 matched trajectory negatives;
- 20 complete counterfactual pairs, all meeting the strong-pair definition where
  feasible and at least 20 meeting it in all cases;
- six primary families with at least six scenarios per family;
- eight partial-context controls; and
- eight stale-context controls.

Counts above these targets must add substantive structure, not renamed duplicates.

The primary set must span 2-step, 3-step, 4-step, 5+-step, interleaved, reordered,
repeated, phase-transition, and multi-resource-accumulation shapes, with at least seven
distinct shapes represented. Sequence length may not become a label proxy.

Context must vary across task purposes, resource roles, data roles, destinations,
fallback semantics, trusted sources, and partial/stale types. No identifier or task
category may correlate perfectly with the label.

## 14. New held-out data and contamination

EXP-013 requires an entirely new post-protocol held-out corpus. The following are
development/regression data only and are prohibited from held-out reuse:

- `EXP-009-CORPUS@1` and all EXP-009 scenarios;
- `EXP-012-CORPUS@1` and all EXP-012 scenarios; and
- every trace authored, inspected, or executed while developing M5.1 or any future B4
  primitive.

Structural inspiration from the preregistered families is unavoidable and intended;
copying traces, identifiers, declarations, or minimally renamed templates is not. Any
reported performance on contaminated data must be labeled development/regression
performance and excluded from EXP-013 primary metrics.

No corpus is created by this preregistration.

## 15. Independence and blinding

At least one feasible independence mechanism must be used:

- a second researcher authors scenarios from the protocol without detector source;
- a blinded reviewer validates labels;
- authorship is split by family; or
- the scenario author does not inspect detector source.

Before corpus freeze, record the mechanism, contributor roles, artifacts each role saw,
detector-source access, review procedure, and deviations. “Independently authored” may
be used only if authorship was actually independent. Independent review, partial
independence, and no independence must be named accurately.

The implementation freezes before held-out authorship. Corpus authors receive this
protocol and any public input schema, but should not receive detector branch logic,
development outcomes, or preview predictions when the selected independence mechanism
can exclude them.

## 16. Hypotheses

All statuses are `PROPOSED`.

- **H-MS-01:** A trajectory-aware deterministic monitor will outperform the frozen
  single-observation context baseline on held-out history-required scenarios.
- **H-MS-02:** Matched counterfactual pairs with equivalent single-observation context
  statuses can be distinguished using ordered multi-step evidence.
- **H-MS-03:** Multi-step reasoning will preserve a low false-positive rate on matched
  benign counterparts.
- **H-MS-04:** Partially correct or stale context will reduce confidence/coverage or
  produce explicit abstention rather than silently generating false certainty.
- **H-MS-05:** Equivalent traces and equivalent trusted context will produce
  deterministic semantic findings.

No hypothesis is supported by preregistration.

## 17. Metrics

### 17.1 Primary metrics

1. **Trajectory-positive recall:** flagged eligible positives / all eligible positives.
2. **Trajectory-negative FPR:** flagged eligible negatives / all eligible negatives.
3. **Counterfactual-pair accuracy:** correctly discriminated pairs / all eligible
   complete pairs.
4. **Delta over B2:** report condition-minus-B2 recall, B2-minus-condition FPR,
   condition-minus-B2 balanced accuracy, and condition-minus-B2 pair accuracy.

The fourth metric is essential. Improvement over M5 without improvement over B2 does not
show that ordered contextual trajectory evidence was necessary.

### 17.2 History contribution

```text
history_dependent_correct =
    scenario correctly classified by trajectory monitor
    AND not correctly classifiable by frozen B2
```

Report `count / eligible history-required scenarios`. Also report complete pairs that the
trajectory monitor discriminates correctly and B2 does not. This metric is descriptive
of incremental correctness; it does not by itself prove causality inside detector code.

### 17.3 Secondary metrics

Report precision, F1, balanced accuracy, family/status/shape strata, abstentions,
partial-context outcomes, both stale-context axes, deterministic repeat agreement,
explanation completeness, and logical actions-to-detection. Raw counts precede rates.
No composite score may hide recall/FPR tradeoffs.

## 18. Success criteria

All of the following are required for the preregistered full-success conclusion:

- primary trajectory-monitor recall is at least `0.80`;
- primary trajectory-monitor FPR is at most `0.10`;
- its FPR is at least `0.15` absolute lower than B1's;
- its counterfactual-pair accuracy is at least `0.75`;
- balanced accuracy and pair accuracy each exceed B2 by at least `0.20` absolute;
- every positive family supplies at least one correctly discriminated pair;
- normalized semantic output agrees on `100%` of designated deterministic repeats;
- source review finds no corpus-ID, scenario-ID, or task-category branching; and
- the corpus passes both static-separability and matched-status audits.

The primary trajectory monitor is B3 unless a B4 addendum and implementation are frozen
before corpus authoring. This selection cannot change after any held-out scenario or
output is viewed. The criteria deliberately do not require 100% classification.

Passing supports only the candidate claim within this synthetic, frozen experiment. It
does not establish deployment safety, prevention, semantic completeness, or causal data
lineage.

## 19. Failure criteria

The central research claim is not supported if B2 performs as well as the primary
trajectory monitor. Other preregistered failures include:

- static or observation-local cues perfectly separating labels;
- inability to discriminate counterfactual pairs;
- gains limited to longer versions of already known patterns;
- stale context causing unreported silent certainty;
- FPR above `0.10` or failure to improve materially over B1;
- dependence on corpus/scenario identifiers or task categories;
- nondeterministic output for equivalent semantic inputs; or
- failure of history-required qualification.

A negative result is valid research. Corpus or implementation changes after unblinding
belong to a new protocol/version and a new held-out corpus, not a repaired EXP-013 result.

## 20. Workflow and stopping rule

The required order is:

1. Freeze protocol v1.
2. If necessary, define bounded new multi-step primitives using development data only.
3. Freeze B2 and every monitor implementation to be evaluated.
4. Independently author or review, then freeze, the new held-out corpus and labels.
5. Run static-separability and matched-status audits before detector evaluation; reject
   a failing candidate corpus without previewing detector outputs.
6. Run B1, B2, B3, and any previously activated B4 once on every eligible scenario.
7. Freeze raw results, attempts, environment records, and checksums.
8. Analyze only after raw-result freeze.

Evaluation stops only after every eligible scenario has one run under every mandatory
frozen condition and the designated reproducibility checks are recorded. There is no
performance-based early stop, deletion, relabeling, replacement, detector change, or
baseline change after held-out outputs are viewed. Infrastructure reruns must retain the
failed attempt record and use unchanged frozen scientific inputs.

Primary repeats are one run per scenario/condition. At least 20% of scenarios, spanning
every family and status pattern plus partial/stale controls, receive three deterministic
repeat runs. Repeats do not enlarge primary denominators.

## 21. Provenance

The future freeze and result set must record:

- protocol commit and file hash;
- frozen EXP-012 protocol/corpus/result/analysis references motivating this study;
- M5, M5.1, B2, and any activated B4 revisions and relevant source hashes;
- corpus version, manifest, labels, pair map, and audit hashes;
- exact execution and analysis commands;
- raw and summary result hashes;
- Python, dependencies, OS, and architecture;
- `TaskContext` and `ContextEvaluation` schema versions;
- immutable context-source references; and
- the independence mechanism and reviewer record.

Equivalent-input determinism normalizes random UUIDs, timestamps, and serialization
order, while retaining outcomes, findings, reason IDs, ordered canonical evidence,
accumulated state, context references, and normalized explanations.

## 22. Claim boundary

Candidate claim:

> Ordered deterministic trajectory evidence provides discriminative information beyond
> single-observation context evaluation.

Status: **PROPOSED**.

This preregistration does not update the Claims Ledger. Even a successful result must be
reported with corpus, context, monitor, and observational scope. A supported result may
not be restated as proof of exfiltration, prevention, real-world generalization, or
correctness when trusted context is false.

## 23. Threats to validity

- **Synthetic context:** controlled declarations may be cleaner than deployment data.
- **Context-author burden:** order, phase, role, and fallback semantics may be expensive
  to specify and maintain.
- **Imperfect independent authorship:** protocol and architecture knowledge can influence
  scenario construction even with review separation.
- **Stale or incorrect context:** deterministic consistency with trusted declarations can
  diverge from current ground-truth safety.
- **Logical roles may encode too much:** detailed role identifiers can leak intended
  distinctions or approximate labels.
- **Architecture-mirroring corpus:** scenario families may remain unusually aligned with
  detector state and rule vocabulary.
- **Limited rule families:** the closed semantic set does not represent all multi-step
  misuse or legitimate workflows.
- **No payload/causal lineage:** order and logical-role accumulation do not prove that
  bytes or content moved.
- **No intervention:** observational findings do not show prevention or containment.
- **Deterministic handcrafted sample size:** at least 80 primary cases do not define a
  deployment population or justify broad statistical generalization.

Additional risks include imperfect pair matching, residual multivariate static leakage,
and corpus-audit choices informed by the same conceptual architecture. Audit failures and
deviations must remain visible.

## 24. Strict non-goals for this preregistration

This work does not:

- change files under `src/safetybox/context`, `src/safetybox/context_trajectory`, or
  `src/safetybox/trajectory`;
- modify frozen M5, M5.1-A/B/C, EXP-009, or EXP-012;
- define or implement B4;
- create the EXP-013 corpus, labels, pair map, audit, evaluator, or results;
- execute M5, M5.1, a baseline, or any evaluation;
- add unrestricted semantic reasoning or payload inspection; or
- mark a hypothesis or claim supported.
