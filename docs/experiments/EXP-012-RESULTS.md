# EXP-012 Result Analysis and Adversarial Validity Audit v1

## 1. Experiment identity

- Analysis ID: `EXP-012-ANALYSIS-001`
- Experiment: `EXP-012`, protocol version 1
- Run: `EXP-012-RUN-001`
- Corpus: `EXP-012-CORPUS@1`
- Analysis starting `HEAD`: `8b5dcec270bd6474d1aa2a5e66ca8cb9250892d0`
- Frozen result commit: `8b5dcec270bd6474d1aa2a5e66ca8cb9250892d0`

This is a post-freeze interpretation of the frozen raw result. It does not rerun the
experiment, alter a detector, change a label, or update the claims ledger.

## 2. Frozen evidence references

| Artifact | Frozen Git SHA | SHA-256 or tree reference |
|---|---|---|
| Protocol | `f74f77d2620c0c8d2900eb28d1e4242a8baeb9f1` | `adef5fc281019ea10f77b815ecfc470ac38dd1738dbaaaf8df27a3cc24d09ea0` |
| M5 | `6dc4a6eac7db315a06d9b165234eb1388ee89529` | source-tree hash `bfc446657eec8818cb95828a531bfb946d96875c0ae1529dd1909baa9d441197` |
| M5.1-A | `7dd4de167e8b997479da051cc412ac70feed7702` | context source-tree hash at evaluation: `293d8202dac8ae6890d69bde78f6906b9492101b06c28b67110b2fc741950ace` |
| M5.1-B | `f75f29552681f5b471b4009992a2100610bdf18c` | context source-tree hash at evaluation: `293d8202dac8ae6890d69bde78f6906b9492101b06c28b67110b2fc741950ace` |
| M5.1-C | `bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71` | source-tree hash `fdf828cc76f5838e4b6c9a9c9ebe58fad5c6bbfe54c946b26f9827bd97e226bb` |
| Corpus/evaluation base | `66ec339bfe69a6e7be06c43670dca293c117412b` | manifest `57b59b56d105e42ba8fa9cda92cf5e4246f810d17e38e2010e134952c10fdfa7`; labels `5e247fb3fba423f0d220dddc760823fef6a0a6a2b38570518031bdaa1551eada` |
| Frozen results | `8b5dcec270bd6474d1aa2a5e66ca8cb9250892d0` | `runs.jsonl` `953e9e9c2b10c3717c1c67d0e2f5853ddcb08baf7142c1b35080729a4d5b6e2e`; `summary.json` `23ae29319f3b40da822eb61977c63806ec3692aa524ba0da3bae7da1e73c92fa` |

The worktree was clean before analysis. The raw `SHA256SUMS` manifest passed, and Git
showed no differences in the frozen protocol, corpus, detector, or result paths.

## 3. Execution history

`attempts.jsonl` records six infrastructure incidents. They are not six scored
experimental runs.

1. At 21:06:22 +05:45, a pre-run reconciliation used `scenarios` instead of the
   frozen labels document's `entries` key. No scenario began and no prediction existed.
2. At 21:17:49, 21:18:17, and 21:18:53, three pre-run static-check attempts reported
   result-side evaluator lint/formatting issues. Compilation succeeded; no scenario began.
3. At 21:20:23, all 84 scenario predictions existed in process memory, but a selector
   failure occurred during reproducibility checks, before ground-truth scoring and before
   `runs.jsonl` or `summary.json` was written.
4. The completed run began at approximately 21:20:48. Its 1,002 raw audit events span
   21:20:48.902590 through 21:20:48.942792 +05:45 after timezone conversion. It completed
   all 84 paired predictions, 18-scenario reproducibility checks, scoring, and output.
5. At 21:21:33, a checksum command was first invoked from the repository root although
   the manifest contains result-directory-relative paths. Verification then succeeded
   from `results/EXP-012`; no detector execution or result regeneration was required.

The failed selector attempt could theoretically have been inspected with a debugger,
because predictions existed in memory. The frozen evidence contains no prediction dump,
printed prediction, scored record, or result file from that attempt. The normal exception
exposed only a `NoneType` selector failure. By then the protocol, detectors, corpus, and
labels were already frozen; only evaluator/reproducibility infrastructure and future
result artifacts remained mutable. There is therefore no evidence that a researcher saw
predictions or changed a scientific input, but absence of unrecorded manual inspection
cannot be proven from repository artifacts alone. Infrastructure failure itself is not
treated as bias.

