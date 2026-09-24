"""Fixed B4 v1 rules over one bounded raw-observation window."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from safetybox.b4.models import (
    CONFIG_VERSION,
    MONITOR_VERSION,
    Applicability,
    B4Classification,
    B4ContextualizedObservation,
    B4HistoricalConstraints,
    B4StateSnapshot,
    B4TrajectoryFinding,
    CandidateOrderMode,
    CandidateTransition,
    ContextSufficiency,
    CyclePolicy,
    FallbackEpisodeSnapshot,
    FallbackProgressionConstraint,
    FinalizationSnapshot,
    HistoryDimension,
    RestartPolicy,
    RoleCombination,
    RoleObservation,
)
from safetybox.capabilities import resource_matches
from safetybox.context import ContextSource, TaskContext
from safetybox.models import Decision


@dataclass(frozen=True, slots=True)
class WindowAnalysis:
    state: B4StateSnapshot
    findings: tuple[B4TrajectoryFinding, ...]


@dataclass(slots=True)
class _ScopeState:
    active: bool = False
    roles: list[RoleObservation] | None = None

    def __post_init__(self) -> None:
        if self.roles is None:
            self.roles = []


@dataclass(slots=True)
class _Episode:
    candidates: list[str]
    evidence: list[B4ContextualizedObservation]
    terminated: bool = False
    termination_sequence: int | None = None
    restart_count: int = 0
    known_start: bool = True


def analyze_window(
    history: tuple[B4ContextualizedObservation, ...],
    task_context: TaskContext,
    context: B4HistoricalConstraints,
    *,
    prefix_evicted: bool,
) -> WindowAnalysis:
    """Recompute all semantics from retained raw inputs; retain no historical summary."""
    if not history:
        return WindowAnalysis(_empty_state(prefix_evicted), ())
    findings: list[B4TrajectoryFinding] = []
    findings.extend(_structural_context_findings(history, task_context, context))
    scope_state, role_findings = _role_analysis(history, context, prefix_evicted)
    findings.extend(role_findings)
    active_phase, phase_findings = _phase_analysis(history, context, prefix_evicted)
    findings.extend(phase_findings)
    finalized_phases, finalizations, final_findings = _finalization_analysis(
        history, context, prefix_evicted
    )
    findings.extend(final_findings)
    episodes, fallback_findings = _fallback_analysis(
        history, task_context, context, prefix_evicted
    )
    findings.extend(fallback_findings)

    active_roles = tuple(
        role
        for scope in scope_state.values()
        if scope.active
        for role in (scope.roles or [])
    )
    state = B4StateSnapshot(
        active_phase_id=active_phase,
        accumulated_resource_role_ids=_unique_sorted(
            role.resource_role_id for role in active_roles if role.resource_role_id is not None
        ),
        accumulated_data_role_ids=_unique_sorted(
            data_role for role in active_roles for data_role in role.data_role_ids
        ),
        accumulated_role_group_ids=_unique_sorted(
            group for role in active_roles for group in role.role_group_ids
        ),
        role_observations=active_roles,
        finalized_phase_ids=tuple(sorted(finalized_phases)),
        finalizations=tuple(finalizations),
        fallback_episodes=tuple(episodes),
        raw_window_sequence_numbers=tuple(
            item.observation.sequence_number for item in history
        ),
        prefix_evicted=prefix_evicted,
    )
    return WindowAnalysis(state, tuple(findings))


def _structural_context_findings(
    history: tuple[B4ContextualizedObservation, ...],
    task_context: TaskContext,
    context: B4HistoricalConstraints,
) -> list[B4TrajectoryFinding]:
    findings: list[B4TrajectoryFinding] = []
    current = history[-1]
    binding_problem_id = next(
        (
            item.semantic_binding_id
            for item in history
            if item.semantic_binding_id
            in {
                "B4-CONTEXT-REFERENCE-MISMATCH",
                "B4-AMBIGUOUS-SEMANTIC-EVENT",
            }
        ),
        None,
    )
    binding_problem = binding_problem_id is not None
    required_declarations: dict[HistoryDimension, tuple[object, ...]] = {
        HistoryDimension.ROLE_COMBINATION: (
            *context.role_groups,
            *context.aggregation_scopes,
            *context.role_combination_constraints,
        ),
        HistoryDimension.PHASE_TRANSITION: (
            *context.semantic_event_bindings,
            *context.phase_definitions,
        ),
        HistoryDimension.FINALIZATION: tuple(context.finalization_constraints),
        HistoryDimension.FALLBACK_PROGRESSION: tuple(
            context.fallback_progression_constraints
        ),
    }
    declaration_complete = {
        HistoryDimension.ROLE_COMBINATION: bool(
            context.role_groups
            and context.aggregation_scopes
            and context.role_combination_constraints
            and context.semantic_event_bindings
        ),
        HistoryDimension.PHASE_TRANSITION: bool(
            context.semantic_event_bindings and context.phase_definitions
        ),
        HistoryDimension.FINALIZATION: bool(
            context.semantic_event_bindings
            and context.phase_definitions
            and context.finalization_constraints
        ),
        HistoryDimension.FALLBACK_PROGRESSION: bool(
            context.fallback_progression_constraints
        ),
    }
    rule_for = {
        HistoryDimension.ROLE_COMBINATION: "B4TRJ-001",
        HistoryDimension.PHASE_TRANSITION: "B4TRJ-002",
        HistoryDimension.FINALIZATION: "B4TRJ-003",
        HistoryDimension.FALLBACK_PROGRESSION: "B4TRJ-004",
    }
    for dimension in HistoryDimension:
        if context.applicability_for(dimension) is Applicability.NOT_APPLICABLE:
            continue
        declarations = required_declarations[dimension]
        missing = not declaration_complete[dimension] or binding_problem
        reason = "required-declarations-absent"
        if binding_problem:
            reason = (
                "task-context-reference-mismatch"
                if binding_problem_id == "B4-CONTEXT-REFERENCE-MISMATCH"
                else "ambiguous-semantic-event-binding"
            )
        elif dimension is HistoryDimension.PHASE_TRANSITION and declarations:
            initials = tuple(item for item in context.phase_definitions if item.initial)
            missing = len(initials) != 1
            reason = "initial-phase-missing-or-ambiguous"
            if not missing and len(context.phase_definitions) > 1:
                missing = not context.permitted_phase_transitions
                reason = "phase-transition-table-absent"
        if (
            not binding_problem
            and dimension is HistoryDimension.FALLBACK_PROGRESSION
            and declarations
        ):
            known_behaviors = {item.behavior_id for item in task_context.fallback_patterns}
            missing = any(
                item.linked_fallback_behavior_id not in known_behaviors
                for item in context.fallback_progression_constraints
            )
            reason = "linked-fallback-declaration-missing"
        if missing:
            findings.append(
                _finding(
                    rule_for[dimension],
                    "REQUIRED_HISTORY_CONTEXT_INSUFFICIENT",
                    B4Classification.INSUFFICIENT_CONTEXT,
                    (current,),
                    context,
                    declaration_ids=(),
                    sources=_dimension_sources(context, dimension),
                    state=(("missing", (dimension.value, reason)),),
                    expected=("complete-trusted-declarations", dimension.value),
                    observed=(reason,),
                    reasons=("B4-CONTEXT-INCOMPLETE",),
                    missing=(dimension,),
                    explanation=(
                        "A required B4 history dimension lacks complete trusted declarations; "
                        "the monitor abstains."
                    ),
                )
            )
    return findings


def _role_analysis(
    history: tuple[B4ContextualizedObservation, ...],
    context: B4HistoricalConstraints,
    prefix_evicted: bool,
) -> tuple[dict[str, _ScopeState], list[B4TrajectoryFinding]]:
    states = {scope.scope_id: _ScopeState() for scope in context.aggregation_scopes}
    findings: list[B4TrajectoryFinding] = []
    if context.applicability_for(HistoryDimension.ROLE_COMBINATION) is Applicability.NOT_APPLICABLE:
        return states, findings
    groups = context.role_groups
    scopes = {item.scope_id: item for item in context.aggregation_scopes}
    current = history[-1]
    for item in history:
        event_id = item.semantic_event_id
        for scope in context.aggregation_scopes:
            state = states[scope.scope_id]
            if event_id in scope.opening_semantic_event_ids:
                state.active = True
                state.roles = []
            if state.active and item.observation.executed:
                role = item.context_evaluation.matched_resource_role_id
                data_roles = item.context_evaluation.matched_data_role_ids
                matched_groups = tuple(
                    sorted(
                        group.group_id
                        for group in groups
                        if group.group_id in scope.tracked_role_group_ids
                        and (
                            (role is not None and role in group.resource_role_ids)
                            or bool(set(data_roles) & group.data_role_ids)
                        )
                    )
                )
                if role is not None or data_roles:
                    role_observation = RoleObservation(
                        role,
                        tuple(sorted(data_roles)),
                        matched_groups,
                        item.observation.request_id,
                        item.observation.sequence_number,
                        item.context_evaluation.context_sources,
                    )
                    if state.roles is None:  # defensive internal invariant
                        state.roles = []
                    state.roles.append(role_observation)

        matching_constraints = tuple(
            constraint
            for constraint in context.role_combination_constraints
            if constraint.outcome_semantic_event_id == event_id
        )
        for constraint in matching_constraints if item is current else ():
            scope = scopes[constraint.aggregation_scope_id]
            state = states[scope.scope_id]
            roles = tuple(state.roles or ())
            if not state.active:
                findings.append(
                    _finding(
                        "B4TRJ-001",
                        "ROLE_COMBINATION_CONTEXT_INSUFFICIENT",
                        B4Classification.INSUFFICIENT_CONTEXT,
                        (item,),
                        context,
                        declaration_ids=(constraint.declaration_id, scope.scope_id),
                        sources=(constraint.source, scope.source),
                        state=(("scope", (scope.scope_id, "inactive-or-opening-evicted")),),
                        expected=("declared-scope-opening-in-window",),
                        observed=("scope-opening-unavailable",),
                        reasons=("B4-ROLE-SCOPE-PREFIX-MISSING",),
                        missing=(HistoryDimension.ROLE_COMBINATION,),
                        explanation=(
                            "The role-combination outcome is visible but its declared scope "
                            "opening is unavailable; the monitor abstains."
                        ),
                    )
                )
            elif not any(role.sequence_number < item.observation.sequence_number for role in roles):
                if prefix_evicted:
                    findings.append(
                        _finding(
                            "B4TRJ-001",
                            "ROLE_COMBINATION_CONTEXT_INSUFFICIENT",
                            B4Classification.INSUFFICIENT_CONTEXT,
                            (item,),
                            context,
                            declaration_ids=(constraint.declaration_id, scope.scope_id),
                            sources=(constraint.source, scope.source),
                            state=(("scope", (scope.scope_id, "role-prefix-evicted")),),
                            expected=("role-history-in-window",),
                            observed=("required-prefix-unavailable",),
                            reasons=("B4-ROLE-PREFIX-EVICTED",),
                            missing=(HistoryDimension.ROLE_COMBINATION,),
                            explanation=(
                                "The fixed raw window cannot establish the role history "
                                "required at this outcome; the monitor abstains."
                            ),
                        )
                    )
            else:
                observed = RoleCombination(
                    resource_role_ids={
                        role.resource_role_id
                        for role in roles
                        if role.resource_role_id in constraint.tracked_resource_role_ids
                    },
                    data_role_ids={
                        data_role
                        for role in roles
                        for data_role in role.data_role_ids
                        if data_role in constraint.tracked_data_role_ids
                    },
                    role_group_ids={
                        group
                        for role in roles
                        for group in role.role_group_ids
                        if group in constraint.tracked_role_group_ids
                    },
                )
                if observed not in constraint.allowed_exact_projected_combinations:
                    evidence_ids = {role.request_id for role in roles}
                    evidence = tuple(
                        historical
                        for historical in history
                        if historical.observation.request_id in evidence_ids
                    ) + (item,)
                    findings.append(
                        _finding(
                            "B4TRJ-001",
                            "ROLE_COMBINATION_OUTSIDE_DECLARED_ALLOW_LIST",
                            B4Classification.SUSPICIOUS,
                            evidence,
                            context,
                            declaration_ids=(
                                constraint.declaration_id,
                                scope.scope_id,
                                *sorted(observed.role_group_ids),
                            ),
                            sources=_ordered_sources(
                                constraint.source,
                                scope.source,
                                *(
                                    group.source
                                    for group in groups
                                    if group.group_id in observed.role_group_ids
                                ),
                                *(source for role in roles for source in role.context_sources),
                            ),
                            state=_combination_state(observed),
                            expected=tuple(
                                sorted(
                                    _combination_text(combo)
                                    for combo in constraint.allowed_exact_projected_combinations
                                )
                            ),
                            observed=(_combination_text(observed),),
                            reasons=("B4-ROLE-COMBINATION-NOT-ALLOWED",),
                            explanation=(
                                "Observed roles occurred in the declared scope before the "
                                "outcome, and their projected combination is outside the "
                                "trusted allow-list; no payload lineage is inferred."
                            ),
                        )
                    )
        for scope in context.aggregation_scopes:
            if event_id in scope.closing_semantic_event_ids:
                states[scope.scope_id].active = False
                states[scope.scope_id].roles = []
    return states, findings


def _phase_analysis(
    history: tuple[B4ContextualizedObservation, ...],
    context: B4HistoricalConstraints,
    prefix_evicted: bool,
) -> tuple[str | None, list[B4TrajectoryFinding]]:
    if context.applicability_for(HistoryDimension.PHASE_TRANSITION) is Applicability.NOT_APPLICABLE:
        return None, []
    event_phase = {
        event_id: phase
        for phase in context.phase_definitions
        for event_id in phase.semantic_event_ids
    }
    allowed = {
        (item.from_phase_id, item.to_phase_id)
        for item in context.permitted_phase_transitions
    }
    initials = {item.phase_id for item in context.phase_definitions if item.initial}
    phase_by_id = {item.phase_id: item for item in context.phase_definitions}
    active: str | None = None
    prior_item: B4ContextualizedObservation | None = None
    findings: list[B4TrajectoryFinding] = []
    current = history[-1]
    if len(initials) != 1:
        return active, findings
    for item in history:
        phase = event_phase.get(item.semantic_event_id or "")
        if phase is None:
            continue
        if active is None:
            if phase.phase_id not in initials:
                if item is current:
                    classification = (
                        B4Classification.INSUFFICIENT_CONTEXT
                        if prefix_evicted
                        else B4Classification.SUSPICIOUS
                    )
                    findings.append(
                        _finding(
                            "B4TRJ-002",
                            (
                                "PHASE_PREFIX_CONTEXT_INSUFFICIENT"
                                if prefix_evicted
                                else "UNDECLARED_INITIAL_PHASE"
                            ),
                            classification,
                            (item,),
                            context,
                            declaration_ids=(phase.phase_id,),
                            sources=(phase.source,),
                            state=(("phase", (phase.phase_id,)),),
                            expected=tuple(sorted(initials)),
                            observed=(phase.phase_id,),
                            reasons=(
                                "B4-PHASE-PREFIX-EVICTED"
                                if prefix_evicted
                                else "B4-PHASE-INITIAL-NOT-DECLARED",
                            ),
                            missing=(HistoryDimension.PHASE_TRANSITION,)
                            if prefix_evicted
                            else (),
                            explanation=(
                                "The first retained phase is not the declared initial phase; "
                                + (
                                    "an evicted prefix prevents classification."
                                    if prefix_evicted
                                    else "the observed start is undeclared."
                                )
                            ),
                        )
                    )
            active = phase.phase_id
            prior_item = item
            continue
        if phase.phase_id != active and (active, phase.phase_id) not in allowed:
            if item is current and prior_item is not None:
                findings.append(
                    _finding(
                        "B4TRJ-002",
                        "UNDECLARED_PHASE_TRANSITION",
                        B4Classification.SUSPICIOUS,
                        (prior_item, item),
                        context,
                        declaration_ids=(active, phase.phase_id),
                        sources=_ordered_sources(
                            prior_item_binding_source(prior_item, context),
                            phase_by_id[active].source,
                            phase.source,
                            *(item.source for item in context.permitted_phase_transitions),
                        ),
                        state=(("phase-transition", (active, phase.phase_id)),),
                        expected=tuple(
                            sorted(f"{source}->{target}" for source, target in allowed)
                        ),
                        observed=(f"{active}->{phase.phase_id}",),
                        reasons=("B4-PHASE-TRANSITION-UNDECLARED",),
                        explanation=(
                            "Two trusted semantic events map to phases whose directed "
                            "transition is not declared."
                        ),
                    )
                )
        active = phase.phase_id
        prior_item = item
    return active, findings


def _finalization_analysis(
    history: tuple[B4ContextualizedObservation, ...],
    context: B4HistoricalConstraints,
    prefix_evicted: bool,
) -> tuple[set[str], list[FinalizationSnapshot], list[B4TrajectoryFinding]]:
    if context.applicability_for(HistoryDimension.FINALIZATION) is Applicability.NOT_APPLICABLE:
        return set(), [], []
    event_phase = {
        event_id: phase.phase_id
        for phase in context.phase_definitions
        for event_id in phase.semantic_event_ids
    }
    current = history[-1]
    current_phase = event_phase.get(current.semantic_event_id or "")
    finalized: dict[str, B4ContextualizedObservation] = {}
    for item in history[:-1]:
        for declaration in context.finalization_constraints:
            if item.semantic_event_id == declaration.finalization_semantic_event_id:
                finalized[declaration.finalization_id] = item
    findings: list[B4TrajectoryFinding] = []
    for declaration in context.finalization_constraints:
        marker = finalized.get(declaration.finalization_id)
        if marker is not None and current_phase in declaration.closed_phase_ids:
            if (
                current.semantic_event_id
                not in declaration.permitted_post_finalization_semantic_event_ids
            ):
                findings.append(
                    _finding(
                        "B4TRJ-003",
                        "CLOSED_PHASE_REENTRY_AFTER_FINALIZATION",
                        B4Classification.SUSPICIOUS,
                        (marker, current),
                        context,
                        declaration_ids=(declaration.finalization_id,),
                        sources=(declaration.source,),
                        state=(
                            ("closed-phases", tuple(sorted(declaration.closed_phase_ids))),
                            ("finalized-at", (str(marker.observation.sequence_number),)),
                        ),
                        expected=tuple(
                            sorted(declaration.permitted_post_finalization_semantic_event_ids)
                        ),
                        observed=(current.semantic_event_id or "unmapped",),
                        reasons=("B4-CLOSED-PHASE-REENTRY",),
                        explanation=(
                            "A later trusted semantic event re-enters a phase closed by a "
                            "retained finalization event without a declared exception."
                        ),
                    )
                )
        elif marker is None and prefix_evicted and current_phase in declaration.closed_phase_ids:
            findings.append(
                _finding(
                    "B4TRJ-003",
                    "FINALIZATION_PREFIX_CONTEXT_INSUFFICIENT",
                    B4Classification.INSUFFICIENT_CONTEXT,
                    (current,),
                    context,
                    declaration_ids=(declaration.finalization_id,),
                    sources=(declaration.source,),
                    state=(("closed-phase-candidate", (current_phase or "",)),),
                    expected=("retained-finalization-or-open-prefix",),
                    observed=("prefix-evicted",),
                    reasons=("B4-FINALIZATION-PREFIX-EVICTED",),
                    missing=(HistoryDimension.FINALIZATION,),
                    explanation=(
                        "The observation maps to a phase that can be closed, but the fixed "
                        "window cannot establish whether finalization occurred."
                    ),
                )
            )
    closed = {
        phase
        for declaration in context.finalization_constraints
        if declaration.finalization_id in finalized
        for phase in declaration.closed_phase_ids
    }
    for declaration in context.finalization_constraints:
        if current.semantic_event_id == declaration.finalization_semantic_event_id:
            closed.update(declaration.closed_phase_ids)
    snapshots = [
        FinalizationSnapshot(
            declaration.finalization_id,
            declaration.outcome_id,
            marker.observation.sequence_number,
            tuple(sorted(declaration.closed_phase_ids)),
            tuple(sorted(declaration.permitted_post_finalization_semantic_event_ids)),
            declaration.source,
        )
        for declaration in context.finalization_constraints
        if (
            marker := next(
                (
                    item
                    for item in reversed(history)
                    if item.semantic_event_id
                    == declaration.finalization_semantic_event_id
                ),
                None,
            )
        )
        is not None
    ]
    return closed, snapshots, findings


def _fallback_analysis(
    history: tuple[B4ContextualizedObservation, ...],
    task_context: TaskContext,
    context: B4HistoricalConstraints,
    prefix_evicted: bool,
) -> tuple[list[FallbackEpisodeSnapshot], list[B4TrajectoryFinding]]:
    if (
        context.applicability_for(HistoryDimension.FALLBACK_PROGRESSION)
        is Applicability.NOT_APPLICABLE
    ):
        return [], []
    findings: list[B4TrajectoryFinding] = []
    snapshots: list[FallbackEpisodeSnapshot] = []
    current = history[-1]
    known_behaviors = {item.behavior_id for item in task_context.fallback_patterns}
    for declaration in context.fallback_progression_constraints:
        if declaration.linked_fallback_behavior_id not in known_behaviors:
            continue
        episode = _Episode([], [], known_start=not prefix_evicted)
        for item in history:
            if item.semantic_event_id == declaration.termination_semantic_event_id:
                episode.terminated = True
                episode.termination_sequence = item.observation.sequence_number
                episode.known_start = True
                continue
            evaluation = item.context_evaluation
            eligible = (
                item.observation.policy_decision is Decision.DENY
                and not item.observation.executed
                and evaluation.matched_fallback_behavior_id
                == declaration.linked_fallback_behavior_id
            )
            if not eligible:
                continue
            candidates = tuple(
                candidate
                for candidate in declaration.candidates
                if resource_matches(candidate.resource_scope, item.observation.resource)
                and evaluation.matched_resource_role_id == candidate.resource_role_id
            )
            if len(candidates) != 1:
                if item is current:
                    findings.append(
                        _fallback_finding(
                            declaration,
                            context,
                            tuple((*episode.evidence, item)),
                            "FALLBACK_CANDIDATE_CONTEXT_INSUFFICIENT",
                            B4Classification.INSUFFICIENT_CONTEXT,
                            "exactly-one-candidate-binding",
                            f"candidate-match-count:{len(candidates)}",
                            "B4-FALLBACK-CANDIDATE-AMBIGUOUS",
                            missing=(HistoryDimension.FALLBACK_PROGRESSION,),
                        )
                    )
                continue
            candidate_id = candidates[0].candidate_id
            violation: tuple[str, str, str] | None = None
            if not episode.known_start and item is current:
                findings.append(
                    _fallback_finding(
                        declaration,
                        context,
                        (item,),
                        "FALLBACK_PREFIX_CONTEXT_INSUFFICIENT",
                        B4Classification.INSUFFICIENT_CONTEXT,
                        "complete-episode-prefix",
                        "prefix-evicted",
                        "B4-FALLBACK-PREFIX-EVICTED",
                        missing=(HistoryDimension.FALLBACK_PROGRESSION,),
                    )
                )
            if episode.terminated:
                if declaration.restart_policy is RestartPolicy.FORBIDDEN:
                    violation = (
                        "FALLBACK_RESTART_FORBIDDEN",
                        "episode-remains-terminated",
                        "fallback-attempt-after-termination",
                    )
                else:
                    episode = _Episode([], [], restart_count=episode.restart_count + 1)
            if episode.candidates and violation is None:
                transition = CandidateTransition(episode.candidates[-1], candidate_id)
                allowed = _allowed_fallback_transitions(declaration)
                if (
                    candidate_id in episode.candidates
                    and declaration.cycle_policy is CyclePolicy.FORBIDDEN
                ):
                    violation = (
                        "FALLBACK_CYCLE_FORBIDDEN",
                        "acyclic-candidate-progression",
                        f"repeated-candidate:{candidate_id}",
                    )
                elif transition not in allowed:
                    violation = (
                        "FALLBACK_TRANSITION_UNDECLARED",
                        "declared-candidate-transition",
                        f"{transition.from_candidate_id}->{transition.to_candidate_id}",
                    )
            episode.candidates.append(candidate_id)
            episode.evidence.append(item)
            if (
                violation is None
                and len(episode.candidates) > declaration.maximum_attempts
            ):
                violation = (
                    "FALLBACK_MAXIMUM_ATTEMPTS_EXCEEDED",
                    f"attempts<={declaration.maximum_attempts}",
                    f"attempts:{len(episode.candidates)}",
                )
            if violation is not None and item is current:
                finding_type, expected, observed = violation
                findings.append(
                    _fallback_finding(
                        declaration,
                        context,
                        tuple(episode.evidence),
                        finding_type,
                        B4Classification.SUSPICIOUS,
                        expected,
                        observed,
                        "B4-FALLBACK-PROGRESSION-VIOLATION",
                    )
                )
        snapshots.append(
            FallbackEpisodeSnapshot(
                declaration.constraint_id,
                tuple(episode.candidates),
                len(episode.candidates),
                episode.candidates[-1] if episode.candidates else None,
                episode.terminated,
                episode.termination_sequence,
                episode.restart_count,
                declaration.source,
            )
        )
    return snapshots, findings


def _fallback_finding(
    declaration: FallbackProgressionConstraint,
    context: B4HistoricalConstraints,
    evidence: tuple[B4ContextualizedObservation, ...],
    finding_type: str,
    classification: B4Classification,
    expected: str,
    observed: str,
    reason: str,
    *,
    missing: tuple[HistoryDimension, ...] = (),
) -> B4TrajectoryFinding:
    return _finding(
        "B4TRJ-004",
        finding_type,
        classification,
        evidence,
        context,
        declaration_ids=(
            declaration.constraint_id,
            *(candidate.candidate_id for candidate in declaration.candidates),
        ),
        sources=(
            declaration.source,
            *(candidate.source for candidate in declaration.candidates),
        ),
        state=(
            (
                "candidate-history",
                tuple(
                    item.observation.request_id
                    for item in evidence
                ),
            ),
        ),
        expected=(expected,),
        observed=(observed,),
        reasons=(reason,),
        missing=missing,
        explanation=(
            "The bounded denied-attempt episode is inconsistent with its trusted "
            "candidate progression declaration."
            if classification is B4Classification.SUSPICIOUS
            else "The bounded window cannot resolve required fallback progression context."
        ),
    )


def _allowed_fallback_transitions(
    declaration: FallbackProgressionConstraint,
) -> frozenset[CandidateTransition]:
    if declaration.order_mode is CandidateOrderMode.EXPLICIT_TRANSITIONS:
        return declaration.allowed_candidate_transitions
    return frozenset(
        CandidateTransition(first.candidate_id, second.candidate_id)
        for first, second in zip(
            declaration.candidates, declaration.candidates[1:], strict=False
        )
    )


def _finding(
    rule_id: str,
    finding_type: str,
    classification: B4Classification,
    evidence: tuple[B4ContextualizedObservation, ...],
    context: B4HistoricalConstraints,
    *,
    declaration_ids: tuple[str, ...],
    sources: tuple[ContextSource, ...],
    state: tuple[tuple[str, tuple[str, ...]], ...],
    expected: tuple[str, ...],
    observed: tuple[str, ...],
    reasons: tuple[str, ...],
    missing: tuple[HistoryDimension, ...] = (),
    explanation: str,
) -> B4TrajectoryFinding:
    binding_by_id = {
        binding.binding_id: binding for binding in context.semantic_event_bindings
    }
    evidence_bindings = tuple(
        binding_by_id[binding_id]
        for item in evidence
        if (binding_id := item.semantic_binding_id) in binding_by_id
    )
    context_reasons = tuple(
        result.reason_id.value
        for item in evidence
        for result in item.context_evaluation.constraint_results
    )
    evidence_sources = tuple(
        source
        for item in evidence
        for source in item.context_evaluation.context_sources
    )
    enriched_state = (
        *state,
        (
            "context-statuses",
            tuple(item.context_evaluation.status.value for item in evidence),
        ),
        (
            "matched-resource-roles",
            tuple(
                item.context_evaluation.matched_resource_role_id or "unmatched"
                for item in evidence
            ),
        ),
        (
            "semantic-events",
            tuple(item.semantic_event_id or "unmapped" for item in evidence),
        ),
    )
    material = "|".join(
        (
            rule_id,
            finding_type,
            evidence[0].observation.session_id,
            evidence[0].observation.task_id,
            *(item.observation.request_id for item in evidence),
            *expected,
            *observed,
        )
    )
    return B4TrajectoryFinding(
        finding_id=f"{rule_id}:{sha256(material.encode()).hexdigest()[:16]}",
        monitor_version=MONITOR_VERSION,
        config_version=CONFIG_VERSION,
        rule_id=rule_id,
        finding_type=finding_type,
        classification=classification,
        session_id=evidence[0].observation.session_id,
        task_id=evidence[0].observation.task_id,
        first_evidence_sequence=evidence[0].observation.sequence_number,
        detection_sequence=evidence[-1].observation.sequence_number,
        request_ids=tuple(item.observation.request_id for item in evidence),
        event_ids=tuple(item.observation.canonical_event_id for item in evidence),
        historical_state_evidence=enriched_state,
        expected_relation=expected,
        observed_relation=observed,
        declaration_ids=tuple(
            dict.fromkeys((*declaration_ids, *(item.binding_id for item in evidence_bindings)))
        ),
        context_sources=_ordered_sources(
            *sources,
            *(item.source for item in evidence_bindings),
            *evidence_sources,
        ),
        context_reason_ids=tuple(dict.fromkeys((*reasons, *context_reasons))),
        context_sufficiency=(
            ContextSufficiency.INSUFFICIENT_CONTEXT
            if classification is B4Classification.INSUFFICIENT_CONTEXT
            else ContextSufficiency.SUFFICIENT_CONTEXT
        ),
        missing_dimensions=missing,
        logical_lineage_available=False,
        explanation=explanation,
    )


def _combination_state(
    combination: RoleCombination,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("resource-roles", tuple(sorted(combination.resource_role_ids))),
        ("data-roles", tuple(sorted(combination.data_role_ids))),
        ("role-groups", tuple(sorted(combination.role_group_ids))),
    )


def _combination_text(combination: RoleCombination) -> str:
    return (
        "resource=" + ",".join(sorted(combination.resource_role_ids))
        + ";data=" + ",".join(sorted(combination.data_role_ids))
        + ";groups=" + ",".join(sorted(combination.role_group_ids))
    )


def _dimension_sources(
    context: B4HistoricalConstraints, dimension: HistoryDimension
) -> tuple[ContextSource, ...]:
    return tuple(
        item.source for item in context.dimension_applicability if item.dimension is dimension
    )


def prior_item_binding_source(
    item: B4ContextualizedObservation, context: B4HistoricalConstraints
) -> ContextSource:
    return next(
        binding.source
        for binding in context.semantic_event_bindings
        if binding.binding_id == item.semantic_binding_id
    )


def _ordered_sources(*sources: ContextSource) -> tuple[ContextSource, ...]:
    return tuple(dict.fromkeys(sources))


def _unique_sorted(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(items)))


def _empty_state(prefix_evicted: bool) -> B4StateSnapshot:
    return B4StateSnapshot(None, (), (), (), (), (), (), (), (), prefix_evicted)
