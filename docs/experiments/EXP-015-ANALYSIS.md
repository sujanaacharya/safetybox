# EXP-015 Adversarial Post-Run Analysis and Bounded Claim Synthesis

**Analysis ID:** `EXP-015-ANALYSIS-001`

**Run:** `EXP-015-RUN-001`

**Raw-result freeze:** `65d047de0fe3b484eaed64bd2adc8562a5835eea`

**Analysis status:** `FINALIZED_BY_THE_COMMIT_CONTAINING_THIS_DOCUMENT`

**Overall disposition:**
`AUTHORIZATION_SUPPORTED_WITHIN_LOW_INDEPENDENCE_SYNTHETIC_SCOPE__REAL_PROCESS_EXECUTION_NOT_DEMONSTRATED`

This analysis does not modify, rescore, repair, or reinterpret the registered raw
outcomes. It adds a post-run adversarial assessment. The frozen run remains
`VALID_RAW_EXECUTION_WITH_RETAINED_SCORING_HARNESS_LIMITATIONS`.

## 1. Frozen basis and integrity

| Frozen item | Identity / verification |
|---|---|
| Raw-result commit | `65d047de0fe3b484eaed64bd2adc8562a5835eea` |
| Protocol | `1b1d22eaded580e9b6f6311bf0e3a8145002e98d` |
| Process implementation | `12c585a9830436d8a88d356cfecbdff132b55487` |
| Runtime schema/materializer | `37368667c438ccbf6a84819ef355590450617d73` |
| `EXP-015-CORPUS@2` | `35dfbb095727f459277db8c7df58864f3be5e907` |
| Frozen `runs.jsonl` SHA-256 | `6e2d27f789595e6df83742c07866ca60c2b21c64d9738c21943d160ca036f2d8` |
| EXP-015 result manifest | `results/EXP-015/SHA256SUMS`: PASS |
| EXP-014 raw manifest | `results/EXP-014/SHA256SUMS`: PASS |
| EXP-014 analysis manifest | `results/EXP-014/ANALYSIS_SHA256SUMS`: PASS |

The pre-analysis worktree was clean and `HEAD` equalled the raw-result freeze. No file
under `results/EXP-015/`, no corpus file, and no frozen scorer file is changed by this
analysis.

## 2. Evidence domains

EXP-015 is not one undifferentiated success or failure.

| Domain | Adversarial disposition |
|---|---|
| A. Authorization discrimination | **SUPPORTED_WITHIN_CORPUS**, with low oracle independence and substantial templating |
| B. Denied-effect prevention | **SUPPORTED_FOR_ADAPTER_PRE-SPAWN_FORWARDING_ONLY**: 60/60 denials had no spawn |
| C. Validation | **PARTIALLY_SUPPORTED**: rejection behavior was exercised; valid-native acceptance and cwd validation were not |
| D. Real process execution | **NOT_DEMONSTRATED**: zero canonical child spawns |
| E. Failure semantics | **NOT_DEMONSTRATED**: 0/12 registered semantics exercised successfully |
| F. Auditability | **PARTIAL**: 120/120 attempt-field completeness; reconstruction is schema-coupled; spawned-path truthfulness is absent |
| G. Control / bypass evidence | **NOT_DEMONSTRATED**: all three registered controls were authored as `ADAPTER` |
| H. Determinism | **REGISTERED_METRIC_FAIL_WITH_KNOWN_CONFOUNDER** |
| I. Performance | **DESCRIPTIVE_EARLY_PATH_TIMING_ONLY** |
| J. Evaluation-harness quality | **MATERIAL_LIMITATIONS_FOUND**: unreachable helpers, route error, pair contamination, missing mappings, terminal-label inconsistencies, and scorer normalization gaps |

## 3. Authorization discrimination

### 3.1 Registered result and what it means

The frozen result is 60 true allows, 60 true denies, zero false allows, and zero false
denies over 120 authorization-evaluable scenarios. The class balance is exactly 50/50.
The corpus has no registered trivial authorization cases and covers both component
decisions in the exact AA/AD/DA/DD distribution 60/20/20/20. It includes task mismatch,
missing or wrong action/resource capability, exact near-name resource boundaries,
one- and two-component denials, zero/missing relevant capability shapes, and literal
arguments that might induce an inappropriate heuristic denial.

This is meaningful evidence that the frozen process-authorization wiring implements the
registered exact task/action/resource rule, composes executable and cwd subdecisions,
and does not use alarming `argv` text as authority. It could have caught task-binding
omission, wrong-component composition, prefix matching, action confusion, or
authorization/validation conflation.

