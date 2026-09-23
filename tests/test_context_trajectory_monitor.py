"""M5.1-C development evidence for deterministic context-aware trajectories."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from safetybox import (
    ActionRequest,
    AllowedOutcome,
    Capability,
    CapabilityEvaluator,
    CompletedActionObservation,
    ContextAuthority,
    ContextAwareTrajectoryMonitor,
    ContextReason,
    ContextSource,
    ContextTrajectoryClassification,
    ContextTrajectoryOrderingError,
    ContextValidationError,
    DataRole,
    Decision,
    DestinationConstraint,
    EnforcementResult,
    ExpectedActionPurpose,
    FallbackPattern,
    ObservationContext,
    ResourceRole,
    TaskContext,
    TaskContextChangedError,
    TaskContract,
    TaskPurpose,
)

CONTRACT_SOURCE = ContextSource(ContextAuthority.TASK_CONTRACT, "contract:development:v1")
REGISTRY_SOURCE = ContextSource(
    ContextAuthority.RESOURCE_REGISTRY, "registry:development:v1"
)
POLICY_SOURCE = ContextSource(ContextAuthority.SYSTEM_POLICY, "policy:development:v1")


def observation(
    sequence: int,
    action: str,
    resource: str,
    *,
    session_id: str = "session-a",
    task_id: str = "task-a",
    decision: Decision = Decision.ALLOW,
) -> CompletedActionObservation:
    request_id = f"request-{sequence}"
    return CompletedActionObservation(
        session_id=session_id,
        task_id=task_id,
        request_id=request_id,
        actor="agent-a",
        action=action,
        resource=resource,
        policy_decision=decision,
        executed=decision is Decision.ALLOW,
        sequence_number=sequence,
        canonical_event_id=f"event-{sequence}",
    )


def trajectory_context(
    *,
    task_id: str = "task-a",
    purpose_id: str = "declared-purpose-a",
    destination_scope: str = "api:declared",
) -> TaskContext:
    return TaskContext(
        "1",
        task_id,
        TaskPurpose(purpose_id, CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("declared-result", CONTRACT_SOURCE),),
        data_roles=(DataRole("input-data", REGISTRY_SOURCE),),
        resource_roles=(
            ResourceRole(
                "/workspace/**", "workspace-input", REGISTRY_SOURCE, "input-data"
            ),
            ResourceRole("database:records", "record-input", REGISTRY_SOURCE, "input-data"),
        ),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                destination_scope,
                "declared-destination",
                "declared-delivery-purpose",
                POLICY_SOURCE,
                allowed_data_role_ids=("input-data",),
                allowed_outcome_ids=("declared-result",),
                allowed_action_purpose_ids=("deliver-result",),
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "deliver-result", CONTRACT_SOURCE),
        ),
    )


def fallback_context(*, task_id: str = "task-a", include_pattern: bool = True) -> TaskContext:
    patterns = (
        FallbackPattern(
            "filesystem.read",
            ("/opt/candidates/**",),
            ("candidate",),
            "candidate-lookup",
            "bounded-candidate-lookup",
            CONTRACT_SOURCE,
            maximum_attempts=3,
        ),
    ) if include_pattern else ()
    return TaskContext(
        "1",
        task_id,
        TaskPurpose("declared-purpose-b", CONTRACT_SOURCE),
        resource_roles=(
            ResourceRole("/opt/candidates/**", "candidate", REGISTRY_SOURCE),
            ResourceRole("/restricted/**", "restricted-resource", REGISTRY_SOURCE),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "filesystem.read", "candidate-lookup", CONTRACT_SOURCE
            ),
        ),
        fallback_patterns=patterns,
    )


def ingest_collection_then_send(
    monitor: ContextAwareTrajectoryMonitor,
    context: TaskContext,
    *,
    send_resource: str,
    exact_m5_shape: bool,
) -> None:
    actions = [("filesystem.read", "/workspace/a")]
    if exact_m5_shape:
        actions.append(("filesystem.read", "/workspace/b"))
    actions.append(("database.query", "database:records"))
    for sequence, (action, resource) in enumerate(actions, start=1):
        monitor.ingest(observation(sequence, action, resource), context)
    sequence = len(actions) + 1
    monitor.ingest(
        observation(sequence, "network.send", send_resource),
        context,
        ObservationContext(
            action_purpose_id="deliver-result", data_role_ids=("input-data",)
        ),
    )


def denied_attempts(prefix: str = "/opt/candidates") -> tuple[CompletedActionObservation, ...]:
    return tuple(
        observation(
            sequence,
            "filesystem.read",
            f"{prefix}/{sequence}",
            decision=Decision.DENY,
        )
        for sequence in range(1, 4)
    )


def test_monitor_construction_and_default_rules() -> None:
    monitor = ContextAwareTrajectoryMonitor()

    assert monitor.window_size == 8
    assert monitor.snapshot("session-a", "task-a").rule_ids == (
        "CTXTRJ-001",
        "CTXTRJ-002",
    )
    with pytest.raises(ValueError):
        ContextAwareTrajectoryMonitor(window_size=0)


def test_snapshot_is_immutable_bounded_and_detached_from_future_state() -> None:
    monitor = ContextAwareTrajectoryMonitor(window_size=2)
    context = trajectory_context()
    monitor.ingest(observation(1, "filesystem.read", "/workspace/a"), context)
    first = monitor.snapshot("session-a", "task-a")
    monitor.ingest(observation(2, "database.query", "database:records"), context)
    monitor.ingest(observation(3, "filesystem.read", "/workspace/b"), context)
    latest = monitor.snapshot("session-a", "task-a")

    assert len(first.recent_observations) == 1
    assert tuple(item.sequence_number for item in latest.recent_observations) == (2, 3)
    assert latest.processed_observation_count == 3
    with pytest.raises(FrozenInstanceError):
        latest.task_id = "changed"  # type: ignore[misc]


def test_duplicate_and_decreasing_sequence_numbers_are_errors() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = trajectory_context()
    first = observation(1, "filesystem.read", "/workspace/a")
    monitor.ingest(first, context)

    with pytest.raises(ContextTrajectoryOrderingError):
        monitor.ingest(first, context)
    with pytest.raises(ContextTrajectoryOrderingError):
        monitor.ingest(replace(first, sequence_number=0), context)


def test_session_and_task_state_never_combine() -> None:
    session_monitor = ContextAwareTrajectoryMonitor()
    context = trajectory_context()
    session_monitor.ingest(observation(1, "filesystem.read", "/workspace/a"), context)
    session_monitor.ingest(
        observation(
            1,
            "network.send",
            "api:other",
            session_id="session-b",
        ),
        context,
    )
    assert session_monitor.snapshot("session-b", "task-a").findings == ()

    task_monitor = ContextAwareTrajectoryMonitor()
    task_a = trajectory_context(task_id="task-a")
    task_b = trajectory_context(task_id="task-b")
    task_monitor.ingest(observation(1, "filesystem.read", "/workspace/a"), task_a)
    task_monitor.ingest(
        observation(2, "network.send", "api:other", task_id="task-b"), task_b
    )
    assert task_monitor.snapshot("session-a", "task-b").findings == ()


def test_same_sequence_is_distinguished_only_by_trusted_context() -> None:
    mismatch_monitor = ContextAwareTrajectoryMonitor()
    ingest_collection_then_send(
        mismatch_monitor,
        trajectory_context(purpose_id="purpose-with-other-destination"),
        send_resource="api:delivery",
        exact_m5_shape=True,
    )
    consistent_monitor = ContextAwareTrajectoryMonitor()
    ingest_collection_then_send(
        consistent_monitor,
        trajectory_context(
            purpose_id="purpose-with-declared-delivery",
            destination_scope="api:delivery",
        ),
        send_resource="api:delivery",
        exact_m5_shape=True,
    )

    mismatch = mismatch_monitor.snapshot("session-a", "task-a")
    consistent = consistent_monitor.snapshot("session-a", "task-a")
    assert [item.classification for item in mismatch.findings] == [
        ContextTrajectoryClassification.SUSPICIOUS
    ]
    assert consistent.findings == ()
    assert mismatch.findings[0].rule_id == "CTXTRJ-001"
    assert ContextReason.DESTINATION_UNDECLARED in mismatch.findings[0].context_reason_ids


def test_non_exact_m5_sequence_is_detected_from_context_semantics() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    ingest_collection_then_send(
        monitor,
        trajectory_context(),
        send_resource="api:outside",
        exact_m5_shape=False,
    )

    finding = monitor.snapshot("session-a", "task-a").findings[0]
    assert finding.related_request_ids == ("request-1", "request-2", "request-3")
    assert finding.matched_resource_role_ids == ("workspace-input", "record-input")
    assert "does not prove" in finding.description
    assert not finding.lineage_evidence_available


def test_declared_fallback_suppresses_repetition_only_within_declared_bound() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = fallback_context()
    for item in denied_attempts():
        assert monitor.ingest(item, context) == ()

    assert monitor.snapshot("session-a", "task-a").findings == ()


def test_declared_fallback_bound_excess_is_a_distinct_later_finding() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = fallback_context()
    for sequence in range(1, 5):
        monitor.ingest(
            observation(
                sequence,
                "filesystem.read",
                f"/opt/candidates/{sequence}",
                decision=Decision.DENY,
            ),
            context,
        )

    finding = monitor.snapshot("session-a", "task-a").findings[0]
    assert finding.classification is ContextTrajectoryClassification.SUSPICIOUS
    assert "CTXTRJ-FALLBACK-BOUND-EXCEEDED" in finding.context_reason_ids


def test_repeated_denials_outside_declared_fallback_emit_probing_finding() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = fallback_context()
    for item in denied_attempts("/restricted"):
        monitor.ingest(item, context)

    finding = monitor.snapshot("session-a", "task-a").findings[0]
    assert finding.rule_id == "CTXTRJ-002"
    assert finding.classification is ContextTrajectoryClassification.SUSPICIOUS
    assert ContextReason.FALLBACK_UNDECLARED in finding.context_reason_ids
    assert CONTRACT_SOURCE in finding.context_sources


def test_missing_fallback_context_is_explicit_abstention() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = fallback_context(include_pattern=False)
    for item in denied_attempts():
        monitor.ingest(item, context)

    finding = monitor.snapshot("session-a", "task-a").findings[0]
    assert finding.classification is ContextTrajectoryClassification.INSUFFICIENT_CONTEXT
    assert finding.finding_type == "REPEATED_DENIAL_CONTEXT_INSUFFICIENT"
    assert ContextReason.FALLBACK_CONTEXT_MISSING in finding.context_reason_ids


def test_missing_destination_context_is_explicit_abstention() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("declared-purpose-c", CONTRACT_SOURCE),
        resource_roles=(ResourceRole("/workspace/**", "input", REGISTRY_SOURCE),),
    )
    monitor = ContextAwareTrajectoryMonitor()
    monitor.ingest(observation(1, "filesystem.read", "/workspace/a"), context)
    monitor.ingest(observation(2, "network.send", "api:unknown"), context)

    finding = monitor.snapshot("session-a", "task-a").findings[0]
    assert finding.classification is ContextTrajectoryClassification.INSUFFICIENT_CONTEXT
    assert ContextReason.DESTINATION_CONTEXT_MISSING in finding.context_reason_ids
    assert ContextReason.OUTCOME_CONTEXT_MISSING in finding.context_reason_ids


def test_untrusted_context_is_rejected_before_it_can_suppress_a_finding() -> None:
    untrusted = ContextSource(ContextAuthority.AGENT_SELF_REPORT, "agent:claim:1")

    with pytest.raises(ContextValidationError):
        TaskContext(
            "1",
            "task-a",
            TaskPurpose("agent-claimed-purpose", untrusted),
        )


def test_authorization_observation_is_unchanged_and_monitor_is_observational() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = trajectory_context(destination_scope="api:delivery")
    capability = Capability("filesystem.read", "/workspace/**")
    contract = TaskContract("task-a", "no outbound authority", (capability,))
    request = ActionRequest(
        "request-2",
        "session-a",
        "task-a",
        "agent-a",
        "network.send",
        "api:delivery",
    )
    policy_decision = CapabilityEvaluator().evaluate(contract, request)
    enforcement_result = EnforcementResult(request, policy_decision, executed=False)
    authority_snapshot = (contract, capability, policy_decision, enforcement_result)
    monitor.ingest(observation(1, "filesystem.read", "/workspace/a"), context)
    denied = observation(
        2,
        "network.send",
        "api:delivery",
        decision=policy_decision.decision,
    )

    monitor.ingest(
        denied,
        context,
        ObservationContext(
            action_purpose_id="deliver-result", data_role_ids=("input-data",)
        ),
    )

    assert denied.policy_decision is Decision.DENY
    assert not denied.executed
    assert (contract, capability, policy_decision, enforcement_result) == authority_snapshot
    assert not hasattr(monitor, "authorize")
    assert not hasattr(monitor, "execute")


def test_finding_preserves_provenance_explanation_and_is_immutable() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    ingest_collection_then_send(
        monitor,
        trajectory_context(),
        send_resource="api:outside",
        exact_m5_shape=False,
    )
    finding = monitor.snapshot("session-a", "task-a").findings[0]

    assert finding.context_sources == (
        CONTRACT_SOURCE,
        REGISTRY_SOURCE,
        POLICY_SOURCE,
    )
    assert finding.expected_context and finding.observed_context
    assert finding.detection_sequence_number == 3
    with pytest.raises(FrozenInstanceError):
        finding.description = "changed"  # type: ignore[misc]


def test_equivalent_inputs_produce_deterministic_findings_and_ids() -> None:
    findings = []
    for _ in range(2):
        monitor = ContextAwareTrajectoryMonitor()
        ingest_collection_then_send(
            monitor,
            trajectory_context(),
            send_resource="api:outside",
            exact_m5_shape=False,
        )
        findings.append(monitor.snapshot("session-a", "task-a").findings)

    assert findings[0] == findings[1]
    assert findings[0][0].finding_id.startswith("CTXTRJ-001:")


def test_distinct_later_evidence_is_not_deduplicated() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    context = fallback_context()
    for sequence in range(1, 5):
        monitor.ingest(
            observation(
                sequence,
                "filesystem.read",
                f"/restricted/{sequence}",
                decision=Decision.DENY,
            ),
            context,
        )

    findings = monitor.snapshot("session-a", "task-a").findings
    assert len(findings) == 2
    assert findings[0].related_request_ids != findings[1].related_request_ids


def test_context_is_fixed_within_a_session_task_boundary() -> None:
    monitor = ContextAwareTrajectoryMonitor()
    monitor.ingest(
        observation(1, "filesystem.read", "/workspace/a"), trajectory_context()
    )

    with pytest.raises(TaskContextChangedError):
        monitor.ingest(
            observation(2, "filesystem.read", "/workspace/b"),
            trajectory_context(purpose_id="different-purpose"),
        )
