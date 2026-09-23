# EXP-012 frozen paired base evaluation

- Experiment: `EXP-012`
- Run: `EXP-012-RUN-001`
- Evaluation base: `66ec339bfe69a6e7be06c43670dca293c117412b`
- Corpus: `EXP-012-CORPUS@1`
- Scenario records: `84` (`40` positive, `40` negative, `4` controls)
- M5 confusion counts: `{"FN": 30, "FP": 11, "TN": 29, "TP": 10}`
- M5.1 confusion counts: `{"FN": 0, "FP": 0, "TN": 40, "TP": 40}`
- Paired transitions: `{"FN -> FN": 0, "FN -> TP": 30, "FP -> FP": 0, "FP -> TN": 11, "TN -> FP": 0, "TN -> TN": 29, "TP -> FN": 0, "TP -> TP": 10}`
- Infrastructure attempts: `attempts.jsonl`

This directory contains execution records and mechanically derived summaries only.
It contains no result interpretation, claim update, hypothesis update, remediation,
detector change, corpus change, label change, threshold change, or protocol change.
