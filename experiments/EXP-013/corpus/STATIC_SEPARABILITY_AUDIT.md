# Static Separability Audit

Corpus: `EXP-013-CORPUS@1`
Method: deterministic contingency analysis over 80 primary scenarios; no model was trained and no B4 output was inspected.

## Single-feature checks

| Feature | Distinct values | Contingency profile `(positive, negative)` | Best value-lookup accuracy | Perfect separator |
|---|---:|---|---:|---|
| `context_completeness` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `declaration_count` | 13 | 5 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (3, 3); 3 value(s) x (4, 4); 2 value(s) x (5, 5); 1 value(s) x (8, 8) | 0.500 | NO |
| `number_of_phases` | 3 | 1 value(s) x (2, 2); 1 value(s) x (18, 18); 1 value(s) x (20, 20) | 0.500 | NO |
| `number_of_roles` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `number_of_role_groups` | 3 | 1 value(s) x (6, 6); 1 value(s) x (8, 8); 1 value(s) x (26, 26) | 0.500 | NO |
| `destination_presence` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `fallback_declaration_presence` | 2 | 1 value(s) x (6, 6); 1 value(s) x (34, 34) | 0.500 | NO |
| `sequence_length` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `final_action` | 11 | 2 value(s) x (0, 1); 2 value(s) x (1, 0); 1 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (3, 3); 1 value(s) x (5, 5); 1 value(s) x (6, 6); 1 value(s) x (7, 7); 1 value(s) x (14, 14) | 0.525 | NO |
| `final_ContextEvaluation_status` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `any_mismatch_presence` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `any_insufficient_context_presence` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `task_category` | 12 | 8 value(s) x (3, 3); 4 value(s) x (4, 4) | 0.500 | NO |
| `purpose_id` | 40 | 40 value(s) x (1, 1) | 0.500 | NO |
| `trusted_source_count` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |
| `action_multiset` | 39 | 38 value(s) x (1, 1); 1 value(s) x (2, 2) | 0.500 | NO |
| `observation_count` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `role_count` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `fallback_attempt_count_alone` | 3 | 1 value(s) x (2, 2); 1 value(s) x (4, 4); 1 value(s) x (34, 34) | 0.500 | NO |
| `phase_count_alone` | 3 | 1 value(s) x (2, 2); 1 value(s) x (18, 18); 1 value(s) x (20, 20) | 0.500 | NO |
| `outcome_count` | 1 | 1 value(s) x (40, 40) | 0.500 | NO |

No single preregistered feature perfectly separates the primary labels. Missingness is zero for every tested primary feature.

## Preregistered obvious combinations

| Combination | Distinct values | Contingency profile `(positive, negative)` | Best value-lookup accuracy | Perfect separator |
|---|---:|---|---:|---|
| `final_ContextEvaluation_status` + `sequence_length` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `role_count` + `outcome_count` | 7 | 2 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (5, 5); 1 value(s) x (8, 8); 1 value(s) x (9, 9); 1 value(s) x (14, 14) | 0.500 | NO |
| `task_category` + `phase_count_alone` | 26 | 13 value(s) x (1, 1); 12 value(s) x (2, 2); 1 value(s) x (3, 3) | 0.500 | NO |
| `fallback_declaration_presence` + `fallback_attempt_count_alone` | 3 | 1 value(s) x (2, 2); 1 value(s) x (4, 4); 1 value(s) x (34, 34) | 0.500 | NO |
| `final_action` + `context_completeness` | 11 | 2 value(s) x (0, 1); 2 value(s) x (1, 0); 1 value(s) x (1, 1); 1 value(s) x (2, 2); 1 value(s) x (3, 3); 1 value(s) x (5, 5); 1 value(s) x (6, 6); 1 value(s) x (7, 7); 1 value(s) x (14, 14) | 0.525 | NO |

Exactly these five combinations were checked; no combinatorial search was performed.

## Identifier and label-leakage checks

- All runtime scenario objects omit labels, pair IDs, family IDs, and rationales.
- Pair-shared task IDs and purpose IDs each occur once under each primary label.
- Scenario suffix `A` and `B`, numeric parity, task category, and purpose ID do not perfectly separate labels.
- The prohibited identifier/description terms audit covers scenario, task, purpose, action, resource, event, role, group, phase, and sequence-shape values and passed.
- Context completeness, local mismatch presence, local insufficient-context presence, final local status, and every tested missingness indicator are label-balanced.

## Result

**PASS.** Neither a single preregistered feature nor any preregistered obvious combination perfectly recovers the primary labels.
