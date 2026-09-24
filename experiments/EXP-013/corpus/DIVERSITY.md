# Corpus Diversity

This report covers `EXP-013-CORPUS@1`. Primary distributions are label-stratified; the 16 secondary controls are reported separately.

## Family by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `MS-A` | 7 | 7 | 14 |
| `MS-B` | 7 | 7 | 14 |
| `MS-C` | 7 | 7 | 14 |
| `MS-D` | 7 | 7 | 14 |
| `MS-E` | 6 | 6 | 12 |
| `MS-F` | 6 | 6 | 12 |

## Task category by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `analytics_processing` | 3 | 3 | 6 |
| `artifact_preparation` | 4 | 4 | 8 |
| `backup_preparation` | 4 | 4 | 8 |
| `compliance_preparation` | 3 | 3 | 6 |
| `configuration_rollout` | 3 | 3 | 6 |
| `content_publishing` | 3 | 3 | 6 |
| `dataset_preparation` | 3 | 3 | 6 |
| `dependency_analysis` | 4 | 4 | 8 |
| `diagnostic_workflow` | 3 | 3 | 6 |
| `document_transformation` | 3 | 3 | 6 |
| `migration_verification` | 4 | 4 | 8 |
| `release_packaging` | 3 | 3 | 6 |

## Sequence length by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `2` | 1 | 1 | 2 |
| `3` | 1 | 1 | 2 |
| `4` | 5 | 5 | 10 |
| `5` | 9 | 9 | 18 |
| `6` | 14 | 14 | 28 |
| `7` | 8 | 8 | 16 |
| `8` | 2 | 2 | 4 |

## Sequence shape by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `eight_step_grouped` | 1 | 1 | 2 |
| `eight_step_reordered` | 1 | 1 | 2 |
| `five_step_boundary` | 1 | 1 | 2 |
| `five_step_cross_phase` | 1 | 1 | 2 |
| `five_step_fallback_edge` | 1 | 1 | 2 |
| `five_step_grouped` | 1 | 1 | 2 |
| `five_step_interleaved` | 1 | 1 | 2 |
| `five_step_multi_source` | 1 | 1 | 2 |
| `five_step_post_finalization` | 1 | 1 | 2 |
| `five_step_reordered` | 1 | 1 | 2 |
| `five_step_termination` | 1 | 1 | 2 |
| `four_step_fallback_order` | 1 | 1 | 2 |
| `four_step_grouped` | 1 | 1 | 2 |
| `three_step_interleaved` | 1 | 1 | 2 |
| `four_step_post_finalization` | 1 | 1 | 2 |
| `four_step_transition` | 2 | 2 | 4 |
| `seven_step_boundary` | 2 | 2 | 4 |
| `seven_step_cross_phase` | 1 | 1 | 2 |
| `seven_step_episode` | 1 | 1 | 2 |
| `seven_step_multi_source` | 1 | 1 | 2 |
| `seven_step_reordered` | 2 | 2 | 4 |
| `seven_step_transition` | 1 | 1 | 2 |
| `six_step_fallback_order` | 1 | 1 | 2 |
| `six_step_grouped` | 2 | 2 | 4 |
| `six_step_interleaved` | 1 | 1 | 2 |
| `six_step_multi_source` | 1 | 1 | 2 |
| `six_step_post_finalization` | 1 | 1 | 2 |
| `six_step_reentry` | 4 | 4 | 8 |
| `six_step_reordered` | 2 | 2 | 4 |
| `six_step_repeated` | 1 | 1 | 2 |
| `six_step_restart` | 1 | 1 | 2 |
| `two_step_reordered` | 1 | 1 | 2 |

## History dimension by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `CROSS_PHASE` | 6 | 6 | 12 |
| `CROSS_SOURCE_GROUPING` | 7 | 7 | 14 |
| `FALLBACK_PROGRESSION` | 6 | 6 | 12 |
| `ORDER_TRANSITION` | 7 | 7 | 14 |
| `POST_FINALIZATION` | 7 | 7 | 14 |
| `ROLE_ACCUMULATION` | 7 | 7 | 14 |

## Role-group count by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `0` | 26 | 26 | 52 |
| `2` | 8 | 8 | 16 |
| `3` | 6 | 6 | 12 |

## Phase count by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `0` | 20 | 20 | 40 |
| `2` | 2 | 2 | 4 |
| `3` | 18 | 18 | 36 |

## Fallback type by label

| Value | Positive | Negative | Total |
|---|---:|---:|---:|
| `EXPLICIT_TRANSITIONS` | 3 | 3 | 6 |
| `NONE` | 34 | 34 | 68 |
| `ORDERED` | 3 | 3 | 6 |

## Provenance sources

| Authority | Primary scenarios containing authority | Positive | Negative |
|---|---:|---:|---:|
| `TASK_CONTRACT` | 80 | 40 | 40 |
| `SYSTEM_POLICY` | 80 | 40 | 40 |
| `RESOURCE_REGISTRY` | 80 | 40 | 40 |
| `TOOL_ADAPTER` | 80 | 40 | 40 |

No trusted authority is label-exclusive; `AGENT_SELF_REPORT` occurs zero times.

## Controls

| Control type | Family/type | Count |
|---|---|---:|
| `PARTIAL_CONTEXT` | `PC-FALLBACK` | 2 |
| `PARTIAL_CONTEXT` | `PC-FINAL` | 2 |
| `PARTIAL_CONTEXT` | `PC-PHASE` | 2 |
| `PARTIAL_CONTEXT` | `PC-ROLE` | 2 |
| `STALE_CONTEXT` | `SC-REVISION` | 4 |
| `STALE_CONTEXT` | `SC-SEMANTIC` | 4 |

Stale controls split evenly: 4 detectable reference mismatches and 4 internally consistent semantic-staleness cases. Partial controls cover each of the four history dimensions twice.

## Counterfactual pair distribution

| Family | Complete strong pairs |
|---|---:|
| `MS-A` | 7 |
| `MS-B` | 7 |
| `MS-C` | 7 |
| `MS-D` | 7 |
| `MS-E` | 6 |
| `MS-F` | 6 |
| **Total** | **40** |

## Review

- All 12 task categories occur under both primary labels.
- Lengths 2, 3, 4, 5, 6, 7, and 8 occur; every length is label-balanced.
- Reordered, interleaved, repeated/progression, phase-transition, multi-source, post-finalization, and scope-grouping structures are present.
- Family, history dimension, phase count, role-group count, fallback type, task category, sequence length, and provenance authority are not label-exclusive.
- Primary pairs share static context and observation multisets, so diversity is obtained across pairs rather than by weakening within-pair parity.