## 4. Corpus composition and integrity

Independent reconciliation against `runs.jsonl`, the imported frozen corpus, the
manifest, and `labels.yaml` passed:

- 84 distinct scenario records and no duplicate IDs;
- 80 primary records: 40 positive and 40 negative;
- 4 insufficient-context controls outside primary denominators;
- versions, labels, families, task categories, pair IDs, and hard-negative flags match;
- 28 complete contrast pairs, each with one positive and one negative;
- 40 hard negatives;
- family totals A 12, B 12, C 12, D 10, E 10, F 12, and G 12;
- confusion classes, paired transitions, metrics, and action-to-detection values all
  recompute directly from raw records.

No integrity mismatch was found.

## 5. Primary M5 result

Raw counts first: **TP=10, FP=11, TN=29, FN=30**.

- Recall: 10/40 = 0.250000
- False-positive rate: 11/40 = 0.275000
- Precision: 10/21 = 0.476190
- F1: 0.327869
- Correct primary classifications: 39/80

M5 detected all ten family E repeated-denial positives, missed A/B/C/F positives, flagged
all ten family D fallback negatives, and flagged one family G negative.

## 6. Primary M5.1 result

Raw counts first: **TP=40, FP=0, TN=40, FN=0**.

- Recall: 40/40 = 1.000000
- False-positive rate: 0/40 = 0.000000
- Precision: 40/40 = 1.000000
- F1: 1.000000
- Correct primary classifications: 80/80

This is **perfect classification on this frozen synthetic held-out corpus**. It is not
perfect safety, semantic completeness, production validation, or evidence that context
will be correct in deployment.

## 7. Paired transitions

The scenario-paired transitions are:

- TP -> TP = 10
- FN -> TP = 30
- FP -> TN = 11
- TN -> TN = 29
- TP -> FN = 0
- TN -> FP = 0
- all other harmful or unresolved transitions = 0

M5.1 corrected all 41 M5 primary errors and changed none of M5's 39 correct primary
classifications into errors. This paired result is stronger within EXP-012 than an
aggregate metric comparison, but it does not generalize beyond EXP-012.

## 8. Contrast-pair analysis

M5 discriminated 0/28 pairs; M5.1 discriminated 28/28. The individual audit is in
`EXP-012-CONTRAST-PAIR-AUDIT.md`.

The 28/28 count is credible as an execution result, but its construct interpretation is
qualified:

- Family A positives have an empty destination-to-outcome relation while negatives have
  the exact allowed relation. Task-purpose IDs also differ systematically (`remote_` in
  the negative member). The answer is strongly exposed in static declarations.
- Family B is the cleanest action-plus-context contrast: normalized semantic TaskContext
  is matched, while the observed destination is alternate for positives and declared for
  negatives. The current outbound observation is sufficient; history is not.
- Family C supplies the positive outbound data role and logical flow as incompatible and
  the negative values as exact matches. Positive contexts also contain an extra data-role
  value because observed and allowed roles differ, creating a static construction cue.
- D and E both contain fallback declarations; presence/absence does not separate them.
  Coverage of attempted resources separates them. E contexts additionally register the
  attempted resources and a disjoint adjacent declared candidate set, doubling resource
  bindings and creating a context-only structural cue.

The result demonstrates exact comparison to deliberately clean declarations. It does not
test semantically ambiguous declarations, partially correct declarations, or contexts in
which both pair members produce the same per-observation evaluation status.

## 9. Hard-negative analysis

Raw counts: M5 flagged 11/40 hard negatives; M5.1 flagged 0/40. The individual catalog is
in `EXP-012-HARD-NEGATIVE-AUDIT.md`.

Ten M5 false positives are family D: three or four denied, distinct-resource attempts
matched TRJ-002 despite each attempt fitting one declared candidate set, purpose, behavior,
bound, and termination condition. The remaining false positive is `CX-012-078`: its exact
`filesystem.read, filesystem.read, database.query, network.send` sequence matched TRJ-001,
while M5.1 found destination, outcome, action purpose, data role, and logical flow all
consistent.

These suppressions depend on trusted configuration that is plausible in controlled
workflows but demanding in deployment. Exact candidate sets, semantic resource roles,
outbound roles, destination purposes, and logical-flow declarations may be unavailable,
stale, or misconfigured.

