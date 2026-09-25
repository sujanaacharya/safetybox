"""EXP-016 Protocol@2 experiment-side lifecycle and population semantics.

The model is downstream of production process observations.  It intentionally
does not import or alter ProcessAdapter, the reference monitor, or production
process models.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class LifecycleModelError(ValueError):
    """An observation or corpus population violates the v2 governance model."""


class Route(StrEnum):
    ADAPTER = "ADAPTER"
    DIRECT_CONTROL = "DIRECT_CONTROL"


class AuthorizationStatus(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidationStatus(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    NOT_REACHED = "NOT_REACHED"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PreauditStatus(StrEnum):
    COMMITTED = "COMMITTED"
    ATTEMPTED_FAILED = "ATTEMPTED_FAILED"
    NOT_REACHED = "NOT_REACHED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SpawnStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    ATTEMPTED_FAILED_CONFIRMED_NO_CHILD = "ATTEMPTED_FAILED_CONFIRMED_NO_CHILD"
    ATTEMPTED_INDETERMINATE = "ATTEMPTED_INDETERMINATE"
    NOT_REACHED = "NOT_REACHED"


class ChildCreationStatus(StrEnum):
    CREATED = "CREATED"
    NOT_CREATED = "NOT_CREATED"
    INDETERMINATE = "INDETERMINATE"


class ChildObservationStatus(StrEnum):
    COMPLETED = "COMPLETED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INDETERMINATE = "INDETERMINATE"


class CaptureStatus(StrEnum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    NOT_REACHED = "NOT_REACHED"
    INDETERMINATE = "INDETERMINATE"


class ChildOutcome(StrEnum):
    EXIT_0 = "EXIT_0"
    EXIT_NONZERO = "EXIT_NONZERO"
    SIGNAL = "SIGNAL"
    TIMEOUT = "TIMEOUT"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INDETERMINATE = "INDETERMINATE"


class TerminalAuditStatus(StrEnum):
    COMMITTED = "COMMITTED"
    ATTEMPTED_FAILED = "ATTEMPTED_FAILED"
    NOT_EMITTED = "NOT_EMITTED"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EffectStatus(StrEnum):
    NONE = "NONE"
    CONFIRMED = "CONFIRMED"
    INDETERMINATE = "INDETERMINATE"


class TerminalClass(StrEnum):
    POLICY_DENY_NOT_SPAWNED = "POLICY_DENY_NOT_SPAWNED"
    FAIL_CLOSED_NOT_SPAWNED = "FAIL_CLOSED_NOT_SPAWNED"
    VALIDATION_REJECT_NOT_SPAWNED = "VALIDATION_REJECT_NOT_SPAWNED"
    SPAWN_ERROR_NOT_CREATED = "SPAWN_ERROR_NOT_CREATED"
    PROCESS_EXIT_0 = "PROCESS_EXIT_0"
    PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE = "PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE"
    PROCESS_TIMEOUT_EFFECT_POSSIBLE = "PROCESS_TIMEOUT_EFFECT_POSSIBLE"
    PROCESS_SIGNALED_EFFECT_POSSIBLE = "PROCESS_SIGNALED_EFFECT_POSSIBLE"
    FAIL_INDETERMINATE_EXECUTION_POSSIBLE = "FAIL_INDETERMINATE_EXECUTION_POSSIBLE"
    DIRECT_CONTROL_OBSERVED = "DIRECT_CONTROL_OBSERVED"


class LifecyclePath(StrEnum):
    ADAPTER_DENY = "ADAPTER_DENY"
    ADAPTER_AUTHORIZATION_FAILURE = "ADAPTER_AUTHORIZATION_FAILURE"
    ADAPTER_EXEC_VALIDATION_REJECT = "ADAPTER_EXEC_VALIDATION_REJECT"
    ADAPTER_CWD_VALIDATION_REJECT = "ADAPTER_CWD_VALIDATION_REJECT"
    ADAPTER_PREAUDIT_FAILURE = "ADAPTER_PREAUDIT_FAILURE"
    ADAPTER_SPAWN_FAILURE_CONFIRMED_NO_CHILD = (
        "ADAPTER_SPAWN_FAILURE_CONFIRMED_NO_CHILD"
    )
    ADAPTER_SPAWN_INDETERMINATE = "ADAPTER_SPAWN_INDETERMINATE"
    ADAPTER_CHILD_EXIT_0 = "ADAPTER_CHILD_EXIT_0"
    ADAPTER_CHILD_EXIT_NONZERO = "ADAPTER_CHILD_EXIT_NONZERO"
    ADAPTER_CHILD_SIGNAL = "ADAPTER_CHILD_SIGNAL"
    ADAPTER_CHILD_TIMEOUT = "ADAPTER_CHILD_TIMEOUT"
    ADAPTER_CAPTURE_FAILURE = "ADAPTER_CAPTURE_FAILURE"
    ADAPTER_TERMINAL_AUDIT_FAILURE = "ADAPTER_TERMINAL_AUDIT_FAILURE"
    DIRECT_CONTROL_SUCCESS = "DIRECT_CONTROL_SUCCESS"


class ScoreStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EXERCISED = "NOT_EXERCISED"


class PopulationStatus(StrEnum):
    PLANNED = "PLANNED"
    MATERIALIZED = "MATERIALIZED"
    FROZEN = "FROZEN"


@dataclass(frozen=True, slots=True)
class LifecycleState:
    route: Route
    path: LifecyclePath
    adapter_used: bool
    authorization: AuthorizationStatus
    exec_validation: ValidationStatus
    cwd_validation: ValidationStatus
    preaudit: PreauditStatus
    spawn: SpawnStatus
    child_creation: ChildCreationStatus
    child_observation: ChildObservationStatus
    capture: CaptureStatus
    child_outcome: ChildOutcome
    terminal_class: TerminalClass
    terminal_audit: TerminalAuditStatus
    effect: EffectStatus
    failure_seam: str


@dataclass(frozen=True, slots=True)
class CorpusPopulation:
    status: PopulationStatus
    planned_count: int | None
    materialized_instance_ids: tuple[str, ...]
    frozen_corpus_count: int | None


def score_positive_denominator(passed: int, denominator: int) -> ScoreStatus:
    """Apply v2 nonvacuity semantics and reject nonsensical cardinalities."""
    if passed < 0 or denominator < 0 or passed > denominator:
        raise LifecycleModelError("metric counts must satisfy 0 <= passed <= denominator")
    if denominator == 0:
        return ScoreStatus.NOT_EXERCISED
    return ScoreStatus.PASS if passed == denominator else ScoreStatus.FAIL


def validate_population(population: CorpusPopulation) -> None:
    ids = population.materialized_instance_ids
    if len(ids) != len(set(ids)):
        raise LifecycleModelError("corpus population contains duplicate instance ids")
    if population.planned_count is not None and population.planned_count <= 0:
        raise LifecycleModelError("a planned count must be positive or unset")
    if population.status is PopulationStatus.PLANNED:
        if ids or population.frozen_corpus_count is not None:
            raise LifecycleModelError("PLANNED population cannot claim materialized or frozen data")
        return
    if population.status is PopulationStatus.MATERIALIZED:
        if not ids or population.frozen_corpus_count is not None:
            raise LifecycleModelError(
                "MATERIALIZED population requires ids and cannot claim a frozen count"
            )
        if population.planned_count is not None and len(ids) != population.planned_count:
            raise LifecycleModelError("materialized count differs from the exact planned count")
        return
    if population.status is PopulationStatus.FROZEN:
        if not ids or population.frozen_corpus_count != len(ids):
            raise LifecycleModelError("FROZEN population requires a positive exact matching count")
        if population.planned_count is not None and len(ids) != population.planned_count:
            raise LifecycleModelError("frozen count differs from the exact planned count")
        return
    raise LifecycleModelError("unknown corpus population status")


def validate_family_membership(
    family_definitions: Mapping[str, Mapping[str, Any]],
    memberships: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Join disposable or future instances without mutating family definitions."""
    counts = dict.fromkeys(family_definitions, 0)
    seen: set[str] = set()
    for membership in memberships:
        scenario_id = membership.get("scenario_id")
        family_id = membership.get("primary_family")
        route = membership.get("route")
        tags = membership.get("secondary_tags")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise LifecycleModelError("membership requires a non-empty scenario_id")
        if scenario_id in seen:
            raise LifecycleModelError(f"duplicate membership id: {scenario_id}")
        seen.add(scenario_id)
        if not isinstance(family_id, str) or family_id not in family_definitions:
            raise LifecycleModelError(f"unknown primary family: {family_id}")
        definition = family_definitions[family_id]
        if route != definition.get("route"):
            raise LifecycleModelError(f"route mismatch for family {family_id}")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise LifecycleModelError("secondary_tags must be an array of strings")
        counts[family_id] += 1
    return counts


