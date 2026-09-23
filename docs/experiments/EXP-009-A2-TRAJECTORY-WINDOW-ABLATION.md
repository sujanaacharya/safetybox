# EXP-009-A2 — Trajectory window-size ablation

## Purpose

EXP-009-A2 characterizes the detection behavior of bounded trajectory windows of 4, 8, and 16 observations on the unchanged frozen `EXP-009-CORPUS@1` held-out corpus. It is an ablation, not detector tuning. The frozen base remains window 8.

## Frozen references

| Reference | SHA / commit |
|---|---|
| Protocol | `17e16d63d9bbf9b17b94d2b4ada7b81f27e3c6f6` |
| Corpus | `b91458f672edb72eaa7b1f3df67dc844933c19c4` |
| Detector | `6dc4a6eac7db315a06d9b165234eb1388ee89529` |
| Base result | `30dc4b5823bb00abfdb14ae74f21d9c43fe48bf6` |
| Base analysis | `88cf8c1b4c45ab9519afeeb6f6c091b9b50b981e` |
| A1 result | `870507f611432fa30a76b4772866080498c230ef` |
| Current HEAD at execution | `870507f611432fa30a76b4772866080498c230ef` |

The protocol preregisters window values 4, 8, and 16. No other window was evaluated. Input artifact SHA-256 values are in `results/EXP-009/ablations/trajectory-window/environment.json`.

## Design and controls

The independent variable is the trajectory state-window size: 4, 8, or 16 completed canonical M3 terminal observations per session/task. `TRJ-001`, `TRJ-002`, the `TRJ-002` threshold (3), observation source and semantics, ordering, session/task isolation, task contracts, labels, and the frozen corpus were held fixed. Each scenario received a fresh monitor state.

This is a paired deterministic design: each of the same 80 frozen scenario traces was run under each of the three configurations. Thus 80 × 3 records are not 240 independent samples; the unit remains the frozen scenario trace.

## Results

All three window conditions produced identical aggregate and per-scenario results.

| Window | TP | FP | TN | FN | Detection rate | FPR | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 40 | 33 | 7 | 0 | 1.000 | 0.825 | 0.548 | 1.000 | 0.708 |
| 8 | 40 | 33 | 7 | 0 | 1.000 | 0.825 | 0.548 | 1.000 | 0.708 |
| 16 | 40 | 33 | 7 | 0 | 1.000 | 0.825 | 0.548 | 1.000 | 0.708 |

Window 8 reproduced the frozen base exactly (TP/FP/TN/FN 40/33/7/0); there were no mismatched scenarios. Reproduction was checked from recomputed output, not hard-coded scoring totals.

### TRJ-001 breakdown

For every window, the TRJ-001-specific matrix was 20 TP, 16 FP, 4 TN, and 0 FN (20 positives and 20 negatives). Detection rate/recall was 1.000, FPR 0.800, precision 0.556, and F1 0.714.

Window 4 did not fail on the corpus's longer staged patterns, window 16 did not recover additional trajectories, and window 16 did not add incidental TRJ-001 matches. The rule evaluates the exact four-observation suffix; all detected matches in this corpus were present when their terminal send arrived, including the labeled longer traces.

### TRJ-002 breakdown

For every window, the TRJ-002-specific matrix was 20 TP, 17 FP, 3 TN, and 0 FN (20 positives and 20 negatives). Detection rate/recall was 1.000, FPR 0.850, precision 0.541, and F1 0.702.

Exactly-three cases had 3 TP and 16 FP; `FOUR_DISTINCT` had 3 TP and 1 FP; `THREE_DISTINCT` had 14 TP; `TWO_DISTINCT`, `SAME_RESOURCE_X3`, and `MIXED_ACTION_TYPES` were each TN. The separated-denial cases remained detected at all windows. The repeated denied fallback-probing false positives therefore persist independently of the window value tested here.

## Window-edge cases

The frozen corpus's actual `window_edge_category` labels, rather than new categories, were used. Results were identical at every window: `INSIDE_8` 3/3 flagged, `ENDS_AT_8` 1/1 flagged, `EVIDENCE_SEPARATED` 3/3 flagged, `EXCEEDS_8` 4/4 flagged (2 TP, 2 FP), and `REPEATED_COLLECTION` 1/1 flagged. Negative controls remained unflagged: `MISSING_DATABASE` 0/1, `MISSING_EGRESS` 0/1, and `REORDERED` 0/2.

The preregistration's descriptive phrases “comfortably within 4”, “within 8”, “near 8”, “exceeds 8”, “within 16”, “evidence-separated”, and repeated-collection variants do not all appear as literal corpus labels; the registered labels above are reported exactly.

## Hard negatives and contrast pairs

Each configuration had 36 hard negatives, of which 33 were flagged: hard-negative FPR 0.917. The larger window did not increase hard-negative flags on this corpus.

All ten contrast pairs (`CP-001` through `CP-010`) were category B at every window: both positive and negative were flagged. These context-insensitive pairs remain B across the ablation, so the evidence does not attribute that limitation to window size.

## Detection delay

For detected positives, every window had the same actions-to-detection summary: overall minimum 3, maximum 10, mean 4.1, median 4.0. TRJ-001: minimum 4, maximum 10, mean 5.0, median 4.0. TRJ-002: minimum 3, maximum 4, mean 3.2, median 3.0. No positive was missed. Changing the state bound did not change detection position in these traces.

## Paired transitions and monotonicity

Among positives, all 40 were detected under 4+8+16; none were detected only at a subset or missed under all three. Among negatives, 33 were flagged under 4+8+16 and 7 were unflagged under all three; every other named combination had count zero. There was no non-monotonic behavior and no outcome transition at all. This is consistent with the actual rule behavior: TRJ-001 tests the latest four observations and TRJ-002 evidence was retained at detection even in window 4. It is not a general proof that larger windows are supersets under all possible rule implementations.

## Interpretation, limitations, and future research

The tested state bounds differ conceptually—4, 8, and 16 observations retained per session/task—but no runtime or memory performance was measured, so no performance claim is made. On this fixed corpus, the ablation reveals no detection/false-positive tradeoff attributable to window size; the high false-positive burden instead remains visible at every bound. This does not establish equivalence on traces where evidence falls outside a smaller retained window, nor does it justify a detector modification or a default change.

The frozen base remains window 8. This supporting characterization does not update H-02 or CL-002. The next preregistered research task is EXP-009-A3, the rule-availability ablation (`TRJ-001` only, `TRJ-002` only, both); it is not begun here.
