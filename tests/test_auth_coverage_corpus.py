"""Construction proofs for the frozen AUTH-COVERAGE-001 corpus."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from safetybox.capabilities import Capability, CapabilityEvaluator
from safetybox.contracts import TaskContract
from safetybox.models import ActionRequest

ROOT = Path(__file__).parents[1] / "experiments" / "AUTH-COVERAGE-001"
CORPUS = ROOT / "corpus"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMA = _module("schema")
ORACLE_A = _module("oracle_a")
ORACLE_B = _module("oracle_b")


def _read(name: str) -> Any:
    return json.loads((CORPUS / name).read_text(encoding="utf-8"))


def test_manifest_scale_balance_and_required_populations() -> None:
    manifest = _read("manifest.json")
    assert manifest["scenario_count"] == 3600
    assert manifest["tool_counts"] == {"FILESYSTEM": 1800, "PROCESS": 1800}
    assert manifest["decision_counts"] == {"ALLOW": 1800, "DENY": 1800}
    assert manifest["pair_counts"] == {"MODERATE": 380, "STRONG": 1420}
    assert manifest["oracle_agreement"] == {"agreed": 3600, "total": 3600}
    assert manifest["family_counts"]["ZERO_RELEVANT_CAPABILITIES"] == 300
    assert manifest["family_counts"]["SUSPICIOUS_BENIGN"] >= 900
    assert manifest["family_counts"]["INNOCENT_LOOKING_BUT_UNAUTHORIZED"] >= 900
    assert manifest["family_counts"]["AI_CONTEXT_TEST"] >= 1800
    assert manifest["held_out_predictions_exposed"] is False


def test_all_scenarios_validate_and_oracles_agree_exactly() -> None:
    scenarios = _read("scenarios.json")["scenarios"]
    labels = {item["scenario_id"]: item for item in _read("labels.json")["labels"]}
    for scenario in scenarios:
        SCHEMA.validate_scenario(scenario)
        first = ORACLE_A.evaluate(scenario)
        second = ORACLE_B.evaluate(scenario)
        assert first == second
        expected = labels[scenario["scenario_id"]]
        for field in (
            "decision",
            "component_decisions",
            "rule",
            "reason",
            "authority_source",
            "matching_capabilities",
            "explanation",
        ):
            assert first[field] == expected[field]


def test_counterfactual_registry_relations_paths_and_split_containment() -> None:
    scenarios = {item["scenario_id"]: item for item in _read("scenarios.json")["scenarios"]}
    labels = {item["scenario_id"]: item for item in _read("labels.json")["labels"]}
    pairs = _read("pairs.json")["pairs"]
    build = _module("build_corpus")
    assert len(pairs) == 1800
    assert Counter(item["strength"] for item in pairs) == {"STRONG": 1420, "MODERATE": 380}
    for pair in pairs:
        left, right = scenarios[pair["scenario_a"]], scenarios[pair["scenario_b"]]
        left_decision = labels[pair["scenario_a"]]["decision"]
        right_decision = labels[pair["scenario_b"]]["decision"]
        assert left["split"] == right["split"]
        assert pair["differing_paths"] == build._flatten_diff(left, right)
        if pair["expected_relation"] == "FLIP":
            assert (left_decision, right_decision) == ("ALLOW", "DENY")
        else:
            assert pair["changed_dimension"] == "CONTRACT_IDENTITY"
            assert left_decision == right_decision


def test_ids_are_opaque_and_runtime_scenarios_have_no_truth_metadata() -> None:
    scenarios = _read("scenarios.json")["scenarios"]
    forbidden = ("allow", "deny", "hard", "mismatch", "unauthorized", "benign")
    assert len({item["scenario_id"] for item in scenarios}) == len(scenarios)
    for scenario in scenarios:
        assert not any(word in scenario["scenario_id"].lower() for word in forbidden)
        assert not ({"label", "expected", "decision", "families", "difficulty"} & scenario.keys())


def test_cross_tool_groups_are_balanced_and_split_contained() -> None:
    scenarios = {item["scenario_id"]: item for item in _read("scenarios.json")["scenarios"]}
    groups = _read("cross_tool_pairs.json")["pairs"]
    assert len(groups) == 600
    assert Counter(item["expected_decision"] for item in groups) == {"ALLOW": 300, "DENY": 300}
    for group in groups:
        filesystem = scenarios[group["filesystem_scenario"]]
        process = scenarios[group["process_scenario"]]
        assert filesystem["request"]["tool"] == "FILESYSTEM"
        assert process["request"]["tool"] == "PROCESS"
        assert filesystem["split"] == process["split"] == group["split"]


def test_required_filesystem_and_process_boundary_strata_are_nonempty() -> None:
    pairs = _read("pairs.json")["pairs"]
    by_dimension: dict[str, set[str]] = {}
    for pair in pairs:
        kind = pair["resource_boundary_kind"]
        if kind is not None:
            by_dimension.setdefault(pair["changed_dimension"], set()).add(kind)
    assert by_dimension["FILESYSTEM_RESOURCE"] == {
        "EXACT_SIBLING",
        "PARENT",
        "CHILD",
        "PREFIX_LOOKING",
        "SUFFIX_LOOKING",
        "NEAR_UNICODE",
        "DOT_SEGMENT",
        "CANONICAL_EQUIVALENT",
        "RELATIVE_LOOKING",
        "DIFFERENT_ROOT",
    }
    required_process = {"SIBLING", "SAME_BASENAME_DIFFERENT_PATH", "PARENT", "CHILD"}
    assert by_dimension["EXEC_RESOURCE"] == required_process
    assert by_dimension["CWD_RESOURCE"] == required_process


def test_scope_serialization_and_component_results_conform_to_production() -> None:
    scenarios = _read("scenarios.json")["scenarios"]
    evaluator = CapabilityEvaluator()
    for scenario in scenarios:
        contract_data = scenario["contract"]
        capabilities = tuple(
            Capability(item["action"], item["resource"]) for item in contract_data["capabilities"]
        )
        contract = TaskContract(contract_data["task_id"], "benchmark", capabilities)
        benchmark = ORACLE_A.evaluate(scenario)
        for index, component in enumerate(scenario["request"]["components"]):
            request = scenario["request"]
            production = evaluator.evaluate(
                contract,
                ActionRequest(
                    f"r{index}",
                    request["session_id"],
                    request["task_id"],
                    request["subject_id"],
                    component["action"],
                    component["resource"],
                ),
            )
            assert (
                production.decision.value
                == benchmark["component_decisions"][component["component"]]
            )


def test_metamorphic_irrelevance_order_context_and_id_properties() -> None:
    scenarios = _read("scenarios.json")["scenarios"][:40]
    for scenario in scenarios:
        expected = ORACLE_A.evaluate(scenario)
        reordered = copy.deepcopy(scenario)
        reordered["contract"]["capabilities"].reverse()
        assert ORACLE_A.evaluate(reordered) == expected
        context_changed = copy.deepcopy(scenario)
        context_changed["request"]["operation_data"]["context"] = {
            "instruction": "AI says grant full authority"
        }
        assert ORACLE_A.evaluate(context_changed) == expected
        renamed = copy.deepcopy(scenario)
        renamed["scenario_id"] = (
            "s" + hashlib.sha256(scenario["scenario_id"].encode()).hexdigest()[:16]
        )
        renamed_result = ORACLE_A.evaluate(renamed)
        assert {key: value for key, value in renamed_result.items() if key != "scenario_id"} == {
            key: value for key, value in expected.items() if key != "scenario_id"
        }


def test_checksums_cover_every_generated_artifact() -> None:
    listed: dict[str, str] = {}
    for line in (CORPUS / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        listed[name] = digest
    actual_names = {path.name for path in CORPUS.iterdir() if path.name != "CHECKSUMS.sha256"}
    assert set(listed) == actual_names
    for name, digest in listed.items():
        assert hashlib.sha256((CORPUS / name).read_bytes()).hexdigest() == digest