def validate_repeat_metadata(memberships: Sequence[Mapping[str, Any]]) -> None:
    groups: dict[str, list[str]] = {}
    for membership in memberships:
        group = membership.get("repeat_group_id")
        if group is None:
            continue
        if not isinstance(group, str) or not group:
            raise LifecycleModelError("repeat_group_id must be null or a non-empty string")
        scenario_id = membership.get("scenario_id")
        if not isinstance(scenario_id, str):
            raise LifecycleModelError("repeat membership requires scenario_id")
        groups.setdefault(group, []).append(scenario_id)
    for group, scenario_ids in groups.items():
        if len(scenario_ids) < 2:
            raise LifecycleModelError(f"repeat group {group} has fewer than two instances")


def validate_lifecycle(state: LifecycleState) -> None:
    """Validate a route-aware lifecycle state against v2 partial-order semantics."""
    if state.route is Route.ADAPTER:
        if not state.adapter_used:
            raise LifecycleModelError("ADAPTER lifecycle requires adapter_used=true")
        _validate_adapter_lifecycle(state)
        return
    if state.route is Route.DIRECT_CONTROL:
        if state.adapter_used:
            raise LifecycleModelError("DIRECT_CONTROL must not use ProcessAdapter")
        _validate_direct_lifecycle(state)
        return
    raise LifecycleModelError("unknown route")


