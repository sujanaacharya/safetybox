"""Small, explicit, deterministic M5 trajectory rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from hashlib import sha256

from safetybox.models import Decision
from safetybox.trajectory.models import (
    CompletedActionObservation,
    FindingClassification,
    TrajectoryFinding,
)


class TrajectoryRule(ABC):
    """A stateless deterministic predicate over one task-local bounded history."""

    rule_id: str

    @abstractmethod
    def evaluate(
        self, history: Sequence[CompletedActionObservation]
    ) -> TrajectoryFinding | None:
        """Return one finding for a match ending at the current observation."""


def _finding_id(rule_id: str, observations: Sequence[CompletedActionObservation]) -> str:
    first = observations[0]
    material = "|".join((first.session_id, first.task_id, rule_id, *(
        item.request_id for item in observations
    )))
    return f"{rule_id}:{sha256(material.encode()).hexdigest()[:16]}"


class StagedCollectionToEgressRule(TrajectoryRule):
    """TRJ-001: two executed reads, an executed query, then executed network send."""

    rule_id = "TRJ-001"

    def evaluate(self, history: Sequence[CompletedActionObservation]) -> TrajectoryFinding | None:
        if len(history) < 4:
            return None
        matched = history[-4:]
        expected_actions = (
            "filesystem.read",
            "filesystem.read",
            "database.query",
            "network.send",
        )
        if tuple(item.action for item in matched) != expected_actions:
            return None
        if not all(item.policy_decision is Decision.ALLOW and item.executed for item in matched):
            return None
        first, last = matched[0], matched[-1]
        return TrajectoryFinding(
            finding_id=_finding_id(self.rule_id, matched),
            session_id=first.session_id,
            task_id=first.task_id,
            rule_id=self.rule_id,
            finding_type="STAGED_COLLECTION_TO_EGRESS",
            classification=FindingClassification.SUSPICIOUS,
            first_sequence_number=first.sequence_number,
            last_sequence_number=last.sequence_number,
            detection_sequence_number=last.sequence_number,
            related_request_ids=tuple(item.request_id for item in matched),
            evidence={
                "action_sequence": tuple(item.action for item in matched),
                "resources": tuple(item.resource for item in matched),
                "canonical_event_ids": tuple(item.canonical_event_id for item in matched),
                "observation_semantics": "executed_allowed_actions",
            },
            description=(
                "Observed two executed filesystem reads followed by an executed database query "
                "and an executed network send within one session and task."
            ),
        )


class RepeatedDeniedBoundaryProbingRule(TrajectoryRule):
    """TRJ-002: three denied requests for one action and three distinct resources."""

    rule_id = "TRJ-002"
    threshold = 3

    def evaluate(self, history: Sequence[CompletedActionObservation]) -> TrajectoryFinding | None:
        if not history:
            return None
        current = history[-1]
        if current.policy_decision is not Decision.DENY:
            return None
        denied = [
            item
            for item in history
            if item.policy_decision is Decision.DENY and item.action == current.action
        ]
        if len(denied) < self.threshold or len({item.resource for item in denied}) < self.threshold:
            return None
        matched = denied[-self.threshold :]
        first, last = matched[0], matched[-1]
        return TrajectoryFinding(
            finding_id=_finding_id(self.rule_id, matched),
            session_id=first.session_id,
            task_id=first.task_id,
            rule_id=self.rule_id,
            finding_type="REPEATED_DENIED_BOUNDARY_PROBING",
            classification=FindingClassification.SUSPICIOUS,
            first_sequence_number=first.sequence_number,
            last_sequence_number=last.sequence_number,
            detection_sequence_number=last.sequence_number,
            related_request_ids=tuple(item.request_id for item in matched),
            evidence={
                "action": current.action,
                "resources": tuple(item.resource for item in matched),
                "canonical_event_ids": tuple(item.canonical_event_id for item in matched),
                "threshold": self.threshold,
                "observation_semantics": "authorization_denied_actions",
            },
            description=(
                "Observed three denied requests for the same action across three distinct "
                "resources within one bounded session/task window."
            ),
        )
