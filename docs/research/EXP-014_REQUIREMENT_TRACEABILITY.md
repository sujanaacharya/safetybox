# EXP-014 Adapter Requirement Traceability

**Status:** pre-corpus implementation traceability; no held-out evidence or EXP-014 result

The implementation baseline is the protocol/design freeze
`7baf20293caa83d3fff6a200174c4f8840918607`. `DEVELOPMENT_VALIDATED` means only the
contaminated development suite passed. It never means held-out validation, RTM-1
achievement, production readiness, or a successful EXP-014 evaluation.

| Requirement | Implementation | Tests | Status | Notes |
|---|---|---|---|---|
| REQ-001 | `filesystem/adapter.py`; adapter FMED-L1 docstring | bypass-boundary development test | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Direct routes remain outside the boundary. |
| REQ-002 | `mapping.py`; explicit `LogicalHostMapper` | isolated-root fixture; mapper configuration tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Every test uses `TemporaryDirectory`. |
| REQ-003 | `models.py`; `audit.py` execution dispatch | real successful operation test; request-model tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Exactly nine operations; no recursive or shell API. |
| REQ-004 | `FilesystemOperation`; M2 action matching | per-operation capability denial tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No action implication. |
| REQ-005 | explicit adapter dependencies | adapter construction and isolation tests | IMPLEMENTED / NOT_YET_HELD_OUT_VALIDATED | Trust remains an evaluated assumption. |
| REQ-006 | audit minimization; no content-derived policy path | payload/content nondisclosure tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Content is returned data or hashed observation only. |
| REQ-007 | `ReferenceMonitor`, injected `Authorizer`, `CompoundAuthorizer` | success, denial, task mismatch, exception tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No filesystem allowlist exists. |
| REQ-008 | immutable `FilesystemRequest`; bound `ActionRequest`; argument digest | reconstruction and payload-minimization tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Primitive consumes bound canonical arguments. |
| REQ-009 | `TaskContractPolicy` integration | denial matrix; session/task test | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Existing M2 rule IDs preserved. |
| REQ-010 | `ReferenceMonitor.lifecycle_hook`; `FilesystemExecutionBoundary` | primitive event observation; denial; audit-failure tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Validation is after allow and before committed execution start. |
| REQ-011 | `canonicalization.py`; `mapping.py` | lexical table; real operations | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Policy sees logical paths only. |
| REQ-012 | `canonicalize_logical_path` | traversal, separators, dot, NFC, root and prefix tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Pure component processing. |
| REQ-013 | `LogicalHostMapper` | denial probe spy; mapper tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Mapping is lexical; no pre-auth target API call. |
| REQ-014 | `PhysicalTargetValidator._inspect` and operation preconditions | missing/existing parent/leaf tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Missing tails do not bypass scope checks. |
| REQ-015 | component `lstat`; hard-link terminal checks | symlink categories; parent links; hard-link operation/rename tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Race-sensitive reject-all-v1 only. |
| REQ-016 | `state_digest.py`; mutation state scopes | deterministic digest and denied-mutation tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Host prefixes and unstable metadata excluded. |
| REQ-017 | monitor denial branch | all six denied mutation tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Independent pre/post digest equality plus zero requested calls. |
| REQ-018 | monitor denial branch; minimized results | denied read/list/stat sentinel tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Bytes, child names, metadata, probes, and primitives absent. |
| REQ-019 | generic `CompoundAuthorizer` | four decision combinations; auth exception; rename bypass tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Source then destination, including after source denial. |
| REQ-020 | delete/mkdir/list primitives and validation | file/empty-dir delete, non-empty delete, mkdir, sorted list tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No recursion or implicit parents. |
| REQ-021 | `FilesystemResultCategory`; typed errors | success/deny/failure matrix | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Five frozen outcome categories represented. |
| REQ-022 | adapter exception classification and audit gates | auth, canonical, validation, state-observation, pre-audit tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No primitive on pre-effect failures. |
| REQ-023 | primitive `effect_possible`; audit failure stage | before/partial write and post-audit tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Partial/post-start cases remain indeterminate. |
| REQ-024 | extended `EventType`; `FilesystemAuditEnvelope` | machine reconstruction and compound evidence tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | One canonical M3-compatible stream, not a parallel stream. |
| REQ-025 | hashes/sizes/logical identifiers only | raw payload and sentinel audit tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No raw file content in events. |
| REQ-026 | canonicalizer, validator, compound rename | traversal, prefix, symlink, hard-link, rename tests | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Held-out bypass suite not authored. |
| REQ-027 | documented direct-route boundary | direct `os.open` development demonstration | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | `EXPECTED_FMED_L1_BYPASS`, inside temp root only. |
| REQ-028 | bound identifiers; M2 task binding; session-local recorder | session/task isolation test | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | Recorder remains single-process/non-concurrent. |
| REQ-029 | canonical results, sorted list/digest/event semantics | equivalent-run determinism test | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | UUIDs/timestamps excluded from comparison. |
| REQ-030 | evaluation harness responsibility; no adapter threshold | pre-corpus applicability audit | NOT_APPLICABLE_PRE_CORPUS / NOT_YET_HELD_OUT_VALIDATED | Descriptive performance measurement is intentionally deferred to the frozen evaluation. |
| REQ-031 | source/test separation; `DEV-FS-*` fixtures | prohibited-pattern audit; development report | IMPLEMENTED / NOT_YET_HELD_OUT_VALIDATED | No corpus or results created. |
| REQ-032 | Linux/POSIX boundary in docs and adapter | platform record in development report | DEVELOPMENT_VALIDATED / NOT_YET_HELD_OUT_VALIDATED | No portability claim. |