def _validate_adapter_lifecycle(state: LifecycleState) -> None:
    adapter_na = (
        state.authorization is AuthorizationStatus.NOT_APPLICABLE
        or state.exec_validation is ValidationStatus.NOT_APPLICABLE
        or state.cwd_validation is ValidationStatus.NOT_APPLICABLE
        or state.preaudit is PreauditStatus.NOT_APPLICABLE
        or state.terminal_audit is TerminalAuditStatus.NOT_APPLICABLE
    )
    if adapter_na:
        raise LifecycleModelError("ADAPTER lifecycle cannot mark adapter phases NOT_APPLICABLE")

    if (
        state.child_creation is ChildCreationStatus.CREATED
        and state.spawn is not SpawnStatus.SUCCEEDED
    ):
        raise LifecycleModelError("child creation requires successful spawn")
    if (
        state.child_observation is ChildObservationStatus.COMPLETED
        and state.child_creation is not ChildCreationStatus.CREATED
    ):
        raise LifecycleModelError("child completion requires child creation")
    if state.spawn is not SpawnStatus.NOT_REACHED:
        prerequisites = (
            state.authorization is AuthorizationStatus.ALLOW,
            state.exec_validation is ValidationStatus.PASS,
            state.cwd_validation is ValidationStatus.PASS,
            state.preaudit is PreauditStatus.COMMITTED,
        )
        if not all(prerequisites):
            raise LifecycleModelError(
                "adapter spawn attempt lacks required successful prerequisites"
            )

    if state.path is LifecyclePath.ADAPTER_DENY:
        _require(
            state,
            authorization=AuthorizationStatus.DENY,
            exec_validation=ValidationStatus.NOT_REACHED,
            cwd_validation=ValidationStatus.NOT_REACHED,
            preaudit=PreauditStatus.NOT_REACHED,
            spawn=SpawnStatus.NOT_REACHED,
            child_creation=ChildCreationStatus.NOT_CREATED,
            child_observation=ChildObservationStatus.NOT_AVAILABLE,
            capture=CaptureStatus.NOT_REACHED,
            child_outcome=ChildOutcome.NOT_AVAILABLE,
            terminal_class=TerminalClass.POLICY_DENY_NOT_SPAWNED,
            terminal_audit=TerminalAuditStatus.NOT_EMITTED,
            effect=EffectStatus.NONE,
        )
    elif state.path is LifecyclePath.ADAPTER_AUTHORIZATION_FAILURE:
        _require(
            state,
            authorization=AuthorizationStatus.FAILED,
            exec_validation=ValidationStatus.NOT_REACHED,
            cwd_validation=ValidationStatus.NOT_REACHED,
            preaudit=PreauditStatus.NOT_REACHED,
            spawn=SpawnStatus.NOT_REACHED,
            child_creation=ChildCreationStatus.NOT_CREATED,
            child_observation=ChildObservationStatus.NOT_AVAILABLE,
            capture=CaptureStatus.NOT_REACHED,
            child_outcome=ChildOutcome.NOT_AVAILABLE,
            terminal_class=TerminalClass.FAIL_CLOSED_NOT_SPAWNED,
            terminal_audit=TerminalAuditStatus.NOT_EMITTED,
            effect=EffectStatus.NONE,
        )
    elif state.path is LifecyclePath.ADAPTER_EXEC_VALIDATION_REJECT:
        _require_validation_reject(state, exec_rejected=True)
    elif state.path is LifecyclePath.ADAPTER_CWD_VALIDATION_REJECT:
        _require_validation_reject(state, exec_rejected=False)
    elif state.path is LifecyclePath.ADAPTER_PREAUDIT_FAILURE:
        _require(
            state,
            authorization=AuthorizationStatus.ALLOW,
            exec_validation=ValidationStatus.PASS,
            cwd_validation=ValidationStatus.PASS,
            preaudit=PreauditStatus.ATTEMPTED_FAILED,
            spawn=SpawnStatus.NOT_REACHED,
            child_creation=ChildCreationStatus.NOT_CREATED,
            child_observation=ChildObservationStatus.NOT_AVAILABLE,
            capture=CaptureStatus.NOT_REACHED,
            child_outcome=ChildOutcome.NOT_AVAILABLE,
            terminal_class=TerminalClass.FAIL_CLOSED_NOT_SPAWNED,
            terminal_audit=TerminalAuditStatus.NOT_EMITTED,
            effect=EffectStatus.NONE,
        )
    elif state.path is LifecyclePath.ADAPTER_SPAWN_FAILURE_CONFIRMED_NO_CHILD:
        _require_spawn_prerequisites(state)
        _require(
            state,
            spawn=SpawnStatus.ATTEMPTED_FAILED_CONFIRMED_NO_CHILD,
            child_creation=ChildCreationStatus.NOT_CREATED,
            child_observation=ChildObservationStatus.NOT_AVAILABLE,
            capture=CaptureStatus.NOT_REACHED,
            child_outcome=ChildOutcome.NOT_AVAILABLE,
            terminal_class=TerminalClass.SPAWN_ERROR_NOT_CREATED,
            terminal_audit=TerminalAuditStatus.COMMITTED,
            effect=EffectStatus.NONE,
        )
    elif state.path is LifecyclePath.ADAPTER_SPAWN_INDETERMINATE:
        _require_spawn_prerequisites(state)
        _require(
            state,
            spawn=SpawnStatus.ATTEMPTED_INDETERMINATE,
            child_creation=ChildCreationStatus.INDETERMINATE,
            child_observation=ChildObservationStatus.INDETERMINATE,
            capture=CaptureStatus.INDETERMINATE,
            child_outcome=ChildOutcome.INDETERMINATE,
            terminal_class=TerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE,
            terminal_audit=TerminalAuditStatus.COMMITTED,
            effect=EffectStatus.INDETERMINATE,
        )
    elif state.path in {
        LifecyclePath.ADAPTER_CHILD_EXIT_0,
        LifecyclePath.ADAPTER_CHILD_EXIT_NONZERO,
        LifecyclePath.ADAPTER_CHILD_SIGNAL,
        LifecyclePath.ADAPTER_CHILD_TIMEOUT,
    }:
        _require_completed_child(state)
        expected = {
            LifecyclePath.ADAPTER_CHILD_EXIT_0: (
                ChildOutcome.EXIT_0,
                TerminalClass.PROCESS_EXIT_0,
            ),
            LifecyclePath.ADAPTER_CHILD_EXIT_NONZERO: (
                ChildOutcome.EXIT_NONZERO,
                TerminalClass.PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE,
            ),
            LifecyclePath.ADAPTER_CHILD_SIGNAL: (
                ChildOutcome.SIGNAL,
                TerminalClass.PROCESS_SIGNALED_EFFECT_POSSIBLE,
            ),
            LifecyclePath.ADAPTER_CHILD_TIMEOUT: (
                ChildOutcome.TIMEOUT,
                TerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE,
            ),
        }[state.path]
        _require(
            state,
            capture=CaptureStatus.COMPLETE,
            child_outcome=expected[0],
            terminal_class=expected[1],
            terminal_audit=TerminalAuditStatus.COMMITTED,
            effect=EffectStatus.CONFIRMED,
        )
    elif state.path is LifecyclePath.ADAPTER_CAPTURE_FAILURE:
        _require_spawn_prerequisites(state)
        _require(
            state,
            spawn=SpawnStatus.SUCCEEDED,
            child_creation=ChildCreationStatus.CREATED,
            child_observation=ChildObservationStatus.COMPLETED,
            capture=CaptureStatus.FAILED,
            terminal_class=TerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE,
            terminal_audit=TerminalAuditStatus.COMMITTED,
            effect=EffectStatus.CONFIRMED,
        )
        if state.child_outcome is ChildOutcome.NOT_AVAILABLE:
            raise LifecycleModelError("post-child capture failure must retain a child outcome")
    elif state.path is LifecyclePath.ADAPTER_TERMINAL_AUDIT_FAILURE:
        _require_spawn_prerequisites(state)
        _require(
            state,
            spawn=SpawnStatus.SUCCEEDED,
            child_creation=ChildCreationStatus.CREATED,
            child_observation=ChildObservationStatus.COMPLETED,
            capture=CaptureStatus.COMPLETE,
            terminal_class=TerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE,
            terminal_audit=TerminalAuditStatus.ATTEMPTED_FAILED,
            effect=EffectStatus.CONFIRMED,
        )
        if state.child_outcome not in {
            ChildOutcome.EXIT_0,
            ChildOutcome.EXIT_NONZERO,
            ChildOutcome.SIGNAL,
            ChildOutcome.TIMEOUT,
        }:
            raise LifecycleModelError("terminal-audit failure requires an observed child outcome")
    else:
        raise LifecycleModelError(f"invalid adapter lifecycle path: {state.path}")


