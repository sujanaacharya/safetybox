"""Validation and stable TaskContext binding for B4 declarations."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any

from safetybox.b4.models import (
    HISTORY_CONTEXT_SCHEMA_VERSION,
    AggregationScope,
    B4HistoricalConstraints,
    CandidateOrderMode,
    HistoryDimension,
)
from safetybox.capabilities import is_valid_resource_scope
from safetybox.context import ContextSource, TaskContext


class B4ValidationError(ValueError):
    """A B4 declaration is malformed, ambiguous, or outside the trust boundary."""


def task_context_reference(task_context: TaskContext) -> str:
    """Return a deterministic semantic reference for an immutable TaskContext."""
    payload = json.dumps(_canonical(task_context), sort_keys=True, separators=(",", ":"))
    return f"task-context-sha256:{sha256(payload.encode()).hexdigest()}"


def validate_history_context(context: B4HistoricalConstraints) -> None:
    if context.schema_version != HISTORY_CONTEXT_SCHEMA_VERSION:
        raise B4ValidationError(f"Unsupported B4 history schema: {context.schema_version!r}.")
    _identifier("constraints_id", context.constraints_id)
    _identifier("task_id", context.task_id)
    if not context.task_context_reference:
        raise B4ValidationError("task_context_reference must not be empty.")

    declared_dimensions = [item.dimension for item in context.dimension_applicability]
    if len(declared_dimensions) != len(set(declared_dimensions)):
        raise B4ValidationError("B4 dimensions must be declared exactly once.")
    if set(declared_dimensions) != set(HistoryDimension):
        raise B4ValidationError("Every B4 history dimension requires explicit applicability.")

    declarations: tuple[object, ...] = (
        *context.dimension_applicability,
        *context.role_groups,
        *context.aggregation_scopes,
        *context.role_combination_constraints,
        *context.semantic_event_bindings,
        *context.phase_definitions,
        *context.permitted_phase_transitions,
        *context.finalization_constraints,
        *context.fallback_progression_constraints,
    )
    for declaration in declarations:
        source = getattr(declaration, "source", None)
        if not isinstance(source, ContextSource) or not source.authority.is_trusted:
            raise B4ValidationError(
                "Every B4 declaration requires trusted ContextSource provenance."
            )

    _unique("role group", [item.group_id for item in context.role_groups])
    _unique("aggregation scope", [item.scope_id for item in context.aggregation_scopes])
    _unique(
        "role combination constraint",
        [item.declaration_id for item in context.role_combination_constraints],
    )
    _unique("semantic binding", [item.binding_id for item in context.semantic_event_bindings])
    _unique("phase", [item.phase_id for item in context.phase_definitions])
    _unique(
        "finalization", [item.finalization_id for item in context.finalization_constraints]
    )
    _unique(
        "fallback progression",
        [item.constraint_id for item in context.fallback_progression_constraints],
    )

    event_ids = {item.semantic_event_id for item in context.semantic_event_bindings}
    group_ids = {item.group_id for item in context.role_groups}
    scope_ids = {item.scope_id for item in context.aggregation_scopes}
    phase_ids = {item.phase_id for item in context.phase_definitions}
    for binding in context.semantic_event_bindings:
        for label, value in (
            ("binding_id", binding.binding_id),
            ("semantic_event_id", binding.semantic_event_id),
            ("action", binding.action),
        ):
            _identifier(label, value)
        optional_values = (
            binding.resource_role_id,
            binding.data_role_id,
            binding.destination_id,
            binding.action_purpose_id,
            binding.outcome_id,
        )
        if all(optional_value is None for optional_value in optional_values):
            continue
        for optional_value in optional_values:
            if optional_value is not None:
                _identifier("semantic binding field", optional_value)

    for group in context.role_groups:
        _identifier("role group ID", group.group_id)
        if not group.resource_role_ids and not group.data_role_ids:
            raise B4ValidationError("Role groups must contain at least one role ID.")
        _identifiers((*group.resource_role_ids, *group.data_role_ids))
    for scope in context.aggregation_scopes:
        _validate_scope(scope, event_ids, group_ids)
    for constraint in context.role_combination_constraints:
        _identifier("role combination declaration ID", constraint.declaration_id)
        if constraint.aggregation_scope_id not in scope_ids:
            raise B4ValidationError("Role combination references an unknown aggregation scope.")
        if constraint.outcome_semantic_event_id not in event_ids:
            raise B4ValidationError("Role combination references an unknown outcome event.")
        if not constraint.allowed_exact_projected_combinations:
            raise B4ValidationError("Role combination allow-list must not be empty.")
        if not constraint.tracked_role_group_ids <= group_ids:
            raise B4ValidationError("Role combination references an unknown role group.")
        for allowed in constraint.allowed_exact_projected_combinations:
            if not allowed.resource_role_ids <= constraint.tracked_resource_role_ids:
                raise B4ValidationError("Allowed resource roles exceed the tracked universe.")
            if not allowed.data_role_ids <= constraint.tracked_data_role_ids:
                raise B4ValidationError("Allowed data roles exceed the tracked universe.")
            if not allowed.role_group_ids <= constraint.tracked_role_group_ids:
                raise B4ValidationError("Allowed groups exceed the tracked universe.")

    for phase in context.phase_definitions:
        _identifier("phase ID", phase.phase_id)
        if not phase.semantic_event_ids or not phase.semantic_event_ids <= event_ids:
            raise B4ValidationError("Phase events must be non-empty known semantic events.")
    event_phase_count: dict[str, int] = {}
    for phase in context.phase_definitions:
        for event_id in phase.semantic_event_ids:
            event_phase_count[event_id] = event_phase_count.get(event_id, 0) + 1
    if any(count > 1 for count in event_phase_count.values()):
        raise B4ValidationError("A semantic event cannot map to multiple phases.")
    for transition in context.permitted_phase_transitions:
        if transition.from_phase_id not in phase_ids or transition.to_phase_id not in phase_ids:
            raise B4ValidationError("Phase transition references an unknown phase.")

    for finalization in context.finalization_constraints:
        _identifier("finalization ID", finalization.finalization_id)
        _identifier("finalization outcome ID", finalization.outcome_id)
        if finalization.finalization_semantic_event_id not in event_ids:
            raise B4ValidationError("Finalization references an unknown semantic event.")
        if not finalization.closed_phase_ids or not finalization.closed_phase_ids <= phase_ids:
            raise B4ValidationError("Finalization must close known phases.")
        if not finalization.permitted_post_finalization_semantic_event_ids <= event_ids:
            raise B4ValidationError("Finalization exception references an unknown event.")

    for progression in context.fallback_progression_constraints:
        _identifier("fallback progression ID", progression.constraint_id)
        _identifier("fallback behavior ID", progression.linked_fallback_behavior_id)
        if progression.maximum_attempts < 1:
            raise B4ValidationError("Fallback maximum_attempts must be positive.")
        if not progression.candidates:
            raise B4ValidationError("Fallback progression requires candidates.")
        candidate_ids = [item.candidate_id for item in progression.candidates]
        _unique("fallback candidate", candidate_ids)
        known_candidates = set(candidate_ids)
        for candidate in progression.candidates:
            _identifier("fallback candidate ID", candidate.candidate_id)
            _identifier("fallback candidate role", candidate.resource_role_id)
            if not is_valid_resource_scope(candidate.resource_scope):
                raise B4ValidationError("Fallback candidate has invalid resource scope.")
            if not candidate.source.authority.is_trusted:
                raise B4ValidationError("Fallback candidates require trusted provenance.")
        for candidate_transition in progression.allowed_candidate_transitions:
            if (
                candidate_transition.from_candidate_id not in known_candidates
                or candidate_transition.to_candidate_id not in known_candidates
            ):
                raise B4ValidationError("Fallback transition references an unknown candidate.")
        if (
            progression.order_mode is CandidateOrderMode.EXPLICIT_TRANSITIONS
            and len(progression.candidates) > 1
            and not progression.allowed_candidate_transitions
        ):
            raise B4ValidationError("Explicit fallback progression requires transitions.")
        has_condition = progression.termination_condition_id is not None
        has_event = progression.termination_semantic_event_id is not None
        if has_condition != has_event:
            raise B4ValidationError(
                "Fallback termination condition and semantic event must be declared together."
            )
        if progression.termination_semantic_event_id not in event_ids and has_event:
            raise B4ValidationError("Fallback termination references an unknown event.")


def _validate_scope(
    scope: AggregationScope, event_ids: set[str], group_ids: set[str]
) -> None:
    _identifier("aggregation scope ID", scope.scope_id)
    if not scope.opening_semantic_event_ids:
        raise B4ValidationError("Aggregation scope requires an opening semantic event.")
    if not scope.closing_semantic_event_ids:
        raise B4ValidationError("Aggregation scope requires a closing semantic event.")
    if not scope.opening_semantic_event_ids <= event_ids:
        raise B4ValidationError("Aggregation scope references an unknown opening event.")
    if not scope.closing_semantic_event_ids <= event_ids:
        raise B4ValidationError("Aggregation scope references an unknown closing event.")
    if not scope.tracked_role_group_ids <= group_ids:
        raise B4ValidationError("Aggregation scope references an unknown role group.")


def _canonical(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonical(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_canonical(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted((_canonical(item) for item in value), key=lambda item: repr(item))
    return value


def _identifier(label: str, value: str) -> None:
    if not value or value.strip() != value or any(character.isspace() for character in value):
        raise B4ValidationError(f"{label} must be a non-empty identifier without whitespace.")


def _identifiers(values: tuple[str, ...]) -> None:
    for value in values:
        _identifier("identifier", value)


def _unique(label: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise B4ValidationError(f"Duplicate {label} identifier.")
