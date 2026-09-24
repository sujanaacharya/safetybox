"""Schema, parity, leakage, and integrity audits for EXP-013-CORPUS@1.

These tests may execute frozen B2.  They never instantiate or call the B4 monitor.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any

import pytest

from safetybox.b4.validation import task_context_reference, validate_history_context
from safetybox.baselines.single_observation import BaselinePrediction, SingleObservationBaseline
from safetybox.context import ContextAuthority, ContextSource
from safetybox.experiments.exp009_corpus import HELD_OUT_SCENARIOS as EXP009_SCENARIOS
from safetybox.experiments.exp012_corpus import HELD_OUT_SCENARIOS as EXP012_SCENARIOS
from safetybox.experiments.exp013_corpus import (
    HELD_OUT_SCENARIOS,
    PARTIAL_CONTEXT_CONTROLS,
    PRIMARY_SCENARIOS,
    STALE_CONTEXT_CONTROLS,
    CounterfactualCorpusScenario,
)

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "experiments" / "EXP-013" / "corpus"
MODULE = ROOT / "src" / "safetybox" / "experiments" / "exp013_corpus.py"
PRIMARY_LABELS = {"TRAJECTORY_POSITIVE", "TRAJECTORY_NEGATIVE"}
PROHIBITED_INPUT_TERMS = re.compile(
    r"(?:positive|negative|attack|benign|unsafe|safe|malicious|evil|exfil|violation)",
    re.IGNORECASE,
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _entries() -> dict[str, dict[str, Any]]:
    raw = _load(CORPUS / "labels.yaml")["entries"]
    assert isinstance(raw, list)
    return {entry["scenario_id"]: entry for entry in raw}


def _scenario_map() -> dict[str, CounterfactualCorpusScenario]:
    return {item.scenario_id: item for item in HELD_OUT_SCENARIOS}


def _sources(value: object) -> tuple[ContextSource, ...]:
    found: list[ContextSource] = []
    seen: set[int] = set()

    def visit(item: object) -> None:
        if id(item) in seen:
            return
        seen.add(id(item))
        if isinstance(item, ContextSource):
            found.append(item)
        elif is_dataclass(item):
            for field in fields(item):
                visit(getattr(item, field.name))
        elif isinstance(item, tuple | list | set | frozenset):
            for member in item:
                visit(member)

    visit(value)
    return tuple(found)


def _local_results(item: CounterfactualCorpusScenario) -> tuple[object, ...]:
    baseline = SingleObservationBaseline()
    return tuple(
        baseline.evaluate(observation, item.task_context, spec.observation_context)
        for observation, spec in zip(
            item.completed_observations(), item.observations, strict=True
        )
    )


def _pair_members() -> dict[str, tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]]:
    entries = _entries()
    groups: dict[str, list[CounterfactualCorpusScenario]] = defaultdict(list)
    for item in PRIMARY_SCENARIOS:
        pair_id = entries[item.scenario_id]["counterfactual_pair_id"]
        groups[pair_id].append(item)
    return {key: (value[0], value[1]) for key, value in groups.items()}


def _feature_values(item: CounterfactualCorpusScenario) -> dict[str, object]:
    results = _local_results(item)
    context = item.task_context
    history = item.history_context
    final = results[-1]
    phase_count = len(history.phase_definitions)
    attempt_count = sum(not observation.executed for observation in item.observations)
    declaration_count = sum(
        len(value)
        for value in (
            context.allowed_outcomes,
            context.data_roles,
            context.resource_roles,
            context.destination_constraints,
            context.data_flow_constraints,
            context.expected_action_purposes,
            context.fallback_patterns,
            history.dimension_applicability,
            history.role_groups,
            history.aggregation_scopes,
            history.role_combination_constraints,
            history.semantic_event_bindings,
            history.phase_definitions,
            history.permitted_phase_transitions,
            history.finalization_constraints,
            history.fallback_progression_constraints,
        )
    )
    statuses = tuple(result.context_status.value for result in results)
    return {
        "context_completeness": "COMPLETE",
        "declaration_count": declaration_count,
        "number_of_phases": phase_count,
        "number_of_roles": len(context.resource_roles),
        "number_of_role_groups": len(history.role_groups),
        "destination_presence": bool(context.destination_constraints),
        "fallback_declaration_presence": bool(context.fallback_patterns),
        "sequence_length": len(item.observations),
        "final_action": item.observations[-1].action,
        "final_ContextEvaluation_status": final.context_status.value,
        "any_mismatch_presence": "CONTEXT_MISMATCH" in statuses,
        "any_insufficient_context_presence": "INSUFFICIENT_CONTEXT" in statuses,
        "task_category": item.task_category,
        "purpose_id": context.purpose.purpose_id,
        "trusted_source_count": len(set(_sources((context, history)))),
        "action_multiset": tuple(sorted(observation.action for observation in item.observations)),
        "observation_count": len(item.observations),
        "role_count": len(context.resource_roles),
        "fallback_attempt_count_alone": attempt_count,
        "phase_count_alone": phase_count,
        "outcome_count": len(context.allowed_outcomes),
    }


def _perfectly_separates(feature: str) -> bool:
    entries = _entries()
    contingencies: dict[object, set[str]] = defaultdict(set)
    for item in PRIMARY_SCENARIOS:
        contingencies[_feature_values(item)[feature]].add(
            entries[item.scenario_id]["ground_truth_label"]
        )
    return all(len(labels) == 1 for labels in contingencies.values())


def test_manifest_labels_and_definitions_match() -> None:
    manifest = _load(CORPUS / "manifest.yaml")
    entries = _entries()
    scenarios = _scenario_map()
    labels = Counter(entry["ground_truth_label"] for entry in entries.values())

    assert manifest["corpus_id"] == "EXP-013-CORPUS@1"
    assert manifest["version"] == 1
    assert len(scenarios) == len(entries) == 96
    assert len(PRIMARY_SCENARIOS) == 80
    assert len(PARTIAL_CONTEXT_CONTROLS) == 8
    assert len(STALE_CONTEXT_CONTROLS) == 8
    assert labels == {
        "TRAJECTORY_POSITIVE": 40,
        "TRAJECTORY_NEGATIVE": 40,
        "ABSTAIN_EXPECTED": 8,
        "STALE_CONTEXT_CONTROL": 8,
    }
    assert manifest["scenario_ids"] == list(scenarios)
    assert set(entries) == set(scenarios)
    assert manifest["scenario_counts"] == {
        "total": 96,
        "primary": 80,
        "partial_context_controls": 8,
        "stale_context_controls": 8,
    }
    assert manifest["primary_positive_count"] == 40
    assert manifest["primary_negative_count"] == 40
    assert manifest["counterfactual_pair_count"] == 40
    assert manifest["strong_counterfactual_pair_count"] == 40
    assert manifest["task_category_counts"] == dict(
        sorted(Counter(item.task_category for item in HELD_OUT_SCENARIOS).items())
    )
    assert manifest["sequence_shape_counts"] == dict(
        sorted(Counter(item.sequence_shape for item in HELD_OUT_SCENARIOS).items())
    )
    assert manifest["family_counts"] == {
        "MS-A": {"TRAJECTORY_POSITIVE": 7, "TRAJECTORY_NEGATIVE": 7, "total": 14},
        "MS-B": {"TRAJECTORY_POSITIVE": 7, "TRAJECTORY_NEGATIVE": 7, "total": 14},
        "MS-C": {"TRAJECTORY_POSITIVE": 7, "TRAJECTORY_NEGATIVE": 7, "total": 14},
        "MS-D": {"TRAJECTORY_POSITIVE": 7, "TRAJECTORY_NEGATIVE": 7, "total": 14},
        "MS-E": {"TRAJECTORY_POSITIVE": 6, "TRAJECTORY_NEGATIVE": 6, "total": 12},
        "MS-F": {"TRAJECTORY_POSITIVE": 6, "TRAJECTORY_NEGATIVE": 6, "total": 12},
    }


def test_contexts_are_bound_valid_trusted_and_immutable() -> None:
    authorities_by_label: dict[str, set[ContextAuthority]] = defaultdict(set)
    entries = _entries()
    for item in HELD_OUT_SCENARIOS:
        assert item.task_id == item.task_context.task_id == item.history_context.task_id
        validate_history_context(item.history_context)
        sources = _sources((item.task_context, item.history_context))
        assert sources
        assert all(source.authority is not ContextAuthority.AGENT_SELF_REPORT for source in sources)
        if item.control_type == "PRIMARY":
            authorities_by_label[entries[item.scenario_id]["ground_truth_label"]].update(
                source.authority for source in sources
            )
        with pytest.raises(FrozenInstanceError):
            item.task_context.task_id = "replacement"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            item.history_context.task_id = "replacement"  # type: ignore[misc]

    detectable = STALE_CONTEXT_CONTROLS[:4]
    internally_consistent = STALE_CONTEXT_CONTROLS[4:]
    assert all(
        item.history_context.task_context_reference != task_context_reference(item.task_context)
        for item in detectable
    )
    assert all(
        item.history_context.task_context_reference == task_context_reference(item.task_context)
        for item in (*PRIMARY_SCENARIOS, *PARTIAL_CONTEXT_CONTROLS, *internally_consistent)
    )
    expected_authorities = {
        ContextAuthority.TASK_CONTRACT,
        ContextAuthority.SYSTEM_POLICY,
        ContextAuthority.RESOURCE_REGISTRY,
        ContextAuthority.TOOL_ADAPTER,
    }
    assert authorities_by_label == {
        "TRAJECTORY_POSITIVE": expected_authorities,
        "TRAJECTORY_NEGATIVE": expected_authorities,
    }


def test_primary_labels_and_history_annotations_are_complete() -> None:
    entries = _entries()
    family_counts: Counter[tuple[str, str]] = Counter()
    dimensions = {
        "MS-A": "ROLE_ACCUMULATION",
        "MS-B": "CROSS_SOURCE_GROUPING",
        "MS-C": "ORDER_TRANSITION",
        "MS-D": "POST_FINALIZATION",
        "MS-E": "FALLBACK_PROGRESSION",
        "MS-F": "CROSS_PHASE",
    }
    for item in PRIMARY_SCENARIOS:
        entry = entries[item.scenario_id]
        assert entry["ground_truth_label"] in PRIMARY_LABELS
        assert entry["history_required"] is True
        assert entry["history_dimension"] == dimensions[entry["family"]]
        assert entry["control_type"] is None
        family_counts[(entry["family"], entry["ground_truth_label"])] += 1
    assert family_counts == Counter(
        {
            ("MS-A", "TRAJECTORY_POSITIVE"): 7,
            ("MS-A", "TRAJECTORY_NEGATIVE"): 7,
            ("MS-B", "TRAJECTORY_POSITIVE"): 7,
            ("MS-B", "TRAJECTORY_NEGATIVE"): 7,
            ("MS-C", "TRAJECTORY_POSITIVE"): 7,
            ("MS-C", "TRAJECTORY_NEGATIVE"): 7,
            ("MS-D", "TRAJECTORY_POSITIVE"): 7,
            ("MS-D", "TRAJECTORY_NEGATIVE"): 7,
            ("MS-E", "TRAJECTORY_POSITIVE"): 6,
            ("MS-E", "TRAJECTORY_NEGATIVE"): 6,
            ("MS-F", "TRAJECTORY_POSITIVE"): 6,
            ("MS-F", "TRAJECTORY_NEGATIVE"): 6,
        }
    )
    assert len({item.task_category for item in PRIMARY_SCENARIOS}) == 12
    assert {len(item.observations) for item in PRIMARY_SCENARIOS} == {2, 3, 4, 5, 6, 7, 8}
    shape_text = " ".join(item.sequence_shape for item in PRIMARY_SCENARIOS)
    for required_shape in (
        "reordered",
        "interleaved",
        "repeated",
        "transition",
        "multi_source",
        "post_finalization",
        "fallback",
    ):
        assert required_shape in shape_text


def test_counterfactual_pairs_have_static_local_and_b2_parity() -> None:
    entries = _entries()
    baseline = SingleObservationBaseline()
    pairs = _pair_members()
    assert len(pairs) == 40
    for pair_id, (left, right) in pairs.items():
        assert pair_id.startswith("CF-013-")
        assert {
            entries[left.scenario_id]["ground_truth_label"],
            entries[right.scenario_id]["ground_truth_label"],
        } == PRIMARY_LABELS
        assert left.task_context == right.task_context
        assert left.history_context == right.history_context
        assert left.task_category == right.task_category
        assert len(left.observations) == len(right.observations)
        local_left = Counter(
            (
                item.action,
                item.resource,
                item.policy_decision,
                item.executed,
                item.observation_context,
            )
            for item in left.observations
        )
        local_right = Counter(
            (
                item.action,
                item.resource,
                item.policy_decision,
                item.executed,
                item.observation_context,
            )
            for item in right.observations
        )
        assert local_left == local_right
        left_results = _local_results(left)
        right_results = _local_results(right)
        assert tuple(result.context_status for result in left_results) == tuple(
            result.context_status for result in right_results
        )
        assert Counter(result.reason_ids for result in left_results) == Counter(
            result.reason_ids for result in right_results
        )
        assert baseline.aggregate(left_results).prediction is BaselinePrediction.NEGATIVE
        assert baseline.aggregate(right_results).prediction is BaselinePrediction.NEGATIVE


def test_static_and_preregistered_combination_features_do_not_separate() -> None:
    features = tuple(_feature_values(PRIMARY_SCENARIOS[0]))
    for feature in features:
        assert not _perfectly_separates(feature), feature

    combinations = (
        ("final_ContextEvaluation_status", "sequence_length"),
        ("role_count", "outcome_count"),
        ("task_category", "phase_count_alone"),
        ("fallback_declaration_presence", "fallback_attempt_count_alone"),
        ("final_action", "context_completeness"),
    )
    entries = _entries()
    for combination in combinations:
        contingency: dict[tuple[object, ...], set[str]] = defaultdict(set)
        for item in PRIMARY_SCENARIOS:
            values = _feature_values(item)
            key = tuple(values[name] for name in combination)
            contingency[key].add(entries[item.scenario_id]["ground_truth_label"])
        assert not all(len(labels) == 1 for labels in contingency.values()), combination


def _normalized_fingerprint(item: CounterfactualCorpusScenario) -> tuple[object, ...]:
    history = item.history_context
    phase_index = {phase.phase_id: index for index, phase in enumerate(history.phase_definitions)}
    event_index = {
        observation.event_key: index for index, observation in enumerate(item.observations)
    }
    return (
        item.control_type,
        tuple(
            (
                re.sub(r"\d+$", "#", observation.action),
                observation.policy_decision.value,
                observation.executed,
                observation.event_key,
            )
            for observation in item.observations
        ),
        tuple(
            (declaration.dimension.value, declaration.applicability.value)
            for declaration in history.dimension_applicability
        ),
        tuple(
            (len(group.resource_role_ids), len(group.data_role_ids))
            for group in history.role_groups
        ),
        tuple(
            (
                len(scope.opening_semantic_event_ids),
                len(scope.closing_semantic_event_ids),
                len(scope.tracked_role_group_ids),
            )
            for scope in history.aggregation_scopes
        ),
        tuple(
            (
                len(constraint.tracked_resource_role_ids),
                len(constraint.tracked_data_role_ids),
                len(constraint.tracked_role_group_ids),
                tuple(
                    (
                        len(combo.resource_role_ids),
                        len(combo.data_role_ids),
                        len(combo.role_group_ids),
                    )
                    for combo in constraint.allowed_exact_projected_combinations
                ),
            )
            for constraint in history.role_combination_constraints
        ),
        tuple(len(phase.semantic_event_ids) for phase in history.phase_definitions),
        tuple(
            (phase_index[edge.from_phase_id], phase_index[edge.to_phase_id])
            for edge in history.permitted_phase_transitions
        ),
        tuple(
            (len(value.closed_phase_ids), len(value.permitted_post_finalization_semantic_event_ids))
            for value in history.finalization_constraints
        ),
        tuple(
            (
                len(value.candidates),
                value.maximum_attempts,
                value.restart_policy.value,
                value.cycle_policy.value,
                value.order_mode.value,
                len(value.allowed_candidate_transitions),
            )
            for value in history.fallback_progression_constraints
        ),
        tuple(event_index[observation.event_key] for observation in item.observations),
    )


def test_no_exact_renamed_or_development_duplicates() -> None:
    exact: set[tuple[object, ...]] = set()
    normalized: dict[tuple[object, ...], str] = {}
    for item in HELD_OUT_SCENARIOS:
        exact_key = (
            item.task_context,
            item.history_context,
            item.observations,
        )
        assert exact_key not in exact
        exact.add(exact_key)
        normalized_key = _normalized_fingerprint(item)
        assert normalized_key not in normalized, (
            item.scenario_id,
            normalized.get(normalized_key),
        )
        normalized[normalized_key] = item.scenario_id

    existing_ids = {
        *(item.scenario_id for item in EXP009_SCENARIOS),
        *(item.scenario_id for item in EXP012_SCENARIOS),
    }
    assert not existing_ids.intersection(item.scenario_id for item in HELD_OUT_SCENARIOS)
    development_action_traces = {
        tuple((step.action, step.resource) for step in item.scenario.steps)
        for item in EXP009_SCENARIOS
    }
    development_action_traces.update(
        tuple((step.action, step.resource) for step in item.scenario.steps)
        for item in EXP012_SCENARIOS
    )
    assert all(
        tuple((obs.action, obs.resource) for obs in item.observations)
        not in development_action_traces
        for item in HELD_OUT_SCENARIOS
    )
    rationales = [entry["ground_truth_rationale"] for entry in _entries().values()]
    assert len(rationales) == len(set(rationales))


def test_no_label_bearing_input_identifiers_or_detector_imports() -> None:
    for item in HELD_OUT_SCENARIOS:
        strings = [
            item.scenario_id,
            item.task_id,
            item.task_category,
            item.sequence_shape,
            item.task_context.purpose.purpose_id,
            *(observation.event_key for observation in item.observations),
            *(observation.action for observation in item.observations),
            *(observation.resource for observation in item.observations),
            *(role.role_id for role in item.task_context.resource_roles),
            *(phase.phase_id for phase in item.history_context.phase_definitions),
            *(group.group_id for group in item.history_context.role_groups),
        ]
        assert not any(PROHIBITED_INPUT_TERMS.search(value) for value in strings)

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    assert not any(name.endswith(".monitor") or name.endswith(".rules") for name in imported)
    source = MODULE.read_text(encoding="utf-8")
    assert "ground_truth_label" not in source
    assert "counterfactual_pair_id" not in source


def test_control_annotations_distinguish_partial_and_stale_axes() -> None:
    entries = _entries()
    partial = [entries[item.scenario_id] for item in PARTIAL_CONTEXT_CONTROLS]
    stale = [entries[item.scenario_id] for item in STALE_CONTEXT_CONTROLS]
    assert all(entry["control_type"] == "PARTIAL_CONTEXT" for entry in partial)
    assert all(entry["ground_truth_label"] == "ABSTAIN_EXPECTED" for entry in partial)
    assert {
        entry["history_dimension"] for entry in partial
    } == {"ROLE_ACCUMULATION", "ORDER_TRANSITION", "POST_FINALIZATION", "FALLBACK_PROGRESSION"}
    assert all(entry["control_type"] == "STALE_CONTEXT" for entry in stale)
    assert Counter(entry["stale_context_type"] for entry in stale) == {
        "DETECTABLE_REVISION_MISMATCH": 4,
        "INTERNALLY_CONSISTENT_SEMANTIC_STALENESS": 4,
    }
    assert all("declaration_relative_outcome" in entry for entry in stale)
    assert all("current_task_truth" in entry for entry in stale)