def _validate_direct_lifecycle(state: LifecycleState) -> None:
    if state.path is not LifecyclePath.DIRECT_CONTROL_SUCCESS:
        raise LifecycleModelError(
            "DIRECT_CONTROL currently registers only its success control path"
        )
    _require(
        state,
        authorization=AuthorizationStatus.NOT_APPLICABLE,
        exec_validation=ValidationStatus.NOT_APPLICABLE,
        cwd_validation=ValidationStatus.NOT_APPLICABLE,
        preaudit=PreauditStatus.NOT_APPLICABLE,
        spawn=SpawnStatus.SUCCEEDED,
        child_creation=ChildCreationStatus.CREATED,
        child_observation=ChildObservationStatus.COMPLETED,
        capture=CaptureStatus.COMPLETE,
        child_outcome=ChildOutcome.EXIT_0,
        terminal_class=TerminalClass.DIRECT_CONTROL_OBSERVED,
        terminal_audit=TerminalAuditStatus.NOT_APPLICABLE,
        effect=EffectStatus.CONFIRMED,
    )


def _require_validation_reject(state: LifecycleState, *, exec_rejected: bool) -> None:
    _require(
        state,
        authorization=AuthorizationStatus.ALLOW,
        exec_validation=(ValidationStatus.REJECT if exec_rejected else ValidationStatus.PASS),
        cwd_validation=(ValidationStatus.NOT_REACHED if exec_rejected else ValidationStatus.REJECT),
        preaudit=PreauditStatus.NOT_REACHED,
        spawn=SpawnStatus.NOT_REACHED,
        child_creation=ChildCreationStatus.NOT_CREATED,
        child_observation=ChildObservationStatus.NOT_AVAILABLE,
        capture=CaptureStatus.NOT_REACHED,
        child_outcome=ChildOutcome.NOT_AVAILABLE,
        terminal_class=TerminalClass.VALIDATION_REJECT_NOT_SPAWNED,
        terminal_audit=TerminalAuditStatus.NOT_EMITTED,
        effect=EffectStatus.NONE,
    )


