# AUTH-COVERAGE-002 Protocol@1 file disposition

**Disposition identity:** `AUTH-COVERAGE-002-PROTOCOL1-FILE-DISPOSITION@1`
**Candidate:** `AUTH-COVERAGE-002-CORPUS@1-CANDIDATE`
**Status:** `BLOCKED_PROTOCOL_AND_EXPLANATION_VALIDITY`

This is the complete inventory of the 64 files that were untracked at the governance
reset. Committing a file here preserves development or negative evidence; it does not
freeze a corpus, convert it into held-out result evidence, or authorize execution.

## HISTORICAL_BLOCKED_EVIDENCE (32)

- `docs/engineering/AUTH-COVERAGE-002_ADVERSARIAL_REVIEW.md`
- `docs/engineering/AUTH-COVERAGE-002_BLOCKED_AUDIT.md`
- `docs/engineering/AUTH-COVERAGE-002_FREEZE_REPORT.md`
- `docs/engineering/AUTH-COVERAGE-002_ORACLE_INDEPENDENCE.md`
- `docs/engineering/AUTH-COVERAGE-002_PRE_RUN_VALIDITY_AUDIT.md`
- `experiments/AUTH-COVERAGE-002/FINAL_CANDIDATE_SOURCE_SHA256SUMS`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/adversarial_leakage.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/analysis.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/audit_report.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/cross_tool_groups.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/cross_tool_groups.unreviewed.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/difficulty.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/fresh_process_isolation.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/invalid_structure_controls.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/labels.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/pairs.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/scorer_compatibility.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/split_assignment.json`
- `experiments/AUTH-COVERAGE-002/corpus/analysis/zero_exposure_audit.json`
- `experiments/AUTH-COVERAGE-002/corpus/construction_receipt.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/DEV/corpus_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/DEV/package_manifest.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/DEV/runtime_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/DEV/scenarios.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/HELD_OUT-runtime/corpus_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/HELD_OUT-runtime/package_manifest.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/HELD_OUT-runtime/runtime_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/HELD_OUT-runtime/scenarios.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/VALIDATION/corpus_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/VALIDATION/package_manifest.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/VALIDATION/runtime_binding.json`
- `experiments/AUTH-COVERAGE-002/corpus/runtime/VALIDATION/scenarios.json`

The historical runtime packages are preserved solely to make the failed authorship
history auditable. In particular, the directory named `HELD_OUT-runtime` is a rejected
authoring artifact: it was never frozen and never sent to production.

## REUSABLE_DEV_INFRASTRUCTURE (31)

- `experiments/AUTH-COVERAGE-002/adversarial_leakage.py`
- `experiments/AUTH-COVERAGE-002/audit_corpus.py`
- `experiments/AUTH-COVERAGE-002/audit_fresh_process_isolation.py`
- `experiments/AUTH-COVERAGE-002/audit_zero_exposure.py`
- `experiments/AUTH-COVERAGE-002/bind_runtime.py`
- `experiments/AUTH-COVERAGE-002/build_corpus.py`
- `experiments/AUTH-COVERAGE-002/build_invalid_controls.py`
- `experiments/AUTH-COVERAGE-002/contracts/claims.json`
- `experiments/AUTH-COVERAGE-002/contracts/error_pressure_mapping.json`
- `experiments/AUTH-COVERAGE-002/contracts/explanation_contract.json`
- `experiments/AUTH-COVERAGE-002/contracts/external_pack.schema.json`
- `experiments/AUTH-COVERAGE-002/contracts/leakage_gate.json`
- `experiments/AUTH-COVERAGE-002/contracts/mutation_and_metamorphic.json`
- `experiments/AUTH-COVERAGE-002/contracts/owasp_precursors.json`
- `experiments/AUTH-COVERAGE-002/contracts/statistical_analysis.json`
- `experiments/AUTH-COVERAGE-002/explanation_scoring.py`
- `experiments/AUTH-COVERAGE-002/final_candidate_policy.json`
- `experiments/AUTH-COVERAGE-002/formal/exhaustive_results.json`
- `experiments/AUTH-COVERAGE-002/formal/exhaustive_verify.py`
- `experiments/AUTH-COVERAGE-002/freeze_manifests.py`
- `experiments/AUTH-COVERAGE-002/oracle_a.py`
- `experiments/AUTH-COVERAGE-002/oracle_b.py`
- `experiments/AUTH-COVERAGE-002/schema.py`
- `experiments/AUTH-COVERAGE-002/statistical_reporting.py`
- `experiments/AUTH-COVERAGE-002/validate_explanation_compatibility.py`
- `experiments/AUTH-COVERAGE-002/validate_scorer_compatibility.py`
- `tests/dev/test_auth_coverage_002_corpus.py`
- `tests/dev/test_auth_coverage_002_explanations.py`
- `tests/dev/test_auth_coverage_002_high_risk_branches.py`
- `tests/dev/test_auth_coverage_002_oracles.py`
- `tests/dev/test_auth_coverage_002_statistics.py`

Reuse means review and modification under the new identities; it never means that an @1
observation may be represented as a new VALIDATION or HELD_OUT observation.

## MUST_NOT_REUSE (1)

- `experiments/AUTH-COVERAGE-002/corpus/analysis/pairs.unreviewed.json`

This incomplete self-declared pair registry is retained as negative evidence but may not
serve as canonical pair-quality evidence in any successor attempt.

## DISCARDABLE_TEMPORARY (0 of the 64)

None of the 64 scientific files was silently deleted. Generated `__pycache__/*.pyc`
files were outside the 64-file Git inventory, are ignored build products, and are the
only disposable artifacts removed during clean-state restoration.
