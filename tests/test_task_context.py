"""M5.1-A evidence for immutable trusted context representation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field

import pytest

from safetybox import (
    ActionRequest,
    AllowedOutcome,
    Capability,
    ContextAuthority,
    ContextField,
    ContextSource,
    ContextStatus,
    ContextValidationError,
    DataFlowConstraint,
    DataRole,
    Decision,
    DestinationConstraint,
    ExpectedActionPurpose,
    FallbackPattern,
    ReferenceMonitor,
    ResourceRole,
    TaskContext,
    TaskContract,
    TaskContractPolicy,
    TaskPurpose,
    validate_task_binding,
)

POLICY_SOURCE = ContextSource(ContextAuthority.SYSTEM_POLICY, "policy:context-v1")
CONTRACT_SOURCE = ContextSource(ContextAuthority.TASK_CONTRACT, "contract:task-a:v1")
REGISTRY_SOURCE = ContextSource(ContextAuthority.RESOURCE_REGISTRY, "registry:resources:v4")


def reporting_context(*, task_id: str = "task-a") -> TaskContext:
    return TaskContext(
        schema_version="1",
        task_id=task_id,
        purpose=TaskPurpose("report_generation", CONTRACT_SOURCE, "Generate a report."),
        allowed_outcomes=(AllowedOutcome("remote_report_delivery", CONTRACT_SOURCE),),
        data_roles=(
            DataRole("analytics_data", REGISTRY_SOURCE),
            DataRole("generated_report", REGISTRY_SOURCE),
        ),
        resource_roles=(
            ResourceRole(
                "db:analytics",
                "analytics_source",
                REGISTRY_SOURCE,
                data_role_id="analytics_data",
            ),
            ResourceRole(
                "/workspace/reports/**",
                "report_artifact",
                REGISTRY_SOURCE,
                data_role_id="generated_report",
            ),
        ),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:reporting-endpoint",
                "reporting-api",
                "report_delivery",
                POLICY_SOURCE,
                allowed_data_role_ids=("generated_report",),
                allowed_outcome_ids=("remote_report_delivery",),
                allowed_action_purpose_ids=("deliver_report",),
            ),
        ),
        data_flow_constraints=(
            DataFlowConstraint(
                ("analytics_source",),
                "generated_report",
                "report_delivery",
                ("deliver_report",),
                CONTRACT_SOURCE,
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "deliver_report", CONTRACT_SOURCE),
        ),
    )


def test_task_context_construction_and_structured_purpose() -> None:
    context = reporting_context()

    assert context.schema_version == "1"
    assert context.task_id == "task-a"
    assert context.purpose.purpose_id == "report_generation"
    assert context.allowed_outcomes[0].outcome_id == "remote_report_delivery"


def test_context_and_nested_collections_are_copied_and_immutable() -> None:
    supplied_outcomes = [AllowedOutcome("local_report", CONTRACT_SOURCE)]
    supplied_roles = ["generated_report"]
    destination = DestinationConstraint(
        "network.send",
        "api:reports",
        "reports-api",
        "report_delivery",
        POLICY_SOURCE,
        allowed_data_role_ids=supplied_roles,
    )
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("analysis", CONTRACT_SOURCE),
        allowed_outcomes=supplied_outcomes,
        data_roles=(DataRole("generated_report", REGISTRY_SOURCE),),
        destination_constraints=(destination,),
    )
    supplied_outcomes.append(AllowedOutcome("remote_report", CONTRACT_SOURCE))
    supplied_roles.append("source_code")

    assert tuple(item.outcome_id for item in context.allowed_outcomes) == ("local_report",)
    assert destination.allowed_data_role_ids == {"generated_report"}
    with pytest.raises(FrozenInstanceError):
        context.task_id = "task-b"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        destination.allowed_data_role_ids.add("source_code")


def test_resource_role_lookup_reuses_m2_boundary_behavior() -> None:
    context = reporting_context()

    binding = context.role_for("/workspace/reports/monthly.csv")

    assert binding is not None
    assert binding.role_id == "report_artifact"
    assert context.role_for("/workspace/reports-secret/monthly.csv") is None
    assert context.role_for("/workspace/reports") is None


def test_overlapping_resource_roles_are_rejected_as_ambiguous() -> None:
    with pytest.raises(ContextValidationError, match="Overlapping resource role"):
        TaskContext(
            "1",
            "task-a",
            TaskPurpose("analysis", CONTRACT_SOURCE),
            resource_roles=(
                ResourceRole("/workspace/**", "workspace", REGISTRY_SOURCE),
                ResourceRole("/workspace/project/**", "project", REGISTRY_SOURCE),
            ),
        )


def test_destination_constraint_lookup_and_allowed_data_role() -> None:
    context = reporting_context()

    destination = context.destination_policy_for(
        "network.send", "api:reporting-endpoint"
    )

    assert destination is not None
    assert destination.destination_purpose_id == "report_delivery"
    assert destination.allowed_data_role_ids == {"generated_report"}
    assert context.destination_policy_for("network.send", "api:other") is None


def test_missing_context_is_an_explicit_abstention_state() -> None:
    context = TaskContext(
        "1", "task-a", TaskPurpose("local_analysis", CONTRACT_SOURCE)
    )

    assessment = context.assess(
        (ContextField.PURPOSE, ContextField.DESTINATION_CONSTRAINTS)
    )

    assert assessment.status is ContextStatus.INSUFFICIENT_CONTEXT
    assert assessment.missing_fields == (ContextField.DESTINATION_CONSTRAINTS,)
    assert context.assess((ContextField.PURPOSE,)).status is ContextStatus.SUFFICIENT_CONTEXT


def test_conflicting_resource_roles_are_rejected() -> None:
    with pytest.raises(ContextValidationError, match="Conflicting resource roles"):
        TaskContext(
            "1",
            "task-a",
            TaskPurpose("analysis", CONTRACT_SOURCE),
            resource_roles=(
                ResourceRole("/workspace/project/**", "source_code", REGISTRY_SOURCE),
                ResourceRole(
                    "/workspace/project/**", "generated_report", REGISTRY_SOURCE
                ),
            ),
        )


def test_task_id_mismatch_is_rejected_by_binding_validation() -> None:
    contract = TaskContract("task-b", "different task")

    with pytest.raises(ContextValidationError, match="does not match"):
        validate_task_binding(contract, reporting_context())


def test_invalid_destination_declaration_is_rejected() -> None:
    destination = DestinationConstraint(
        "network.send",
        "api:reporting-endpoint",
        "reporting-api",
        "report_delivery",
        POLICY_SOURCE,
        allowed_data_role_ids=("undeclared_data_role",),
    )

    with pytest.raises(ContextValidationError, match="Unknown destination data role"):
        TaskContext(
            "1",
            "task-a",
            TaskPurpose("reporting", CONTRACT_SOURCE),
            destination_constraints=(destination,),
        )


def test_destination_without_purpose_is_rejected() -> None:
    with pytest.raises(ContextValidationError, match="destination_purpose_id"):
        DestinationConstraint(
            "network.send",
            "api:reporting-endpoint",
            "reporting-api",
            "",
            POLICY_SOURCE,
        )


def test_fallback_declaration_is_bounded_and_lookup_is_generic() -> None:
    fallback = FallbackPattern(
        action="filesystem.read",
        candidate_resource_scopes=("/opt/compat/**",),
        candidate_resource_role_ids=("compatibility_candidate",),
        purpose_id="compatibility_lookup",
        behavior_id="declared_fallback_lookup",
        maximum_attempts=4,
        source=CONTRACT_SOURCE,
    )
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("migration", CONTRACT_SOURCE),
        resource_roles=(
            ResourceRole("/opt/compat/**", "compatibility_candidate", REGISTRY_SOURCE),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "filesystem.read", "compatibility_lookup", CONTRACT_SOURCE
            ),
        ),
        fallback_patterns=(fallback,),
    )

    assert context.fallback_for("filesystem.read", "/opt/compat/v2/config") == fallback
    assert context.fallback_for("filesystem.read", "/etc/shadow") is None
    assert fallback.maximum_attempts == 4


def test_fallback_requires_a_semantic_bound_and_valid_scope() -> None:
    with pytest.raises(ContextValidationError, match="maximum_attempts"):
        FallbackPattern(
            "filesystem.read",
            ("/opt/compat/**",),
            (),
            "compatibility_lookup",
            "declared_fallback_lookup",
            CONTRACT_SOURCE,
        )
    with pytest.raises(ContextValidationError, match="invalid resource scope"):
        FallbackPattern(
            "filesystem.read",
            ("/opt/compat/../secret/**",),
            (),
            "compatibility_lookup",
            "declared_fallback_lookup",
            CONTRACT_SOURCE,
            maximum_attempts=2,
        )


def test_unsupported_context_schema_is_rejected() -> None:
    with pytest.raises(ContextValidationError, match="Unsupported context schema"):
        TaskContext("2", "task-a", TaskPurpose("analysis", CONTRACT_SOURCE))


def test_trusted_source_is_preserved_and_agent_source_is_rejected() -> None:
    assert reporting_context().purpose.source == CONTRACT_SOURCE
    untrusted = ContextSource(ContextAuthority.AGENT_SELF_REPORT, "message:agent-1")

    with pytest.raises(ContextValidationError, match="cannot declare task purpose"):
        TaskPurpose("self_claimed_reporting", untrusted)


def test_same_action_sequence_can_be_bound_to_distinct_contexts() -> None:
    trace = (
        ("filesystem.read", "/workspace/project/a.py"),
        ("network.send", "api:reporting-endpoint"),
    )
    local_context = TaskContext(
        "1", "task-a", TaskPurpose("local_analysis", CONTRACT_SOURCE)
    )
    remote_context = reporting_context()

    paired_inputs = ((trace, local_context), (trace, remote_context))

    assert paired_inputs[0][0] == paired_inputs[1][0]
    assert paired_inputs[0][1] != paired_inputs[1][1]


@dataclass
class RecordingTool:
    requests: list[ActionRequest] = field(default_factory=list)

    def execute(self, request: ActionRequest) -> object:
        self.requests.append(request)
        return "executed"


def network_request() -> ActionRequest:
    return ActionRequest(
        "request-1",
        "session-1",
        "task-a",
        "agent-1",
        "network.send",
        "api:reporting-endpoint",
    )


def test_task_context_never_grants_capability_authority() -> None:
    context = reporting_context()
    contract = TaskContract("task-a", "report without network authority")
    validate_task_binding(contract, context)
    tool = RecordingTool()

    result = ReferenceMonitor(TaskContractPolicy(contract), tool).execute(network_request())

    assert context.destination_policy_for(
        "network.send", "api:reporting-endpoint"
    ) is not None
    assert result.policy_decision.decision is Decision.DENY
    assert result.executed is False
    assert tool.requests == []


def test_task_contract_can_allow_action_absent_from_context() -> None:
    context = TaskContext(
        "1", "task-a", TaskPurpose("local_analysis", CONTRACT_SOURCE)
    )
    contract = TaskContract(
        "task-a",
        "network authority is independent",
        (Capability("network.send", "api:reporting-endpoint"),),
    )
    validate_task_binding(contract, context)
    tool = RecordingTool()

    result = ReferenceMonitor(TaskContractPolicy(contract), tool).execute(network_request())

    assert context.destination_policy_for(
        "network.send", "api:reporting-endpoint"
    ) is None
    assert result.policy_decision.decision is Decision.ALLOW
    assert result.executed is True
    assert tool.requests == [network_request()]