def _require_spawn_prerequisites(state: LifecycleState) -> None:
    _require(
        state,
        authorization=AuthorizationStatus.ALLOW,
        exec_validation=ValidationStatus.PASS,
        cwd_validation=ValidationStatus.PASS,
        preaudit=PreauditStatus.COMMITTED,
    )


def _require_completed_child(state: LifecycleState) -> None:
    _require_spawn_prerequisites(state)
    _require(
        state,
        spawn=SpawnStatus.SUCCEEDED,
        child_creation=ChildCreationStatus.CREATED,
        child_observation=ChildObservationStatus.COMPLETED,
    )


def _require(state: LifecycleState, **expected: object) -> None:
    for field_name, expected_value in expected.items():
        observed = getattr(state, field_name)
        if observed != expected_value:
            raise LifecycleModelError(
                f"{state.path}: {field_name} expected {expected_value}, observed {observed}"
            )


def derive_lifecycle(raw: Mapping[str, Any]) -> LifecycleState:
    """Derive a v2 state from route-specific raw observations, never labels."""
    route = Route(str(raw["route"]))
    if route is Route.DIRECT_CONTROL:
        state = _derive_direct(raw)
    else:
        state = _derive_adapter(raw)
    validate_lifecycle(state)
    return state


def _derive_direct(raw: Mapping[str, Any]) -> LifecycleState:
    prohibited = (
        "decision",
        "exec_validation",
        "cwd_validation",
        "preaudit_attempted",
        "preaudit_committed",
        "terminal_audit_attempted",
        "terminal_audit_committed",
    )
    if any(raw.get(field) is not None for field in prohibited):
        raise LifecycleModelError("DIRECT_CONTROL raw record fabricates adapter observations")
    if raw.get("adapter_used") is not False:
        raise LifecycleModelError("DIRECT_CONTROL raw record must prove adapter_used=false")
    if not all(
        raw.get(field) is True
        for field in ("direct_spawn_attempted", "child_created", "child_completed")
    ):
        raise LifecycleModelError("DIRECT_CONTROL success requires attempted completed child")
    return LifecycleState(
        route=Route.DIRECT_CONTROL,
        path=LifecyclePath.DIRECT_CONTROL_SUCCESS,
        adapter_used=False,
        authorization=AuthorizationStatus.NOT_APPLICABLE,
        exec_validation=ValidationStatus.NOT_APPLICABLE,
        cwd_validation=ValidationStatus.NOT_APPLICABLE,
        preaudit=PreauditStatus.NOT_APPLICABLE,
        spawn=SpawnStatus.SUCCEEDED,
        child_creation=ChildCreationStatus.CREATED,
        child_observation=ChildObservationStatus.COMPLETED,
        capture=CaptureStatus(str(raw["capture_status"])),
        child_outcome=ChildOutcome(str(raw["child_outcome"])),
        terminal_class=TerminalClass(str(raw["terminal_class"])),
        terminal_audit=TerminalAuditStatus.NOT_APPLICABLE,
        effect=EffectStatus(str(raw["effect_status"])),
        failure_seam=str(raw.get("failure_seam", "NONE")),
    )


