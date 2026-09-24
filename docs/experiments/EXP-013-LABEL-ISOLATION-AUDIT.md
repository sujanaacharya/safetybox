# EXP-013 Label-Isolation Audit

Analysis ID: `EXP-013-ANALYSIS-001`  
Frozen evaluator: `results/EXP-013/evaluate.py` at result freeze

## Conclusion

Ground-truth labels, pair IDs, family IDs, history-required annotations, hard-negative
flags, and control truth axes do not enter M5, B2, M5.1-C, or B4 detector-facing calls.
They are joined to prediction records by scenario ID in `_score` after canonical and
reproducibility predictions finish.

There is one documentation caveat: `_validate_corpus_before_prediction` reads
`labels.yaml` before prediction to validate the frozen scenario-ID set, family/label
counts, and pair completeness. The local mapping is discarded; it is not returned,
stored globally, passed to `_execute_scenario`, or passed to a detector. Consequently,
the frozen summary field `labels_loaded_after_predictions_and_repeats: true` is literally
too broad. The narrower statement—label metadata first enters prediction records only
after detector execution—is verified. This is a provenance-description defect, not an
observed detector dataflow leak.

## Reconstructed dataflow

```text
labels.yaml
  |-- pre-run integrity validation only
  |     scenario IDs, aggregate counts, pair completeness
  |     local mapping discarded
  |
  `-- post-prediction _score join by scenario_id
        family, pair, label, history annotation, control truth
        |
        `-- confusion classes, pair metrics, summaries

exp013_corpus.HELD_OUT_SCENARIOS
  -> CounterfactualCorpusScenario
  -> _execute_scenario
       |-- M5: canonical SafetyBoxEvent tuple
       |-- B2: observation + TaskContext + ObservationContext
       |-- M5.1-C: observation + TaskContext + ObservationContext
       `-- B4: observation + TaskContext + B4HistoricalConstraints
                + ObservationContext (only through frozen evaluation)
  -> label-free prediction record
  -> reproducibility repeats
  -> _score
```

## Corpus object boundary

`CounterfactualCorpusScenario` contains `scenario_id`, version, task ID, task category,
sequence shape, `TaskContext`, `B4HistoricalConstraints`, observations, and control type.
It contains no ground-truth label, counterfactual pair ID, family, rationale,
history-required annotation, or hard-negative flag.

`task_category` and `sequence_shape` are reporting fields on the object, but
`_execute_scenario` does not pass either to a detector. `scenario_id` is used to create
opaque session/request/event IDs. Those IDs appear in evidence and deterministic finding
identity, but production rules contain no value-specific branch over them.

## Detector-facing values

| Condition | Values received | Label-side values received |
|---|---|---|
| M5 | canonical events derived from completed observations | none |
| B2 | current observation, `TaskContext`, current `ObservationContext` | none |
| M5.1-C | ordered observations, `TaskContext`, per-observation context | none |
| B4 | ordered observations, `TaskContext`, frozen history declarations, per-observation context | none |

For B4, the detector sees opaque role, group, phase, fallback, task, request, and event
identifiers because these are part of the declared runtime semantics. It does not see
which identifier values correspond to labels, families, or pairs.

## Scoring boundary

The prediction record is initially created with `family`, `counterfactual_pair_id`,
`ground_truth_label`, `history_required`, and `history_dimension` set to `None`.
After all 96 canonical predictions and 60 semantic repeat comparisons, `_score` loads the
label document and joins metadata. Only then are confusion classes and paired transitions
computed. The label document cannot alter already materialized detector findings.

## Coupling search

Exact searches of production detector directories found no EXP-013 scenario ID, pair
ID, family ID, task-category value, corpus purpose ID, role ID, role-group ID, phase ID,
fallback behavior ID, fallback constraint ID, or candidate ID. Generic field and type
names such as `phase_id`, `role_group_ids`, `candidate_id`, `task_id`, and `scenario`
occur as schema vocabulary, validation labels, or opaque comparisons. They are not
benchmark-specific executable branches.

## Residual limitations

- The evaluator process has technical access to the label file before prediction for
  integrity validation. Stronger process isolation would put label validation/scoring in
  a separate process or capability boundary.
- The same repository contains corpus, evaluator, and detector code. Static review can
  establish dataflow structure, not prove the absence of unrecorded out-of-band human
  knowledge.
- Corpus authoring had only protocol/schema-level procedural separation and no
  independent or blinded reviewer.

Within those limits, no label, pair, or family metadata reached a detector-facing object,
and no benchmark-specific detector branch was found.
