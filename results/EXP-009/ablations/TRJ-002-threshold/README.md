# EXP-009-A1 — TRJ-002 denial-threshold ablation

This directory is separate from the frozen EXP-009 base run. It contains three deterministic, paired evaluations of the unchanged `EXP-009-CORPUS@1`, varying only the distinct denied-resource threshold of an evaluation-time `TRJ-002` rule instance: 2, 3, and 4.

`threshold-3.jsonl` is a reproducibility/reference condition, not an independent sample. Its TRJ-002 matrix recomputed as 20 TP, 17 FP, 3 TN, and 0 FN, matching the frozen base analysis.

Each JSONL file has 80 records. The same scenarios occur in each condition, so the 240 records are not 240 independent scenario samples. `summary.json` contains condition metrics, edge strata, delay values, and paired transitions. `environment.json` records frozen commits, input hashes, and the evaluation-layer configuration injection. `SHA256SUMS` hashes the artifacts in this directory.

No detector source, corpus, protocol, base results, labels, task contracts, or policy behavior was changed.
