# EXP-012-CORPUS@1 diversity review

Counts below describe authored inputs only. They are not detector results. Primary label denominators exclude the four missing-context controls.

## Composition

| Dimension | Count |
|---|---:|
| All definitions | 84 |
| Primary scenarios | 80 |
| Trajectory positive | 40 |
| Trajectory negative | 40 |
| Insufficient-context controls | 4 |
| Complete contrast pairs | 28 (56 members) |
| Hard negatives | 40 |
| Individually authorized positive access-to-egress cases | 30 |

## Family and label

| Family | Positive | Negative | Control | Total |
|---|---:|---:|---:|---:|
| A | 6 | 6 | 0 | 12 |
| B | 6 | 6 | 0 | 12 |
| C | 6 | 6 | 0 | 12 |
| D | 0 | 10 | 0 | 10 |
| E | 10 | 0 | 0 | 10 |
| F | 12 | 0 | 0 | 12 |
| G | 0 | 12 | 0 | 12 |
| CONTROL | 0 | 0 | 4 | 4 |

## Task categories

| Category | Primary count |
|---|---:|
| analytics_delivery | 5 |
| artifact_publishing | 5 |
| backup | 3 |
| compliance_review | 8 |
| configuration_migration | 9 |
| data_export | 6 |
| dependency_audit | 8 |
| document_generation | 10 |
| local_code_analysis | 3 |
| local_diagnostics | 8 |
| migration_verification | 5 |
| release_preparation | 9 |
| remote_report_delivery | 1 |

The 13 categories exceed the protocol minimum of six. `remote_report_delivery` and `migration_verification` are held-out category additions beyond the preregistered candidate list.

## Sequence shapes

| Shape | Count |
|---|---:|
| collection_before_egress | 1 |
| denial_sequence | 20 |
| four_step | 2 |
| interleaved_local_operations | 2 |
| multi_source_collection | 3 |
| three_step | 22 |
| two_step | 30 |

All 12 Family F positives differ from the frozen four-action `filesystem.read, filesystem.read, database.query, network.send` sequence. Shapes include two-, three-, and four-step traces, interleaved local work, multi-source collection, and denial sequences.

## Destination purposes

| Purpose | Count |
|---|---:|
| analytics_delivery | 5 |
| archive_backup | 3 |
| artifact_publication | 12 |
| compliance_delivery | 8 |
| dependency_registry | 4 |
| diagnostics_collection | 4 |
| document_delivery | 8 |
| migration_service | 8 |
| report_delivery | 8 |

## Resource and data roles

| Role | Count |
|---|---:|
| analytics_data | 18 |
| backup_snapshot | 3 |
| configuration | 12 |
| dependency_metadata | 4 |
| diagnostic_output | 4 |
| document_template | 4 |
| generated_report | 27 |
| lookup_metadata | 20 |
| migration_metadata | 8 |
| release_artifact | 13 |
| source_material | 17 |
| verification_metadata | 1 |

Counts are scenario presences, not occurrence totals. Role declarations cover source material, configuration, analytics, dependency metadata, generated reports, release artifacts, diagnostics, migration metadata, backup snapshots, templates, verification metadata, and lookup metadata.

## Fallback types

| Type | Count |
|---|---:|
| catalog_fallback | 2 |
| dependency_discovery | 2 |
| diagnostic_alternative | 2 |
| endpoint_fallback | 2 |
| format_probe | 2 |
| locale_fallback | 2 |
| migration_lookup | 4 |
| toolchain_fallback | 2 |
| version_fallback | 2 |

Each type appears as a D/E contrast; migration lookup has two substantively different resource/action settings. Attempt counts vary between three and four, actions span filesystem, artifact, database, registry, service, network, and document operations, and every declaration includes a numeric bound plus a termination condition.

## Duplicate and concentration review

No exact input/context duplicate is retained. No same-sequence/same-context entry appears under a new ID. Intentional contrast members share observable structure but differ in the declared semantic variable documented in `CONTRAST_PAIRS.md`. Rationales were reviewed for task-specific substance rather than resource-only renaming. No single category, shape, destination purpose, data role, or fallback type determines a label.