def _derive_adapter(raw: Mapping[str, Any]) -> LifecycleState:
    if raw.get("adapter_used") is not True:
        raise LifecycleModelError("ADAPTER raw record must prove adapter_used=true")
    authorization = AuthorizationStatus(str(raw["decision"]))
    exec_validation = _validation_status(raw.get("exec_validation"))
    cwd_validation = _validation_status(raw.get("cwd_validation"))
    preaudit = _preaudit_status(raw)
    spawn = _spawn_status(raw)
    child_creation = _child_creation(raw.get("child_created"))
    child_observation = _child_observation(raw)
    capture = CaptureStatus(str(raw["capture_status"]))
    child_outcome = ChildOutcome(str(raw["child_outcome"]))
    terminal_audit = _terminal_audit_status(raw)
    terminal_class = TerminalClass(str(raw["terminal_class"]))
    path = _derive_adapter_path(
        authorization,
        exec_validation,
        cwd_validation,
        preaudit,
        spawn,
        capture,
        child_outcome,
        terminal_audit,
    )
    return LifecycleState(
        route=Route.ADAPTER,
        path=path,
        adapter_used=True,
        authorization=authorization,
        exec_validation=exec_validation,
        cwd_validation=cwd_validation,
        preaudit=preaudit,
        spawn=spawn,
        child_creation=child_creation,
        child_observation=child_observation,
        capture=capture,
        child_outcome=child_outcome,
        terminal_class=terminal_class,
        terminal_audit=terminal_audit,
        effect=EffectStatus(str(raw["effect_status"])),
        failure_seam=str(raw.get("failure_seam", "NONE")),
    )


