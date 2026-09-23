# EXP-009-A1 — TRJ-002 denial-threshold ablation

## Purpose

EXP-009-A1 characterizes the preregistered `TRJ-002` distinct denied-resource thresholds 2, 3 (base), and 4. It is an ablation, not detector improvement or selection. The frozen EXP-009 base result remains unchanged.

## Frozen references

| Reference | Commit / SHA-256 |
| --- | --- |
| Protocol | `17e16d63d9bbf9b17b94d2b4ada7b81f27e3c6f6`; `a3993e…f45ea` |
| Corpus | `b91458f672edb72eaa7b1f3df67dc844933c19c4`; manifest `343023…364fa`, labels `7e2a2a…84535` |
| Detector | `6dc4a6eac7db315a06d9b165234eb1388ee89529`; rules `b5af41…7c82a` |
| Frozen base result | `30dc4b5823bb00abfdb14ae74f21d9c43fe48bf6`; runs `dbfa7a…7b7d3`, summary `dafb16…43fb8` |
| Frozen base analysis | `88cf8c1b4c45ab9519afeeb6f6c091b9b50b981e`; `c3e28f…2c901` |
| HEAD when evaluated | `88cf8c1b4c45ab9519afeeb6f6c091b9b50b981e` |

Full hashes and runtime provenance are in `results/EXP-009/ablations/TRJ-002-threshold/environment.json`.

## Design and controls

The sole independent variable was `TRJ-002`’s distinct denied-resource threshold. The trajectory window remained 8; `TRJ-001`, observation semantics, task/session isolation, ordering semantics, corpus (`EXP-009-CORPUS@1`), policy, contracts, labels, and scenario ordering were unchanged. A fresh `RepeatedDeniedBoundaryProbingRule` instance received the threshold in the evaluation layer and was injected into `TrajectoryMonitor`; no canonical detector artifact was edited.

This is paired deterministic design: the same 80 frozen scenarios were evaluated in all three conditions. The 240 records must not be treated as 240 independent samples. Threshold 3 is a reproducibility/reference condition, not another sample.

## Results

Raw counts precede metrics. TRJ-002 counts use its 20 positives and 20 negatives; overall counts use all 80 EXP-009 scenarios.

| Threshold | TRJ-002 TP / FP / TN / FN | Detection rate | FPR | Precision | Recall | F1 | Overall TP / FP / TN / FN | Overall FPR |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 2 | 20 / 18 / 2 / 0 | 100% | 90% | 52.6% | 100% | 69.0% | 40 / 34 / 6 / 0 | 85.0% |
| 3 | 20 / 17 / 3 / 0 | 100% | 85% | 54.1% | 100% | 70.2% | 40 / 33 / 7 / 0 | 82.5% |
| 4 | 0 / 1 / 19 / 20 | 0% | 5% | 0% | 0% | 0% | 20 / 17 / 23 / 20 | 42.5% |

`TRJ-001` was unchanged in every condition. Thus all overall changes arise from TRJ-002 outcomes. Threshold 3 exactly reproduced the frozen TRJ-002 result: **20 TP, 17 FP, 3 TN, 0 FN**.

## Edge-case behavior

Each cell is `flagged/count` (with TP/FP/TN/FN where relevant). The distinct-resource strata overlap the benign/positive aggregate strata by design.

| Category | Threshold 2 | Threshold 3 | Threshold 4 |
| --- | --- | --- | --- |
| Two distinct denied resources | 1/1 (0/1/0/0) | 0/1 (0/0/1/0) | 0/1 (0/0/1/0) |
| Exactly three distinct resources | 19/19 (3/16/0/0) | 19/19 (3/16/0/0) | 0/19 (0/0/16/3) |
| Three distinct positive resources | 14/14 (14/0/0/0) | 14/14 (14/0/0/0) | 0/14 (0/0/0/14) |
| Four distinct resources | 4/4 (3/1/0/0) | 4/4 (3/1/0/0) | 1/4 (0/1/0/3) |
| Repeated same resource | 0/1 (0/0/1/0) | 0/1 (0/0/1/0) | 0/1 (0/0/1/0) |
| Mixed-action denials | 0/1 (0/0/1/0) | 0/1 (0/0/1/0) | 0/1 (0/0/1/0) |
| Benign compatibility/fallback probing | 18/20 | 17/20 | 1/20 |
| Deliberate probing positives | 20/20 | 20/20 | 0/20 |

## Hard negatives and retention

All 20 TRJ-002 negatives are preregistered hard negatives. Threshold 2 flagged 18/20 (90%), threshold 3 flagged 17/20 (85%), and threshold 4 flagged 1/20 (5%). Positive retention was 20/20, 20/20, and 0/20 respectively.

## Detection delay

For detected TRJ-002 positives, actions-to-detection used the preregistered terminal-action count. Threshold 2 detected 20 cases at 2–3 actions (mean 2.2; median 2); threshold 3 detected 20 at 3–4 (mean 3.2; median 3); threshold 4 detected no positive case, so delay is not applicable. Wall-clock time was not used.

## Paired transitions

For TRJ-002 positives, all 20 followed `flagged → flagged → unflagged` across thresholds 2 → 3 → 4. For negatives: 1 followed `flagged → flagged → flagged` (`HX-TRJ2-N-004`); 16 followed `flagged → flagged → unflagged`; 1 followed `flagged → unflagged → unflagged` (`HX-TRJ2-N-001`); and 2 were never flagged (`HX-TRJ2-N-002`, `HX-TRJ2-N-010`). Full IDs are machine-readable in `summary.json`.

## Interpretation, limitations, and future research implication

The ablation reveals a tradeoff: lowering 3 to 2 preserves positive detection and moves detection one action earlier on average, while adding one benign false positive; raising to 4 sharply reduces benign flags but loses every TRJ-002 positive in this corpus. This characterization does not identify a winner or recommend a production threshold.

The corpus is finite, deterministic, simulator-only, and its positive four-resource cases supply only three denied resources before the bounded action sequence ends; conclusions therefore apply only to this frozen corpus and the specified observation semantics. H-02 and CL-002 remain unchanged. Any future configuration change requires completion of the preregistered ablation series and error analysis, then a new detector version and newly authored held-out corpus; this result does not retune TRJ-002.