It is not broad semantic generalization. Most scenarios instantiate a small deterministic
rule with repeated task IDs, two main paths, one actor/session template, and systematically
generated near names. Perfect agreement is therefore less surprising than it would be on
an independently designed or naturally occurring authorization workload.

### 3.2 Oracle independence: LOW

The corpus authoring script contains a local oracle, but that oracle explicitly computes
task equality plus exact action/resource membership—the same conceptual rule used by
production `TaskContractPolicy`. It then overwrites the expected exec, cwd, compound,
and spawn labels. The integrity checker repeats the same conceptual computation. The
implementation was frozen before Corpus@2 and the runner did not load labels before raw
execution, which protects against post-exposure tuning and label leakage. It does not
make the semantics independent.

Evidence independence is therefore **LOW**:

- production and oracle are separate code paths;
- corpus construction occurred after production implementation freeze;
- prediction and label loading were isolated;
- but the same project team specified the rule, protocol, corpus, and oracle;
- labels were generated directly from a restatement of the production rule; and
- no external reviewer supplied competing cases or independently interpreted authority.

The 120/120 result is same-team held-out synthetic conformance evidence, not external
validation.

### 3.3 Statistical limitation

`0/60` is an observed error count, not proof of a zero population error probability.
For zero errors in 60 independent Bernoulli trials, the exact one-sided 95% Clopper–Pearson
upper bound is

`1 - 0.05^(1/60) = 0.0487`.

Thus each of the unseen false-allow and false-deny probabilities is only constrained to
less than about 4.87% under the independent, identically distributed sampling model.
The corresponding two-sided 95% upper endpoint is about 5.96%. Because Corpus@2 is
handcrafted and highly structured rather than an IID population sample, these numbers
are an intuition about finite-denominator uncertainty, not a generalization guarantee.

### 3.4 Hard-benign reassessment

All 40 registered `HARD_BENIGN` cases were reviewed. Their authorization is identical;
their difficulty comes entirely from literal `argv` text, not misleading capabilities,
near-boundary authorized resources, or unusual task structures. The reassessment is:

| Class | Count | Scenario IDs | Basis |
|---|---:|---|---|
| `STRONG_HARD_BENIGN` | 21 | `C2-001`–`013`, `020`, `021`, `030`–`034`, `039` | Semantically alarming text, shell operators/substitutions, redirection/pipeline forms, or traversal-like data that a content heuristic could wrongly deny |
| `MODERATE_HARD_BENIGN` | 14 | `C2-014`, `016`, `018`, `019`, `022`–`026`, `028`, `029`, `035`, `037`, `040` | Real literal-boundary stress such as empty/tab/quotes/globs/options/JSON/URL/embedded spacing, but weaker authorization difficulty |
| `EDGE_ONLY` | 5 | `C2-015`, `017`, `027`, `036`, `038` | Visually unusual or ordinary structured data with little genuine authority ambiguity |

The raw 40/40 registered designation is retained. Bounded claim wording should not call
all 40 independently established “hard” cases; it may say “40 corpus-designated hard
benign cases,” followed by this reassessment.

### 3.5 Hard-unauthorized reassessment

All 50 registered `HARD_UNAUTHORIZED` cases were reviewed.

| Family | Count | Conservative difficulty |
|---|---:|---|
| Task mismatch, with resources/capabilities otherwise matching (`C2-061`–`072`) | 12 | Close-boundary negative |
| One exec or cwd capability-resource mismatch (`C2-073`–`088`) | 16 | Close-boundary negative, though generated from repeated templates |
| Requested exec/cwd near-name mismatch (`C2-089`–`096`) | 8 | Close-boundary negative and useful exact-vs-prefix test |
| Compound AD/DA (`C2-098`, `099`, `102`, `103`) | 4 | Close-boundary single-component denial |
| Compound DD (`C2-100`, `104`) | 2 | Moderate, two authority dimensions deny |
| Zero/missing-relevant shapes (`C2-105`–`112`) | 8 | Useful negative coverage but not close-boundary |

The conservative truly close-boundary count is **40/50**. The other ten still test
fail-closed composition, but should not be marketed as close negatives.

### 3.6 Strong-pair reaudit

The registered score remains 36/36 outcome-correct. The post-run pair-quality audit is:

| Classification | Count | Pairs | Reason |
|---|---:|---|---|
| `VALID_STRONG` | 12 | `P-TASK-01`–`12` | Request task ID alone changes among authorization inputs; executable, cwd, capabilities, `argv`, route, and fixture state remain matched |
| `MODERATE` | 24 | Eight exec-capability, eight cwd-capability, four exec-resource, four cwd-resource pairs | Exactly one authority dimension changes, but `argv` also changes because the authoring script indexed an interleaved scenario list by numeric position; resource pairs also necessarily change their requested fixture, and some paired fixture/helper states differ |
| `WEAK` | 0 | — | No pair changes more than one authorization dimension |

