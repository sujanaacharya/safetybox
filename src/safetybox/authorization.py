"""Small generic authorization-composition primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType

from safetybox.models import ActionRequest, Decision, PolicyDecision
from safetybox.protocols import Authorizer


class CompoundAuthorizationError(RuntimeError):
    """One or more compound subdecisions could not be evaluated."""

    def __init__(self, subdecisions: tuple[dict[str, object], ...]) -> None:
        super().__init__("Compound authorization failed closed.")
        self.audit_metadata = MappingProxyType({"subdecisions": subdecisions})


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

        frozen_records = tuple(records)
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
