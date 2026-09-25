"""Freeze-contract tests for AUTH-COVERAGE-001 governance artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "AUTH-COVERAGE-001"


def load_json(relative: str) -> object:
    return json.loads((EXPERIMENT / relative).read_text(encoding="utf-8"))


def test_protocol_preregisters_scope_and_prohibits_current_run() -> None:
    protocol = load_json("protocol.json")
    assert isinstance(protocol, dict)
    assert protocol["protocol_id"] == "AUTH-COVERAGE-001-PROTOCOL@1"
    assert protocol["corpus_id"] == "AUTH-COVERAGE-001-CORPUS@1"
    assert protocol["status"] == "FROZEN_NOT_RUN"
    assert protocol["scope"] == ["FILESYSTEM_AUTHORIZATION", "PROCESS_AUTHORIZATION"]
    assert protocol["held_out_predictions_exposed"] is False
    assert protocol["held_out_execution_authorized"] is False
    assert protocol["aggregate_score_permitted"] is False
    assert protocol["minimum_authorized_fraction"] >= 0.5
    assert protocol["minimum_strong_pairs"] >= 500


def test_raw_first_one_shot_contract_is_fail_closed() -> None:
    policy = load_json("contracts/run_policy.json")
    assert isinstance(policy, dict)
    assert policy["current_state"] == "FROZEN_NOT_AUTHORIZED_TO_RUN"
    assert policy["raw_first"] is True
    assert policy["rerun_after_prediction_exposure"] is False
    prohibited = set(policy["runner_must_not_load"])
    assert {"labels", "families", "difficulty", "pair registry"} <= prohibited


def test_scoring_contract_has_independent_metrics_and_complete_explanation() -> None:
    scoring = load_json("contracts/scoring_contract.json")
    assert isinstance(scoring, dict)
    assert scoring["aggregate_score"] is None
    assert len(scoring["metrics"]) == 12
    assert set(scoring["explanation_fields"]) == {
        "subject_or_session",
        "task",
        "action",
        "resource",
        "capability",
        "rule",
        "authority_source",
        "component",
        "decision",
        "reason",
    }


def test_external_pack_cannot_claim_authoritative_labels() -> None:
    schema = load_json("contracts/external_pack.schema.json")
    assert isinstance(schema, dict)
    assert schema["$id"] == "EXTERNAL_PACK@1"
    assert schema["additionalProperties"] is False
    authorship = schema["properties"]["authorship"]
    assert authorship["properties"]["production_outputs_seen"]["const"] is False
    assert any("labels" in rule for rule in schema["prohibited_semantics"])


def test_prior_experiment_trees_equal_recorded_baseline() -> None:
    integrity = load_json("contracts/existing_experiment_integrity.json")
    assert isinstance(integrity, dict)
    for path, expected in integrity["git_tree_objects"].items():
        actual = subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True
        ).strip()
        assert actual == expected


def test_no_prediction_or_raw_result_artifact_exists() -> None:
    forbidden_tokens = {"predictions", "raw_results", "held_out_results", "scores"}
    present = {path.stem for path in EXPERIMENT.rglob("*") if path.is_file()}
    assert not forbidden_tokens & present


def test_checksum_manifest_covers_each_registered_file_once() -> None:
    manifest = EXPERIMENT / "CHECKSUMS.sha256"
    if not manifest.exists():
        return
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", maxsplit=1)
        assert relative not in entries
        entries[relative] = digest
    assert entries
    for relative, expected in entries.items():
        payload = (ROOT / relative).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected
