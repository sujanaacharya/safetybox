"""Immutable models for deterministic context-aware trajectory reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from safetybox.context import (
    ContextEvaluation,
    ContextSource,
    ObservationContext,
)
from safetybox.trajectory import CompletedActionObservation


class ContextTrajectoryClassification(StrEnum):
    """Preregistered M5.1 semantic outcomes represented by emitted findings."""

    SUSPICIOUS = "SUSPICIOUS"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


@dataclass(frozen=True, slots=True)
class ContextualizedObservation:
    """One canonical observation paired with its frozen M5.1-B interpretation."""

    observation: CompletedActionObservation
    context_evaluation: ContextEvaluation
    supplied_context: ObservationContext


@dataclass(frozen=True, slots=True)
class ContextAwareTrajectoryFinding:
    """Explainable observational evidence from one context-aware rule match."""

    finding_id: str
    session_id: str
    task_id: str
    rule_id: str
    finding_type: str
    classification: ContextTrajectoryClassification
    first_sequence_number: int
    detection_sequence_number: int
    related_request_ids: tuple[str, ...]
    canonical_event_ids: tuple[str, ...]
    context_reason_ids: tuple[str, ...]
    context_sources: tuple[ContextSource, ...]
    matched_resource_role_ids: tuple[str, ...]
    matched_data_role_ids: tuple[str, ...]
    expected_context: tuple[str, ...]
    observed_context: tuple[str, ...]
    lineage_evidence_available: bool
    description: str

    def __post_init__(self) -> None:
        size = len(self.related_request_ids)
        if size == 0 or len(self.canonical_event_ids) != size:
            raise ValueError("Finding evidence requires aligned non-empty request/event IDs.")
        if self.first_sequence_number > self.detection_sequence_number:
            raise ValueError("Finding sequence range is invalid.")


@dataclass(frozen=True, slots=True)
class ContextAwareTrajectoryEvaluation:
    """Immutable bounded state and finding snapshot for one session/task pair."""

    session_id: str
    task_id: str
    findings: tuple[ContextAwareTrajectoryFinding, ...]
    recent_observations: tuple[CompletedActionObservation, ...]
    context_evaluations: tuple[ContextEvaluation, ...]
    processed_observation_count: int
    rule_ids: tuple[str, ...]