The frozen pair audit's claim that `argv` was held fixed for all 36 pairs is not borne out
by the frozen scenario records. Consequently, “36 registered strong pairs scored 36/36”
is a raw fact; “36 independently revalidated strong counterfactual pairs” is prohibited.

### 3.7 Task binding

The 12/12 strict task-binding pairs provide Level 3 evidence that the process request's
declared task ID must equal the supplied `TaskContract.task_id` under schema v2. Schema
v2 intentionally allows a mismatch so production authorization, rather than schema
construction, makes the decision.

This is evidence for **request-to-TaskContract binding** only. It does not authenticate
the session, actor, caller, contract issuer, or the relationship between `session_id` and
the contract. Authenticated session/identity-to-contract binding remains unresolved.

### 3.8 Capability distractors

The only frozen machine-recoverable `DISTRACTOR` denominator is 24:

- `C2-073`–`088`: 16 capability counterfactual negatives; and
- `C2-097`–`104`: eight compound-quadrant cases.

The stated `/34` target came from the corpus audit's conceptual combination of 16
capability-distractor counterfactuals and 18 `ZERO_RELEVANT`/multi-capability cases. Those
18 are separately machine-tagged, but the scorer's `DISTRACTOR` selector does not include
them; meanwhile, the eight compound cases do carry `DISTRACTOR`. There is therefore no
frozen, unambiguous 34-member registry. The ten-case gap cannot be uniquely identified
without choosing a post-exposure family definition. No such relabeling is performed.

Claims are limited to **24/24 frozen `DISTRACTOR`-tagged cases** and, separately,
**18/18 `ZERO_RELEVANT`-tagged cases**.

### 3.9 Candidate-wording stress test

| Phrase | Disposition |
|---|---|
| `held-out` | Defensible only as post-implementation-frozen and label-isolated execution; not independent authorship or external validation |
| `synthetic` | Required; fixtures and authority records are handcrafted/generated |
| `hard` | Use only as “corpus-designated hard” unless accompanied by the 21/14/5 and 40/50 reaudits |
| `strong` | Use “registered strong” for the raw 36/36; only 12/36 remain strict `VALID_STRONG` after reaudit |
| `authorization-evaluable` | Defensible for all 120 because every case has frozen exec, cwd, and compound authority labels and decisions |
| `TaskContract` | Defensible for the represented declared task/action/resource rule; not authenticated contract issuance or session binding |
| `false allow` | Empirical mismatch against the coupled frozen oracle; 0/60 observed, not zero population risk |
| `false deny` | Empirical mismatch against the coupled frozen oracle; 0/60 observed, not zero population risk |

## 4. Validation and process execution

### 4.1 Validation success and fixture failure can coexist

The protocol requires a controlled native ELF executable and explicitly rejects shebang
scripts or wrappers. The materializer's helper generator writes UTF-8 text beginning
with `#!/usr/bin/env python3` and marks `REGULAR_EXECUTABLE` files mode `0755`. The
production validator reads four bytes and accepts only `\x7fELF`; it correctly rejected
these helpers with `PROC-VALIDATION-EXECUTABLE-FORMAT`.

Both statements are true:

1. the frozen executable constraint was enforced; and
2. the corpus fixture design failed to produce an expected-valid object satisfying that
   constraint.

The primary root-cause classification is **`CORPUS_FIXTURE_DESIGN_FAILURE`**. It is also
a protocol/fixture mismatch in ordinary language, but the protocol itself clearly states
the native-ELF requirement and the observed validator behavior matches it. Frozen raw
evidence does not support classifying the adapter as broken.

The helper was a **text executable / Python shebang script**, not a native executable.

### 4.2 What validation did and did not establish

The 16 registered validation-negative scenarios were authorization-correct and produced
a validation rejection. Ten scenarios with intentionally invalid executable fixtures
reached executable rejection. The other six were intended cwd-negative scenarios, but
their purportedly valid executables were scripts and failed format validation first.
The run therefore supports the reached executable rejection behavior, but not successful
acceptance of a valid native executable or the intended cwd rejection behavior.

Six scenarios intended to test missing/symlink/non-directory cwd used a purported
`REGULAR_EXECUTABLE`; that fixture was a script and failed executable validation first.
Therefore physical cwd validation was never reached. The frozen scorer's 16/16 generic
validation row must not be restated as 16/16 executable-and-cwd validation semantics.
Authorization over cwd remains separately supported 120/120.

