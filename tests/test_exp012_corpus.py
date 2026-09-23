"""Schema-only validation for EXP-012-CORPUS@1; no trajectory monitor is used."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from safetybox.capabilities import CapabilityEvaluator
from safetybox.context import ContextAuthority, ContextField, ContextStatus, validate_task_binding
from safetybox.experiments.exp009_corpus import HELD_OUT_SCENARIOS as EXP009_SCENARIOS
from safetybox.experiments.exp012_corpus import (
    HELD_OUT_SCENARIOS,
    INSUFFICIENT_CONTEXT_CONTROLS,
    PRIMARY_SCENARIOS,
    ContextualCorpusScenario,
)
from safetybox.models import ActionRequest, Decision

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "experiments" / "EXP-012" / "corpus"
MODULE = ROOT / "src" / "safetybox" / "experiments" / "exp012_corpus.py"
PRIMARY_LABELS = {"TRAJECTORY_POSITIVE", "TRAJECTORY_NEGATIVE"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _label_entries() -> dict[str, dict[str, Any]]:
    labels = _load(CORPUS / "labels.yaml")
    entries = labels["entries"]
    assert isinstance(entries, list)
    return {entry["scenario_id"]: entry for entry in entries}


def _actions(item: ContextualCorpusScenario) -> tuple[tuple[str, str], ...]:
    return tuple((step.action, step.resource) for step in item.scenario.steps)


def _context_semantics(item: ContextualCorpusScenario) -> tuple[object, ...]:
    context = item.task_context
    return (
        context.schema_version,
        context.purpose.purpose_id,
        tuple(outcome.outcome_id for outcome in context.allowed_outcomes),
        tuple(role.role_id for role in context.data_roles),
        tuple(
            (role.resource_scope, role.role_id, role.data_role_id)
            for role in context.resource_roles
        ),
        tuple(
            (
                destination.action,
                destination.destination_scope,
                destination.destination_id,
                destination.destination_purpose_id,
                destination.allowed_data_role_ids,
                destination.allowed_outcome_ids,
                destination.allowed_action_purpose_ids,
            )
            for destination in context.destination_constraints
        ),
        tuple(
            (
                flow.source_resource_role_ids,
                flow.derived_data_role_id,
                flow.destination_purpose_id,
                flow.allowed_action_purpose_ids,
            )
            for flow in context.data_flow_constraints
        ),
        tuple((purpose.action, purpose.purpose_id) for purpose in context.expected_action_purposes),
        tuple(
            (
                fallback.action,
                fallback.candidate_resource_scopes,
                fallback.candidate_resource_role_ids,
                fallback.purpose_id,
                fallback.behavior_id,
                fallback.maximum_attempts,
                fallback.termination_condition_id,
            )
            for fallback in context.fallback_patterns
        ),
    )


def _observation_semantics(item: ContextualCorpusScenario) -> tuple[object, ...]:
    return tuple(
        (
            supplied.action_purpose_id,
            supplied.data_role_ids,
            (
                supplied.logical_data_flow.source_resource_role_ids,
                supplied.logical_data_flow.derived_data_role_id,
                supplied.logical_data_flow.destination_purpose_id,
                supplied.logical_data_flow.action_purpose_id,
            )
            if supplied.logical_data_flow
            else None,
        )
        for supplied in item.observation_contexts
    )


def _all_sources(item: ContextualCorpusScenario) -> tuple[object, ...]:
    context = item.task_context
    declarations = (
        context.purpose,
        *context.allowed_outcomes,
        *context.data_roles,
        *context.resource_roles,
        *context.destination_constraints,
        *context.data_flow_constraints,
        *context.expected_action_purposes,
        *context.fallback_patterns,
    )
    return tuple(declaration.source for declaration in declarations)


def test_manifest_labels_and_definitions_match_exactly() -> None:
    manifest = _load(CORPUS / "manifest.yaml")
    entries = _label_entries()
    definitions = {item.scenario_id: item for item in HELD_OUT_SCENARIOS}

    assert manifest["corpus_id"] == "EXP-012-CORPUS@1"
    assert manifest["scenario_count"] == len(definitions) == 84
    assert manifest["primary_scenario_count"] == len(PRIMARY_SCENARIOS) == 80
    assert manifest["insufficient_control_count"] == len(INSUFFICIENT_CONTEXT_CONTROLS) == 4
    assert manifest["scenario_ids"] == list(definitions)
    assert set(entries) == set(definitions)
    assert all(entry["version"] == 1 for entry in entries.values())

    labels = Counter(entry["ground_truth_label"] for entry in entries.values())
    assert labels == {
        "TRAJECTORY_POSITIVE": 40,
        "TRAJECTORY_NEGATIVE": 40,
        "INSUFFICIENT_CONTEXT_CONTROL": 4,
    }
    assert manifest["positive_count"] == labels["TRAJECTORY_POSITIVE"]
    assert manifest["negative_count"] == labels["TRAJECTORY_NEGATIVE"]


def test_protocol_targets_and_diversity_margins_are_met() -> None:
    manifest = _load(CORPUS / "manifest.yaml")
    entries = _label_entries()
    primary_entries = [entries[item.scenario_id] for item in PRIMARY_SCENARIOS]

    assert manifest["families"] == {
        "A": 12,
        "B": 12,
        "C": 12,
        "D": 10,
        "E": 10,
        "F": 12,
        "G": 12,
    }
    assert len(manifest["task_categories"]) >= 6
    assert len(manifest["sequence_shapes"]) == 7
    assert len(manifest["destination_purposes"]) == 9
    assert len(manifest["resource_data_roles"]) == 12
    assert len(manifest["fallback_types"]) == 9
    assert sum(entry["hard_negative"] for entry in primary_entries) == 40
    assert sum(entry["family"] == "D" for entry in primary_entries) == 10
    assert sum(entry["family"] == "E" for entry in primary_entries) == 10
    assert sum(entry["family"] == "F" for entry in primary_entries) == 12
    assert (
        sum(
            entry["ground_truth_label"] == "TRAJECTORY_POSITIVE"
            and entry["policy_expectation"] == "ACTIONS_INDIVIDUALLY_AUTHORIZED"
            for entry in primary_entries
        )
        == 30
    )


def test_contexts_are_valid_complete_for_their_family_and_immutable() -> None:
    access_fields = (
        ContextField.PURPOSE,
        ContextField.ALLOWED_OUTCOMES,
        ContextField.DATA_ROLES,
        ContextField.RESOURCE_ROLES,
        ContextField.DESTINATION_CONSTRAINTS,
        ContextField.DATA_FLOW_CONSTRAINTS,
        ContextField.EXPECTED_ACTION_PURPOSES,
    )
    fallback_fields = (
        ContextField.PURPOSE,
        ContextField.ALLOWED_OUTCOMES,
        ContextField.DATA_ROLES,
        ContextField.RESOURCE_ROLES,
        ContextField.EXPECTED_ACTION_PURPOSES,
        ContextField.FALLBACK_PATTERNS,
    )
    for item in PRIMARY_SCENARIOS:
        validate_task_binding(item.scenario.task_contract, item.task_context)
        required = fallback_fields if item.family in {"D", "E"} else access_fields
        assert item.task_context.assess(required).status is ContextStatus.SUFFICIENT_CONTEXT
        assert len(item.observation_contexts) == len(item.scenario.steps)
        assert item.scenario_version == 1

    with pytest.raises(FrozenInstanceError):
        PRIMARY_SCENARIOS[0].family = "G"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        PRIMARY_SCENARIOS[0].task_context.task_id = "replacement"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        PRIMARY_SCENARIOS[0].observation_contexts[0].action_purpose_id = "replacement"  # type: ignore[misc]


def test_missing_context_controls_are_separate_and_dimension_specific() -> None:
    controls = {item.scenario_id: item for item in INSUFFICIENT_CONTEXT_CONTROLS}
    assert not any(item.primary_eligible for item in controls.values())
    assert not controls["CX-012-081"].task_context.destination_constraints
    assert not controls["CX-012-082"].task_context.fallback_patterns
    assert not controls["CX-012-083"].task_context.data_flow_constraints
    assert controls["CX-012-083"].observation_contexts[-1].logical_data_flow is not None
    assert not controls["CX-012-084"].task_context.resource_roles
    assert all(
        _label_entries()[item.scenario_id]["ground_truth_label"] == "INSUFFICIENT_CONTEXT_CONTROL"
        for item in controls.values()
    )


def test_all_context_provenance_is_trusted_and_varied() -> None:
    authorities: set[ContextAuthority] = set()
    for item in HELD_OUT_SCENARIOS:
        sources = _all_sources(item)
        assert sources
        assert all(source.authority.is_trusted and source.immutable_reference for source in sources)
        assert all(source.authority is not ContextAuthority.AGENT_SELF_REPORT for source in sources)
        authorities.update(source.authority for source in sources)
    assert authorities == {
        ContextAuthority.TASK_CONTRACT,
        ContextAuthority.SYSTEM_POLICY,
        ContextAuthority.RESOURCE_REGISTRY,
        ContextAuthority.TOOL_ADAPTER,
    }


def test_action_policy_expectations_without_trajectory_execution() -> None:
    entries = _label_entries()
    evaluator = CapabilityEvaluator()
    for item in HELD_OUT_SCENARIOS:
        for index, step in enumerate(item.scenario.steps, start=1):
            request = ActionRequest(
                request_id=f"schema-{item.scenario_id}-{index}",
                session_id=f"schema-{item.scenario_id}",
                task_id=item.scenario.task_contract.task_id,
                actor=step.actor,
                action=step.action,
                resource=step.resource,
            )
            decision = evaluator.evaluate(item.scenario.task_contract, request).decision
            expectation = entries[item.scenario_id]["policy_expectation"]
            expected = (
                Decision.DENY
                if expectation == "ACTIONS_DENIED_CONTEXT_INTERPRETED_SEPARATELY"
                else Decision.ALLOW
            )
            assert decision is expected


def test_no_exact_or_renamed_input_duplicates() -> None:
    seen: dict[tuple[object, ...], str] = {}
    for item in HELD_OUT_SCENARIOS:
        key = (_actions(item), _context_semantics(item), _observation_semantics(item))
        assert key not in seen, f"{item.scenario_id} duplicates {seen.get(key)}"
        seen[key] = item.scenario_id

    rationales = [entry["ground_truth_rationale"] for entry in _label_entries().values()]
    assert len(rationales) == len(set(rationales))


def test_contrast_pairs_have_opposite_labels_and_intended_minimal_difference() -> None:
    entries = _label_entries()
    pairs: dict[str, list[ContextualCorpusScenario]] = defaultdict(list)
    for item in PRIMARY_SCENARIOS:
        if item.contrast_pair_id:
            pairs[item.contrast_pair_id].append(item)
    assert len(pairs) == 28

    for pair_id, members in pairs.items():
        assert len(members) == 2
        left, right = members
        assert {
            entries[left.scenario_id]["ground_truth_label"],
            entries[right.scenario_id]["ground_truth_label"],
        } == PRIMARY_LABELS
        families = {left.family, right.family}
        if families == {"A"}:
            assert _actions(left) == _actions(right)
            assert left.task_context.purpose.purpose_id != right.task_context.purpose.purpose_id
        elif families == {"B"}:
            assert left.task_context.purpose.purpose_id == right.task_context.purpose.purpose_id
            assert _context_semantics(left) == _context_semantics(right)
            assert _observation_semantics(left) == _observation_semantics(right)
            assert _actions(left)[:-1] == _actions(right)[:-1]
            assert _actions(left)[-1] != _actions(right)[-1]
        elif families == {"C"}:
            assert _actions(left) == _actions(right)
            assert (
                left.observation_contexts[-1].data_role_ids
                != right.observation_contexts[-1].data_role_ids
            )
        else:
            assert families == {"D", "E"}, pair_id
            assert _actions(left) == _actions(right)
            assert left.task_context.purpose.purpose_id == right.task_context.purpose.purpose_id
            assert (
                left.task_context.fallback_patterns[0].candidate_resource_scopes
                != right.task_context.fallback_patterns[0].candidate_resource_scopes
            )


def test_family_f_uses_unfamiliar_positive_structures() -> None:
    frozen_exact_sequence = (
        "filesystem.read",
        "filesystem.read",
        "database.query",
        "network.send",
    )
    family_f = [item for item in PRIMARY_SCENARIOS if item.family == "F"]
    assert len(family_f) == 12
    assert all(
        tuple(step.action for step in item.scenario.steps) != frozen_exact_sequence
        for item in family_f
    )
    assert len({tuple(step.action for step in item.scenario.steps) for item in family_f}) >= 8


def test_labels_are_not_detector_inputs_and_names_do_not_leak_labels() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "safetybox.trajectory.monitor" not in imported_modules
    assert "safetybox.context_trajectory" not in imported_modules
    assert "TRAJECTORY_POSITIVE" not in source
    assert "TRAJECTORY_NEGATIVE" not in source

    prohibited = re.compile(r"\b(malicious|benign|positive|negative|attack|safe)\b", re.IGNORECASE)
    for item in HELD_OUT_SCENARIOS:
        context = item.task_context
        fields = [
            item.scenario_id,
            item.scenario.title,
            item.scenario.description,
            item.scenario.task_contract.description,
            context.purpose.purpose_id,
            context.purpose.description,
            *(step.resource for step in item.scenario.steps),
            *(destination.destination_id for destination in context.destination_constraints),
            *(destination.destination_scope for destination in context.destination_constraints),
            *(
                destination.destination_purpose_id
                for destination in context.destination_constraints
            ),
        ]
        assert not any(prohibited.search(value) for value in fields)


def test_held_out_ids_do_not_overlap_contaminated_or_core_source_ids() -> None:
    held_out_ids = {item.scenario_id for item in HELD_OUT_SCENARIOS}
    contaminated_ids = {item.scenario_id for item in EXP009_SCENARIOS} | {
        "TS-008",
        "TS-009",
        "BENIGN-001",
        "BENIGN-002",
    }
    assert held_out_ids.isdisjoint(contaminated_ids)
    assert {_actions(item) for item in HELD_OUT_SCENARIOS}.isdisjoint(
        {
            tuple((step.action, step.resource) for step in item.scenario.steps)
            for item in EXP009_SCENARIOS
        }
    )

    occurrences: dict[str, list[Path]] = defaultdict(list)
    for path in (ROOT / "src" / "safetybox").rglob("*.py"):
        if path == MODULE:
            continue
        text = path.read_text(encoding="utf-8")
        for scenario_id in held_out_ids:
            if scenario_id in text:
                occurrences[scenario_id].append(path)
    assert not occurrences