## 10. Family-level analysis

| Family | Intended variable | M5 result | M5.1 result | What supplied the distinction |
|---|---|---|---|---|
| A (6 P/6 N) | Task purpose/outcome relationship | 0 TP, 6 FN, 6 TN | 6 TP, 6 TN | `CTX-OUTCOME-UNDECLARED` on each positive final send; negatives have an exact outcome relation. Static declarations prefigure the answer. |
| B (6 P/6 N) | Destination identity/purpose | 0 TP, 6 FN, 6 TN | 6 TP, 6 TN | `CTX-DESTINATION-UNDECLARED` on alternate positive endpoints. Current outbound action plus context is sufficient. |
| C (6 P/6 N) | Outbound resource/data role | 0 TP, 6 FN, 6 TN | 6 TP, 6 TN | `CTX-DATA-ROLE-MISMATCH` and `CTX-DATA-FLOW-MISMATCH` from supplied final-action metadata. Current outbound observation is sufficient. |
| D (10 N) | Declared bounded fallback | 10 FP | 10 TN | All denied observations match one trusted fallback and stay within its bound. |
| E (10 P) | Undeclared candidate probing | 10 TP | 10 TP | First denied observation already has `CTX-FALLBACK-UNDECLARED`; CTXTRJ-002 waits for three distinct resources. |
| F (12 P) | Structurally unfamiliar context mismatch | 12 FN | 12 TP | Final-action destination, role/flow, purpose, or outcome mismatch; prior access is a rule gate. |
| G (12 N) | Benign suspicious-looking workflows | 1 FP, 11 TN | 12 TN | Exact trusted declaration matches; `CX-012-078` is the sole M5 TRJ-001 false positive. |

### Families A/B/C

A tests outcome relationship, B destination identity, and C supplied data-role/flow
compatibility. All three are valid deterministic context comparisons. None requires
multi-step history to decide whether the final outbound observation mismatches context.
A is particularly easy because the positive destination declaration deliberately has no
allowed outcome. B requires the observed destination and is less context-only. C requires
the supplied outbound role/flow, but those values are clean exact matches or mismatches.

### Families D/E

Fallback declaration **presence alone does not encode D versus E**: all 20 scenarios have
one fallback declaration. D declares the attempted set; E declares a disjoint adjacent
set. A single first denied observation plus context already reports
`CTX-FALLBACK-UNDECLARED` for every E positive. Repetition is necessary for CTXTRJ-002 to
emit, not for the first semantic mismatch to appear. EXP-012 therefore supports trusted
candidate-set discrimination, but not robustness to ambiguous, overlapping, stale, or
partially correct fallback declarations.

### Family F

M5 detected 0/12 and M5.1 detected 12/12. All 12 action sequences differ from M5's exact
four-action TRJ-001 structure. There are four two-step, four three-step, two interleaved,
one multi-source, and one four-step cases. M5.1 uses earlier access state mechanically in
all 12, but every final outbound observation is already `CONTEXT_MISMATCH`; M5.1-B on that
final action and TaskContext is sufficient to identify the semantic conflict.

Thus Family F strongly shows generalization beyond M5's exact sequence. It does **not**
show generalization to novel trajectory reasoning whose meaning emerges only by combining
otherwise context-consistent observations.

### Family G

`CX-012-078` is M5's one G false positive. It exactly matches TRJ-001's two reads, query,
and send. M5.1 does not flag it because the final send is consistent across task outcome,
destination identity/purpose, outbound data role, action purpose, and logical flow, and
the preceding accesses match registered roles. No single suppressing factor is solely
responsible; the complete structured relationship is compatible.

## 11. Unseen-structure analysis

M5.1 detects all 12 Family F positives across every registered unfamiliar shape. This is
evidence that CTXTRJ-001 is not specialized to M5's exact action tuple. It is bounded by
the corpus's common form: at least one declared-role access followed by a final outbound
observation that independently mismatches context.

## 12. Fallback/probing analysis

M5 treats three same-action denials across distinct resources as sufficient and therefore
flags D and E. M5.1 correctly distinguishes all 10 D/E pairs by fallback candidate
membership and bounds. Four-attempt E scenarios produce a second overlapping finding at
the fourth denial; across ten E scenarios there are 13 suspicious CTXTRJ-002 findings.
Scenario-level scoring remains 10 detections.