### 4.3 Consequences of zero canonical child spawns

The following EXP-015 statuses are explicit:

| Sub-property | Status |
|---|---|
| Real direct-child launch | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Authorized requests crossing the full mediation path | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| `argv` integrity at the child | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Literal execution without shell reinterpretation | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Fixed child environment / parent-variable exclusion | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| stdout/stderr capture and output correctness | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Nonzero exit mapping | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Timeout and TERM/KILL escalation | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Signal mapping | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Cleanup and process lifecycle | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Pre/post-spawn failure injection seams | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |
| Real child side effects | `NOT_DEMONSTRATED_IN_EXP_015_RUN_001` |

Prior development tests remain Level 2 development evidence. They do not silently fill
these held-out gaps.

### 4.4 Denied spawn and benign completion

All 60 authorization-negative cases terminated before validation and recorded zero
primitive invocations, no PID/child token, and no observed marker or stream effect. This
is meaningful Level 3 evidence that **the adapter did not forward these registered denied
requests to its spawn primitive**.

It is not evidence that arbitrary unauthorized subprocess effects are prevented through
direct APIs, shell routes, native code, descendants, or other bypasses.

For completion, two denominators are needed:

| Metric | Result | Interpretation |
|---|---:|---|
| Authorized canonical child completion | 0/60 | No authorization-positive case produced a canonical child |
| `AUTHORIZED_BUT_EXPECTED_VALIDATION_REJECT` | 16 | Registered negative-validation cases; excluded from intended benign completion |
| `AUTHORIZED_AND_INTENDED_TO_EXECUTE` | 44 | Frozen labels have `ALLOW`, `SUCCEEDED`, and expected spawn `YES` |
| `BENIGN_COMPLETION_RATE` | **0/44 (0%)** | None of the intended-to-execute authorization-positive cases completed its intended operation |

The intended-execution denominator is recoverable from frozen labels; no post-hoc case
membership is needed.

### 4.5 Terminal accuracy 0/120

This is a major result, not a cosmetic scorer issue. Exact terminal matching failed in
three ways:

- 44 cases expected execution/failure outcomes but were shifted to
  `VALIDATION_REJECT_NOT_SPAWNED` by the unexpected script-format rejection;
- 16 cases expected the label token `VALIDATION_REJECT`, while runtime used
  `VALIDATION_REJECT_NOT_SPAWNED`, even though the generic validation rejection was
  semantically expected; and
- all 60 denied labels retained the label builder's default `EXIT_0` terminal despite
  expected spawn `NO`, while runtime correctly returned `POLICY_DENY_NOT_SPAWNED`.

Thus the universal early format failure explains the intended-execution failures, while
label-taxonomy/default inconsistencies explain the rest. The official 0/120 must remain
0/120. It simultaneously exposes a failed end-to-end experiment and terminal-label
harness defects.

### 4.6 Failure semantics

The 12 failure-tagged cases were authorization-correct but none reached its registered
failure behavior: registered failure-semantic correctness is 0/12. EXP-015 therefore
makes no held-out empirical claim about timeout correctness, TERM/KILL escalation,
signal handling, injected pre-audit failure, uncertain post-spawn handling,
post-completion audit failure, or output-capture interruption.

## 5. Controls, determinism, audit, and performance

### 5.1 PMED controls

`manifest.json` registers `C2-055`–`057` as PMED controls, but each frozen runtime
scenario has route `ADAPTER`. The authoring helper defaulted route to `ADAPTER`, and the
practical/control construction never overrode it. The materializer preserved that value;
the scorer correctly observed no `DIRECT_CONTROL` route.

Root cause: **corpus runtime route authoring error**, not materializer rewriting or a
pair/scorer metadata mismatch. EXP-015 provides no valid direct-bypass-control evidence.
PMED-L1's direct non-adapter bypass remains an architectural/prior-evidence boundary.

### 5.2 Determinism

The official result is **`REGISTERED_METRIC_FAIL`**: 0/6. The comparison removed several
ephemeral fields but failed to normalize all temporary-root paths embedded in audit and
authorization resources. Raw inspection shows the same decisions, validation result,
terminal class, error code, primitive count, and event-type sequence in each canonical/
repeat pair. That is a secondary exploratory observation only.

The adversarial disposition is
**`REGISTERED_METRIC_FAIL_WITH_KNOWN_SCORING_NORMALIZATION_CONFOUNDER`**. No replacement
metric is computed and the registered failure is not rewritten.

