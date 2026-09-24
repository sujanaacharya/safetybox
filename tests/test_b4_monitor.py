"""Development-only tests for B4-BOUNDED-CONTEXT-TRAJECTORY@1."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from safetybox import (
    B4_CONFIG,
    ActionRequest,
    AggregationScope,
    Applicability,
    B4CapacityError,
    B4Classification,
    B4Config,
    B4ContextChangedError,
    B4HistoricalConstraints,
    B4Monitor,
    B4OrderingError,
    B4TaskBindingError,
    B4ValidationError,
    BaselinePrediction,
    CandidateOrderMode,
    CandidateTransition,
    Capability,
    CapabilityEvaluator,
    CompletedActionObservation,
    ContextAuthority,
    ContextEvaluationStatus,
    ContextSource,
    CyclePolicy,
    Decision,
    DimensionDeclaration,
    EnforcementResult,
    ExpectedActionPurpose,
    FallbackCandidate,
    FallbackPattern,
    FallbackProgressionConstraint,
    FinalizationConstraint,
    HistoryDimension,
    PhaseDefinition,
    PhaseTransition,
    ResourceRole,
    RestartPolicy,
    RoleCombination,
    RoleCombinationConstraint,
    RoleGroup,
    SemanticEventBinding,
    SingleObservationBaseline,
    TaskContext,
    TaskContract,
    TaskPurpose,
    task_context_reference,
)

TRUSTED = ContextSource(ContextAuthority.TASK_CONTRACT, "contract:b4-dev:v1")
REGISTRY = ContextSource(ContextAuthority.RESOURCE_REGISTRY, "registry:b4-dev:v1")
POLICY = ContextSource(ContextAuthority.SYSTEM_POLICY, "policy:b4-dev:v1")


def task_context(task_id: str = "task-b4") -> TaskContext:
    return TaskContext(
        "1",
        task_id,
        TaskPurpose("purpose", TRUSTED),
        resource_roles=(
            ResourceRole("resource:a", "role_a", REGISTRY),
            ResourceRole("resource:b", "role_b", REGISTRY),
            ResourceRole("resource:c", "role_c", REGISTRY),
            ResourceRole("resource:out", "role_out", REGISTRY),
            ResourceRole("resource:final", "role_final", REGISTRY),
            ResourceRole("resource:filler", "role_filler", REGISTRY),
            ResourceRole("/candidate/a", "candidate_a", REGISTRY),
            ResourceRole("/candidate/b", "candidate_b", REGISTRY),
            ResourceRole("/candidate/c", "candidate_c", REGISTRY),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("candidate.try", "candidate-purpose", TRUSTED),
        ),
        fallback_patterns=(
            FallbackPattern(
                "candidate.try",
                ("/candidate/a", "/candidate/b", "/candidate/c"),
                ("candidate_a", "candidate_b", "candidate_c"),
                "candidate-purpose",
                "fallback-behavior",
                TRUSTED,
                maximum_attempts=8,
                termination_condition_id="termination-condition",
            ),
        ),
    )


def history_context(
    task: TaskContext,
    *,
    required: frozenset[HistoryDimension] = frozenset(HistoryDimension),
    role_allow: tuple[RoleCombination, ...] = (
        RoleCombination(role_group_ids=("group_a",)),
    ),
    phase_edges: tuple[tuple[str, str], ...] = (
        ("phase_1", "phase_2"),
        ("phase_2", "phase_3"),
    ),
    post_final_events: tuple[str, ...] = (),
    fallback_edges: tuple[tuple[str, str], ...] = (
        ("candidate_a", "candidate_b"),
        ("candidate_b", "candidate_c"),
    ),
    maximum_attempts: int = 3,
    restart_policy: RestartPolicy = RestartPolicy.FORBIDDEN,
    cycle_policy: CyclePolicy = CyclePolicy.FORBIDDEN,
    constraints_id: str = "history-constraints",
) -> B4HistoricalConstraints:
    applicability = tuple(
        DimensionDeclaration(
            dimension,
            Applicability.REQUIRED if dimension in required else Applicability.NOT_APPLICABLE,
            POLICY,
        )
        for dimension in HistoryDimension
    )
    bindings = (
        SemanticEventBinding("binding-a", "event-a", "step.a", REGISTRY, "role_a"),
        SemanticEventBinding("binding-b", "event-b", "step.b", REGISTRY, "role_b"),
        SemanticEventBinding("binding-c", "event-c", "step.c", REGISTRY, "role_c"),
        SemanticEventBinding(
            "binding-out", "event-out", "step.out", REGISTRY, "role_out"
        ),
        SemanticEventBinding(
            "binding-final", "event-final", "step.final", REGISTRY, "role_final"
        ),
    )
    return B4HistoricalConstraints(
        "B4-HISTORY-CONTEXT@1",
        constraints_id,
        task.task_id,
        task_context_reference(task),
        applicability,
        role_groups=(
            RoleGroup("group_a", REGISTRY, resource_role_ids=("role_a",)),
            RoleGroup("group_b", REGISTRY, resource_role_ids=("role_b",)),
        ),
        aggregation_scopes=(
            AggregationScope(
                "scope",
                ("event-a",),
                ("event-out",),
                ("group_a", "group_b"),
                POLICY,
            ),
        ),
        role_combination_constraints=(
            RoleCombinationConstraint(
                "role-constraint",
                "scope",
                "event-out",
                POLICY,
                tracked_role_group_ids=("group_a", "group_b"),
                allowed_exact_projected_combinations=role_allow,
            ),
        ),
        semantic_event_bindings=bindings,
        phase_definitions=(
            PhaseDefinition("phase_1", ("event-a",), POLICY, initial=True),
            PhaseDefinition("phase_2", ("event-b",), POLICY),
            PhaseDefinition(
                "phase_3", ("event-c", "event-out", "event-final"), POLICY, terminal=True
            ),
        ),
        permitted_phase_transitions=tuple(
            PhaseTransition(source, target, POLICY) for source, target in phase_edges
        ),
        finalization_constraints=(
            FinalizationConstraint(
                "finalization",
                "outcome",
                "event-final",
                ("phase_1",),
                post_final_events,
                POLICY,
            ),
        ),
        fallback_progression_constraints=(
            FallbackProgressionConstraint(
                "fallback-progression",
                "fallback-behavior",
                (
                    FallbackCandidate(
                        "candidate_a", "/candidate/a", "candidate_a", REGISTRY
                    ),
                    FallbackCandidate(
                        "candidate_b", "/candidate/b", "candidate_b", REGISTRY
                    ),
                    FallbackCandidate(
                        "candidate_c", "/candidate/c", "candidate_c", REGISTRY
                    ),
                ),
                maximum_attempts,
                restart_policy,
                cycle_policy,
                CandidateOrderMode.EXPLICIT_TRANSITIONS,
                POLICY,
                tuple(CandidateTransition(source, target) for source, target in fallback_edges),
                "termination-condition",
                "event-final",
            ),
        ),
    )


def observation(
    sequence: int,
    action: str,
    resource: str,
    *,
    decision: Decision = Decision.ALLOW,
    session_id: str = "session-b4",
    task_id: str = "task-b4",
    request_id: str | None = None,
) -> CompletedActionObservation:
    identity = request_id or f"request-{sequence}"
    return CompletedActionObservation(
        session_id,
        task_id,
        identity,
        "agent",
        action,
        resource,
        decision,
        decision is Decision.ALLOW,
        sequence,
        f"event-{identity}",
    )


def run(
    steps: tuple[tuple[str, str, Decision], ...],
    task: TaskContext,
    history: B4HistoricalConstraints,
    *,
    session_id: str,
) -> tuple[BaselinePrediction, tuple[ContextEvaluationStatus, ...], B4Monitor]:
    monitor = B4Monitor()
    baseline = SingleObservationBaseline()
    results = []
    statuses = []
    for sequence, (action, resource, decision) in enumerate(steps, start=1):
        item = observation(
            sequence,
            action,
            resource,
            decision=decision,
            session_id=session_id,
            request_id=f"{session_id}-{sequence}",
        )
        result = baseline.evaluate(item, task)
        results.append(result)
        statuses.append(result.context_status)
        monitor.observe(item, task, history)
    return baseline.aggregate(results).prediction, tuple(statuses), monitor


def suspicious_rules(monitor: B4Monitor, session_id: str) -> set[str]:
    return {
        finding.rule_id
        for finding in monitor.snapshot(session_id, "task-b4").retained_findings
        if finding.classification is B4Classification.SUSPICIOUS
    }


def test_history_context_construction_versions_and_immutability() -> None:
    task = task_context()
    mutable_roles = ["role_a"]
    group = RoleGroup("copy-test", REGISTRY, resource_role_ids=mutable_roles)
    mutable_roles.append("role_b")
    context = history_context(task)

    assert group.resource_role_ids == frozenset({"role_a"})
    assert context.schema_version == "B4-HISTORY-CONTEXT@1"
    assert B4_CONFIG.config_version == "B4-CONFIG@1"
    assert B4Monitor().version_info.monitor_version == "B4-BOUNDED-CONTEXT-TRAJECTORY@1"
    with pytest.raises(FrozenInstanceError):
        context.task_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        B4Config(window_size=17)


def test_untrusted_declaration_and_missing_applicability_are_rejected() -> None:
    task = task_context()
    untrusted = ContextSource(ContextAuthority.AGENT_SELF_REPORT, "agent:claim")
    with pytest.raises(B4ValidationError):
        B4HistoricalConstraints(
            "B4-HISTORY-CONTEXT@1",
            "untrusted",
            task.task_id,
            task_context_reference(task),
            tuple(
                DimensionDeclaration(dimension, Applicability.NOT_APPLICABLE, untrusted)
                for dimension in HistoryDimension
            ),
        )
    with pytest.raises(B4ValidationError):
        B4HistoricalConstraints(
            "B4-HISTORY-CONTEXT@1",
            "missing-dimension",
            task.task_id,
            task_context_reference(task),
            (),
        )


def test_task_binding_revision_binding_and_context_replacement() -> None:
    task = task_context()
    history = history_context(task, required=frozenset())
    monitor = B4Monitor()
    with pytest.raises(B4TaskBindingError):
        monitor.observe(
            observation(1, "step.a", "resource:a", task_id="other"), task, history
        )

    revised = replace(task, purpose=TaskPurpose("revised-purpose", TRUSTED))
    evaluation = B4Monitor().observe(
        observation(1, "step.a", "resource:a"), revised, history
    )
    assert evaluation.emitted_findings == ()  # all dimensions explicitly not applicable

    monitor.observe(observation(1, "step.a", "resource:a"), task, history)
    with pytest.raises(B4ContextChangedError):
        monitor.observe(
            observation(2, "step.b", "resource:b"),
            task,
            history_context(task, required=frozenset(), constraints_id="replacement"),
        )
    with pytest.raises(B4ContextChangedError):
        monitor.observe(
            observation(2, "step.b", "resource:b"),
            replace(task, purpose=TaskPurpose("replacement-purpose", TRUSTED)),
            history,
        )


def test_detectable_revision_mismatch_abstains_when_dimension_required() -> None:
    task = task_context()
    history = history_context(task, required=frozenset({HistoryDimension.PHASE_TRANSITION}))
    revised = replace(task, purpose=TaskPurpose("revised-purpose", TRUSTED))
    evaluation = B4Monitor().observe(
        observation(1, "step.a", "resource:a"), revised, history
    )
    assert evaluation.emitted_findings[0].classification is B4Classification.INSUFFICIENT_CONTEXT
    assert "task-context-reference-mismatch" in evaluation.emitted_findings[0].observed_relation


def test_strict_ordering_session_and_task_isolation() -> None:
    task = task_context()
    history = history_context(task, required=frozenset())
    monitor = B4Monitor()
    first = observation(1, "step.a", "resource:a")
    monitor.observe(first, task, history)
    with pytest.raises(B4OrderingError):
        monitor.observe(first, task, history)
    with pytest.raises(B4OrderingError):
        monitor.observe(replace(first, sequence_number=0), task, history)

    other_session = observation(
        1, "step.b", "resource:b", session_id="session-other"
    )
    monitor.observe(other_session, task, history)
    assert monitor.snapshot("session-other", task.task_id).state.raw_window_sequence_numbers == (1,)
    assert monitor.snapshot("session-b4", task.task_id).state.raw_window_sequence_numbers == (1,)

    task_b = task_context("task-b")
    history_b = history_context(
        task_b, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    task_monitor = B4Monitor()
    task_monitor.observe(observation(1, "step.a", "resource:a"), task, history)
    task_monitor.observe(
        observation(2, "step.b", "resource:b", task_id="task-b"),
        task_b,
        history_b,
    )
    task_b_result = task_monitor.observe(
        observation(3, "step.out", "resource:out", task_id="task-b"),
        task_b,
        history_b,
    )
    assert not any(
        finding.classification is B4Classification.SUSPICIOUS
        for finding in task_b_result.retained_findings
    )


def test_role_combination_dev_pair_has_b2_and_local_status_parity() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    positive_steps = (
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.b", "resource:b", Decision.ALLOW),
        ("step.out", "resource:out", Decision.ALLOW),
    )
    negative_steps = (
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.out", "resource:out", Decision.ALLOW),
        ("step.b", "resource:b", Decision.ALLOW),
    )
    positive = run(positive_steps, task, history, session_id="role-positive")
    negative = run(negative_steps, task, history, session_id="role-negative")

    assert positive[0] is negative[0] is BaselinePrediction.NEGATIVE
    assert sorted(positive[1]) == sorted(negative[1])
    assert suspicious_rules(positive[2], "role-positive") == {"B4TRJ-001"}
    assert suspicious_rules(negative[2], "role-negative") == set()


def test_phase_order_dev_pair_and_same_phase_continuation() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.PHASE_TRANSITION})
    )
    valid = (
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.b", "resource:b", Decision.ALLOW),
        ("step.c", "resource:c", Decision.ALLOW),
    )
    invalid = (valid[1], valid[0], valid[2])
    negative = run(valid, task, history, session_id="phase-negative")
    positive = run(invalid, task, history, session_id="phase-positive")
    assert negative[0] is positive[0] is BaselinePrediction.NEGATIVE
    assert sorted(negative[1]) == sorted(positive[1])
    assert suspicious_rules(negative[2], "phase-negative") == set()
    assert suspicious_rules(positive[2], "phase-positive") == {"B4TRJ-002"}

    monitor = B4Monitor()
    monitor.observe(observation(1, "step.a", "resource:a"), task, history)
    evaluation = monitor.observe(
        observation(2, "step.a", "resource:a", request_id="same-phase"), task, history
    )
    assert not any(item.rule_id == "B4TRJ-002" for item in evaluation.emitted_findings)


def test_cross_phase_interleaving_dev_pair_is_b2_matched() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.PHASE_TRANSITION})
    )
    negative_steps = (
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.b", "resource:b", Decision.ALLOW),
    )
    positive_steps = (
        negative_steps[0],
        negative_steps[2],
        negative_steps[1],
    )
    negative = run(negative_steps, task, history, session_id="cross-phase-negative")
    positive = run(positive_steps, task, history, session_id="cross-phase-positive")
    assert negative[0] is positive[0] is BaselinePrediction.NEGATIVE
    assert sorted(negative[1]) == sorted(positive[1])
    assert suspicious_rules(negative[2], "cross-phase-negative") == set()
    assert suspicious_rules(positive[2], "cross-phase-positive") == {"B4TRJ-002"}


def test_finalization_dev_pair_and_declared_reentry_exception() -> None:
    task = task_context()
    required = frozenset(
        {HistoryDimension.PHASE_TRANSITION, HistoryDimension.FINALIZATION}
    )
    history = history_context(
        task,
        required=required,
        phase_edges=(
            ("phase_1", "phase_2"),
            ("phase_2", "phase_3"),
            ("phase_3", "phase_1"),
        ),
    )
    base = (
        ("step.a", "resource:a", Decision.ALLOW),
        ("step.b", "resource:b", Decision.ALLOW),
        ("step.final", "resource:final", Decision.ALLOW),
    )
    negative = run(base, task, history, session_id="final-negative")
    positive = run(
        (*base, ("step.a", "resource:a", Decision.ALLOW)),
        task,
        history,
        session_id="final-positive",
    )
    assert negative[0] is positive[0] is BaselinePrediction.NEGATIVE
    assert set(negative[1]) == set(positive[1]) == {ContextEvaluationStatus.CONTEXT_CONSISTENT}
    assert suspicious_rules(negative[2], "final-negative") == set()
    assert "B4TRJ-003" in suspicious_rules(positive[2], "final-positive")
    final_state = positive[2].snapshot("final-positive", task.task_id).state
    assert final_state.finalizations[0].finalization_sequence == 3
    assert final_state.finalizations[0].source == POLICY

    allowed = history_context(
        task,
        required=required,
        phase_edges=(("phase_1", "phase_2"), ("phase_2", "phase_3"), ("phase_3", "phase_1")),
        post_final_events=("event-a",),
    )
    permitted = run(
        (*base, ("step.a", "resource:a", Decision.ALLOW)),
        task,
        allowed,
        session_id="final-allowed",
    )
    assert "B4TRJ-003" not in suspicious_rules(permitted[2], "final-allowed")


def test_fallback_progression_dev_pair_has_b2_status_parity() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.FALLBACK_PROGRESSION})
    )
    attempt = Decision.DENY
    valid = (
        ("candidate.try", "/candidate/a", attempt),
        ("candidate.try", "/candidate/b", attempt),
        ("candidate.try", "/candidate/c", attempt),
    )
    invalid = (valid[0], valid[2], valid[1])
    negative = run(valid, task, history, session_id="fallback-negative")
    positive = run(invalid, task, history, session_id="fallback-positive")
    assert negative[0] is positive[0] is BaselinePrediction.NEGATIVE
    assert negative[1] == positive[1]
    assert suspicious_rules(negative[2], "fallback-negative") == set()
    assert suspicious_rules(positive[2], "fallback-positive") == {"B4TRJ-004"}


def test_fallback_post_termination_pair_and_restart_policy() -> None:
    task = task_context()
    required = frozenset({HistoryDimension.FALLBACK_PROGRESSION})
    forbidden = history_context(task, required=required)
    attempt = Decision.DENY
    terminated_last = (
        ("candidate.try", "/candidate/a", attempt),
        ("candidate.try", "/candidate/b", attempt),
        ("step.final", "resource:final", Decision.ALLOW),
    )
    post_termination = (
        terminated_last[0],
        terminated_last[2],
        terminated_last[1],
    )
    negative = run(terminated_last, task, forbidden, session_id="restart-negative")
    positive = run(post_termination, task, forbidden, session_id="restart-positive")
    assert negative[0] is positive[0] is BaselinePrediction.NEGATIVE
    assert sorted(negative[1]) == sorted(positive[1])
    assert suspicious_rules(negative[2], "restart-negative") == set()
    assert suspicious_rules(positive[2], "restart-positive") == {"B4TRJ-004"}
    episode = negative[2].snapshot("restart-negative", task.task_id).fallback_episodes[0]
    assert episode.terminated and episode.termination_sequence == 3
    assert episode.source == POLICY

    allowed = history_context(
        task,
        required=required,
        restart_policy=RestartPolicy.AFTER_DECLARED_TERMINATION,
    )
    restarted = run(post_termination, task, allowed, session_id="restart-allowed")
    assert suspicious_rules(restarted[2], "restart-allowed") == set()


@pytest.mark.parametrize(
    ("maximum", "steps", "expected_type"),
    [
        (
            2,
            (
                ("candidate.try", "/candidate/a", Decision.DENY),
                ("candidate.try", "/candidate/b", Decision.DENY),
                ("candidate.try", "/candidate/c", Decision.DENY),
            ),
            "FALLBACK_MAXIMUM_ATTEMPTS_EXCEEDED",
        ),
        (
            3,
            (
                ("candidate.try", "/candidate/a", Decision.DENY),
                ("candidate.try", "/candidate/a", Decision.DENY),
            ),
            "FALLBACK_CYCLE_FORBIDDEN",
        ),
    ],
)
def test_fallback_bound_and_forbidden_cycle(
    maximum: int,
    steps: tuple[tuple[str, str, Decision], ...],
    expected_type: str,
) -> None:
    task = task_context()
    history = history_context(
        task,
        required=frozenset({HistoryDimension.FALLBACK_PROGRESSION}),
        fallback_edges=(
            ("candidate_a", "candidate_a"),
            ("candidate_a", "candidate_b"),
            ("candidate_b", "candidate_c"),
        ),
        maximum_attempts=maximum,
    )
    result = run(steps, task, history, session_id=f"fallback-{expected_type}")
    assert any(
        finding.finding_type == expected_type
        for finding in result[2].snapshot(
            f"fallback-{expected_type}", task.task_id
        ).retained_findings
    )


def test_declared_cycle_is_allowed() -> None:
    task = task_context()
    history = history_context(
        task,
        required=frozenset({HistoryDimension.FALLBACK_PROGRESSION}),
        fallback_edges=(("candidate_a", "candidate_a"),),
        cycle_policy=CyclePolicy.DECLARED_TRANSITIONS_ONLY,
    )
    result = run(
        (
            ("candidate.try", "/candidate/a", Decision.DENY),
            ("candidate.try", "/candidate/a", Decision.DENY),
        ),
        task,
        history,
        session_id="cycle-allowed",
    )
    assert suspicious_rules(result[2], "cycle-allowed") == set()


def test_required_missing_context_and_ambiguous_event_abstain() -> None:
    task = task_context()
    declarations = tuple(
        DimensionDeclaration(
            dimension,
            Applicability.REQUIRED
            if dimension is HistoryDimension.FALLBACK_PROGRESSION
            else Applicability.NOT_APPLICABLE,
            POLICY,
        )
        for dimension in HistoryDimension
    )
    missing = B4HistoricalConstraints(
        "B4-HISTORY-CONTEXT@1",
        "missing",
        task.task_id,
        task_context_reference(task),
        declarations,
    )
    result = B4Monitor().observe(
        observation(1, "step.a", "resource:a"), task, missing
    )
    assert result.emitted_findings[0].classification is B4Classification.INSUFFICIENT_CONTEXT

    base = history_context(
        task, required=frozenset({HistoryDimension.PHASE_TRANSITION})
    )
    ambiguous = replace(
        base,
        semantic_event_bindings=(
            *base.semantic_event_bindings,
            SemanticEventBinding("binding-a-duplicate", "event-a", "step.a", POLICY, "role_a"),
        ),
    )
    ambiguous_result = B4Monitor().observe(
        observation(1, "step.a", "resource:a"), task, ambiguous
    )
    assert any(
        item.classification is B4Classification.INSUFFICIENT_CONTEXT
        for item in ambiguous_result.emitted_findings
    )


@pytest.mark.parametrize("initial_phase_ids", [(), ("phase_1", "phase_2")])
def test_missing_or_ambiguous_initial_phase_abstains(
    initial_phase_ids: tuple[str, ...],
) -> None:
    task = task_context()
    base = history_context(
        task, required=frozenset({HistoryDimension.PHASE_TRANSITION})
    )
    phases = tuple(
        replace(phase, initial=phase.phase_id in initial_phase_ids)
        for phase in base.phase_definitions
    )
    context = replace(base, phase_definitions=phases)
    result = B4Monitor().observe(
        observation(1, "step.a", "resource:a"), task, context
    )
    assert any(
        finding.classification is B4Classification.INSUFFICIENT_CONTEXT
        and "initial-phase-missing-or-ambiguous" in finding.observed_relation
        for finding in result.emitted_findings
    )


def test_raw_window_eviction_removes_role_semantics_and_abstains() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    monitor = B4Monitor()
    monitor.observe(observation(1, "step.a", "resource:a"), task, history)
    for sequence in range(2, 18):
        monitor.observe(
            observation(sequence, "filler", "resource:filler"), task, history
        )
    result = monitor.observe(observation(18, "step.out", "resource:out"), task, history)

    assert result.state.prefix_evicted
    assert 1 not in result.state.raw_window_sequence_numbers
    assert "group_a" not in result.state.accumulated_role_group_ids
    assert any(
        item.rule_id == "B4TRJ-001"
        and item.classification is B4Classification.INSUFFICIENT_CONTEXT
        for item in result.emitted_findings
    )
    assert not any(
        item.rule_id == "B4TRJ-001"
        and item.classification is B4Classification.SUSPICIOUS
        for item in result.emitted_findings
    )


def test_finding_identity_deduplication_provenance_and_new_evidence() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    monitor = B4Monitor()
    for sequence, (action, resource) in enumerate(
        (("step.a", "resource:a"), ("step.b", "resource:b"), ("step.out", "resource:out")),
        start=1,
    ):
        result = monitor.observe(observation(sequence, action, resource), task, history)
    finding = result.emitted_findings[0]
    assert finding.finding_id.startswith("B4TRJ-001:")
    assert finding.context_sources
    assert finding.declaration_ids[:2] == ("role-constraint", "scope")
    assert {"binding-a", "binding-b", "binding-out"} <= set(finding.declaration_ids)
    assert not finding.logical_lineage_available
    assert monitor.snapshot("session-b4", task.task_id).emitted_findings == ()
    with pytest.raises(FrozenInstanceError):
        finding.explanation = "changed"  # type: ignore[misc]

    for sequence, (action, resource) in enumerate(
        (("step.a", "resource:a"), ("step.b", "resource:b"), ("step.out", "resource:out")),
        start=4,
    ):
        result = monitor.observe(
            observation(sequence, action, resource, request_id=f"later-{sequence}"),
            task,
            history,
        )
    assert result.emitted_findings[0].finding_id != finding.finding_id


def test_equivalent_runs_have_identical_semantic_findings() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    traces = []
    for _ in range(2):
        monitor = B4Monitor()
        for sequence, (action, resource) in enumerate(
            (
                ("step.a", "resource:a"),
                ("step.b", "resource:b"),
                ("step.out", "resource:out"),
            ),
            start=1,
        ):
            monitor.observe(observation(sequence, action, resource), task, history)
        traces.append(monitor.snapshot("session-b4", task.task_id).retained_findings)
    assert traces[0] == traces[1]


def test_finding_retention_and_active_key_capacities_are_bounded() -> None:
    task = task_context()
    history = history_context(
        task, required=frozenset({HistoryDimension.ROLE_COMBINATION})
    )
    monitor = B4Monitor()
    sequence = 0
    for occurrence in range(33):
        for action, resource in (
            ("step.a", "resource:a"),
            ("step.b", "resource:b"),
            ("step.out", "resource:out"),
        ):
            sequence += 1
            monitor.observe(
                observation(
                    sequence,
                    action,
                    resource,
                    request_id=f"capacity-{occurrence}-{sequence}",
                ),
                task,
                history,
            )
    retained = monitor.snapshot("session-b4", task.task_id).retained_findings
    assert len(retained) == B4_CONFIG.max_findings == 32
    assert monitor.snapshot("session-b4", task.task_id).finding_retention_truncated
    assert all("capacity-0-" not in request for request in retained[0].request_ids)

    capacity_monitor = B4Monitor()
    no_rules = history_context(task, required=frozenset())
    for number in range(B4_CONFIG.max_active_keys):
        capacity_monitor.observe(
            observation(
                1,
                "step.a",
                "resource:a",
                session_id=f"capacity-session-{number}",
            ),
            task,
            no_rules,
        )
    with pytest.raises(B4CapacityError):
        capacity_monitor.observe(
            observation(
                1,
                "step.a",
                "resource:a",
                session_id="capacity-overflow",
            ),
            task,
            no_rules,
        )


def test_close_discards_state_and_snapshot_is_detached() -> None:
    task = task_context()
    history = history_context(task, required=frozenset())
    monitor = B4Monitor()
    first = monitor.observe(observation(1, "step.a", "resource:a"), task, history)
    monitor.close("session-b4", task.task_id)
    assert first.state.raw_window_sequence_numbers == (1,)
    assert monitor.snapshot("session-b4", task.task_id).state.raw_window_sequence_numbers == ()


def test_b4_is_observational_and_cannot_change_authority() -> None:
    task = task_context()
    history = history_context(task, required=frozenset())
    monitor = B4Monitor()
    capability = Capability("step.a", "resource:a")
    contract = TaskContract(task.task_id, "purpose", (capability,))
    request = ActionRequest(
        "authority-request",
        "session-b4",
        task.task_id,
        "agent",
        "step.b",
        "resource:b",
    )
    policy = CapabilityEvaluator().evaluate(contract, request)
    enforcement = EnforcementResult(request, policy, False)
    before = (contract, capability, policy, enforcement)
    monitor.observe(observation(1, "step.a", "resource:a"), task, history)

    assert (contract, capability, policy, enforcement) == before
    assert not hasattr(monitor, "authorize")
    assert not hasattr(monitor, "execute")
    assert not hasattr(monitor, "quarantine")
