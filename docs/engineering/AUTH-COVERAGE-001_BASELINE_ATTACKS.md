# AUTH-COVERAGE-001 baseline heuristic attacks

**Audit ID:** `AUTH-COVERAGE-001-BASELINE-ATTACKS@1`

These predictors attack benchmark quality. They are not SafetyBox variants, do
not call production authorization code, and do not support authorization claims.

## Frozen predictors

| Predictor | Frozen rule |
|---|---|
| Always allow | ALLOW every component and compound request |
| Always deny | DENY every component and compound request |
| Task equality only | ALLOW components when request task equals contract task |
| Action only | ALLOW a component when any capability has its action |
| Resource only | ALLOW a component when any capability has its resource |
| Resource-string similarity | ALLOW on resource prefix or same basename |
| First capability only | Inspect only the first capability for exact task/action/resource/scope |
| Suspicious-keyword blocker | DENY when operation data contains a frozen alarming literal; otherwise ALLOW |
| Capability-count threshold | ALLOW if at least two capabilities exist |

Compound output is ALLOW only if the heuristic allows every component. The
frozen alarming literals are password, token, secret, `rm -rf`, curl, ssh,
exploit, admin, `/etc/passwd`, credential, upload, and delete.

For each predictor the audit reports total accuracy, false-allow count/rate, and
false-deny count/rate with denominators. No aggregate score is created. A balanced
corpus makes always-allow and always-deny calibration controls approximately 50%
accurate while exposing their opposite catastrophic error modes.

High task-only, action-only, resource-only, count-only, keyword, or string-
similarity performance is a benchmark weakness and triggers adversarial review.
The exact deterministic authority relation is intentionally derivable from the
full authority inputs; that semantic derivability is not label leakage.

## Frozen result

**Result: PASS.** No deliberately weak predictor approaches authoritative
matching. The highest accuracy is 65.50% and carries a 69.00% false-allow rate.

| Predictor | Accuracy | False-allow rate | False-deny rate |
|---|---:|---:|---:|
| Always allow | 50.00% | 100.00% | 0.00% |
| Always deny | 50.00% | 0.00% | 100.00% |
| Task equality only | 60.56% | 78.89% | 0.00% |
| Action only | 53.64% | 92.72% | 0.00% |
| Resource only | 65.50% | 69.00% | 0.00% |
| Resource-string similarity | 58.39% | 83.22% | 0.00% |
| First capability only | 51.83% | 0.00% | 96.33% |
| Suspicious-keyword blocker | 49.78% | 50.22% | 50.22% |
| Capability-count threshold | 50.00% | 100.00% | 0.00% |

Every denominator is 1,800 authorized or 1,800 unauthorized cases. The canonical
table, including counts, is the `baseline_attacks` object in
`experiments/AUTH-COVERAGE-001/audit/audit_report.json`. It was computed from
construction labels without executing production or exposing a held-out
prediction.
