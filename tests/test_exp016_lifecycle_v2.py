"""Development-only governance tests for EXP-016 Protocol@2."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from safetybox.experiments.exp016_lifecycle_v2 import (
    AuthorizationStatus,
    ChildCreationStatus,
    ChildOutcome,
    CorpusPopulation,
    EffectStatus,
    LifecycleModelError,
    LifecyclePath,
    PopulationStatus,
    PreauditStatus,
    ScoreStatus,
    SpawnStatus,
    TerminalAuditStatus,
    ValidationStatus,
    derive_lifecycle,
    score_positive_denominator,
    validate_family_membership,
    validate_lifecycle,
    validate_population,
    validate_repeat_metadata,
)
from safetybox.experiments.exp016_reachability import (
    ReachabilityError,
    stage_funnel_counts,
)

ROOT = Path(__file__).parents[1]
V1 = ROOT / "experiments" / "EXP-016"
V2 = V1 / "v2"
CONTRACTS = V2 / "contracts"

V1_HASHES = {
    "protocol.yaml": "dbc5ee5fe0422413f59a9805c3f191098bf7857184f473a4464000fef4ae5c7f",
    "contracts/family_registry.json": (
        "5c8b1150b66f6937e12dff025176c3508f31213e53c1442c5fef77a4913d4594"
    ),
    "contracts/scoring_contract.json": (
        "8821cb2a2bbc822d58b313aca974eb4fe29b2e7d7f77aac699001a53db2ba914"
    ),
    "contracts/reachability_gate.json": (
        "ae0126428c72b9562498e869472fad18ca848f902ebedd7270bcd31ef60dcd79"
    ),
    "contracts/validation_reachability_matrix.json": (
        "e002fd29adf6069c00fa8da01c5db024d29c7e784c0ba0bfb07af0d85cb7814d"
    ),
}


def load_contract(name: str) -> dict[str, Any]:
    value = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def adapter_success_raw() -> dict[str, Any]:
    return {
        "route": "ADAPTER",
        "adapter_used": True,
        "decision": "ALLOW",
        "exec_validation": "SUCCEEDED",
        "cwd_validation": "SUCCEEDED",
        "preaudit_attempted": True,
        "preaudit_committed": True,
        "spawn_attempted": True,
        "child_created": True,
        "child_completed": True,
        "capture_status": "COMPLETE",
        "child_outcome": "EXIT_0",
        "terminal_class": "PROCESS_EXIT_0",
        "terminal_audit_attempted": True,
        "terminal_audit_committed": True,
        "effect_status": "CONFIRMED",
        "failure_seam": "NONE",
    }


def direct_success_raw() -> dict[str, Any]:
    return {
        "route": "DIRECT_CONTROL",
        "adapter_used": False,
        "decision": None,
        "exec_validation": None,
        "cwd_validation": None,
        "preaudit_attempted": None,
        "preaudit_committed": None,
        "terminal_audit_attempted": None,
        "terminal_audit_committed": None,
        "direct_spawn_attempted": True,
        "child_created": True,
        "child_completed": True,
        "capture_status": "COMPLETE",
        "child_outcome": "EXIT_0",
        "terminal_class": "DIRECT_CONTROL_OBSERVED",
        "effect_status": "CONFIRMED",
        "failure_seam": "NONE",
    }


def test_historical_v1_contracts_remain_byte_immutable() -> None:
    for relative, expected in V1_HASHES.items():
        assert hashlib.sha256((V1 / relative).read_bytes()).hexdigest() == expected


def test_v2_model_is_downstream_and_imports_no_process_implementation() -> None:
    source = (
        ROOT / "src" / "safetybox" / "experiments" / "exp016_lifecycle_v2.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("safetybox.process") for name in modules)


def test_success_nonzero_signal_and_timeout_paths_derive() -> None:
    cases = (
        ("EXIT_0", "PROCESS_EXIT_0", LifecyclePath.ADAPTER_CHILD_EXIT_0),
        (
            "EXIT_NONZERO",
            "PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE",
            LifecyclePath.ADAPTER_CHILD_EXIT_NONZERO,
        ),
        (
            "SIGNAL",
            "PROCESS_SIGNALED_EFFECT_POSSIBLE",
            LifecyclePath.ADAPTER_CHILD_SIGNAL,
        ),
        (
            "TIMEOUT",
            "PROCESS_TIMEOUT_EFFECT_POSSIBLE",
            LifecyclePath.ADAPTER_CHILD_TIMEOUT,
        ),
    )
    for outcome, terminal, path in cases:
        raw = adapter_success_raw()
        raw.update(child_outcome=outcome, terminal_class=terminal)
        assert derive_lifecycle(raw).path is path


def test_exec_and_cwd_validation_rejection_paths_derive() -> None:
    exec_reject = adapter_success_raw()
    exec_reject.update(
        exec_validation="REJECTED",
        cwd_validation="NOT_ATTEMPTED",
        preaudit_attempted=False,
        preaudit_committed=False,
        spawn_attempted=False,
        child_created=False,
        child_completed=False,
        capture_status="NOT_REACHED",
        child_outcome="NOT_AVAILABLE",
        terminal_class="VALIDATION_REJECT_NOT_SPAWNED",
        terminal_audit_attempted=False,
        terminal_audit_committed=False,
        effect_status="NONE",
    )
    assert derive_lifecycle(exec_reject).path is LifecyclePath.ADAPTER_EXEC_VALIDATION_REJECT
    cwd_reject = dict(exec_reject)
    cwd_reject.update(exec_validation="SUCCEEDED", cwd_validation="REJECTED")
    assert derive_lifecycle(cwd_reject).path is LifecyclePath.ADAPTER_CWD_VALIDATION_REJECT


def test_preaudit_failure_is_attempted_failed_and_never_spawned() -> None:
    raw = adapter_success_raw()
    raw.update(
        preaudit_committed=False,
        spawn_attempted=False,
        child_created=False,
        child_completed=False,
        capture_status="NOT_REACHED",
        child_outcome="NOT_AVAILABLE",
        terminal_class="FAIL_CLOSED_NOT_SPAWNED",
        terminal_audit_attempted=False,
        terminal_audit_committed=False,
        effect_status="NONE",
        failure_seam="PRE_EXECUTION_AUDIT",
    )
    state = derive_lifecycle(raw)
    assert state.path is LifecyclePath.ADAPTER_PREAUDIT_FAILURE
    assert state.preaudit is PreauditStatus.ATTEMPTED_FAILED
    assert state.spawn is SpawnStatus.NOT_REACHED


def test_truthful_spawn_failure_is_valid_in_v2() -> None:
    raw = adapter_success_raw()
    raw.update(
        child_created=False,
        child_completed=False,
        capture_status="NOT_REACHED",
        child_outcome="NOT_AVAILABLE",
        terminal_class="SPAWN_ERROR_NOT_CREATED",
        effect_status="NONE",
        failure_seam="SPAWN_FAILURE_CONFIRMED_NO_CHILD",
    )
    state = derive_lifecycle(raw)
    assert state.path is LifecyclePath.ADAPTER_SPAWN_FAILURE_CONFIRMED_NO_CHILD
    assert state.spawn is SpawnStatus.ATTEMPTED_FAILED_CONFIRMED_NO_CHILD
    assert state.child_creation is ChildCreationStatus.NOT_CREATED
    assert state.terminal_audit is TerminalAuditStatus.COMMITTED


def test_v1_rejects_the_same_truthful_spawn_failure_v2_accepts() -> None:
    v1 = {
        "AUTHORIZED": True,
        "EXEC_VALIDATION_REACHED": True,
        "EXEC_VALIDATION_PASSED": True,
        "CWD_VALIDATION_REACHED": True,
        "CWD_VALIDATION_PASSED": True,
        "PREAUDIT_COMMITTED": True,
        "SPAWN_ATTEMPTED": True,
        "CHILD_CREATED": False,
        "CHILD_COMPLETED": False,
        "TERMINAL_AUDIT_COMPLETED": True,
    }
    with pytest.raises(ReachabilityError, match="TERMINAL_AUDIT_COMPLETED"):
        stage_funnel_counts((v1,))
    test_truthful_spawn_failure_is_valid_in_v2()


def test_spawn_indeterminate_preserves_uncertainty() -> None:
    raw = adapter_success_raw()
    raw.update(
        child_created=None,
        child_completed=None,
        capture_status="INDETERMINATE",
        child_outcome="INDETERMINATE",
        terminal_class="FAIL_INDETERMINATE_EXECUTION_POSSIBLE",
        effect_status="INDETERMINATE",
    )
    state = derive_lifecycle(raw)
    assert state.path is LifecyclePath.ADAPTER_SPAWN_INDETERMINATE
    assert state.child_creation is ChildCreationStatus.INDETERMINATE
    assert state.effect is EffectStatus.INDETERMINATE


def test_capture_and_terminal_audit_failures_remain_distinct() -> None:
    capture = adapter_success_raw()
    capture.update(
        capture_status="FAILED",
        terminal_class="FAIL_INDETERMINATE_EXECUTION_POSSIBLE",
        failure_seam="CAPTURE_FAILURE_AFTER_CHILD",
    )
    assert derive_lifecycle(capture).path is LifecyclePath.ADAPTER_CAPTURE_FAILURE
    audit = adapter_success_raw()
    audit.update(
        terminal_class="FAIL_INDETERMINATE_EXECUTION_POSSIBLE",
        terminal_audit_committed=False,
        failure_seam="POST_COMPLETION_AUDIT_SUCCESS",
    )
    state = derive_lifecycle(audit)
    assert state.path is LifecyclePath.ADAPTER_TERMINAL_AUDIT_FAILURE
    assert state.child_outcome is ChildOutcome.EXIT_0
    assert state.terminal_audit is TerminalAuditStatus.ATTEMPTED_FAILED


def test_denial_and_authorization_failure_do_not_become_terminal_audits() -> None:
    denied = adapter_success_raw()
    denied.update(
        decision="DENY",
        exec_validation="NOT_ATTEMPTED",
        cwd_validation="NOT_ATTEMPTED",
        preaudit_attempted=False,
        preaudit_committed=False,
        spawn_attempted=False,
        child_created=False,
        child_completed=False,
        capture_status="NOT_REACHED",
        child_outcome="NOT_AVAILABLE",
        terminal_class="POLICY_DENY_NOT_SPAWNED",
        terminal_audit_attempted=False,
        terminal_audit_committed=False,
        effect_status="NONE",
    )
    assert derive_lifecycle(denied).path is LifecyclePath.ADAPTER_DENY
    failed = dict(denied)
    failed.update(decision="FAILED", terminal_class="FAIL_CLOSED_NOT_SPAWNED")
    assert derive_lifecycle(failed).path is LifecyclePath.ADAPTER_AUTHORIZATION_FAILURE


def test_direct_control_success_has_explicit_not_applicable_adapter_state() -> None:
    state = derive_lifecycle(direct_success_raw())
    assert state.path is LifecyclePath.DIRECT_CONTROL_SUCCESS
    assert state.authorization is AuthorizationStatus.NOT_APPLICABLE
    assert state.exec_validation is ValidationStatus.NOT_APPLICABLE
    assert state.cwd_validation is ValidationStatus.NOT_APPLICABLE
    assert state.preaudit is PreauditStatus.NOT_APPLICABLE
    assert state.terminal_audit is TerminalAuditStatus.NOT_APPLICABLE
    assert not state.adapter_used


def test_direct_control_rejects_adapter_state_and_route_confusion() -> None:
    fabricated = direct_success_raw()
    fabricated["decision"] = "ALLOW"
    with pytest.raises(LifecycleModelError, match="fabricates adapter observations"):
        derive_lifecycle(fabricated)
    confused = direct_success_raw()
    confused["adapter_used"] = True
    with pytest.raises(LifecycleModelError, match="adapter_used=false"):
        derive_lifecycle(confused)


def test_invalid_partial_order_states_are_rejected() -> None:
    success = derive_lifecycle(adapter_success_raw())
    with pytest.raises(LifecycleModelError, match="child creation requires successful spawn"):
        validate_lifecycle(replace(success, spawn=SpawnStatus.NOT_REACHED))
    with pytest.raises(LifecycleModelError, match="child completion requires child creation"):
        validate_lifecycle(
            replace(success, child_creation=ChildCreationStatus.NOT_CREATED)
        )
    with pytest.raises(LifecycleModelError, match="lacks required successful prerequisites"):
        validate_lifecycle(replace(success, cwd_validation=ValidationStatus.REJECT))


def test_zero_denominator_is_not_exercised_and_invalid_counts_fail() -> None:
    assert score_positive_denominator(0, 0) is ScoreStatus.NOT_EXERCISED
    assert score_positive_denominator(3, 3) is ScoreStatus.PASS
    assert score_positive_denominator(2, 3) is ScoreStatus.FAIL
    with pytest.raises(LifecycleModelError, match="0 <= passed <= denominator"):
        score_positive_denominator(0, -1)
    with pytest.raises(LifecycleModelError, match="0 <= passed <= denominator"):
        score_positive_denominator(2, 1)


def test_planned_population_does_not_claim_a_frozen_empty_corpus() -> None:
    validate_population(CorpusPopulation(PopulationStatus.PLANNED, 120, (), None))
    with pytest.raises(LifecycleModelError, match="PLANNED"):
        validate_population(CorpusPopulation(PopulationStatus.PLANNED, 120, (), 0))
    with pytest.raises(LifecycleModelError, match="positive exact matching count"):
        validate_population(CorpusPopulation(PopulationStatus.FROZEN, 120, (), 0))


def test_disposable_positive_population_does_not_mutate_definitions() -> None:
    registry = load_contract("family_definitions.json")
    families = {item["family_id"]: item for item in registry["families"]}
    before = json.dumps(families, sort_keys=True)
    memberships = [
        {
            "scenario_id": "DEV-SYNTH-A",
            "primary_family": "SUCCESS_BASIC",
            "secondary_tags": [],
            "route": "ADAPTER",
            "repeat_group_id": "DEV-GROUP",
        },
        {
            "scenario_id": "DEV-SYNTH-B",
            "primary_family": "DIRECT_CONTROL",
            "secondary_tags": ["route_boundary"],
            "route": "DIRECT_CONTROL",
            "repeat_group_id": "DEV-GROUP",
        },
    ]
    counts = validate_family_membership(families, memberships)
    validate_repeat_metadata(memberships)
    validate_population(
        CorpusPopulation(
            PopulationStatus.MATERIALIZED,
            None,
            ("DEV-SYNTH-A", "DEV-SYNTH-B"),
            None,
        )
    )
    assert counts["SUCCESS_BASIC"] == 1
    assert counts["DIRECT_CONTROL"] == 1
    assert json.dumps(families, sort_keys=True) == before


def test_membership_route_and_repeat_errors_are_rejected() -> None:
    registry = load_contract("family_definitions.json")
    families = {item["family_id"]: item for item in registry["families"]}
    bad_route = [
        {
            "scenario_id": "DEV-SYNTH-C",
            "primary_family": "DIRECT_CONTROL",
            "secondary_tags": [],
            "route": "ADAPTER",
        }
    ]
    with pytest.raises(LifecycleModelError, match="route mismatch"):
        validate_family_membership(families, bad_route)
    with pytest.raises(LifecycleModelError, match="fewer than two"):
        validate_repeat_metadata(
            ({"scenario_id": "DEV-SYNTH-D", "repeat_group_id": "DEV-ONE"},)
        )


def test_family_definitions_are_complete_and_membership_free() -> None:
    registry = load_contract("family_definitions.json")
    families = registry["families"]
    assert registry["registry_id"] == "EXP-016-FAMILY-REGISTRY@2"
    assert registry["contains_scenario_membership"] is False
    assert len(families) == 20
    assert len({item["family_id"] for item in families}) == 20
    registered_paths = set(load_contract("lifecycle_model.json")["registered_paths"])
    for family in families:
        assert family["lifecycle_shape"] in registered_paths
        assert family["route"] in {"ADAPTER", "DIRECT_CONTROL"}
        assert family["minimum_future_count"] > 0
        assert family["requirements"]
        assert isinstance(family["threats"], list)
        assert "scenario_id" not in family


def test_requirement_threat_and_route_joins_are_definition_level() -> None:
    requirements = load_contract("requirement_mapping.json")
    threats = load_contract("threat_mapping.json")
    routes = load_contract("route_contract.json")
    assert requirements["current_empirical_instance_count"] == 0
    assert set(requirements["not_empirically_claimed"]) == {"REQ-035", "REQ-047", "REQ-061"}
    assert threats["current_empirical_instance_count"] == 0
    assert all(
        value == "EXPECTED_BOUNDARY_NOT_EVALUATED"
        for value in threats["boundaries"].values()
    )
    assert routes["routes"]["DIRECT_CONTROL"]["adapter_used"] is False
    assert routes["metric_applicability"]["adapter_audit_ordering_rate"] == ["ADAPTER"]
    assert routes["metric_applicability"]["direct_control_boundary_rate"] == [
        "DIRECT_CONTROL"
    ]


def test_family_requirement_and_threat_joins_preserve_v1_mapping_intent() -> None:
    registry = load_contract("family_definitions.json")
    families = {item["family_id"]: item for item in registry["families"]}
    v1_requirements = json.loads(
        (V1 / "contracts" / "requirement_mapping.json").read_text(encoding="utf-8")
    )
    for requirement, mapped_families in v1_requirements["tested_requirements"].items():
        if mapped_families == ["ALL_FAMILIES"]:
            assert all(requirement in family["requirements"] for family in families.values())
        else:
            assert all(
                requirement in families[family_id]["requirements"]
                for family_id in mapped_families
            )
    v1_threats = json.loads(
        (V1 / "contracts" / "threat_mapping.json").read_text(encoding="utf-8")
    )
    for threat, mapped_families in v1_threats["tested"].items():
        assert all(threat in families[family_id]["threats"] for family_id in mapped_families)


def test_contract_paths_metrics_and_repeat_projection_match_implementations() -> None:
    lifecycle = load_contract("lifecycle_model.json")
    scoring = load_contract("scoring_contract.json")
    routes = load_contract("route_contract.json")
    assert set(lifecycle["registered_paths"]) == {path.value for path in LifecyclePath}
    for metric in scoring["metric_registry"]:
        assert routes["metric_applicability"][metric["metric_id"]] == metric["routes"]
    v1_scoring = json.loads(
        (V1 / "contracts" / "scoring_contract.json").read_text(encoding="utf-8")
    )
    assert set(scoring["repeat_normalization"]["normalized_ephemeral_fields"]) == set(
        v1_scoring["repeat_normalization"]["normalized_ephemeral_fields"]
    )
    assert set(scoring["repeat_normalization"]["semantic_fields_never_normalized"]) == set(
        v1_scoring["repeat_normalization"]["semantic_fields_never_normalized"]
    )


def test_scoring_contract_is_schema_not_premature_population() -> None:
    scoring = load_contract("scoring_contract.json")
    metrics = scoring["metric_registry"]
    assert scoring["contract_id"] == "EXP-016-SCORING-CONTRACT@2"
    assert scoring["frozen_corpus_count"] is None
    assert scoring["scenario_membership"] == "NOT_YET_FROZEN"
    assert scoring["zero_denominator_rule"]["denominator_equal_zero"] == "NOT_EXERCISED"
    assert scoring["zero_denominator_rule"]["not_applicable_member"] == "EXCLUDED_NOT_PASS"
    assert scoring["overall_success"]["empty_corpus_can_satisfy"] is False
    assert len(metrics) == len({metric["metric_id"] for metric in metrics})
    assert all(metric["positive_denominator_required"] for metric in metrics)


def test_design_target_and_future_freeze_states_are_distinct() -> None:
    design = load_contract("corpus_design_target.json")
    population = load_contract("population_model.json")
    future = load_contract("future_corpus_freeze.json")
    assert design["status"] == "PLANNED"
    assert design["planned_total"] == 120
    assert design["materialized_count"] == 0
    assert design["frozen_corpus_count"] is None
    assert design["exact_family_counts"] == "NOT_YET_FROZEN"
    assert population["current_state"] == "PLANNED"
    assert population["frozen_corpus_count"] is None
    assert future["current_status"] == "NOT_YET_FROZEN"


def test_raw_record_model_keeps_labels_out_and_routes_explicit() -> None:
    raw = load_contract("raw_record_model.json")
    prohibited = set(raw["prohibited_runtime_fields"])
    assert {"expected_lifecycle", "prediction", "requirement_ids", "threat_ids"} <= prohibited
    assert "adapter_used" in raw["common_required_fields"]
    assert "process_audit_envelope" in raw["adapter_required_fields"]
    assert "process_audit_envelope" in raw["direct_control_fields_required_null"]


def test_no_held_out_corpus_prediction_or_results_were_created() -> None:
    protocol = (V2 / "protocol.yaml").read_text(encoding="utf-8")
    proofs = json.loads(
        (V2 / "proofs" / "development_proof_registry.json").read_text(encoding="utf-8")
    )
    assert "held_out_scenarios_authored: 0" in protocol
    assert "predictions_exposed: false" in protocol
    assert proofs["held_out_scenarios_authored"] == 0
    assert proofs["future_predictions_exposed"] is False
    assert proofs["adapter_exposure_to_future_held_out_data"] is False
    assert not (ROOT / "results" / "EXP-016").exists()
    assert not any(path.is_file() for path in (V1 / "corpus").glob("**/*"))


def test_v2_governance_checksum_manifest() -> None:
    manifest = V2 / "SHA256SUMS"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