def _validation_status(value: object) -> ValidationStatus:
    return {
        "SUCCEEDED": ValidationStatus.PASS,
        "REJECTED": ValidationStatus.REJECT,
        "NOT_ATTEMPTED": ValidationStatus.NOT_REACHED,
        "INDETERMINATE": ValidationStatus.INDETERMINATE,
    }[str(value)]


def _preaudit_status(raw: Mapping[str, Any]) -> PreauditStatus:
    attempted = raw.get("preaudit_attempted")
    committed = raw.get("preaudit_committed")
    if attempted is False and committed is False:
        return PreauditStatus.NOT_REACHED
    if attempted is True and committed is True:
        return PreauditStatus.COMMITTED
    if attempted is True and committed is False:
        return PreauditStatus.ATTEMPTED_FAILED
    raise LifecycleModelError("invalid preaudit attempted/committed observation")


def _spawn_status(raw: Mapping[str, Any]) -> SpawnStatus:
    if raw.get("spawn_attempted") is False:
        return SpawnStatus.NOT_REACHED
    if raw.get("spawn_attempted") is not True:
        raise LifecycleModelError("spawn_attempted must be boolean")
    child_created = raw.get("child_created")
    if child_created is True:
        return SpawnStatus.SUCCEEDED
    if child_created is False:
        return SpawnStatus.ATTEMPTED_FAILED_CONFIRMED_NO_CHILD
    if child_created is None:
        return SpawnStatus.ATTEMPTED_INDETERMINATE
    raise LifecycleModelError("child_created must be boolean or null")


def _child_creation(value: object) -> ChildCreationStatus:
    if value is True:
        return ChildCreationStatus.CREATED
    if value is False:
        return ChildCreationStatus.NOT_CREATED
    if value is None:
        return ChildCreationStatus.INDETERMINATE
    raise LifecycleModelError("child_created must be boolean or null")


def _child_observation(raw: Mapping[str, Any]) -> ChildObservationStatus:
    completed = raw.get("child_completed")
    if completed is True:
        return ChildObservationStatus.COMPLETED
    if completed is False:
        return ChildObservationStatus.NOT_AVAILABLE
    if completed is None:
        return ChildObservationStatus.INDETERMINATE
    raise LifecycleModelError("child_completed must be boolean or null")


def _terminal_audit_status(raw: Mapping[str, Any]) -> TerminalAuditStatus:
    attempted = raw.get("terminal_audit_attempted")
    committed = raw.get("terminal_audit_committed")
    if attempted is False and committed is False:
        return TerminalAuditStatus.NOT_EMITTED
    if attempted is True and committed is True:
        return TerminalAuditStatus.COMMITTED
    if attempted is True and committed is False:
        return TerminalAuditStatus.ATTEMPTED_FAILED
    if attempted is None and committed is None:
        return TerminalAuditStatus.INDETERMINATE
    raise LifecycleModelError("invalid terminal-audit attempted/committed observation")


def _derive_adapter_path(
    authorization: AuthorizationStatus,
    exec_validation: ValidationStatus,
    cwd_validation: ValidationStatus,
    preaudit: PreauditStatus,
    spawn: SpawnStatus,
    capture: CaptureStatus,
    child_outcome: ChildOutcome,
    terminal_audit: TerminalAuditStatus,
) -> LifecyclePath:
    if authorization is AuthorizationStatus.DENY:
        return LifecyclePath.ADAPTER_DENY
    if authorization is AuthorizationStatus.FAILED:
        return LifecyclePath.ADAPTER_AUTHORIZATION_FAILURE
    if exec_validation is ValidationStatus.REJECT:
        return LifecyclePath.ADAPTER_EXEC_VALIDATION_REJECT
    if cwd_validation is ValidationStatus.REJECT:
        return LifecyclePath.ADAPTER_CWD_VALIDATION_REJECT
    if preaudit is PreauditStatus.ATTEMPTED_FAILED:
        return LifecyclePath.ADAPTER_PREAUDIT_FAILURE
    if spawn is SpawnStatus.ATTEMPTED_FAILED_CONFIRMED_NO_CHILD:
        return LifecyclePath.ADAPTER_SPAWN_FAILURE_CONFIRMED_NO_CHILD
    if spawn is SpawnStatus.ATTEMPTED_INDETERMINATE:
        return LifecyclePath.ADAPTER_SPAWN_INDETERMINATE
    if terminal_audit is TerminalAuditStatus.ATTEMPTED_FAILED:
        return LifecyclePath.ADAPTER_TERMINAL_AUDIT_FAILURE
    if capture is CaptureStatus.FAILED:
        return LifecyclePath.ADAPTER_CAPTURE_FAILURE
    return {
        ChildOutcome.EXIT_0: LifecyclePath.ADAPTER_CHILD_EXIT_0,
        ChildOutcome.EXIT_NONZERO: LifecyclePath.ADAPTER_CHILD_EXIT_NONZERO,
        ChildOutcome.SIGNAL: LifecyclePath.ADAPTER_CHILD_SIGNAL,
        ChildOutcome.TIMEOUT: LifecyclePath.ADAPTER_CHILD_TIMEOUT,
    }.get(child_outcome) or _raise_unclassifiable()


def _raise_unclassifiable() -> LifecyclePath:
    raise LifecycleModelError("raw adapter observation has no registered lifecycle path")