### 5.3 Audit ordering

Denied and validation-rejected paths show authorization before any possible primitive;
60 denied cases did not spawn. But no spawned case exists. Therefore:

- `DENIED_PATH_ORDERING_SUPPORTED`; and
- `AUTHORIZED_SPAWN_ORDERING_NOT_DEMONSTRATED`.

The raw generic ordering PASS has a zero spawned denominator and is a vacuous pass for
the intended `... < spawn` property.

### 5.4 Reconstruction and truthfulness

Required attempt fields were present 120/120. This is useful evidence that the attempt
envelope records request identity, task IDs, resources, authorization, validation,
primitive count, terminal class, and audit events on denial/early-rejection paths.

Semantic reconstruction remains **`SCHEMA_COUPLED`** because the verifier follows the
producer's schema rather than an independent process observer. The 120/120 truthfulness
check confirms stream metadata self-consistency and no impossible `child_created=true`
claim when the primitive count is zero. It has no positive-child denominator and is not
independent end-to-end audit verification.

### 5.5 Performance

Median 0.509 ms (mean 0.544 ms, p95 0.842 ms, p99 0.993 ms; n=120) describes the
**decision/early-validation path timing under the EXP-015 workload**. It must not be
called subprocess mediation overhead, process-launch latency, or steady-state real-child
performance.

## 6. Requirement and threat mapping

Frozen labels contain neither `requirement_coverage` nor `threat_coverage`. Therefore
REQ-033–REQ-062 are `NOT_EVALUATED`, and there is no registered threat-level empirical
result. This is evaluation-harness incompleteness. No post-hoc mapping is backfilled into
raw evidence. Architecture documents can still describe qualitative relevance, but such
mapping is `POST_HOC_ANALYTICAL_ONLY` and carries no registered EXP-015 score.

## 7. Success-criteria adversarial review

Raw status is preserved in the second column.

| Success criterion | Raw | Adversarial class | Reason |
|---|---|---|---|
| 100% authorization correctness | PASS | `NONVACUOUS_PASS` | 120 balanced decisions, bounded by low oracle independence |
| 100% denied-spawn prevention | PASS | `NONVACUOUS_PASS` | 60 denied adapter paths, zero spawn observations |
| 100% authorize-before-spawn ordering | PASS | `VACUOUS_PASS` | Spawn denominator is zero |
| 100% registered argument-boundary preservation | FAIL | `NOT_MEANINGFULLY_EXERCISED` | No child observed any argument |
| 100% audit reconstruction completeness | PASS | `NONVACUOUS_PASS` | 120 attempt envelopes complete, schema-coupled |
| 100% registered executable and cwd correctness | PASS | `NOT_MEANINGFULLY_EXERCISED` | Bundled row masks no valid-executable acceptance and no reached cwd validation |
| 100% environment containment | FAIL | `NOT_MEANINGFULLY_EXERCISED` | No child environment existed |
| 100% frozen terminal-semantic correctness | FAIL | `FAIL` | Registered 0/120; execution reachability and label taxonomy both failed |
| Zero adapter-routed policy escapes | PASS | `NONVACUOUS_PASS` | Same bounded evidence as denied-spawn prevention |
| Expected direct-route bypass demonstrated | FAIL | `NOT_MEANINGFULLY_EXERCISED` | Registered controls were authored as adapter routes |
| Deterministic repeats | FAIL | `FAIL` | Official 0/6, with known normalization confounder |
| No frozen regression | PASS | `NONVACUOUS_PASS` | Post-run suite disposition passed apart from two declared lifecycle nodes |
| Zero authorization false allows | PASS | `NONVACUOUS_PASS` | Observed 0/60, finite and coupled scope |
| Zero authorization false denies | PASS | `NONVACUOUS_PASS` | Observed 0/60, finite and coupled scope |

## 8. Failure-criteria adversarial review

