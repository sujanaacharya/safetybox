# EXP-009 held-out corpus diversity review

This review records authored characteristics only. It contains no trajectory-monitor outcome.

| Dimension | Count |
|---|---:|
| TRJ-001 positive | 20 |
| TRJ-001 negative | 20 |
| TRJ-002 positive | 20 |
| TRJ-002 negative | 20 |
| Straightforward cases | 10 |
| Variants | 34 |
| Hard negatives | 36 |
| Contrast pairs | 10 (20 members) |
| Window-edge cases | 16 |
| Threshold-edge cases | 40 |

## Task categories

| Category | Count |
|---|---:|
| CODE_ANALYSIS | 23 |
| PROJECT_MAINTENANCE | 17 |
| DIAGNOSTICS | 17 |
| REPORTING | 13 |
| DATA_INSPECTION | 4 |
| MIGRATION_CHECK | 4 |
| DEPENDENCY_LOOKUP | 2 |

## Edge coverage

Window annotations: inside 8 (3), evidence separated (3), ends at 8 (1), exceeds 8 (4), reordered (2), missing database (1), missing egress (1), repeated collection (1). Threshold annotations: two distinct (1), exactly three (19), three distinct (14), four distinct (4), same resource repeated three times (1), mixed action types (1).

## Deterministic duplicate review

The structural comparison used action sequence, task category, capability set, label, and resource-shape pattern. Exact duplicates were not retained. The ten CP-001 through CP-010 pairs intentionally have identical action/resource sequences and opposite labels, but their objectives differ: local analysis versus an explicitly required reporting/export workflow. This is a reviewed contrast, not a duplicate.

## Manual label review

All 80 definitions were reviewed against the pre-freeze questions: clear task objective, plausible synthetic sequence, detector-independent label rationale, coherent contract, explicit positive deviation or negative legitimate explanation, material distinction, and no accidental renamed duplicate. TRJ-001 positives are individually policy-allowed; TRJ-002 positives retain policy denials by design.
