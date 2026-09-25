# AUTH-COVERAGE-001 difficulty audit

**Audit ID:** `AUTH-COVERAGE-001-DIFFICULTY-AUDIT@1`

Difficulty is structural authority distance, not reviewer intuition and not a
risk score. It never changes the authorization oracle.

## Frozen features

Every scenario has a separate difficulty record containing:

- authority distance;
- matching and mismatching component counts;
- exact and near resource-match counts;
- partial-capability-match count;
- irrelevant-capability and total-capability counts;
- compound-component count;
- suspicious-literal count; and
- structural score and class.

The frozen structural score is:

```text
min(irrelevant_capability_count, 6)
+ 2 * near_resource_match_count
+ 2 * partial_capability_match_count
+ 2 * (compound_component_count - 1)
+ 2 if authority_distance == 1 else 0
+ 1 if authority_distance >= 2 else 0
+ 1 if suspicious_literal_count > 0 else 0
```

Class boundaries are `EASY_CONTROL` 0–11, `MODERATE` 12–15, `HARD` 16–21, and
`ADVERSARIAL` 22 or greater. The auditor independently recomputes score and class
from the frozen fields and requires exact agreement with both the difficulty file
and label metadata.

Authority distance is corpus-analysis metadata: zero is an exact authorization;
one is a nearest authority object with one authorization-relevant mismatch; two
or more records multiple mismatches. It is not a probability, severity, or
behavioral-suspicion score.

## Freeze gates

Freeze requires:

- one difficulty record per scenario and no extra records;
- exact label/difficulty agreement;
- exact formula/class agreement;
- a corpus dominated by `MODERATE`, `HARD`, and `ADVERSARIAL`; and
- separately reported filesystem and process distributions in the final audit.

The result cannot establish human difficulty, operational realism, or resistance
to an adaptive attacker. `HARD_BENIGN`, `HARD_UNAUTHORIZED`, `EDGE_BENIGN`, and
`EDGE_UNAUTHORIZED` are corpus families, not substitutes for the structural
difficulty class.

## Frozen result

**Result: PASS.** The canonical distribution is 70 `EASY_CONTROL`, 1,003
`MODERATE`, 1,746 `HARD`, and 781 `ADVERSARIAL`. Thus 3,530/3,600 (98.06%) are
moderate or harder and the benchmark is dominated by the intended structural
difficulty classes. All 3,600 formula recomputations agree with the frozen score
and class, and all 3,600 label/difficulty records agree on class and authority
distance.

Canonical counts and mismatch lists are recorded in
`experiments/AUTH-COVERAGE-001/audit/audit_report.json`. No held-out decision was
made by this audit.