| Failure criterion | Raw | Adversarial class | Reason |
|---|---|---|---|
| Authorization false allow/deny | NOT_TRIGGERED | `NOT_TRIGGERED` | All 120 matched |
| Denied request invokes/creates child | NOT_TRIGGERED | `NOT_TRIGGERED` | 60 denied paths had no spawn evidence |
| Spawn precedes complete allow | NOT_TRIGGERED | `NOT_EXERCISED` | No spawn |
| Spawn precedes validation | NOT_TRIGGERED | `NOT_EXERCISED` | No spawn |
| Spawn precedes required audit | NOT_TRIGGERED | `NOT_EXERCISED` | No spawn |
| Shell metacharacter interpreted | NOT_TRIGGERED | `NOT_EXERCISED` | No child/argv observation |
| Unauthorized cwd accepted | NOT_TRIGGERED | `NOT_TRIGGERED` | Component denials stopped before validation/spawn; arbitrary bypass is outside scope |
| Canonicalization expands scope | NOT_TRIGGERED | `NOT_TRIGGERED` | Frozen lexical comparison matched 120/120 |
| Audit denies/nonexecution after known spawn | NOT_TRIGGERED | `NOT_EXERCISED` | No known spawn |
| Unreconstructable process attempt | NOT_TRIGGERED | `NOT_TRIGGERED` | Required fields present 120/120 |
| Corpus-specific runtime branch | NOT_TRIGGERED | `NOT_EXERCISED` | Scorer value is hard-coded; it is not a registered empirical search result |
| Nondeterministic authorization | TRIGGERED | `SCORER_CONFOUNDED_TRIGGER` | Temp-root resource paths were not fully normalized |
| Frozen predecessor regression | NOT_TRIGGERED | `NOT_TRIGGERED` | Established lifecycle disposition retained |

No failure criterion is reclassified as a genuine implementation trigger. The genuine
experiment failure is instead captured by terminal accuracy, benign completion, and the
unexercised execution-semantic criteria.

## 9. Evidence level by subclaim

Level 0 is architecture, 1 implementation, 2 unit/development tested, 3 preregistered
held-out synthetic, 4 real-system/real-tool, and 5 external/design-partner evidence.

| Subclaim | Level | EXP-015 assessment |
|---|---:|---|
| TaskContract authorization discrimination | 3 | 120/120, low oracle independence and same-team synthetic scope |
| Task-contract binding discrimination | 3 | 12/12 strict pairs; not authenticated identity/session binding |
| Capability matching | 3 | Exact registered action/resource semantics; templated corpus |
| Exact resource matching | 3 | Four exec and four cwd negative boundary records, with matched positive context in moderate-quality pairs |
| Denied spawn prevention | 3 | Adapter pre-spawn forwarding only, 60/60 |
| Executable rejection validation | 3 | Invalid/native-format rejection reached; valid-native acceptance absent |
| Cwd object validation | 2 | Development evidence only; never reached in EXP-015 |
| Real subprocess execution | 2 | Development evidence only; zero held-out children |
| `argv` preservation | 2 | Development evidence only; zero held-out child observations |
| Environment filtering | 2 | Development evidence only |
| Output capture | 2 | Development evidence only |
| Timeout/signal semantics | 2 | Development evidence only |
| PMED bypass characterization | 0 | Architectural boundary only; controls invalid |
| Audit attempt-field completeness | 3 | 120/120, schema-coupled |
| Audit semantic truthfulness for real children | 2 | Development evidence only; no child denominator |
| Determinism | 2 | Registered Level 3 metric failed with confounder; only lower-level evidence remains |

EXP-015 does not raise any process-lifecycle subclaim to Level 4 because it produced no
real process execution.

## 10. Bounded claims table

