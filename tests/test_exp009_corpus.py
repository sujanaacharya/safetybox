"""Structural and action-policy validation for the frozen-candidate held-out corpus."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from safetybox.experiments.exp009_corpus import HELD_OUT_SCENARIOS
from safetybox.simulation import ScenarioRunner

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "experiments" / "EXP-009" / "corpus"
DEVELOPMENT_IDS = {"TS-008", "TS-009", "BENIGN-001", "BENIGN-002"}


def _json_yaml(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_and_labels_are_machine_readable_and_match_definitions() -> None:
    manifest = _json_yaml(CORPUS / "manifest.yaml")
    labels = _json_yaml(CORPUS / "labels.yaml")
    assert isinstance(manifest, dict)
    assert isinstance(labels, dict)
    definitions = {item.scenario_id: item for item in HELD_OUT_SCENARIOS}
    assert manifest["scenario_count"] == len(definitions) == 80
    assert manifest["scenario_ids"] == list(definitions)
    assert {entry["scenario_id"] for entry in labels["entries"]} == set(definitions)
    assert all(
        entry["scenario_version"] == 1 and entry["rationale_summary"] for entry in labels["entries"]
    )
    for entry in labels["entries"]:
        definition = definitions[entry["scenario_id"]]
        assert entry["family"] == definition.family
        assert entry["ground_truth_label"] == definition.ground_truth_label
        assert entry["expected_rule_family"] == definition.expected_rule_family


def test_ids_labels_steps_and_versions_are_valid_and_held_out() -> None:
    ids = [item.scenario_id for item in HELD_OUT_SCENARIOS]
    assert len(ids) == len(set(ids))
    for item in HELD_OUT_SCENARIOS:
        assert item.scenario_version == 1
        assert item.ground_truth_label in {"TRAJECTORY_POSITIVE", "TRAJECTORY_NEGATIVE"}
        assert item.family in {"TRJ-001", "TRJ-002"}
        assert item.scenario_id not in DEVELOPMENT_IDS
        assert (
            item.task_title
            and item.task_description
            and item.task_objective
            and item.security_rationale
            and item.policy_sufficiency
        )
        step_ids = [step.step_id for step in item.scenario.steps]
        assert step_ids and len(step_ids) == len(set(step_ids))


def test_policy_baseline_semantics_without_trajectory_monitor() -> None:
    for item in HELD_OUT_SCENARIOS:
        result = ScenarioRunner().run(item.scenario)
        assert result.expectations_failed == 0
        if item.family == "TRJ-001" and item.ground_truth_label == "TRAJECTORY_POSITIVE":
            assert result.blocked_count == 0
        if item.family == "TRJ-002" and item.ground_truth_label == "TRAJECTORY_POSITIVE":
            assert result.executed_count < result.attempted_steps
            assert any(not step.executed for step in result.step_results)
            assert all(
                not step.executed
                for step in result.step_results
                if not item.scenario.steps[
                    int(step.step_id.removeprefix("step-")) - 1
                ].resource.startswith("/sim/project/")
            )


def test_contrast_pairs_have_two_contextually_opposed_members() -> None:
    pairs: dict[str, list[object]] = {}
    for item in HELD_OUT_SCENARIOS:
        if item.contrast_pair:
            pairs.setdefault(item.contrast_pair, []).append(item)
    assert len(pairs) == 10
    for members in pairs.values():
        assert len(members) == 2
        left, right = members
        assert left.ground_truth_label != right.ground_truth_label
        assert [(s.action, s.resource) for s in left.scenario.steps] == [
            (s.action, s.resource) for s in right.scenario.steps
        ]
        assert left.task_objective != right.task_objective


def test_definitions_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        HELD_OUT_SCENARIOS[0].family = "TRJ-002"  # type: ignore[misc]


def test_no_accidental_structural_duplicates_outside_intentional_contrast_pairs() -> None:
    seen: dict[tuple[object, ...], str] = {}
    for item in HELD_OUT_SCENARIOS:
        key = (
            item.family,
            item.ground_truth_label,
            item.source_category,
            tuple(
                sorted(
                    (cap.action, cap.resource) for cap in item.scenario.task_contract.capabilities
                )
            ),
            tuple((step.action, step.resource) for step in item.scenario.steps),
        )
        assert key not in seen, f"{item.scenario_id} duplicates {seen.get(key)}"
        seen[key] = item.scenario_id


def test_malformed_scenario_is_rejected_by_existing_schema() -> None:
    from safetybox.simulation import ThreatScenario

    with pytest.raises(ValueError, match="at least one step"):
        ThreatScenario(
            "BAD",
            "Bad",
            "Bad",
            "bad",
            HELD_OUT_SCENARIOS[0].scenario.task_contract,
            (),
            HELD_OUT_SCENARIOS[0].scenario.expectation,
        )
