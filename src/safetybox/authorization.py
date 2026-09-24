"""Small generic authorization-composition primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from safetybox.models import ActionRequest, Decision, PolicyDecision
from safetybox.protocols import Authorizer


def _freeze_evidence(value: object) -> object:
    """Recursively freeze compound-decision evidence before exposing it."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_evidence(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_evidence(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze_evidence(item) for item in value)
    return value


def _freeze_records(
    records: list[dict[str, object]],
) -> tuple[Mapping[str, object], ...]:
    return tuple(
        MappingProxyType({key: _freeze_evidence(value) for key, value in record.items()})
        for record in records
    )


class CompoundAuthorizationError(RuntimeError):
    """One or more compound subdecisions could not be evaluated."""

    def __init__(self, subdecisions: tuple[Mapping[str, object], ...]) -> None:
        super().__init__("Compound authorization failed closed.")
        self.audit_metadata = MappingProxyType({"subdecisions": subdecisions})


@dataclass(frozen=True, slots=True)
class AuthorizationComponent:
    """One named ordinary authorization request in a compound decision."""

    name: str
    request: ActionRequest

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Authorization component name must not be empty.")


@dataclass(frozen=True, slots=True)
class CompoundActionAuthorizer:
    """Evaluate ordered requests with potentially distinct actions.

    This is generic authorization composition, not a policy engine. Every
    component is delegated to the same authoritative authorizer and every
    ordinary denial is retained without short-circuiting.
    """

    delegate: Authorizer
    additional_components: tuple[AuthorizationComponent, ...]
    primary_name: str = "primary"

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        components = (
            AuthorizationComponent(self.primary_name, request),
            *self.additional_components,
        )
        records: list[dict[str, object]] = []
        decisions: list[PolicyDecision] = []
        failed = False
        for index, component in enumerate(components):
            component_request = component.request
            try:
                decision = self.delegate.authorize(component_request)
            except Exception as error:
                failed = True
                records.append(
                    {
                        "index": index,
                        "component": component.name,
                        "session_id": component_request.session_id,
                        "task_id": component_request.task_id,
                        "action": component_request.action,
                        "resource": component_request.resource,
                        "decision": "ERROR",
                        "error_type": type(error).__name__,
                    }
                )
                continue
            decisions.append(decision)
            records.append(
                {
                    "index": index,
                    "component": component.name,
                    "session_id": component_request.session_id,
                    "task_id": component_request.task_id,
                    "action": component_request.action,
                    "resource": component_request.resource,
                    "decision": decision.decision.value,
                    "rule_id": decision.rule_id,
                    "reason": decision.reason,
                    **dict(decision.metadata),
                }
            )

        frozen_records = _freeze_records(records)
        if failed:
            raise CompoundAuthorizationError(frozen_records)
        if all(item.decision is Decision.ALLOW for item in decisions):
            return PolicyDecision(
                Decision.ALLOW,
                "POL-COMPOUND-ALL-ALLOW",
                "Every bound authorization component received an explicit allow decision.",
                {"subdecisions": frozen_records},
            )
        return PolicyDecision(
            Decision.DENY,
            "POL-COMPOUND-DENY",
            "At least one bound authorization component was denied.",
            {"subdecisions": frozen_records},
        )


@dataclass(frozen=True, slots=True)
class CompoundAuthorizer:
    """Evaluate one action independently for a bound ordered resource tuple.

    The primary resource comes from ``ActionRequest.resource``. Additional
    resources are supplied at construction after request binding. Every
    subdecision is evaluated in order, including after an ordinary denial.
    """

    delegate: Authorizer
    additional_resources: tuple[str, ...]

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        records: list[dict[str, object]] = []
        decisions: list[PolicyDecision] = []
        failed = False
        for index, resource in enumerate((request.resource, *self.additional_resources)):
            derived = replace(request, resource=resource)
            try:
                decision = self.delegate.authorize(derived)
            except Exception as error:
                failed = True
                records.append(
                    {
                        "index": index,
                        "resource": resource,
                        "decision": "ERROR",
                        "error_type": type(error).__name__,
                    }
                )
                continue
            decisions.append(decision)
            records.append(
                {
                    "index": index,
                    "resource": resource,
                    "decision": decision.decision.value,
                    "rule_id": decision.rule_id,
                }
            )

        frozen_records = _freeze_records(records)
        if failed:
            raise CompoundAuthorizationError(frozen_records)
        if all(item.decision is Decision.ALLOW for item in decisions):
            return PolicyDecision(
                Decision.ALLOW,
                "POL-COMPOUND-ALL-ALLOW",
                "Every bound resource received an explicit allow decision.",
                {"subdecisions": frozen_records},
            )
        return PolicyDecision(
            Decision.DENY,
            "POL-COMPOUND-DENY",
            "At least one bound resource was denied.",
            {"subdecisions": frozen_records},
        )