| Subclaim | Raw result | Adversarial assessment | Level | Bound | Supported wording | Prohibited overclaim |
|---|---|---|---:|---|---|---|
| Authorization | 120/120 | Meaningful exact-rule conformance; low independence | 3 | Same-team Corpus@2, adapter route | Frozen process authorization matched the registered exact task/action/resource oracle in 120/120 cases | SafetyBox authorization is generally correct |
| Task binding | 12/12 pairs | Strict request/contract task discrimination | 3 | Declared task IDs only | Mismatched request and contract task IDs were denied in 12/12 strict pairs | Session, actor, or identity was authenticated |
| False allows | 0/60 | Finite observed count | 3 | Registered negatives | No false allow was observed among 60 corpus negatives | Underlying false-allow probability is zero |
| False denies | 0/60 | Finite observed count | 3 | Registered positives | No false deny was observed among 60 corpus positives | Underlying false-deny probability is zero |
| Hard benign | 40/40 registered | 21 strong, 14 moderate, 5 edge-only after review | 3 | Authorization only | All 40 corpus-designated hard-benign positives were authorized | All 40 are independently hard or executed safely |
| Hard unauthorized | 50/50 registered | 40 conservative close-boundary negatives | 3 | Authorization only | All 50 corpus-designated hard-unauthorized negatives were denied | Broad adversarial robustness |
| Strong pairs | 36/36 registered | 12 valid strong, 24 moderate | 3 | Pair outcome only | All 36 registered pairs had the expected decision; 12 remain strict strong pairs | 36 strict counterfactuals independently validated |
| Denied spawn | 60/60 | Strong for adapter pre-spawn forwarding | 3 | Registered adapter denials | Denied requests were not forwarded to the spawn primitive | All unauthorized process effects are contained |
| Executable validation | All authorized helpers rejected | Correct native-format constraint; fixture failure | 3 | Rejection paths | The validator rejected non-ELF helpers and registered invalid executable shapes | Valid native execution works |
| Cwd validation | Not reached | Not demonstrated | 2 | Development only | No EXP-015 held-out claim | Cwd object validation passed EXP-015 |
| Real execution | Child count 0 | Not demonstrated | 2 | Development only | No EXP-015 held-out claim | Real subprocess mediation succeeded |
| `argv` | 0 observed child cases | Not demonstrated | 2 | Development only | Suspicious `argv` was authorized as literal data | Arguments were preserved or not shell-reinterpreted at execution |
| Environment | No child denominator | Not demonstrated | 2 | Development only | No EXP-015 held-out claim | Environment containment passed |
| Output | No child denominator | Not demonstrated | 2 | Development only | No EXP-015 held-out claim | stdout/stderr capture is correct |
| Failure semantics | 0/12 | Not exercised successfully | 2 | Development only | Authorization was correct for 12 registered failure cases | Timeout, signal, or audit-failure semantics passed |
| Audit | 120/120 fields | Schema-coupled attempt completeness | 3/2 | Denial/early rejection | Attempt records contained all registered fields | Independent end-to-end audit truthfulness |
| Controls | 0/3 direct | Corpus route error | 0 | Architecture only | No EXP-015 control claim | PMED bypass behavior was empirically demonstrated |
| Determinism | 0/6 official | Metric fail with normalization confounder | 2 | No replacement score | Registered repeat metric failed; raw semantic projections appear stable exploratorily | EXP-015 determinism passed |
| Performance | Median 0.509 ms | Decision/early-validation timing | 3 descriptive | This workload/host | Median adapter decision/early-validation path time was about 0.509 ms | Subprocess mediation overhead is 0.509 ms |

## 11. CL-011, RTM, and EXP-014 comparison

### 11.1 CL-011

The current CL-011 bundles real subprocess mediation, authorize-before-spawn ordering,
and denied-child prevention. Its disposition is **`PARTIALLY_SUPPORTED`**:

- the task-scoped authorization and denied pre-spawn forwarding subclaims are supported
  within Corpus@2;
- the real-execution and positive authorize-before-spawn subclaims are not supported by
  EXP-015; and
- bypass evidence failed at the harness level.

Splitting is preferable. Repository naming permits monotonic `CL-NNN` identifiers, not
letter-suffixed IDs, so this analysis does not create `CL-011A/B`. A future governance
change should allocate separate ordinary claim records for (1) task-scoped process
authorization discrimination and (2) real subprocess mediation semantics, preserving
CL-011 provenance.

### 11.2 RTM disposition

Repository maturity remains **RTM-1**, justified by EXP-014's bounded filesystem result.
EXP-015 adds Level 3 process-authorization evidence but no successful real child and
therefore does not establish a second evaluated real local-tool adapter. RTM-2 is not
supported.

### 11.3 EXP-014 versus EXP-015

EXP-014 exercised real filesystem primitives and independently observed successful and
denied effects across 94/94 adapter-routed terminal outcomes. Its strength is real object
operations, state observation, and reached failure/order paths within FMED-L1.

EXP-015 has the stronger authorization-specific benchmark: balanced classes, explicit
compound quadrants, task-binding pairs, near resource boundaries, and no authorization
errors. But it never crossed executable validation into real process execution. Neither
experiment is categorically stronger: EXP-014 is stronger for real-tool mediation;
EXP-015 is stronger for exact TaskContract authorization discrimination.

## 12. Benchmark-engineering lesson and future reachability oracle

The systemic lesson is that materializability is not reachability. Corpus@2 verified that
objects could be created reproducibly, but not that an expected-valid executable met the
production protocol's native-executable semantics.

Every future real-tool corpus freeze should require a **VALIDATION-REACHABILITY AUDIT**
before held-out prediction execution. For a process study, an independent oracle should:

1. build a small native helper from separately reviewed source, or consume a provenance-
   pinned native artifact for the target architecture;
2. use no production validator code, constants, exception classes, or imports;
3. independently inspect `lstat` type, executable mode, ELF magic/class/type/machine and
   program-header viability, using a small frozen parser or an independently pinned
   system tool;
4. include negative controls (script, symlink, directory, non-executable, wrong
   architecture) so the oracle is not an always-valid assertion;
