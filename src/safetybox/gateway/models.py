"""Immutable authority, action, decision, and effect models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    FLAG = "FLAG"


def utc_now() -> datetime:
    return datetime.now(UTC)


def freeze_value(value: Any) -> Any:
    """Recursively copy JSON-like authority data into immutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, (str, bytes, bool, int)) or value is None:
        return value
    raise TypeError(f"Unsupported authority value: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Authority:
    capability_id: str
    principal: str
    agent: str
    task: str
    action: str
    resource: str
    constraints: Mapping[str, Any]
    issuer: str
    issued_at: datetime
    expires_at: datetime | None = None
    parent_capability_id: str | None = None
    delegation_depth: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraints", freeze_value(self.constraints))


@dataclass(frozen=True, slots=True)
class Action:
    subject: str
    agent: str
    task: str
    operation: str
    resource: str
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", freeze_value(self.arguments))


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    decision: Decision
    authorized: bool
    action_digest: str
    policy_digest: str
    capability_id: str | None
    reason: str
    approval_id: str | None = None


@dataclass(frozen=True, slots=True)
class EffectResult:
    authorization: AuthorizationResult
    executed: bool
    value: Any = None
    effect_id: str | None = None
    result_class: str = "NOT_FORWARDED"


@dataclass(frozen=True, slots=True)
class PendingApproval:
    approval_id: str
    action_digest: str
    action: Action
    requested_at: datetime


@dataclass(frozen=True, slots=True)
class ApprovalCapability:
    approval_id: str
    capability_id: str
    action_digest: str
    approver: str
    issued_at: datetime
    expires_at: datetime
    used: bool = False
