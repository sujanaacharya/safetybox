# EXP-009-A2 — Trajectory window-size ablation

This directory contains the preregistered paired window-size ablation of the unchanged frozen `EXP-009-CORPUS@1` corpus. The only configuration variable is the `TrajectoryMonitor` state window: 4, 8, and 16 terminal observations per `(session_id, task_id)`.

Each JSONL contains exactly 80 deterministic scenario records. The same frozen trace is evaluated in all three configurations, so the 240 records are not 240 independent samples. A fresh monitor is instantiated for every scenario.

`window-8.jsonl` reproduced the frozen EXP-009 base result exactly: overall TP/FP/TN/FN = 40/33/7/0. All outcome, finding-rule, evidence-sequence, detection-sequence, and actions-to-detection values matched the base records.

All three conditions had the same outcomes on this corpus. This is a characterization result, not a detector change or a choice of a new default. `summary.json` holds machine-readable aggregates and paired transitions; `environment.json` records frozen provenance and input hashes. `SHA256SUMS` authenticates only these A2 artifacts.
