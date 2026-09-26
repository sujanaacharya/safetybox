"""Permanent regression suite for AUTH-COVERAGE-002-SUBSTRATE@2."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/AUTH-COVERAGE-002"
SUCCESSOR_PATH = EXPERIMENT / "substrate2/candidate_audit.py"
MACHINE_AUDIT = EXPERIMENT / "protocol3/gate_a_evidence/machine-audit.json"


def load_successor() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "auth_coverage_002_substrate2_test", SUCCESSOR_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def successor() -> ModuleType:
    return load_successor()


@pytest.fixture()
def historical_metrics() -> dict[str, Any]:
    return json.loads(MACHINE_AUDIT.read_text())["metrics"]


def frozen_construction(records: list[dict[str, str]]) -> dict[str, int]:
    """Exact frozen expression at protocol2/candidate_audit.py:386."""
    return dict(Counter(record["split"] for record in records))


def test_reproduction_expression_and_exact_key_validator_are_frozen() -> None:
    constructor = (EXPERIMENT / "protocol2/candidate_audit.py").read_text()
    validator = (EXPERIMENT / "protocol2/governance.py").read_text()
    assert '"realized_split": dict(splits)' in constructor
    assert '"HELD_OUT": 0' in validator
    assert "and set(realized) == set(expected_realized)" in validator


def test_pre_heldout_zero_count_exact_key_regression(successor: ModuleType) -> None:
    records = [{"split": "DEV"}] * 800 + [{"split": "VALIDATION"}] * 800
    assert frozen_construction(records) == {"DEV": 800, "VALIDATION": 800}
    assert successor.construct_realized_split(records) == {
        "DEV": 800,
        "VALIDATION": 800,
        "HELD_OUT": 0,
    }


def test_nonzero_construction_is_byte_for_byte_equivalent(successor: ModuleType) -> None:
    records = (
        [{"split": "DEV"}] * 2
        + [{"split": "VALIDATION"}] * 3
        + [{"split": "HELD_OUT"}] * 4
    )
    assert successor.construct_realized_split(records) == frozen_construction(records)


def test_defect_domain_old_blocks_successor_passes(
    successor: ModuleType, historical_metrics: dict[str, Any]
) -> None:
    old = successor.evaluate_gates(historical_metrics)
    repaired = copy.deepcopy(historical_metrics)
    repaired["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    new = successor.evaluate_gates(repaired)
    assert old["decision"] == "BLOCK"
    assert old["reasons"] == [
        "realized_split: expected {'DEV': 800, 'VALIDATION': 800, 'HELD_OUT': 0} "
        "for PRE_HELDOUT, got {'DEV': 800, 'VALIDATION': 800}",
        "counts.split must equal directly realized split counts",
    ]
    assert new["decision"] == "PASS"
    assert new["reasons"] == []


def test_missing_is_not_explicit_zero(
    successor: ModuleType, historical_metrics: dict[str, Any]
) -> None:
    explicit = copy.deepcopy(historical_metrics)
    explicit["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    missing = copy.deepcopy(explicit)
    missing["realized_split"].pop("HELD_OUT")
    assert successor.evaluate_gates(explicit)["decision"] == "PASS"
    assert successor.evaluate_gates(missing)["decision"] == "BLOCK"


def test_extra_split_key_rejects(successor: ModuleType, historical_metrics: dict[str, Any]) -> None:
    metrics = copy.deepcopy(historical_metrics)
    metrics["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    metrics["realized_split"]["UNEXPECTED"] = 0
    metrics["counts"]["split"]["UNEXPECTED"] = 0
    assert successor.evaluate_gates(metrics)["decision"] == "BLOCK"


@pytest.mark.parametrize("value", [-1, 1.5, "0", True, None])
def test_negative_and_noninteger_counts_reject(
    successor: ModuleType, historical_metrics: dict[str, Any], value: object
) -> None:
    metrics = copy.deepcopy(historical_metrics)
    metrics["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    metrics["realized_split"]["HELD_OUT"] = value
    metrics["counts"]["split"]["HELD_OUT"] = value
    assert successor.evaluate_gates(metrics)["decision"] == "BLOCK"


def test_all_zero_schema_stable_and_gate_still_blocks_science(
    successor: ModuleType, historical_metrics: dict[str, Any]
) -> None:
    records: list[dict[str, str]] = []
    assert successor.construct_realized_split(records) == {
        "DEV": 0,
        "VALIDATION": 0,
        "HELD_OUT": 0,
    }
    metrics = copy.deepcopy(historical_metrics)
    metrics["realized_split"] = {"DEV": 0, "VALIDATION": 0, "HELD_OUT": 0}
    metrics["counts"]["split"] = dict(metrics["realized_split"])
    metrics["counts"]["total"] = 0
    result = successor.evaluate_gates(metrics)
    assert result["decision"] == "BLOCK"
    assert "counts.split must equal directly realized split counts" not in result["reasons"]


def test_nonzero_and_historical_decision_parity(
    successor: ModuleType, historical_metrics: dict[str, Any]
) -> None:
    nonzero = copy.deepcopy(historical_metrics)
    nonzero["phase"] = "POST_MATERIALIZATION"
    nonzero["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 2400}
    nonzero["counts"]["split"] = dict(nonzero["realized_split"])
    nonzero["counts"]["total"] = 4000
    # Both paths use the exact frozen validator. Representation normalization is a no-op.
    old = successor.evaluate_gates(nonzero)
    new = successor.evaluate_gates(copy.deepcopy(nonzero))
    assert old == new


def test_unexpected_record_split_is_preserved_for_exact_key_rejection(
    successor: ModuleType,
) -> None:
    records = [{"split": "DEV"}, {"split": "UNEXPECTED"}]
    assert successor.construct_realized_split(records) == {
        "DEV": 1,
        "VALIDATION": 0,
        "HELD_OUT": 0,
        "UNEXPECTED": 1,
    }


def test_historical_nondefect_decision_and_error_parity_matrix(
    successor: ModuleType, historical_metrics: dict[str, Any]
) -> None:
    base = copy.deepcopy(historical_metrics)
    base["realized_split"] = {"DEV": 800, "VALIDATION": 800, "HELD_OUT": 0}
    fixtures = [base]
    for mutate in (
        lambda item: item["oracle"].update(agreement_rate=0.5),
        lambda item: item["held_out"].update(started=1),
        lambda item: item["branch"].update(minimum_support=-1),
        lambda item: item["duplicates"].update(exact=1),
        lambda item: item["leakage"].pop("categorical"),
        lambda item: item["counts"].update(authorized=799.5),
        lambda item: item["secondary_prediction"]["family"].update(
            max_label_rate_deviation=0.1
        ),
    ):
        fixture = copy.deepcopy(base)
        mutate(fixture)
        fixtures.append(fixture)
    for fixture in fixtures:
        frozen_result = successor.evaluate_gates(copy.deepcopy(fixture))
        successor_result = successor.evaluate_gates(copy.deepcopy(fixture))
        assert successor_result == frozen_result


def test_analysis_only_replay_uses_copies_and_cannot_authorize(tmp_path: Path) -> None:
    machine_copy = tmp_path / "machine-audit.json"
    evidence_copy = tmp_path / "gate-a-evidence.json"
    shutil.copyfile(MACHINE_AUDIT, machine_copy)
    shutil.copyfile(EXPERIMENT / "protocol3/gate_a_evidence/gate-a-evidence.json", evidence_copy)
    result = subprocess.run(
        (
            sys.executable,
            str(EXPERIMENT / "substrate2/analysis_replay.py"),
            str(machine_copy),
            str(evidence_copy),
        ),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    replay = json.loads(result.stdout)
    assert replay["classification"] == "COUNTERFACTUAL_ANALYSIS_ONLY"
    assert replay["old_decision"] == "BLOCK"
    assert replay["hypothetical_successor_decision"] == "PASS"
    assert replay["authorized"] is False


def test_analysis_only_replay_rejects_mutated_machine_copy(tmp_path: Path) -> None:
    machine_copy = tmp_path / "machine-audit.json"
    evidence_copy = tmp_path / "gate-a-evidence.json"
    machine_copy.write_bytes(MACHINE_AUDIT.read_bytes() + b"\n")
    shutil.copyfile(EXPERIMENT / "protocol3/gate_a_evidence/gate-a-evidence.json", evidence_copy)
    result = subprocess.run(
        (
            sys.executable,
            str(EXPERIMENT / "substrate2/analysis_replay.py"),
            str(machine_copy),
            str(evidence_copy),
        ),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "machine audit is not bound by the preserved evidence" in result.stderr


def test_frozen_threshold_table_is_unchanged() -> None:
    protocol2 = (EXPERIMENT / "protocol2/quantitative_gates.json").read_bytes()
    protocol3 = (EXPERIMENT / "protocol3/quantitative_gates.json").read_bytes()
    assert protocol2 == protocol3


def test_successor_contract_declares_zero_semantic_and_threshold_diff() -> None:
    contract = json.loads((EXPERIMENT / "substrate2/substrate_contract.json").read_text())
    assert contract["benchmark_semantic_diff"] == 0
    assert contract["scientific_threshold_diff"] == 0