## Mechanical completeness and concrete development checks

The pre-freeze audit found 32 unique requirement rows, covering the contiguous range
REQ-001 through REQ-032 with no duplicate or orphan. The concrete test symbols below are
in `tests/dev/test_exp014_filesystem_adapter.py` unless another file is named. REQ-030 is
an explicit evaluation-only disposition rather than a fabricated implementation test:
protocol v1 has no performance acceptance threshold.

| Requirement | Concrete development check |
|---|---|
| REQ-001 | `test_expected_fmed_l1_direct_route_bypass_is_demonstrated_only_in_temp_root` |
| REQ-002 | `isolated_root`; `test_expected_fmed_l1_direct_route_bypass_is_demonstrated_only_in_temp_root` |
| REQ-003 | `test_request_models_enforce_operation_specific_arguments`; `test_real_successful_operations_and_audit_lifecycle` |
| REQ-004 | `tests/test_task_contract_policy.py::test_same_resource_different_action_does_not_grant_write` |
| REQ-005 | `test_adapter_requires_explicit_policy_reference`; `adapter_for` dependency injection |
| REQ-006 | `test_write_payload_is_hashed_but_never_recorded_in_audit`; `test_denied_retrieval_discloses_no_protected_value` |
| REQ-007 | `tests/test_reference_monitor.py::test_allowed_action_is_authorized_then_forwarded`; `test_rename_requires_two_recorded_decisions` |
| REQ-008 | `test_real_successful_operations_and_audit_lifecycle`; `test_write_payload_is_hashed_but_never_recorded_in_audit` |
| REQ-009 | `tests/test_task_contract_policy.py::test_task_mismatch_denies_without_execution`; `test_component_prefix_collisions_are_denied_without_probe` |
| REQ-010 | `test_real_successful_operations_and_audit_lifecycle`; `test_denied_mutations_do_not_probe_invoke_or_change_state`; `test_pre_execution_audit_failure_prevents_effect` |
| REQ-011 | `test_pure_lexical_canonicalization`; `test_real_successful_operations_and_audit_lifecycle` |
| REQ-012 | `test_pure_lexical_canonicalization`; `test_lexical_rejections_do_not_depend_on_host_state`; `test_component_prefix_collisions_are_denied_without_probe` |
| REQ-013 | `test_mapper_rejects_ambiguous_configuration_and_noncanonical_resources`; denied probe matrices |
| REQ-014 | `test_missing_and_existing_preconditions_are_tool_errors`; `test_create_and_mkdir_reject_symlinked_parent_after_allow` |
| REQ-015 | `test_symlink_categories_reject_after_allow_before_primitive`; hard-link and rename link tests |
| REQ-016 | `test_state_digest_is_deterministic_and_excludes_host_prefix`; `test_state_digest_changes_for_registered_semantic_mutations`; `test_equivalent_roots_have_identical_semantic_state_digest` |
| REQ-017 | `test_denied_mutations_do_not_probe_invoke_or_change_state` |
| REQ-018 | `test_denied_retrieval_discloses_no_protected_value` |
| REQ-019 | `test_rename_requires_two_recorded_decisions`; `test_compound_authorization_exception_records_both_subdecisions` |
| REQ-020 | `test_nonempty_directory_delete_is_nonrecursive_tool_error`; `test_rename_directory_semantics_are_bounded`; successful operation matrix |
| REQ-021 | success, deny, validation, tool, partial-effect, and audit-failure category tests |
| REQ-022 | `test_authorization_exception_fails_closed_without_probe`; canonicalization/validation/state/audit failure tests |
| REQ-023 | `test_write_failure_classification_tracks_partial_effect_possibility`; `test_post_effect_lifecycle_failure_never_claims_nonexecution`; terminal audit failure test |
| REQ-024 | `test_development_audit_evidence_is_machine_reconstructable`; successful operation reconstruction matrix |
| REQ-025 | `test_write_payload_is_hashed_but_never_recorded_in_audit`; `test_governed_identifier_hides_invalid_path_payload` |
| REQ-026 | lexical, prefix, symlink, hard-link, rename, mapper, and direct-route tests |
| REQ-027 | `test_expected_fmed_l1_direct_route_bypass_is_demonstrated_only_in_temp_root` |
| REQ-028 | `test_task_and_session_provenance_remain_isolated` |
| REQ-029 | `test_semantically_equivalent_runs_are_deterministic`; `test_equivalent_roots_have_identical_semantic_state_digest` |
| REQ-030 | `NOT_APPLICABLE_PRE_CORPUS`: descriptive held-out measurement only; no implementation threshold exists |
| REQ-031 | pre-corpus source/status audit and documented `DEV-FS-*` contamination inventory |
| REQ-032 | development environment record and Linux hard-link/symlink/rename tests |

## Desired invariant test mapping

The invariant statuses in `SAFETY_INVARIANTS.md` remain `DESIRED`. Development tests do
not establish deployment or held-out properties.

| Invariant | Concrete development checks | Status |
|---|---|---|
| INV-016 | denied mutating operation matrix; pre-execution audit failure; rename denials | DESIRED; development-test mapped |
| INV-017 | denied read/list/stat sentinel and primitive-spy matrix | DESIRED; development-test mapped |
| INV-018 | lexical traversal/NFC/prefix cases; symlink/hard-link cases; two-endpoint rename | DESIRED; development-test mapped; TOCTOU not solved |
| INV-019 | authorization/canonicalization/validation/audit fault injection; partial write and terminal audit failure | DESIRED; development-test mapped |
