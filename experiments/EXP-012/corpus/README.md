# EXP-012-CORPUS@1

## Purpose and status

This is the frozen held-out contextual trajectory corpus for EXP-012. It was authored after the M5.1-C freeze at `bd21c4cc6f0c5e5b176fc7cf471aa7d72bb76d71` and before evaluation. The corpus contains 80 primary scenarios and four deliberate missing-context controls. It contains no detector predictions, performance measurements, or result artifacts.

Definitions live in `src/safetybox/experiments/exp012_corpus.py`. They are frozen dataclasses containing simulator inputs, TaskContext values, and ObservationContext values, but no ground-truth label. `labels.yaml` is the canonical ground truth and is never passed as detector input. The JSON documents use a YAML-compatible subset and require no executable loader.

## Frozen protocol extraction

Primary question: “Can explicit deterministic task-purpose and action-purpose context reduce trajectory false positives on task-context contrast cases while preserving detection of contextually inappropriate trajectories?”

The five frozen hypotheses are:

- `H-CTX-01`: “A deterministic context-aware trajectory monitor will reduce false positives on task-context contrast scenarios relative to frozen M5 sequence-only monitoring.”
- `H-CTX-02`: “The context-aware monitor will preserve detection of contextually inappropriate collection-to-egress trajectories that are individually authorized.”
- `H-CTX-03`: “Explicit task-purpose context will improve discrimination between structurally similar positive and benign trajectories.”
- `H-CTX-04`: “Explicit denied-action purpose context will reduce benign TRJ-002-like probing false positives without requiring an LLM.”
- `H-CTX-05`: “Context-aware monitoring will remain deterministic and reproducible for equivalent semantic inputs.”

The baselines are `B0` “Action-level authorization only,” `B1` “Frozen M5 sequence/count monitor,” and `B2` “Future M5.1 context-aware deterministic monitor.” The protocol excludes `LLM_only_monitor` and `deterministic_plus_LLM_hybrid`.

The exact allowed context fields are `task_id`, `declared_purpose_id`, `allowed_outcome_ids`, `allowed_data_flows`, `allowed_destination_ids`, `allowed_destination_purpose_ids`, `resource_bindings_and_roles`, `data_classes`, `expected_action_purpose_ids`, `expected_fallback_patterns`, `lightweight_logical_lineage_references`, and `per_field_authority_and_immutable_reference`.

The required held-out families are:

- A: same or closely matched action sequence with different task purpose;
- B: same task purpose with different destination purpose or approval;
- C: same destination with different resource role or data class;
- D: legitimate repeated denied fallback behavior within declared bounds;
- E: undeclared repeated boundary probing;
- F: contextually suspicious structurally unfamiliar trajectories, without requiring the exact TRJ-001 sequence; and
- G: benign workflows with superficially suspicious structure.

The co-primary metrics are `scenario_level_detection_rate` and `scenario_level_false_positive_rate`. The registered pair and hard-negative metrics are `contrast_pair_discrimination` and `hard_negative_false_positive_rate`. Secondary metrics are `precision`, `F1`, `contrast_pair_discrimination`, `hard_negative_false_positive_rate`, `rule_family_detection_rate`, `actions_to_detection`, `finding_explainability_completeness`, `semantic_determinism`, `abstention_count_and_rate`, `deterministic_error_count_and_rate`, and `policy_blocked_step_counts`.

The exact minimum targets are 80 distinct scenarios, 40 trajectory positives, 40 contextual negatives, 10 complete pairs, 20 pair members, 20 hard negatives, 10 individually authorized collection-to-egress positives, eight Family D negatives, eight Family E positives, and eight Family F positives. Renamed duplicates do not count; higher counts must be substantively distinct and frozen before evaluation. At least eight positives must differ from the exact `read, read, query, send` sequence.

The contaminated sets are `EXP-009-CORPUS@1`, all existing EXP-009 scenarios, and every scenario used or inspected during M5.1 implementation. This corpus also explicitly excludes the M5.1-A examples, M5.1-B tests, and M5.1-C development traces named by the authoring task. Contaminated material is development/regression-only and prohibited from unbiased evaluation.

The stopping rule is: “Final evaluation ends only after every frozen eligible held-out scenario has been evaluated once under both B1 and B2 and every designated reproducibility check is recorded. There is no performance-based early stopping and no scenario deletion, relabeling, or replacement after observing results.”

Future result provenance must record `protocol_commit_sha_and_file_sha256`, `frozen_m5_baseline_detector_sha`, `m5_1_detector_git_sha_and_relevant_hashes`, `held_out_corpus_git_sha_version_and_manifest_label_hashes`, `raw_and_summary_result_shas`, `safetybox_version`, `exact_python_version`, `os_platform_architecture`, `context_schema_version`, `task_contract_policy_tool_adapter_resource_registry_versions_and_hashes`, `execution_and_analysis_commands`, and `canonical_event_audit_references_and_hashes`.

## Ground truth and denominator treatment

`TRAJECTORY_POSITIVE` means contextually inappropriate; `TRAJECTORY_NEGATIVE` means contextually legitimate. Rationales use task purpose, destination semantics, resource/data roles, or fallback declarations and make no claim of byte-level transfer. The four `INSUFFICIENT_CONTEXT_CONTROL` entries are deterministic abstention fixtures and contribute to neither primary denominator.

Action authorization and trajectory meaning remain separate. Access-and-egress primary cases are individually authorized. Families D and E intentionally contain action-level denials; their labels concern repeated behavior relative to a trusted fallback declaration.

## Independence and limitations

The authoring process did not instantiate or run either trajectory monitor on this corpus and did not inspect predictions. Scenarios were designed from preregistered semantic families, not source branches. The same research environment knows the architecture, which is recorded as a validity threat. Synthetic declarations may be cleaner than deployment context, and logical lineage records compatibility only; it does not prove payload or byte flow.

A material change to an action sequence, contract, context, observation metadata, label, or rationale requires a new corpus version. The future commit containing these files is the corpus-freeze commit; no uncreated SHA is claimed.
