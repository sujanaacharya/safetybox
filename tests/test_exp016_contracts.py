"""Static freeze gates for EXP-016 pre-corpus contracts and native fixture."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from safetybox.experiments.exp016_reachability import (
    ExecutableState,
    ReachabilityError,
    Route,
    ScoreStatus,
    normalize_projection,
    require_executable_state,
    require_route,
    score_positive_denominator,
    stage_funnel_counts,
)

ROOT = Path(__file__).parents[1]
EXP = ROOT / "experiments" / "EXP-016"
CONTRACTS = EXP / "contracts"


def load(name: str) -> object:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_native_helper_matches_frozen_provenance() -> None:
    provenance = load("../fixture/build_provenance.json")
    assert isinstance(provenance, dict)
    source = ROOT / provenance["source_path"]
    binary = ROOT / provenance["binary_path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["source_sha256"]
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == provenance["binary_sha256"]
    observed = require_executable_state(binary, ExecutableState.VALID_NATIVE_EXECUTABLE)
    assert observed.link_count == 1
    assert observed.elf is not None and observed.elf.architecture_compatible
    assert provenance["elf"]["machine"] == observed.elf.machine
    assert provenance["elf"]["class_bits"] == observed.elf.elf_class
    assert provenance["required_loader"] == "/lib64/ld-linux-x86-64.so.2"


def test_independent_oracle_has_no_production_validator_or_adapter_import() -> None:
    source = (ROOT / "src" / "safetybox" / "experiments" / "exp016_reachability.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("safetybox.process") for name in imported_modules)


def test_no_held_out_corpus_or_prediction_artifact_exists() -> None:
    prohibited_names = {
        "scenarios.json",
        "scenarios.yaml",
        "labels.json",
        "labels.yaml",
        "predictions.json",
        "predictions.yaml",
    }
    assert not any(path.name in prohibited_names for path in EXP.rglob("*"))
    registry = load("family_registry.json")
    assert isinstance(registry, dict)
    assert registry["held_out_instance_count"] == 0
    assert registry["held_out_instances"] == []
    proofs = json.loads(
        (EXP / "proofs" / "development_proof_registry.json").read_text(encoding="utf-8")
    )
    assert proofs["held_out_scenarios_authored"] == 0
    assert proofs["future_predictions_exposed"] is False
    assert proofs["adapter_exposure_to_future_held_out_data"] is False


def test_family_registry_is_canonical_and_matrix_exact() -> None:
    registry = load("family_registry.json")
    matrix = load("validation_reachability_matrix.json")
    assert isinstance(registry, dict) and isinstance(matrix, dict)
    families = [item["id"] for item in registry["families"]]
    rows = [item["family"] for item in matrix["rows"]]
    assert len(families) == len(set(families))
    assert len(rows) == len(set(rows))
    assert rows == families
    assert {item["route"] for item in registry["families"]} == {
        "ADAPTER",
        "DIRECT_CONTROL",
    }


def test_requirement_and_threat_mappings_reference_registered_families() -> None:
    registry = load("family_registry.json")
    requirements = load("requirement_mapping.json")
    threats = load("threat_mapping.json")
    assert isinstance(registry, dict) and isinstance(requirements, dict)
    assert isinstance(threats, dict)
    families = {item["id"] for item in registry["families"]} | {"ALL_FAMILIES"}
    for requirement, mapped in requirements["tested_requirements"].items():
        number = int(requirement.removeprefix("REQ-"))
        assert 33 <= number <= 62
        assert set(mapped) <= families
    for mapped in threats["tested"].values():
        assert set(mapped) <= families
    assert threats["boundaries"]["network_activity_by_child"].startswith("EXPECTED_BOUNDARY")
    assert threats["boundaries"]["validation_to_exec_toctou"].startswith("EXPECTED_BOUNDARY")


def test_candidate_claims_remain_proposed_and_bounded() -> None:
    claims = load("candidate_claims.json")
    assert isinstance(claims, dict)
    assert claims["promotion_permitted_by_this_freeze"] is False
    assert claims["claims"]
    assert all(item["status"] == "PROPOSED" for item in claims["claims"])
    assert "production readiness" in claims["forbidden_claims"]


def test_zero_denominator_and_repeat_projection_rules_are_executable() -> None:
    assert score_positive_denominator(0, 0) is ScoreStatus.NOT_EXERCISED
    assert score_positive_denominator(2, 2) is ScoreStatus.PASS
    assert score_positive_denominator(1, 2) is ScoreStatus.FAIL
    raw = {
        "pid": 1234,
        "timestamp": "ephemeral",
        "stdout_sha256": "semantic-hash",
        "argv_frames": ["; rm -rf /"],
    }
    normalized = normalize_projection(
        raw, {"pid": "<PID>", "timestamp": "<TIMESTAMP>", "missing": "<NOPE>"}
    )
    assert normalized == {
        "pid": "<PID>",
        "timestamp": "<TIMESTAMP>",
        "stdout_sha256": "semantic-hash",
        "argv_frames": ["; rm -rf /"],
    }


def test_stage_funnel_and_route_checks_are_executable() -> None:
    stages = {
        "AUTHORIZED": True,
        "EXEC_VALIDATION_REACHED": True,
        "EXEC_VALIDATION_PASSED": True,
    }
    counts = stage_funnel_counts((stages, stages))
    assert counts["AUTHORIZED"] == 2
    assert counts["EXEC_VALIDATION_PASSED"] == 2
    assert counts["CWD_VALIDATION_REACHED"] == 0
    with pytest.raises(ReachabilityError, match="unreached prior stage"):
        stage_funnel_counts(({"AUTHORIZED": False, "EXEC_VALIDATION_REACHED": True},))
    require_route(Route.ADAPTER, adapter_used=True)
    require_route(Route.DIRECT_CONTROL, adapter_used=False)
    with pytest.raises(ReachabilityError, match="disagrees"):
        require_route(Route.DIRECT_CONTROL, adapter_used=True)


def test_scoring_contract_separates_labels_and_denominators() -> None:
    scoring = load("scoring_contract.json")
    assert isinstance(scoring, dict)
    assert scoring["held_out_scenario_count"] == 0
    assert scoring["label_isolation"]["raw_first"] is True
    assert scoring["label_isolation"]["runtime_input_may_contain_expected_outcome"] is False
    assert scoring["zero_denominator_rule"]["status_when_zero"] == "NOT_EXERCISED"
    assert scoring["overall_success"]["authorization_only_can_satisfy"] is False
    assert scoring["failure_seams"]["POST_SPAWN_AUDIT"]["representable"] is False
    assert scoring["failure_seams"]["POST_SPAWN_AUDIT"]["corpus_use"] == "PROHIBITED"
