"""Immutable M5 observations, findings, and evaluation snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from safetybox.models import Decision


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze(item) for item in value)
    return value


class FindingClassification(StrEnum):
    """Uncalibrated M5 finding classes, deliberately not risk scores."""

    INFO = "INFO"
    SUSPICIOUS = "SUSPICIOUS"


@dataclass(frozen=True, slots=True)
class CompletedActionObservation:
    """One terminal action outcome derived from a canonical M3 event.

    This is a compact rule input, not a second telemetry source: each instance
    preserves the canonical terminal event ID and its authoritative sequence.
    M5 currently emits observations only for executed successes and explicit
    authorization denials; failed or incomplete lifecycles are not action
    outcomes for the initial rules.
    """

    session_id: str
    task_id: str
    request_id: str
    actor: str
    action: str
    resource: str
    policy_decision: Decision
    executed: bool
    sequence_number: int
    canonical_event_id: str


@dataclass(frozen=True, slots=True)
class TrajectoryFinding:
    """Explainable, observational evidence that a deterministic rule matched."""

    finding_id: str
    session_id: str
    task_id: str
    rule_id: str
    finding_type: str
    classification: FindingClassification
    first_sequence_number: int
    last_sequence_number: int
    detection_sequence_number: int
    related_request_ids: tuple[str, ...]
    evidence: Mapping[str, object] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.related_request_ids:
            raise ValueError("Trajectory findings require related request IDs.")
        if self.first_sequence_number > self.last_sequence_number:
            raise ValueError("Finding sequence range is invalid.")
        if self.detection_sequence_number != self.last_sequence_number:
            raise ValueError("M5 finding detection must occur at its final evidence event.")
        frozen_evidence = _freeze(self.evidence)
        if not isinstance(frozen_evidence, Mapping):  # pragma: no cover - type invariant
            raise TypeError("Finding evidence must be a mapping.")
        object.__setattr__(self, "evidence", frozen_evidence)


@dataclass(frozen=True, slots=True)
class TrajectoryEvaluation:
    """Immutable snapshot for one session's processed canonical evidence."""

    session_id: str
    findings: tuple[TrajectoryFinding, ...]
    processed_event_count: int
    rule_ids: tuple[str, ...]
