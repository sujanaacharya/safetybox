"""Development-only M5.1-A contexts illustrating semantic contrasts."""

from safetybox.context import (
    AllowedOutcome,
    ContextAuthority,
    ContextSource,
    DataFlowConstraint,
    DataRole,
    DestinationConstraint,
    ExpectedActionPurpose,
    FallbackPattern,
    ResourceRole,
    TaskContext,
    TaskPurpose,
)

CONTRACT = ContextSource(ContextAuthority.TASK_CONTRACT, "example-contract:v1")
REGISTRY = ContextSource(ContextAuthority.RESOURCE_REGISTRY, "example-registry:v1")
POLICY = ContextSource(ContextAuthority.SYSTEM_POLICY, "example-policy:v1")


def local_analysis_context() -> TaskContext:
    """Context with dependency lookup but no declared inspected-data egress."""
    return TaskContext(
        "1",
        "example-analysis-task",
        TaskPurpose("local_analysis", CONTRACT),
        allowed_outcomes=(AllowedOutcome("local_report", CONTRACT),),
        data_roles=(
            DataRole("source_code", REGISTRY),
            DataRole("analytics_data", REGISTRY),
            DataRole("dependency_metadata", REGISTRY),
        ),
        resource_roles=(
            ResourceRole(
                "/workspace/project/**", "project_input", REGISTRY, "source_code"
            ),
            ResourceRole("db:analytics", "analytics_source", REGISTRY, "analytics_data"),
        ),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:dependency-index",
                "dependency-index",
                "dependency_lookup",
                POLICY,
                allowed_data_role_ids=("dependency_metadata",),
                allowed_action_purpose_ids=("lookup_dependency_metadata",),
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "network.send", "lookup_dependency_metadata", CONTRACT
            ),
        ),
    )


def report_delivery_context() -> TaskContext:
    """Context declaring a generated-report flow to a reporting endpoint."""
    return TaskContext(
        "1",
        "example-report-task",
        TaskPurpose("report_generation", CONTRACT),
        allowed_outcomes=(AllowedOutcome("remote_report_delivery", CONTRACT),),
        data_roles=(
            DataRole("analytics_data", REGISTRY),
            DataRole("generated_report", REGISTRY),
        ),
        resource_roles=(
            ResourceRole("db:analytics", "analytics_source", REGISTRY, "analytics_data"),
            ResourceRole(
                "artifact:generated-report",
                "report_artifact",
                REGISTRY,
                "generated_report",
            ),
        ),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:reporting-endpoint",
                "reporting-endpoint",
                "report_delivery",
                POLICY,
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
                CONTRACT,
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "deliver_report", CONTRACT),
        ),
    )


def compatibility_fallback_context() -> TaskContext:
    """Context with bounded, predeclared compatibility lookup behavior."""
    return TaskContext(
        "1",
        "example-migration-task",
        TaskPurpose("configuration_migration", CONTRACT),
        resource_roles=(
            ResourceRole("/opt/compat/**", "compatibility_candidate", REGISTRY),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "filesystem.read", "compatibility_lookup", CONTRACT
            ),
        ),
        fallback_patterns=(
            FallbackPattern(
                "filesystem.read",
                ("/opt/compat/**",),
                ("compatibility_candidate",),
                "compatibility_lookup",
                "declared_fallback_lookup",
                CONTRACT,
                maximum_attempts=4,
            ),
        ),
    )


def undeclared_probing_context() -> TaskContext:
    """Comparable task context with no trusted fallback declaration."""
    return TaskContext(
        "1",
        "example-undeclared-probing-task",
        TaskPurpose("local_diagnostics", CONTRACT),
    )
