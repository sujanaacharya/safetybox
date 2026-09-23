"""Immutable domain types for the M1 reference-monitor boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


def _immutable_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    """Copy a mapping before exposing it as an immutable view."""
    return MappingProxyType(dict(values))


class Decision(StrEnum):
    """The only enforcement outcomes implemented in M1."""

    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """A fully identified attempted action presented to the monitor."""

    request_id: str
    session_id: str
    task_id: str
    actor: str
    action: str
    resource: str
    arguments: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", _immutable_mapping(self.arguments))


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """A deterministic policy result with attributable rule information."""

    decision: Decision
    rule_id: str
    reason: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class EnforcementResult:
    """The outcome of one monitored action request."""

    request: ActionRequest
    policy_decision: PolicyDecision
    executed: bool
    tool_result: object | None = None
    correlation_id: str | None = None
