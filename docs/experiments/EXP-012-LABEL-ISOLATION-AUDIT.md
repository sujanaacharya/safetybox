# EXP-012 Label-Isolation and Detector-Corpus Coupling Audit v1

## Conclusion

**Ground-truth isolation result: PASS WITH RUNNER CAVEAT.** No ground-truth label,
expected detector outcome, contrast-pair decision, family, or task category reaches M5,
M5.1-B, or M5.1-C classification logic. The runner does read `labels.yaml` during a
pre-execution integrity check, contrary to the evaluator module's broad claim that ground
truth is loaded only after prediction. That mapping is discarded and never passed to a
detector-facing object. Labels are loaded again after all primary and repeat predictions
and are then joined solely for scoring.

No scenario-, corpus-, pair-, family-, category-, purpose-, role-, or destination-specific
branch was found in detector source. The 100% result therefore does not appear to arise
from an accidental label read or explicit memorization branch. It does remain highly
separable by intended context mismatch construction.

## Data-flow trace

```text
labels.yaml
  |-- pre-run: _validate_corpus_before_execution()
  |     validates ID set, version/metadata equality, 40/40/4 counts,
  |     pair completeness, and hard-negative denominator
  |     returns (manifest, labels), but main discards the return value
  |
  `-- post-prediction: main() reloads labels
        -> _score_predictions(predictions, labels)
        -> ground_truth_label, confusion_class, paired_transition, summary only

exp012_corpus.py
  -> ContextualCorpusScenario (no ground-truth label field)
       |-- ThreatScenario / TaskContract / steps
       |-- TaskContext
       |-- ObservationContext tuple
       `-- design metadata: family, category, pair, hard_negative
  -> _execute_scenario(item) (does not accept labels)
       |-- ReferenceMonitor executes TaskContractPolicy -> canonical audit events
       |-- M5.evaluate(events)
       `-- for each completed observation:
             M5.1.ingest(observation, item.task_context, supplied ObservationContext)
  -> primary predictions for all 84
  -> repeat predictions for selected 18
  -> only then post-prediction label join and scoring