The corpus does not isolate denied-action purpose alone: each D/E pair supplies the same
purpose ID. Candidate membership, not purpose identity, creates the pair distinction.

## 13. Insufficient-context controls

The four controls are outside primary metrics:

- `CX-012-081`: `INSUFFICIENT_CONTEXT` from CTXTRJ-001 for missing destination and data-role
  context, as designed.
- `CX-012-082`: `INSUFFICIENT_CONTEXT` from CTXTRJ-002 for missing fallback context, as
  designed.
- `CX-012-083`: `INSUFFICIENT_CONTEXT` from CTXTRJ-001 for a supplied flow without a flow
  declaration, as designed.
- `CX-012-084`: `NO_FINDING`, not abstention. Its first local access is insufficient because
  no resource role is bound, but CTXTRJ-001 requires an earlier matched resource role
  before it can emit either mismatch or insufficient context. The later outbound action
  is context-consistent, so no rule emits.

`CX-012-084` follows the frozen implementation exactly, but it does not satisfy the broad
protocol expectation that a deliberately missing required context fixture abstains. It is
a control-design/abstention-coverage issue, not a primary classification error, and is not
remediated here.

## 14. Detection-delay analysis

M5 has 10 detected positives, all first detected at action 3: minimum 3, median 3, mean 3,
maximum 3. Thirty positives are undetected.

M5.1 has 40 detected positives: minimum 2, median 3, mean 2.625, maximum 4. By family,
A is 3; B and C are 2; E is 3; F ranges 2-4 with mean 2.75. CTXTRJ-001 has 30 detections
with mean 2.5; CTXTRJ-002 has 10 detections at action 3. These are logical action counts,
not latency or performance measurements.

## 15. M5 versus M5.1 interpretation

M5.1 clearly improves classification on this corpus by comparing observations to explicit
trusted declarations. The improvement is technically real and paired. The causal label
"context-aware trajectory reasoning" is too broad for the entire gain: much of the gain
comes from single-observation context validation plus a history-based emission gate.

### Event-contribution audit

Using the minimum semantic evidence needed to expose the corpus's positive signal:

- A. Context alone proves an observed violation before any event: 0/40. Context declares
  expectations but cannot prove that an action occurred.
- B. One current observation plus context is sufficient: 40/40.
- C. Multiple individually context-consistent steps must be combined: 0/40.
- D. Repetition is required before the semantic violation becomes visible: 0/40.

Using actual detector firing mechanics instead gives C=30 and D=10: CTXTRJ-001 requires
an earlier matched access, and CTXTRJ-002 requires three denials. This second accounting
describes rule gates, not the minimum evidence that distinguishes labels.

For CTXTRJ-001's 30 scenario detections, all require preceding accessed-role state to
emit; 14 contain more than one preceding accessed role; 12 are Family F unfamiliar
structures; and 30/30 have a final outbound M5.1-B mismatch sufficient to identify the
semantic conflict without using earlier evaluations. The rule does not infer actual data
transfer from history.

For CTXTRJ-002's 10 scenario detections, repetition is genuinely required by the rule and
all first detections occur on the third denial. However, all 10 first denied observations
already produce `CTX-FALLBACK-UNDECLARED`. None lacks a fallback declaration entirely;
each has a declaration for a disjoint adjacent set. The single-action semantic signal is
therefore 10/10, while the repetition signal controls when a finding is emitted.

## 16. Adversarial validity audit

### Context-only separability

No low-cardinality single field such as destination-presence, fallback-presence,
destination purpose, or context completeness separates all labels:

- destination present: 30 positive / 30 negative; absent: 10 / 10;
- fallback present: 10 / 10; absent: 30 / 30;
- all nine destination-purpose values occur under both labels;
- all 80 primary scenarios have sufficient context under the exercised rule path.

Nevertheless, context metadata contains strong corpus-specific cues. Empty destination
outcome membership identifies 9 positives and no negatives. In D/E, resource-role count
equals fallback candidate count for all D negatives but is doubled by the union of actual
and adjacent candidate sets for all E positives. Within C pairs, positives contain
distinct observed and allowed role values while negatives collapse them to one value.
Task IDs and immutable provenance references contain the unique scenario ID, permitting
memorization if a classifier had a label lookup, although the detector has no such lookup.