5. directly execute each helper mode in a sacrificial temporary root, outside the adapter,
   and verify argv, cwd, environment, output, exit, sleep/signal, and marker behavior;
6. model stage reachability from fixture facts: a valid executable must permit cwd checks,
   a valid cwd must permit pre-spawn audit, and each fault recipe must name a seam that
   exists after all preceding prerequisites;
7. verify `DIRECT_CONTROL` route values from runtime records rather than only a manifest;
8. verify strict counterfactual equality with a structural diff over every non-target
   field; and
9. freeze the oracle and gate before new held-out corpus authorship, ideally under an
   external or red-team reviewer.

This gate may execute fixture helpers, but it must not invoke the held-out adapter or
produce adapter predictions. External corpus authorship should add alternate task,
resource, capability, actor/session, naming, and composition patterns not derived from
production branches. Independent label review should start from protocol semantics, not
from production or corpus-builder code.

## 13. Recommended program sequence

Do not discard the authorization result, and do not scale the current end-to-end harness.
The recommended order is:

1. freeze this bounded EXP-015 analysis;
2. build and freeze independent process-fixture reachability infrastructure;
3. preregister and run a new, small `EXP-016` execution-semantic conformance study; and
4. only then launch `AUTH-COVERAGE-001` with a dedicated authorization-only harness and
   stronger external/red-team corpus independence.

### EXP-016 purpose

Recommended question: **Given an already-authorized process request with independently
validated native executable fixtures, does SafetyBox correctly mediate real direct-child
execution semantics?**

EXP-016 should emphasize native execution, physical cwd validation, exact child `argv`,
fixed environment, stdout/stderr, nonzero exit, timeout, TERM/KILL escalation, signal,
cleanup, failure injection, positive audit ordering, true direct PMED controls, and
normalized semantic repeats. Authorization should be a prerequisite/control, not the
dominant corpus dimension. EXP-015 remains frozen forever; EXP-016 is a new experiment,
not Corpus@3 or a disguised rerun.

### AUTH-COVERAGE-001 purpose

The later program should be a 2,000–5,000-decision authorization precision benchmark
covering filesystem and process initially: hard benign, hard unauthorized, task
confusion, exact and near resource boundaries, capability distractors, compound
authorization, strict counterfactuals, and cross-tool consistency. It should use an
authorization-only runner so lifecycle failures cannot obscure decision metrics, and it
should incorporate independent/external authoring and label review. It must not claim
process lifecycle semantics.

## 14. Strongest defensible claim and prohibited claims

**Strongest defensible claim:**

> On the same-team-authored, post-implementation-frozen `EXP-015-CORPUS@2` synthetic
> corpus, SafetyBox's frozen TaskContract-based process authorization matched the
> corpus's exact task/action/resource oracle in all 120 cases: 60 allows and 60 denies,
> with observed false-allow 0/60 and false-deny 0/60. This is bounded Level 3 conformance
> evidence under low oracle independence; EXP-015 did not demonstrate real subprocess
> execution.

Explicitly prohibited restatements include:

- zero false-allow or false-deny probability;
- external or independent validation of authorization semantics;
- all 40 benign cases are genuinely hard;
- all 50 negatives are close-boundary;
- 36 strict strong counterfactual pairs;
- successful real subprocess mediation or real child launch;
- child `argv` preservation or absence of shell reinterpretation;
- cwd object validation, environment containment, output correctness, timeout, signal,
  cleanup, or failure-injection correctness from EXP-015;
- independent end-to-end audit truthfulness;
- demonstrated direct-route bypass behavior;
- deterministic repeats passing;
- 0.509 ms subprocess mediation overhead;
- requirement- or threat-level empirical coverage;
- authenticated session/identity-to-contract binding;
- descendant, filesystem-syscall, network, TOCTOU, or deployment-wide confinement;
- RTM-2, production readiness, or general process-security effectiveness.

## 15. Analysis validation

No EXP-015 runner or held-out scenario was rerun.

| Gate | Result |
|---|---|
| Full pytest | 617 passed; two established lifecycle-only failures retained |
| Coverage lifecycle disposition | 617 passed, 2 deselected; 95% (`5,329` statements, `261` missed) |
| Ruff | PASS |
| strict mypy | PASS, 67 source files |
| `git diff --check` | PASS |
| EXP-015 result checksums | PASS |
| Corpus@2 checksums | PASS |
| EXP-014 raw and analysis checksums | PASS |

The two full-suite failures are the frozen shared-process import-state assertion and the
fresh-process pre-run assertion that `results/EXP-015/` does not exist. They are handled
only through the already established lifecycle disposition; no test or artifact was
changed.
