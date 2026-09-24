"""Immutable models for B4 bounded contextual trajectory monitoring."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from safetybox.context import ContextEvaluation, ContextSource
from safetybox.trajectory import CompletedActionObservation

MONITOR_VERSION = "B4-BOUNDED-CONTEXT-TRAJECTORY@1"
HISTORY_CONTEXT_SCHEMA_VERSION = "B4-HISTORY-CONTEXT@1"
CONFIG_VERSION = "B4-CONFIG@1"
ENABLED_RULE_IDS = ("B4TRJ-001", "B4TRJ-002", "B4TRJ-003", "B4TRJ-004")


class HistoryDimension(StrEnum):
    ROLE_COMBINATION = "ROLE_COMBINATION"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    FINALIZATION = "FINALIZATION"
    FALLBACK_PROGRESSION = "FALLBACK_PROGRESSION"


class Applicability(StrEnum):
    REQUIRED = "REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RestartPolicy(StrEnum):
    FORBIDDEN = "FORBIDDEN"
    AFTER_DECLARED_TERMINATION = "AFTER_DECLARED_TERMINATION"


class CyclePolicy(StrEnum):
    FORBIDDEN = "FORBIDDEN"
    DECLARED_TRANSITIONS_ONLY = "DECLARED_TRANSITIONS_ONLY"


class CandidateOrderMode(StrEnum):
    ORDERED = "ORDERED"
    EXPLICIT_TRANSITIONS = "EXPLICIT_TRANSITIONS"


class B4Classification(StrEnum):
    SUSPICIOUS = "SUSPICIOUS"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class ContextSufficiency(StrEnum):
    SUFFICIENT_CONTEXT = "SUFFICIENT_CONTEXT"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


@dataclass(frozen=True, slots=True)
class DimensionDeclaration:
    dimension: HistoryDimension
    applicability: Applicability
    source: ContextSource


@dataclass(frozen=True, slots=True)
class RoleGroup:
    group_id: str
    source: ContextSource
    resource_role_ids: frozenset[str] = field(default_factory=frozenset)
    data_role_ids: frozenset[str] = field(default_factory=frozenset)

    def __init__(
        self,
        group_id: str,
        source: ContextSource,
        resource_role_ids: Iterable[str] = (),
        data_role_ids: Iterable[str] = (),
    ) -> None:
        object.__setattr__(self, "group_id", group_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "resource_role_ids", frozenset(resource_role_ids))
        object.__setattr__(self, "data_role_ids", frozenset(data_role_ids))


@dataclass(frozen=True, slots=True)
class AggregationScope:
    scope_id: str
    opening_semantic_event_ids: frozenset[str]
    closing_semantic_event_ids: frozenset[str]
    tracked_role_group_ids: frozenset[str]
    source: ContextSource

    def __init__(
        self,
        scope_id: str,
        opening_semantic_event_ids: Iterable[str],
        closing_semantic_event_ids: Iterable[str],
        tracked_role_group_ids: Iterable[str],
        source: ContextSource,
    ) -> None:
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(
            self, "opening_semantic_event_ids", frozenset(opening_semantic_event_ids)
        )
        object.__setattr__(
            self, "closing_semantic_event_ids", frozenset(closing_semantic_event_ids)
        )
        object.__setattr__(self, "tracked_role_group_ids", frozenset(tracked_role_group_ids))
        object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class RoleCombination:
    resource_role_ids: frozenset[str] = field(default_factory=frozenset)
    data_role_ids: frozenset[str] = field(default_factory=frozenset)
    role_group_ids: frozenset[str] = field(default_factory=frozenset)

    def __init__(
        self,
        resource_role_ids: Iterable[str] = (),
        data_role_ids: Iterable[str] = (),
        role_group_ids: Iterable[str] = (),
    ) -> None:
        object.__setattr__(self, "resource_role_ids", frozenset(resource_role_ids))
        object.__setattr__(self, "data_role_ids", frozenset(data_role_ids))
        object.__setattr__(self, "role_group_ids", frozenset(role_group_ids))


@dataclass(frozen=True, slots=True)
class RoleCombinationConstraint:
    declaration_id: str
    aggregation_scope_id: str
    outcome_semantic_event_id: str
    tracked_resource_role_ids: frozenset[str]
    tracked_data_role_ids: frozenset[str]
    tracked_role_group_ids: frozenset[str]
    allowed_exact_projected_combinations: frozenset[RoleCombination]
    source: ContextSource

    def __init__(
        self,
        declaration_id: str,
        aggregation_scope_id: str,
        outcome_semantic_event_id: str,
        source: ContextSource,
        tracked_resource_role_ids: Iterable[str] = (),
        tracked_data_role_ids: Iterable[str] = (),
        tracked_role_group_ids: Iterable[str] = (),
        allowed_exact_projected_combinations: Iterable[RoleCombination] = (),
    ) -> None:
        object.__setattr__(self, "declaration_id", declaration_id)
        object.__setattr__(self, "aggregation_scope_id", aggregation_scope_id)
        object.__setattr__(self, "outcome_semantic_event_id", outcome_semantic_event_id)
        object.__setattr__(
            self, "tracked_resource_role_ids", frozenset(tracked_resource_role_ids)
        )
        object.__setattr__(self, "tracked_data_role_ids", frozenset(tracked_data_role_ids))
        object.__setattr__(self, "tracked_role_group_ids", frozenset(tracked_role_group_ids))
        object.__setattr__(
            self,
            "allowed_exact_projected_combinations",
            frozenset(allowed_exact_projected_combinations),
        )
        object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class SemanticEventBinding:
    binding_id: str
    semantic_event_id: str
    action: str
    source: ContextSource
    resource_role_id: str | None = None
    data_role_id: str | None = None
    destination_id: str | None = None
    action_purpose_id: str | None = None
    outcome_id: str | None = None


@dataclass(frozen=True, slots=True)
class PhaseDefinition:
    phase_id: str
    semantic_event_ids: frozenset[str]
    source: ContextSource
    initial: bool = False
    terminal: bool = False

    def __init__(
        self,
        phase_id: str,
        semantic_event_ids: Iterable[str],
        source: ContextSource,
        *,
        initial: bool = False,
        terminal: bool = False,
    ) -> None:
        object.__setattr__(self, "phase_id", phase_id)
        object.__setattr__(self, "semantic_event_ids", frozenset(semantic_event_ids))
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "initial", initial)
        object.__setattr__(self, "terminal", terminal)


@dataclass(frozen=True, slots=True)
class PhaseTransition:
    from_phase_id: str
    to_phase_id: str
    source: ContextSource


@dataclass(frozen=True, slots=True)
class FinalizationConstraint:
    finalization_id: str
    outcome_id: str
    finalization_semantic_event_id: str
    closed_phase_ids: frozenset[str]
    permitted_post_finalization_semantic_event_ids: frozenset[str]
    source: ContextSource

    def __init__(
        self,
        finalization_id: str,
        outcome_id: str,
        finalization_semantic_event_id: str,
        closed_phase_ids: Iterable[str],
        permitted_post_finalization_semantic_event_ids: Iterable[str],
        source: ContextSource,
    ) -> None:
        object.__setattr__(self, "finalization_id", finalization_id)
        object.__setattr__(self, "outcome_id", outcome_id)
        object.__setattr__(self, "finalization_semantic_event_id", finalization_semantic_event_id)
        object.__setattr__(self, "closed_phase_ids", frozenset(closed_phase_ids))
        object.__setattr__(
            self,
            "permitted_post_finalization_semantic_event_ids",
            frozenset(permitted_post_finalization_semantic_event_ids),
        )
        object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class FallbackCandidate:
    candidate_id: str
    resource_scope: str
    resource_role_id: str
    source: ContextSource


@dataclass(frozen=True, slots=True)
class CandidateTransition:
    from_candidate_id: str
    to_candidate_id: str


@dataclass(frozen=True, slots=True)
class FallbackProgressionConstraint:
    constraint_id: str
    linked_fallback_behavior_id: str
    candidates: tuple[FallbackCandidate, ...]
    allowed_candidate_transitions: frozenset[CandidateTransition]
    maximum_attempts: int
    restart_policy: RestartPolicy
    cycle_policy: CyclePolicy
    order_mode: CandidateOrderMode
    source: ContextSource
    termination_condition_id: str | None = None
    termination_semantic_event_id: str | None = None

    def __init__(
        self,
        constraint_id: str,
        linked_fallback_behavior_id: str,
        candidates: Iterable[FallbackCandidate],
        maximum_attempts: int,
        restart_policy: RestartPolicy,
        cycle_policy: CyclePolicy,
        order_mode: CandidateOrderMode,
        source: ContextSource,
        allowed_candidate_transitions: Iterable[CandidateTransition] = (),
        termination_condition_id: str | None = None,
        termination_semantic_event_id: str | None = None,
    ) -> None:
        object.__setattr__(self, "constraint_id", constraint_id)
        object.__setattr__(self, "linked_fallback_behavior_id", linked_fallback_behavior_id)
        object.__setattr__(self, "candidates", tuple(candidates))
        object.__setattr__(
            self, "allowed_candidate_transitions", frozenset(allowed_candidate_transitions)
        )
        object.__setattr__(self, "maximum_attempts", maximum_attempts)
        object.__setattr__(self, "restart_policy", restart_policy)
        object.__setattr__(self, "cycle_policy", cycle_policy)
        object.__setattr__(self, "order_mode", order_mode)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "termination_condition_id", termination_condition_id)
        object.__setattr__(self, "termination_semantic_event_id", termination_semantic_event_id)


@dataclass(frozen=True, slots=True)
class B4HistoricalConstraints:
    schema_version: str
    constraints_id: str
    task_id: str
    task_context_reference: str
    dimension_applicability: tuple[DimensionDeclaration, ...]
    role_groups: tuple[RoleGroup, ...] = ()
    aggregation_scopes: tuple[AggregationScope, ...] = ()
    role_combination_constraints: tuple[RoleCombinationConstraint, ...] = ()
    semantic_event_bindings: tuple[SemanticEventBinding, ...] = ()
    phase_definitions: tuple[PhaseDefinition, ...] = ()
    permitted_phase_transitions: tuple[PhaseTransition, ...] = ()
    finalization_constraints: tuple[FinalizationConstraint, ...] = ()
    fallback_progression_constraints: tuple[FallbackProgressionConstraint, ...] = ()

    def __init__(
        self,
        schema_version: str,
        constraints_id: str,
        task_id: str,
        task_context_reference: str,
        dimension_applicability: Iterable[DimensionDeclaration],
        role_groups: Iterable[RoleGroup] = (),
        aggregation_scopes: Iterable[AggregationScope] = (),
        role_combination_constraints: Iterable[RoleCombinationConstraint] = (),
        semantic_event_bindings: Iterable[SemanticEventBinding] = (),
        phase_definitions: Iterable[PhaseDefinition] = (),
        permitted_phase_transitions: Iterable[PhaseTransition] = (),
        finalization_constraints: Iterable[FinalizationConstraint] = (),
        fallback_progression_constraints: Iterable[FallbackProgressionConstraint] = (),
    ) -> None:
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "constraints_id", constraints_id)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "task_context_reference", task_context_reference)
        object.__setattr__(self, "dimension_applicability", tuple(dimension_applicability))
        object.__setattr__(self, "role_groups", tuple(role_groups))
        object.__setattr__(self, "aggregation_scopes", tuple(aggregation_scopes))
        object.__setattr__(
            self, "role_combination_constraints", tuple(role_combination_constraints)
        )
        object.__setattr__(self, "semantic_event_bindings", tuple(semantic_event_bindings))
        object.__setattr__(self, "phase_definitions", tuple(phase_definitions))
        object.__setattr__(
            self, "permitted_phase_transitions", tuple(permitted_phase_transitions)
        )
        object.__setattr__(self, "finalization_constraints", tuple(finalization_constraints))
        object.__setattr__(
            self,
            "fallback_progression_constraints",
            tuple(fallback_progression_constraints),
        )
        from safetybox.b4.validation import validate_history_context

        validate_history_context(self)

    def applicability_for(self, dimension: HistoryDimension) -> Applicability:
        return next(
            item.applicability
            for item in self.dimension_applicability
            if item.dimension is dimension
        )


@dataclass(frozen=True, slots=True)
class B4Config:
    config_version: str = CONFIG_VERSION
    window_size: int = 16
    max_findings: int = 32
    max_active_keys: int = 128
    strict_ordering: bool = True
    enabled_rule_ids: tuple[str, ...] = ENABLED_RULE_IDS
    insufficient_context_behavior: str = "EMIT_AND_DEDUPLICATE"
    destination_transition_rule: str = "DISABLED_NOT_IMPLEMENTED"

    def __post_init__(self) -> None:
        fixed = (
            CONFIG_VERSION,
            16,
            32,
            128,
            True,
            ENABLED_RULE_IDS,
            "EMIT_AND_DEDUPLICATE",
            "DISABLED_NOT_IMPLEMENTED",
        )
        supplied = (
            self.config_version,
            self.window_size,
            self.max_findings,
            self.max_active_keys,
            self.strict_ordering,
            self.enabled_rule_ids,
            self.insufficient_context_behavior,
            self.destination_transition_rule,
        )
        if supplied != fixed:
            raise ValueError("B4-CONFIG@1 is fixed and cannot be tuned.")


B4_CONFIG = B4Config()


@dataclass(frozen=True, slots=True)
class B4VersionInfo:
    monitor_version: str = MONITOR_VERSION
    history_context_schema_version: str = HISTORY_CONTEXT_SCHEMA_VERSION
    config_version: str = CONFIG_VERSION
    enabled_rule_ids: tuple[str, ...] = ENABLED_RULE_IDS


@dataclass(frozen=True, slots=True)
class B4ContextualizedObservation:
    observation: CompletedActionObservation
    context_evaluation: ContextEvaluation
    semantic_event_id: str | None
    semantic_binding_id: str | None


@dataclass(frozen=True, slots=True)
class RoleObservation:
    resource_role_id: str | None
    data_role_ids: tuple[str, ...]
    role_group_ids: tuple[str, ...]
    request_id: str
    sequence_number: int
    context_sources: tuple[ContextSource, ...]


@dataclass(frozen=True, slots=True)
class FallbackEpisodeSnapshot:
    constraint_id: str
    candidate_history: tuple[str, ...]
    attempt_count: int
    last_candidate_id: str | None
    terminated: bool
    termination_sequence: int | None
    restart_count: int
    source: ContextSource


@dataclass(frozen=True, slots=True)
class FinalizationSnapshot:
    finalization_id: str
    outcome_id: str
    finalization_sequence: int
    closed_phase_ids: tuple[str, ...]
    permitted_post_finalization_semantic_event_ids: tuple[str, ...]
    source: ContextSource


@dataclass(frozen=True, slots=True)
class B4StateSnapshot:
    active_phase_id: str | None
    accumulated_resource_role_ids: tuple[str, ...]
    accumulated_data_role_ids: tuple[str, ...]
    accumulated_role_group_ids: tuple[str, ...]
    role_observations: tuple[RoleObservation, ...]
    finalized_phase_ids: tuple[str, ...]
    finalizations: tuple[FinalizationSnapshot, ...]
    fallback_episodes: tuple[FallbackEpisodeSnapshot, ...]
    raw_window_sequence_numbers: tuple[int, ...]
    prefix_evicted: bool


@dataclass(frozen=True, slots=True)
class B4TrajectoryFinding:
    finding_id: str
    monitor_version: str
    config_version: str
    rule_id: str
    finding_type: str
    classification: B4Classification
    session_id: str
    task_id: str
    first_evidence_sequence: int
    detection_sequence: int
    request_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    historical_state_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    expected_relation: tuple[str, ...]
    observed_relation: tuple[str, ...]
    declaration_ids: tuple[str, ...]
    context_sources: tuple[ContextSource, ...]
    context_reason_ids: tuple[str, ...]
    context_sufficiency: ContextSufficiency
    missing_dimensions: tuple[HistoryDimension, ...]
    logical_lineage_available: bool
    explanation: str

    def __post_init__(self) -> None:
        if not self.request_ids or len(self.request_ids) != len(self.event_ids):
            raise ValueError("B4 finding evidence IDs must be aligned and non-empty.")
        if self.first_evidence_sequence > self.detection_sequence:
            raise ValueError("B4 finding sequence range is invalid.")


@dataclass(frozen=True, slots=True)
class B4Evaluation:
    session_id: str
    task_id: str
    emitted_findings: tuple[B4TrajectoryFinding, ...]
    retained_findings: tuple[B4TrajectoryFinding, ...]
    state: B4StateSnapshot
    context_evaluation: ContextEvaluation | None
    semantic_event_id: str | None
    active_phase_id: str | None
    accumulated_role_group_ids: tuple[str, ...]
    fallback_episodes: tuple[FallbackEpisodeSnapshot, ...]
    finding_retention_truncated: bool
    version_info: B4VersionInfo = B4VersionInfo()