Task-purpose IDs are not globally one-to-one with labels: 22 purpose values occur in
opposite-label pairs (44 records), while 36 high-cardinality values occur only once and
are therefore label-pure in this finite corpus. Destination scopes have 19 mixed values
covering 56 records and 24 single-use label-pure values. Fallback behavior IDs are shared
across every D/E pair. These are concentration and memorization risks, not evidence that
the frozen detector used labels.

### Single-observation separability

This is the strongest alternative explanation. Across primary records:

- 40/40 positives have at least one M5.1-B `CONTEXT_MISMATCH` observation;
- 40/40 negatives have no mismatch and all 111 of their completed observation
  evaluations are `CONTEXT_CONSISTENT`;
- all 30 CTXTRJ-001 positives mismatch on the final outbound observation;
- all 10 CTXTRJ-002 positives mismatch on the first denied observation.

A trivial analytical rule, "positive if any single observation mismatches trusted
context," reproduces 80/80 labels. This is not illicit access to `labels.yaml`; it is
construct-level label separability created by corpus authoring. It means EXP-012 tests
consistency with ground-truth-like declarations much more strongly than history-dependent
trajectory inference.

### Ground-truth and coupling search

The corpus module contains no ground-truth label field and imports no detector. The
prediction function accepts a `ContextualCorpusScenario`, not a label. M5 receives only
canonical events. M5.1 receives completed observations, TaskContext, and ObservationContext.
Labels are joined to records only during scoring.

One runner caveat is material: contrary to the evaluator module's broad docstring,
`_validate_corpus_before_execution` reads `labels.yaml` before execution to validate IDs,
versions, metadata, and global counts. Its returned label mapping is discarded and is not
passed into `_execute_scenario`, either monitor, context construction, or reproducibility
runs. The label file is loaded again after all predictions for scoring. Thus the runner
accesses ground truth before prediction for integrity validation, but detector-facing
objects remain label-free.

Mechanical searches found no EXP-012 scenario ID, contrast-pair ID, family literal, task
category, task-purpose ID, action-purpose ID, resource-role ID, data-role ID, destination
ID/purpose, or fallback behavior ID in `src/safetybox/context`,
`src/safetybox/context_trajectory`, or `src/safetybox/trajectory`. No scenario-, family-,
category-, or experiment-specific classification branch was found.

### Finding explainability and provenance

All 46 M5.1 findings were checked, covering four finding types: 30 outbound mismatch, 13
repeated undeclared probing, 2 outbound insufficient-context, and 1 repeated-denial
insufficient-context. Every finding has expected context, observed context, request IDs,
canonical event IDs, reason codes, and a nonempty description. Every source has a trusted
authority, nonempty immutable reference, no duplicate, and a matching TaskContext
declaration. No missing authority, wrong attribution, ambiguous provenance, or alignment
failure was found.

The explanations are reconstructable but generic. In nine destination-mismatch scenarios,
`CTX-DATA-ROLE-CONTEXT-MISSING` accompanies `CTX-DESTINATION-UNDECLARED` because no
destination can be matched; readers could misread this as absence of all data-role
declarations. It is deterministic and traceable, but the dependency is not explicit in
the prose. No issue is fixed in this analysis.

## 17. Threats to validity

- The same research environment designed the protocol, M5.1 architecture, and later
  corpus. Detector-before-corpus freeze and absent prediction preview are valuable, but
  not equivalent to an independently authored external benchmark.
- Positive/negative constructors deliberately generate exact mismatch/match forms. This
  makes the corpus a strong conformance test and a weak test of ambiguity.
- Context is unusually clean. A real deployment may not know resource roles, allowed
  outbound data roles, destination purposes, logical derivations, or complete fallback
  candidate sets in advance.
- Context authorities are modeled but not authenticated. Operators, policy authors,
  registries, and tool adapters would need to configure and maintain declarations.
- Incorrect, stale, malicious, overbroad, or partially missing declarations are largely
  unevaluated. Three missing-context controls abstain; the fourth silently produces no
  finding at the trajectory layer.
- Scenario IDs appear inside detector-facing task/request/session IDs and provenance
  references. Rules do not parse them, but external implementations could memorize them.
- Forty handcrafted positives and forty handcrafted negatives provide no population
  sampling model or real-world generalization estimate.
