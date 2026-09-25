"""Construction-audit tests; no held-out authorization decision is executed."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

AUDIT_ROOT = Path("experiments/AUTH-COVERAGE-001/audit")


def _module(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, AUDIT_ROOT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_core = _module("auth_coverage_audit_core", "audit_core.py")
sys.modules["audit_core"] = audit_core


def _scenario(identifier: str, request_task: str, *, suspicious: bool = False) -> dict[str, Any]:
    return {
        "schema_id": "AUTH-COVERAGE-001-SCENARIO@1",
        "scenario_id": identifier,
        "split": "DEV",
        "request": {
            "subject_id": "subject-x",
            "session_id": "session-x",
            "task_id": request_task,
            "contract_id": "contract-x",
            "tool": "FILESYSTEM",
            "components": [
                {"component": "filesystem", "action": "filesystem.read", "resource": "/a/x"}
            ],
            "operation_data": {"argv": ["secret"] if suspicious else [], "context": {}},
        },
        "contract": {
            "contract_id": "contract-x",
            "task_id": "task-a",
            "capabilities": [
                {
                    "capability_id": "cap-x",
                    "action": "filesystem.read",
                    "resource": "/a/x",
                    "scope_type": "EXACT",
                },
                {
                    "capability_id": "cap-distractor",
                    "action": "filesystem.write",
                    "resource": "/a/y",
                    "scope_type": "EXACT",
                },
            ],
        },
    }


def _difficulty(identifier: str, distance: int, score: int, classification: str) -> dict[str, Any]:
    return {
        "scenario_id": identifier,
        "authority_distance": distance,
        "matching_component_count": 1 if distance == 0 else 0,
        "mismatching_component_count": 0 if distance == 0 else 1,
        "exact_resource_match_count": 1,
        "near_resource_match_count": 0,
        "partial_capability_match_count": 0,
        "irrelevant_capability_count": 2,
        "capability_count": 2,
        "compound_component_count": 1,
        "suspicious_literal_count": 0,
        "structural_score": score,
        "class": classification,
    }


def _fixtures() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    scenarios = [_scenario("s001", "task-a"), _scenario("s002", "task-b")]
    labels = [
        {
            "scenario_id": "s001",
            "decision": "ALLOW",
            "component_decisions": {"filesystem": "ALLOW"},
            "families": ["HARD_BENIGN", "TASK_BINDING", "CAPABILITY_DISTRACTORS"],
            "difficulty": "EASY_CONTROL",
            "authority_distance": 0,
        },
        {
            "scenario_id": "s002",
            "decision": "DENY",
            "component_decisions": {"filesystem": "DENY"},
            "families": ["TASK_BINDING", "CROSS_TASK_REUSE"],
            "difficulty": "EASY_CONTROL",
            "authority_distance": 1,
        },
    ]
    pairs = [
        {
            "pair_id": "p001",
            "scenario_a": "s001",
            "scenario_b": "s002",
            "changed_dimension": "TASK_BINDING",
            "strength": "STRONG",
            "differing_paths": ["/request/task_id"],
        }
    ]
    difficulty = [
        _difficulty("s001", 0, 2, "EASY_CONTROL"),
        _difficulty("s002", 1, 4, "EASY_CONTROL"),
    ]
    return scenarios, labels, pairs, difficulty


def _write(path: Path, key: str, values: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({key: values}), encoding="utf-8")


def _explanation(decision: str) -> dict[str, str]:
    return {
        "subject_or_session": "session-x",
        "task": "task-a",
        "action": "filesystem.read",
        "resource": "/a/x",
        "capability": "cap-x",
        "rule": "exact",
        "authority_source": "contract-x",
        "component": "filesystem",
        "decision": decision,
        "reason": "deterministic test",
    }


def test_pair_strength_is_recomputed_from_actual_leaf_differences() -> None:
    scenarios, _, pairs, _ = _fixtures()
    report = audit_core.audit_pairs(scenarios, pairs)
    assert report["exact_registry_agreement"] is True
    pairs[0]["differing_paths"] = ["/contract/task_id"]
    report = audit_core.audit_pairs(scenarios, pairs)
    assert report["exact_registry_agreement"] is False
    assert report["strength_disagreements"][0]["derived"] == "MODERATE"


def test_baselines_and_leakage_are_label_symmetric() -> None:
    scenarios, labels, _, _ = _fixtures()
    baselines = audit_core.baseline_attacks(scenarios, labels)
    assert baselines["always_allow"]["false_allow_rate"] == 1.0
    assert baselines["always_allow"]["false_deny_rate"] == 0.0
    assert baselines["always_deny"]["false_allow_rate"] == 0.0
    assert baselines["always_deny"]["false_deny_rate"] == 1.0
    assert baselines["task_id_equality_only"]["accuracy"] == 1.0
    leakage = audit_core.audit_leakage(scenarios, labels)
    assert leakage["runtime_outcome_word_id_count"] == 0
    assert leakage["label_fields_absent_from_runtime"] is True


def test_metrics_remain_separate_and_explanations_are_mechanical() -> None:
    _, labels, pairs, _ = _fixtures()
    predictions = [
        {
            "scenario_id": label["scenario_id"],
            "decision": label["decision"],
            "component_decisions": label["component_decisions"],
            "explanations": [_explanation(label["decision"])],
        }
        for label in labels
    ]
    metrics = audit_core.score_predictions(predictions, labels, pairs)
    assert "aggregate_score" not in metrics
    assert metrics["false_allow_rate"]["errors"] == 0
    assert metrics["false_allow_rate"]["denominator"] == 1
    assert metrics["false_allow_rate"]["value"] == 0.0
    assert metrics["false_allow_rate"]["zero_error_upper_bound_95"] == pytest.approx(0.95)
    assert metrics["false_deny_rate"]["errors"] == 0
    assert metrics["false_deny_rate"]["zero_error_upper_bound_95"] == pytest.approx(0.95)
    assert metrics["pair_accuracy"]["value"] == 1.0
    assert metrics["pair_accuracy"]["wilson_95"] is not None
    assert metrics["authority_explanation_completeness"]["completeness"] == 1.0
    assert audit_core.zero_error_upper_bound(100) == pytest.approx(0.029513, abs=1e-6)
    assert audit_core.wilson_interval(50, 100) == pytest.approx(
        [0.4038315, 0.5961685], abs=1e-6
    )


def test_full_construction_audit_reads_separate_artifacts(tmp_path: Path) -> None:
    scenarios, labels, pairs, difficulty = _fixtures()
    _write(tmp_path / "scenarios.json", "scenarios", scenarios)
    _write(tmp_path / "labels.json", "labels", labels)
    _write(tmp_path / "pairs.json", "pairs", pairs)
    _write(tmp_path / "difficulty.json", "difficulty", difficulty)
    _write(tmp_path / "cross_tool_pairs.json", "pairs", [])
    report = audit_core.audit_corpus(tmp_path)
    assert report["prediction_execution"] == "NOT_PERFORMED"
    assert report["scenario_count"] == 2
    assert report["freeze_gate_pass"] is True


def test_raw_first_capture_is_one_shot_and_scoring_is_separate(tmp_path: Path) -> None:
    capture = _module("auth_coverage_capture_raw", "capture_raw.py")
    scorer = _module("auth_coverage_score_sealed", "score_sealed.py")
    scenarios, labels, pairs, _ = _fixtures()
    scenario_path = tmp_path / "scenarios.json"
    incoming_path = tmp_path / "incoming.json"
    labels_path = tmp_path / "labels.json"
    pairs_path = tmp_path / "pairs.json"
    output_dir = tmp_path / "sealed"
    _write(scenario_path, "scenarios", scenarios)
    _write(labels_path, "labels", labels)
    _write(pairs_path, "pairs", pairs)
    predictions = [
        {
            "scenario_id": label["scenario_id"],
            "decision": label["decision"],
            "component_decisions": label["component_decisions"],
            "explanations": [_explanation(label["decision"])],
        }
        for label in labels
    ]
    _write(incoming_path, "predictions", predictions)
    receipt = capture.capture_raw(scenario_path, incoming_path, output_dir)
    assert json.loads(receipt.read_text())["labels_loaded_before_persistence"] is False
    assert os.stat(output_dir / "raw_decisions.json").st_mode & 0o222 == 0
    with pytest.raises(capture.CaptureFailure, match="rerun prohibited"):
        capture.capture_raw(scenario_path, incoming_path, output_dir)
    scores_path = tmp_path / "scores.json"
    scorer.score_sealed(receipt, labels_path, pairs_path, scores_path)
    assert json.loads(scores_path.read_text())["metrics"]["pair_accuracy"]["value"] == 1.0
    with pytest.raises(audit_core.AuditFailure, match="already exists"):
        scorer.score_sealed(receipt, labels_path, pairs_path, scores_path)


def test_capture_import_isolated_in_fresh_process() -> None:
    capture_path = (AUDIT_ROOT / "capture_raw.py").resolve()
    script = """
import importlib.util
import json
import sys
before = set(sys.modules)
spec = importlib.util.spec_from_file_location("auth_capture_isolated", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
loaded = set(sys.modules) - before
forbidden = sorted(
    name for name in loaded
    if name.startswith("safetybox") or "audit_core" in name or "score_sealed" in name
)
print(json.dumps(forbidden))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(capture_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == []
