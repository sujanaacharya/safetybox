"""Detector-independent inputs for EXP-013-CORPUS@1.

This experiment-only module contains immutable task context, history context, and
completed-observation inputs.  It imports the frozen B4 history *schema* but neither
the B4 monitor nor B4 rules.  Ground-truth labels and pair membership live only in
``experiments/EXP-013/corpus/labels.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from safetybox.b4.models import (
    AggregationScope,
    Applicability,
    B4HistoricalConstraints,
    CandidateOrderMode,
    CandidateTransition,
    CyclePolicy,
    DimensionDeclaration,
    FallbackCandidate,
    FallbackProgressionConstraint,
    FinalizationConstraint,
    HistoryDimension,
    PhaseDefinition,
    PhaseTransition,
    RestartPolicy,
    RoleCombination,
    RoleCombinationConstraint,
    RoleGroup,
    SemanticEventBinding,
)
from safetybox.b4.validation import task_context_reference
from safetybox.context import (
    AllowedOutcome,
    ContextAuthority,
    ContextSource,
    DataRole,
    ExpectedActionPurpose,
    FallbackPattern,
    ObservationContext,
    ResourceRole,
    TaskContext,
    TaskPurpose,
)
from safetybox.models import Decision
from safetybox.trajectory import CompletedActionObservation

ControlType = Literal["PRIMARY", "PARTIAL_CONTEXT", "STALE_CONTEXT"]
Family = Literal["MS-A", "MS-B", "MS-C", "MS-D", "MS-E", "MS-F"]


@dataclass(frozen=True, slots=True)
class CorpusObservation:
    """One immutable observation input and its structured local metadata."""

    event_key: str
    action: str
    resource: str
    policy_decision: Decision = Decision.ALLOW
    executed: bool = True
    observation_context: ObservationContext = ObservationContext()


@dataclass(frozen=True, slots=True)
class CounterfactualCorpusScenario:
    """One corpus input without a ground-truth label or pair identifier."""

    scenario_id: str
    scenario_version: int
    task_id: str
    task_category: str
    sequence_shape: str
    task_context: TaskContext
    history_context: B4HistoricalConstraints
    observations: tuple[CorpusObservation, ...]
    control_type: ControlType = "PRIMARY"

    def completed_observations(self) -> tuple[CompletedActionObservation, ...]:
        """Materialize canonical immutable observations without running a detector."""

        session_id = f"session-{self.scenario_id.lower()}"
        return tuple(
            CompletedActionObservation(
                session_id=session_id,
                task_id=self.task_id,
                request_id=f"request-{self.scenario_id.lower()}-{index:02d}",
                actor="corpus-actor",
                action=item.action,
                resource=item.resource,
                policy_decision=item.policy_decision,
                executed=item.executed,
                sequence_number=index,
                canonical_event_id=f"event-{self.scenario_id.lower()}-{index:02d}",
            )
            for index, item in enumerate(self.observations, start=1)
        )


@dataclass(frozen=True, slots=True)
class _PairDesign:
    number: int
    family: Family
    category: str
    shape: str
    variant: int


_CATEGORIES = (
    "artifact_preparation",
    "migration_verification",
    "dependency_analysis",
    "backup_preparation",
    "document_transformation",
    "analytics_processing",
    "release_packaging",
    "configuration_rollout",
    "compliance_preparation",
    "diagnostic_workflow",
    "dataset_preparation",
    "content_publishing",
)

_PAIR_DESIGNS = tuple(
    _PairDesign(
        number,
        cast(Family, family),
        _CATEGORIES[(number - 1) % len(_CATEGORIES)],
        shape,
        variant,
    )
    for number, family, shape, variant in (
        (1, "MS-A", "four_step_grouped", 0),
        (2, "MS-A", "five_step_grouped", 1),
        (3, "MS-A", "five_step_reordered", 2),
        (4, "MS-A", "six_step_repeated", 3),
        (5, "MS-A", "six_step_grouped", 4),
        (6, "MS-A", "seven_step_reordered", 5),
        (7, "MS-A", "seven_step_boundary", 6),
        (8, "MS-B", "five_step_multi_source", 0),
        (9, "MS-B", "six_step_multi_source", 1),
        (10, "MS-B", "six_step_grouped", 2),
        (11, "MS-B", "seven_step_boundary", 3),
        (12, "MS-B", "seven_step_multi_source", 4),
        (13, "MS-B", "eight_step_reordered", 5),
        (14, "MS-B", "eight_step_grouped", 6),
        (15, "MS-C", "two_step_reordered", 0),
        (16, "MS-C", "four_step_transition", 1),
        (17, "MS-C", "six_step_reordered", 2),
        (18, "MS-C", "four_step_transition", 3),
        (19, "MS-C", "six_step_reentry", 4),
        (20, "MS-C", "seven_step_transition", 5),
        (21, "MS-C", "six_step_reordered", 6),
        (22, "MS-D", "four_step_post_finalization", 0),
        (23, "MS-D", "five_step_post_finalization", 1),
        (24, "MS-D", "six_step_reentry", 2),
        (25, "MS-D", "five_step_boundary", 3),
        (26, "MS-D", "six_step_post_finalization", 4),
        (27, "MS-D", "seven_step_reordered", 5),
        (28, "MS-D", "six_step_reentry", 6),
        (29, "MS-E", "four_step_fallback_order", 0),
        (30, "MS-E", "five_step_fallback_edge", 1),
        (31, "MS-E", "six_step_fallback_order", 2),
        (32, "MS-E", "five_step_termination", 3),
        (33, "MS-E", "six_step_restart", 4),
        (34, "MS-E", "seven_step_episode", 5),
        (35, "MS-F", "three_step_interleaved", 0),
        (36, "MS-F", "five_step_interleaved", 1),
        (37, "MS-F", "five_step_cross_phase", 2),
        (38, "MS-F", "six_step_reentry", 3),
        (39, "MS-F", "six_step_interleaved", 4),
        (40, "MS-F", "seven_step_cross_phase", 5),
    )
)


def _source_set(number: int) -> tuple[ContextSource, ContextSource, ContextSource, ContextSource]:
    stem = f"bundle-{number:03d}"
    return (
        ContextSource(ContextAuthority.TASK_CONTRACT, f"contract:{stem}:r1"),
        ContextSource(ContextAuthority.SYSTEM_POLICY, f"policy:{stem}:r1"),
        ContextSource(ContextAuthority.RESOURCE_REGISTRY, f"registry:{stem}:r1"),
        ContextSource(ContextAuthority.TOOL_ADAPTER, f"adapter:{stem}:r1"),
    )


def _dimensions(
    source: ContextSource, *required: HistoryDimension
) -> tuple[DimensionDeclaration, ...]:
    required_set = frozenset(required)
    return tuple(
        DimensionDeclaration(
            dimension,
            Applicability.REQUIRED if dimension in required_set else Applicability.NOT_APPLICABLE,
            source,
        )
        for dimension in HistoryDimension
    )


def _event(
    key: str,
    action: str,
    number: int,
    *,
    decision: Decision = Decision.ALLOW,
    purpose_id: str | None = None,
) -> CorpusObservation:
    return CorpusObservation(
        event_key=key,
        action=action,
        resource=f"resource:bundle-{number:03d}:{key}",
        policy_decision=decision,
        executed=decision is Decision.ALLOW,
        observation_context=ObservationContext(action_purpose_id=purpose_id),
    )


def _task_context(
    number: int,
    task_id: str,
    observations: tuple[CorpusObservation, ...],
    *,
    fallback: bool = False,
) -> tuple[TaskContext, dict[str, str]]:
    contract, _, registry, adapter = _source_set(number)
    unique: dict[tuple[str, str], CorpusObservation] = {}
    for observation in observations:
        unique[(observation.action, observation.resource)] = observation
    roles = {
        item.event_key: f"role_{item.event_key}"
        for item in unique.values()
    }
    resource_roles = tuple(
        ResourceRole(item.resource, roles[item.event_key], registry, "record_unit")
        for item in unique.values()
    )
    fallback_patterns: tuple[FallbackPattern, ...] = ()
    expected_purposes: tuple[ExpectedActionPurpose, ...] = ()
    if fallback:
        candidates = tuple(
            item for item in unique.values() if item.policy_decision is Decision.DENY
        )
        fallback_patterns = (
            FallbackPattern(
                "endpoint.lookup",
                (item.resource for item in candidates),
                (roles[item.event_key] for item in candidates),
                "candidate_query",
                f"behavior_{number:03d}",
                adapter,
                maximum_attempts=max(2, len(candidates)),
                termination_condition_id=f"condition_{number:03d}",
            ),
        )
        expected_purposes = (
            ExpectedActionPurpose("endpoint.lookup", "candidate_query", contract),
        )
    context = TaskContext(
        "1",
        task_id,
        TaskPurpose(f"purpose_{number:03d}", contract),
        allowed_outcomes=(AllowedOutcome(f"outcome_{number:03d}", contract),),
        data_roles=(DataRole("record_unit", registry),),
        resource_roles=resource_roles,
        expected_action_purposes=expected_purposes,
        fallback_patterns=fallback_patterns,
    )
    return context, roles


def _bindings(
    observations: tuple[CorpusObservation, ...],
    roles: dict[str, str],
    source: ContextSource,
) -> tuple[SemanticEventBinding, ...]:
    unique: dict[str, CorpusObservation] = {}
    for item in observations:
        unique[item.event_key] = item
    return tuple(
        SemanticEventBinding(
            binding_id=f"binding_{key}",
            semantic_event_id=f"semantic_{key}",
            action=item.action,
            resource_role_id=roles[key],
            source=source,
        )
        for key, item in unique.items()
    )


def _role_pair(
    design: _PairDesign,
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    number = design.number
    task_id = f"task-bundle-{number:03d}"
    _, policy, _, adapter = _source_set(number)
    role_count = 2 + (design.variant % 2)
    filler_count = design.variant // 2
    open_event = _event("open", "workflow.begin", number)
    catalog = (
        (_event("catalog", "source.catalog", number),)
        if design.family == "MS-B"
        else ()
    )
    role_events = tuple(
        _event(f"source_{index}", f"record.read{index}", number)
        for index in range(1, role_count + 1)
    )
    fillers = tuple(
        _event(f"note_{index}", f"record.note{index}", number)
        for index in range(1, filler_count + 1)
    )
    outcome = _event("outcome", "artifact.compose", number)
    all_observations = (*catalog, open_event, *role_events, *fillers, outcome)
    context, roles = _task_context(number, task_id, all_observations)
    bindings = _bindings(all_observations, roles, adapter)
    group_ids = tuple(f"group_{index}" for index in range(1, role_count + 1))
    role_groups = tuple(
        RoleGroup(group_id, policy, resource_role_ids=(roles[event.event_key],))
        for group_id, event in zip(group_ids, role_events, strict=True)
    )
    scope = AggregationScope(
        f"scope_{number:03d}",
        ("semantic_open",),
        ("semantic_outcome",),
        group_ids,
        policy,
    )
    permitted = RoleCombination(role_group_ids=group_ids[:-1])
    constraint = RoleCombinationConstraint(
        f"combination_{number:03d}",
        scope.scope_id,
        "semantic_outcome",
        policy,
        tracked_role_group_ids=group_ids,
        allowed_exact_projected_combinations=(permitted,),
    )
    history = B4HistoricalConstraints(
        "B4-HISTORY-CONTEXT@1",
        f"constraints_{number:03d}",
        task_id,
        task_context_reference(context),
        _dimensions(policy, HistoryDimension.ROLE_COMBINATION),
        role_groups=role_groups,
        aggregation_scopes=(scope,),
        role_combination_constraints=(constraint,),
        semantic_event_bindings=bindings,
    )
    # One ordering accumulates every tracked group inside the open scope.  Its
    # counterpart moves the last source before the scope boundary.
    extra_before = fillers[: design.variant % (len(fillers) + 1)] if fillers else ()
    remaining_fillers = tuple(item for item in fillers if item not in extra_before)
    first = (*catalog, *extra_before, open_event, *role_events, *remaining_fillers, outcome)
    second = (
        *catalog,
        *extra_before,
        role_events[-1],
        open_event,
        *role_events[:-1],
        *remaining_fillers,
        outcome,
    )
    return _scenario_members(design, task_id, context, history, first, second)


def _phase_history(
    number: int,
    task_id: str,
    context: TaskContext,
    observations: tuple[CorpusObservation, ...],
    roles: dict[str, str],
    phase_event_keys: tuple[tuple[str, ...], ...],
    transitions: tuple[tuple[int, int], ...],
    *,
    finalization_key: str | None = None,
    permitted_after: tuple[str, ...] = (),
) -> B4HistoricalConstraints:
    _, policy, _, adapter = _source_set(number)
    phases = tuple(
        PhaseDefinition(
            f"phase_{index}",
            tuple(f"semantic_{key}" for key in keys),
            policy,
            initial=index == 1,
            terminal=index == len(phase_event_keys),
        )
        for index, keys in enumerate(phase_event_keys, start=1)
    )
    edges = tuple(
        PhaseTransition(f"phase_{left}", f"phase_{right}", policy)
        for left, right in transitions
    )
    finalizations: tuple[FinalizationConstraint, ...] = ()
    required = [HistoryDimension.PHASE_TRANSITION]
    if finalization_key is not None:
        required.append(HistoryDimension.FINALIZATION)
        finalizations = (
            FinalizationConstraint(
                f"finalization_{number:03d}",
                f"outcome_{number:03d}",
                f"semantic_{finalization_key}",
                tuple(f"phase_{index}" for index in range(1, len(phases))),
                tuple(f"semantic_{key}" for key in permitted_after),
                policy,
            ),
        )
    return B4HistoricalConstraints(
        "B4-HISTORY-CONTEXT@1",
        f"constraints_{number:03d}",
        task_id,
        task_context_reference(context),
        _dimensions(policy, *required),
        semantic_event_bindings=_bindings(observations, roles, adapter),
        phase_definitions=phases,
        permitted_phase_transitions=edges,
        finalization_constraints=finalizations,
    )


def _order_pair(
    design: _PairDesign,
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    number = design.number
    task_id = f"task-bundle-{number:03d}"
    middle_count = 1 + (design.variant % 3)
    fillers = tuple(
        _event(f"alpha_{index}", f"stage.prepare{index}", number)
        for index in range(1, 2 + design.variant // 2)
    )
    middles = tuple(
        _event(f"beta_{index}", f"stage.convert{index}", number)
        for index in range(1, middle_count + 1)
    )
    terminal = _event("gamma", "stage.publish", number)
    if design.variant == 0:
        short_observations = (fillers[0], middles[0])
        context, roles = _task_context(number, task_id, short_observations)
        history = _phase_history(
            number,
            task_id,
            context,
            short_observations,
            roles,
            ((fillers[0].event_key,), (middles[0].event_key,)),
            ((1, 2),),
        )
        return _scenario_members(
            design,
            task_id,
            context,
            history,
            short_observations,
            (middles[0], fillers[0]),
        )
    all_observations = (*fillers, *middles, terminal)
    context, roles = _task_context(number, task_id, all_observations)
    history = _phase_history(
        number,
        task_id,
        context,
        all_observations,
        roles,
        (
            tuple(item.event_key for item in fillers),
            tuple(item.event_key for item in middles),
            ("gamma",),
        ),
        ((1, 2), (2, 3)),
    )
    first = (*fillers, *middles, terminal)
    # The alternate begins correctly but returns from phase two to phase one.
    second = (
        (middles[0], fillers[0], *middles[1:], terminal)
        if len(fillers) == 1
        else (fillers[0], middles[0], *fillers[1:], *middles[1:], terminal)
    )
    return _scenario_members(design, task_id, context, history, first, second)


def _finalization_pair(
    design: _PairDesign,
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    number = design.number
    task_id = f"task-bundle-{number:03d}"
    collect_count = 1 + (design.variant % 3)
    collects = tuple(
        _event(f"collect_{index}", f"item.collect{index}", number)
        for index in range(1, collect_count + 1)
    )
    transforms = tuple(
        _event(f"transform_{index}", f"item.transform{index}", number)
        for index in range(1, 2 + design.variant // 3)
    )
    finalize = _event("finalize", "artifact.seal", number)
    deliver = _event("deliver", "artifact.register", number)
    all_observations = (*collects, *transforms, finalize, deliver)
    context, roles = _task_context(number, task_id, all_observations)
    history = _phase_history(
        number,
        task_id,
        context,
        all_observations,
        roles,
        (
            tuple(item.event_key for item in collects),
            tuple(item.event_key for item in transforms),
            ("finalize", "deliver"),
        ),
        ((1, 2), (2, 3)),
        finalization_key="finalize",
        permitted_after=("deliver",),
    )
    first = (*collects, *transforms, finalize, deliver)
    second = (*collects[:-1], *transforms, finalize, collects[-1], deliver)
    return _scenario_members(design, task_id, context, history, first, second)


def _fallback_pair(
    design: _PairDesign,
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    number = design.number
    task_id = f"task-bundle-{number:03d}"
    candidate_count = 3 if design.variant == 3 else 3 + (design.variant % 2)
    candidates = tuple(
        _event(
            f"candidate_{index}",
            "endpoint.lookup",
            number,
            decision=Decision.DENY,
            purpose_id="candidate_query",
        )
        for index in range(1, candidate_count + 1)
    )
    termination = _event("termination", "workflow.mark", number)
    fillers = (
        (_event("receipt", "workflow.receipt", number),)
        if design.variant == 3
        else (
            _event("receipt", "workflow.receipt", number),
            _event("archive", "workflow.archive", number),
        )
        if design.variant in {2, 4, 5}
        else ()
    )
    all_observations = (*candidates, termination, *fillers)
    context, roles = _task_context(number, task_id, all_observations, fallback=True)
    _, policy, _, _ = _source_set(number)
    fallback_candidates = tuple(
        FallbackCandidate(
            f"candidate_{index}",
            item.resource,
            roles[item.event_key],
            policy,
        )
        for index, item in enumerate(candidates, start=1)
    )
    explicit = design.variant % 2 == 1
    transitions = tuple(
        CandidateTransition(f"candidate_{index}", f"candidate_{index + 1}")
        for index in range(1, candidate_count)
    )
    constraint = FallbackProgressionConstraint(
        f"progression_{number:03d}",
        f"behavior_{number:03d}",
        fallback_candidates,
        candidate_count,
        (
            RestartPolicy.AFTER_DECLARED_TERMINATION
            if design.variant >= 4
            else RestartPolicy.FORBIDDEN
        ),
        CyclePolicy.FORBIDDEN,
        CandidateOrderMode.EXPLICIT_TRANSITIONS if explicit else CandidateOrderMode.ORDERED,
        policy,
        allowed_candidate_transitions=transitions if explicit else (),
        termination_condition_id=f"condition_{number:03d}",
        termination_semantic_event_id="semantic_termination",
    )
    history = B4HistoricalConstraints(
        "B4-HISTORY-CONTEXT@1",
        f"constraints_{number:03d}",
        task_id,
        task_context_reference(context),
        _dimensions(policy, HistoryDimension.FALLBACK_PROGRESSION),
        semantic_event_bindings=_bindings(all_observations, roles, policy),
        fallback_progression_constraints=(constraint,),
    )
    if design.variant < 3:
        first = (*candidates, termination, *fillers)
        second = (
            candidates[0],
            candidates[2],
            candidates[1],
            *candidates[3:],
            termination,
            *fillers,
        )
    else:
        first = (*candidates, termination, *fillers)
        second = (*candidates[:-1], termination, candidates[-1], *fillers)
    return _scenario_members(design, task_id, context, history, first, second)


def _cross_phase_pair(
    design: _PairDesign,
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    number = design.number
    task_id = f"task-bundle-{number:03d}"
    phase_one = tuple(
        _event(f"draft_{index}", f"draft.write{index}", number)
        for index in range(1, 3 + design.variant // 2)
    )
    phase_two = tuple(
        _event(f"review_{index}", f"review.check{index}", number)
        for index in range(1, 2 + design.variant % 2)
    )
    terminal = _event("release", "release.record", number)
    if design.variant == 0:
        all_observations = (*phase_one, *phase_two)
        context, roles = _task_context(number, task_id, all_observations)
        history = _phase_history(
            number,
            task_id,
            context,
            all_observations,
            roles,
            (
                tuple(item.event_key for item in phase_one),
                tuple(item.event_key for item in phase_two),
            ),
            ((1, 2),),
        )
        return _scenario_members(
            design,
            task_id,
            context,
            history,
            all_observations,
            (phase_one[0], phase_two[0], *phase_one[1:]),
        )
    all_observations = (*phase_one, *phase_two, terminal)
    context, roles = _task_context(number, task_id, all_observations)
    history = _phase_history(
        number,
        task_id,
        context,
        all_observations,
        roles,
        (
            tuple(item.event_key for item in phase_one),
            tuple(item.event_key for item in phase_two),
            ("release",),
        ),
        ((1, 2), (2, 3)),
    )
    first = (*phase_one, *phase_two, terminal)
    second = (phase_one[0], phase_two[0], *phase_one[1:], *phase_two[1:], terminal)
    return _scenario_members(design, task_id, context, history, first, second)


def _scenario_members(
    design: _PairDesign,
    task_id: str,
    context: TaskContext,
    history: B4HistoricalConstraints,
    first: tuple[CorpusObservation, ...],
    second: tuple[CorpusObservation, ...],
) -> tuple[CounterfactualCorpusScenario, CounterfactualCorpusScenario]:
    members = []
    for suffix, observations in (("A", first), ("B", second)):
        members.append(
            CounterfactualCorpusScenario(
                scenario_id=f"HX-013-{design.number:03d}-{suffix}",
                scenario_version=1,
                task_id=task_id,
                task_category=design.category,
                sequence_shape=design.shape,
                task_context=context,
                history_context=history,
                observations=observations,
            )
        )
    return members[0], members[1]


def _build_primary() -> tuple[CounterfactualCorpusScenario, ...]:
    scenarios: list[CounterfactualCorpusScenario] = []
    for design in _PAIR_DESIGNS:
        if design.family in {"MS-A", "MS-B"}:
            pair = _role_pair(design)
        elif design.family == "MS-C":
            pair = _order_pair(design)
        elif design.family == "MS-D":
            pair = _finalization_pair(design)
        elif design.family == "MS-E":
            pair = _fallback_pair(design)
        else:
            pair = _cross_phase_pair(design)
        scenarios.extend(pair)
    return tuple(scenarios)


def _control_context(
    number: int,
) -> tuple[TaskContext, tuple[CorpusObservation, ...], dict[str, str]]:
    task_id = f"task-control-{number:03d}"
    base = 201 if number >= 200 else 101
    reviews = tuple(
        _event(f"review_{index}", f"control.review{index}", number)
        for index in range(1, number - base + 1)
    )
    observations = (
        _event("prepare", "control.prepare", number),
        _event("record", "control.record", number),
        *reviews,
        _event("complete", "control.complete", number),
    )
    context, roles = _task_context(number, task_id, observations)
    return context, observations, roles


def _partial_controls() -> tuple[CounterfactualCorpusScenario, ...]:
    scenarios = []
    required_dimensions = (
        HistoryDimension.ROLE_COMBINATION,
        HistoryDimension.PHASE_TRANSITION,
        HistoryDimension.FINALIZATION,
        HistoryDimension.FALLBACK_PROGRESSION,
    )
    categories = _CATEGORIES[::3]
    for offset in range(8):
        number = 101 + offset
        context, observations, _ = _control_context(number)
        _, policy, _, _ = _source_set(number)
        history = B4HistoricalConstraints(
            "B4-HISTORY-CONTEXT@1",
            f"constraints_{number:03d}",
            context.task_id,
            task_context_reference(context),
            _dimensions(policy, required_dimensions[offset % 4]),
        )
        scenarios.append(
            CounterfactualCorpusScenario(
                f"HX-013-{number:03d}",
                1,
                context.task_id,
                categories[offset % len(categories)],
                f"{len(observations)}_step_partial_context",
                context,
                history,
                observations,
                "PARTIAL_CONTEXT",
            )
        )
    return tuple(scenarios)


def _stale_controls() -> tuple[CounterfactualCorpusScenario, ...]:
    scenarios = []
    for offset in range(8):
        number = 201 + offset
        context, observations, roles = _control_context(number)
        _, policy, _, adapter = _source_set(number)
        history = B4HistoricalConstraints(
            "B4-HISTORY-CONTEXT@1",
            f"constraints_{number:03d}",
            context.task_id,
            ("0" * 64) if offset < 4 else task_context_reference(context),
            _dimensions(policy, HistoryDimension.PHASE_TRANSITION),
            semantic_event_bindings=_bindings(observations, roles, adapter),
            phase_definitions=(
                PhaseDefinition(
                    "phase_1",
                    ("semantic_prepare", "semantic_record"),
                    policy,
                    initial=True,
                ),
                PhaseDefinition(
                    "phase_2",
                    ("semantic_complete",),
                    policy,
                    terminal=True,
                ),
            ),
            permitted_phase_transitions=(PhaseTransition("phase_1", "phase_2", policy),),
        )
        scenarios.append(
            CounterfactualCorpusScenario(
                f"HX-013-{number:03d}",
                1,
                context.task_id,
                _CATEGORIES[(offset * 2 + 1) % len(_CATEGORIES)],
                f"{len(observations)}_step_stale_context",
                context,
                history,
                observations,
                "STALE_CONTEXT",
            )
        )
    return tuple(scenarios)


PRIMARY_SCENARIOS = _build_primary()
PARTIAL_CONTEXT_CONTROLS = _partial_controls()
STALE_CONTEXT_CONTROLS = _stale_controls()
HELD_OUT_SCENARIOS = PRIMARY_SCENARIOS + PARTIAL_CONTEXT_CONTROLS + STALE_CONTEXT_CONTROLS

if len(PRIMARY_SCENARIOS) != 80:  # pragma: no cover - import-time design invariant
    raise AssertionError("EXP-013 primary corpus must contain exactly 80 scenarios.")
if len(HELD_OUT_SCENARIOS) != 96:  # pragma: no cover - import-time design invariant
    raise AssertionError("EXP-013 corpus must contain exactly 96 scenarios.")


__all__ = [
    "CounterfactualCorpusScenario",
    "CorpusObservation",
    "HELD_OUT_SCENARIOS",
    "PARTIAL_CONTEXT_CONTROLS",
    "PRIMARY_SCENARIOS",
    "STALE_CONTEXT_CONTROLS",
]