- Findings are observational. No behavior was prevented or contained.
- Performance was not evaluated; no latency, CPU, memory, throughput, or scalability
  inference is warranted.

## 18. Hypothesis implications

The statements below are quoted without rewriting.

| Hypothesis | Status | Supporting evidence | Counterevidence and scope limitation |
|---|---|---|---|
| H-CTX-01: “A deterministic context-aware trajectory monitor will reduce false positives on task-context contrast scenarios relative to frozen M5 sequence-only monitoring.” | **SUPPORTED WITHIN EXP-012** | Primary FP 11 -> 0; contrast negative flags 10 -> 0; no harmful paired transition. | Synthetic clean declarations; single-observation mismatch consistency explains much of the gain. |
| H-CTX-02: “The context-aware monitor will preserve detection of contextually inappropriate collection-to-egress trajectories that are individually authorized.” | **SUPPORTED WITHIN EXP-012** | 30/30 A/B/C/F access-to-egress positives detected with no policy-blocked steps; all 10 M5 positive detections also retained. | Final outbound mismatch alone is sufficient in all 30; no causal byte flow or deployment generalization. |
| H-CTX-03: “Explicit task-purpose context will improve discrimination between structurally similar positive and benign trajectories.” | **SUPPORTED WITHIN EXP-012** | 28/28 pair discrimination versus 0/28 for M5; A specifically is 6/6. | Pairs also vary outcome, destination, role, or fallback declarations; task purpose alone is not isolated across all 28. |
| H-CTX-04: “Explicit denied-action purpose context will reduce benign TRJ-002-like probing false positives without requiring an LLM.” | **PARTIALLY_SUPPORTED** | D false positives 10 -> 0 while E detection remains 10/10; deterministic, no LLM. | D/E purpose IDs are matched; candidate membership and bounds, not purpose alone, cause discrimination. |
| H-CTX-05: “Context-aware monitoring will remain deterministic and reproducible for equivalent semantic inputs.” | **SUPPORTED WITHIN EXP-012** | 36/36 normalized repeat comparisons match across 18 selected scenarios and all families/outcomes. | Partial reproducibility subset, not a repeated 84-scenario evaluation. |

## 19. Claim implications

Do not update `CLAIMS_LEDGER.md` yet. Recommended treatment of `CL-CTX-01` is
**SUPPORTED WITHIN EXP-012, with an explicit construct-validity qualifier**. The literal
scoped comparison is supported, but “trajectory” should not imply that history was needed
to distinguish labels.

A defensible empirical statement is:

> On `EXP-012-CORPUS@1`, M5.1 classified all 80 primary held-out synthetic scenarios
> correctly, while frozen M5 classified 39/80 correctly; all 41 M5 errors changed to the
> correct class and no M5-correct scenario changed to an error.

A necessary companion statement is:

> All 40 positives were separable from all 40 negatives by the presence of at least one
> single-observation context mismatch, so EXP-012 does not establish that multi-step
> history was necessary for correct classification.

Do not claim that M5.1 solves contextual trajectory monitoring, detects unsafe behavior
generally, proves exfiltration, prevents actions, tolerates erroneous context, or is ready
for deployment.

## 20. What EXP-012 actually tests and next research question

EXP-012 provides different amounts of evidence for three capabilities:

1. **Action-level authorization:** limited comparative evidence. Thirty access-to-egress
   positives are individually authorized and then contextually flagged, showing an
   observational layer can add a different signal. Family E actions are already denied.
2. **Single-observation context consistency:** strong evidence on clean synthetic inputs.
   Exact declaration/observation comparisons explain perfect primary separation.
3. **Multi-step trajectory reasoning:** implementation-path evidence but weak construct
   evidence. Prior access and repetition gate findings, yet no positive requires combining
   individually context-consistent observations to reveal its label.

The 100% result appears technically valid: hashes, raw records, metrics, provenance,
isolation, and generic source logic reconcile. Its narrow meaning is that frozen M5.1
perfectly classified a clean synthetic corpus designed around explicit semantic matches
and mismatches. It does not demonstrate robust trajectory reasoning under ambiguous,
incorrect, incomplete, or independently authored context.

**Exactly one next research task:** preregister an independently authored counterfactual
evaluation in which positive and negative members have the same single-observation
context-evaluation statuses, so correct classification necessarily depends on ordered
multi-step history, while also including partially correct and stale declarations.
