# EXP-009-A3 — Trajectory rule-availability ablation

This directory contains the preregistered paired rule-availability ablation of the unchanged frozen `EXP-009-CORPUS@1` corpus. The only independent variable is the enabled trajectory rule set: `TRJ-001` only, `TRJ-002` only, or both rules. The trajectory window remains 8 and the `TRJ-002` distinct-resource threshold remains 3.

Each JSONL contains exactly 80 deterministic scenario records. Every condition re-evaluates the same frozen canonical event traces with a fresh `TrajectoryMonitor`; the 240 records are paired evaluations, not independent samples. Rule availability is supplied through the existing `TrajectoryMonitor(rules=...)` configuration seam. No detector source was changed.

`both.jsonl` reproduces the frozen EXP-009 base result exactly: TP/FP/TN/FN = 40/33/7/0. Complete findings, finding rule IDs, evidence positions, detection positions, and actions-to-detection match all 80 frozen base records.

`summary.json` contains condition metrics, family breakdowns, TP/FP attribution, hard-negative and contrast-pair results, policy-versus-trajectory counts, paired transitions, and semantic union/interaction checks. `environment.json` records frozen references and input hashes. `SHA256SUMS` authenticates only the A3 artifacts in this directory.