```

## Detector-facing objects

M5 receives canonical audit events containing session ID, task ID, action, resource,
decision/execution status, sequence, request ID, and canonical event identity. M5.1
receives the derived completed observation plus `TaskContext` and per-observation
`ObservationContext`. Neither object has a ground-truth field.

`ContextualCorpusScenario` contains family, task category, contrast-pair ID, and
hard-negative metadata, and `_execute_scenario` copies those fields into the unscored
result record. It does not pass them into either monitor. Scenario ID is used to construct
session, request, task, and provenance identifiers; the monitors use those values for
state partitioning, binding, evidence, and finding identity, but no rule parses their
contents for classification.

## Source audit

The following searches were performed across `src/safetybox/context`,
`src/safetybox/context_trajectory`, and `src/safetybox/trajectory`:

| Identifier set | Distinct corpus values | Detector-source overlaps |
|---|---:|---:|
| EXP-012 scenario IDs | 84 | 0 |
| Family IDs as quoted literals | 8 | 0 |
| Task categories | 13 | 0 |
| Task-purpose IDs | 62 | 0 |
| Action-purpose IDs | 54 | 0 |
| Resource-role IDs | 24 | 0 |
| Data-role IDs | 12 | 0 |
| Destination IDs | 44 | 0 |
| Destination-purpose IDs | 9 | 0 |
| Fallback behavior IDs | 10 | 0 |

No `EXP-012`, `CX-012`, `CP-012`, `ground_truth`, `hard_negative`, `task_category`, or
`scenario_family` reference occurs in those detector directories. Shared generic concepts
such as destination, outcome, fallback, and data role are schema dimensions, not corpus
identifier matches.

## Evaluator ground-truth access

The evaluator's scientific isolation is stronger than its docstring's wording but weaker
than literal "ground truth is not read before prediction":

1. `_validate_corpus_before_execution` parses the labels file before execution.
2. It compares label metadata with corpus metadata and reads label values to enforce the
   aggregate 40 positive / 40 negative / 4 control freeze.
3. It neither constructs context nor selects a detector condition based on a per-scenario
   label.
4. Its return value is not bound in `main`; the local mapping becomes unreachable after
   validation.
5. `_execute_scenario` has no label parameter or label-file access.
6. Reproducibility repeats use the same label-free execution function.
7. The scoring-stage reload occurs only after those predictions finish.

Therefore label data is present in the runner process before prediction for read-only
integrity validation, but absent from detector inputs and prediction control flow. This
should be described accurately in future reporting.

## Corpus-construction audit

The corpus module does not import a trajectory monitor, load labels, or store expected
findings. However, family constructors systematically create label-correlated forms:

- A base cases have an empty destination outcome relation; paired negatives populate it.
- B base cases execute against an alternate destination; paired negatives use the
  declared destination.
- C base cases supply a different outbound role/flow from the allowed role; paired
  negatives make them equal.
- D declares exactly the attempted candidate set; E retains the attempts but declares a
  disjoint adjacent set.
- F selects one explicit destination, role, action-purpose, or outcome mismatch.
- G supplies exact compatible relationships.

These are intended semantic contrasts, not hidden runtime label branches. They also make
the corpus unusually easy for generic consistency checking. Across raw results, at least
one per-observation `CONTEXT_MISMATCH` occurs in every positive and no negative. That
perfect construct separability is the main alternative explanation for 100%, rather than
ground-truth access by the detector.

## Context metadata and memorization risks

No simple low-cardinality field globally separates labels:

- destination declaration presence is 30 positive / 30 negative, with absence 10 / 10;
- fallback declaration presence is 10 / 10, with absence 30 / 30;
- destination-purpose values all occur under both labels;
- primary context completeness is uniform under exercised rule requirements;
- task category is mixed for all but a single one-record category.

High-cardinality and structural cues still matter:

- `task_id` and every immutable source reference embed the unique scenario ID. A lookup
  table could recover labels, although no such table or branch exists.
- Of 58 distinct task-purpose values in primary records, 22 values are shared by
  opposite-label pairs (44 records) and 36 occur once (36 label-pure records).
- Of 43 destination-scope tuples, 19 are mixed (56 records) and 24 are single-use and
  label-pure (24 records).
- An empty destination allowed-outcome set occurs in 9 positives and no negatives.
- In D, resource-role count equals fallback candidate count; in E, roles include both
  observed and disjoint declared candidates, so the role count is twice the candidate
  count. This context-only cue separates all D/E members even before an event.
- Within C pairs, different observed/allowed roles produce an extra data-role declaration
  in positives; negatives collapse the values.

These observations do not prove that TaskContext alone semantically establishes a
behavioral violation—without events, no action has occurred. They show that a corpus-level
predictor could exploit metadata construction and that context is more ground-truth-like
than a noisy deployment declaration.

## Context creation and evaluator selection

No label selects a context at runtime. `HELD_OUT_SCENARIOS` is constructed at import time
from frozen family specs; the evaluation loop iterates that tuple unchanged. The labels
document is not consulted to select a TaskContext, ObservationContext, scenario variant,
monitor rule, threshold, family, or execution path. Both M5 and M5.1 receive every frozen
scenario.

The evaluator does use expected labels after prediction to calculate confusion classes,
pair discrimination, family summaries, and metrics, which is necessary scoring rather
than prediction leakage.

## Attempt-history implications

The failed reproducibility-selector attempt reached 84 in-memory predictions before
scoring. No artifact or log contains those predictions, and the exception record exposes
only a selector error. Corpus, labels, protocol, and detectors were frozen before that
attempt. Result-side evaluator code was still mutable, so an unrecorded researcher could
in principle have instrumented or inspected memory after failure; repository evidence
cannot prove a negative about off-record behavior. There is no affirmative evidence of
prediction visibility or subsequent scientific-input change.

## Final isolation assessment

- Direct detector access to `ground_truth_label`: **not found**.
- Runner access before prediction: **yes, integrity validation only**.
- Label passed into M5/M5.1/ContextEvaluator: **no**.
- Scenario/family/category-specific detector branch: **not found**.
- Context construction selected by labels at evaluation time: **no**.
- Corpus-constructor match/mismatch asymmetry: **yes, substantial**.
- Unique identifier memorization surface: **present, unused by frozen rules**.
- Technical credibility of recorded 100% classification: **yes**.
- Evidence that 100% reflects necessary multi-step reasoning: **no**.
