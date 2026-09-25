"""Normative executable model for AUTH-COVERAGE-001-PROTOCOL@1.

This module is deliberately outside ``src/safetybox`` and imports no SafetyBox
production authorization code.  It is the executable counterpart of the compact
specification in ``docs/experiments/AUTH-COVERAGE-001_AUTHORIZATION_SPEC.md``.
It reasons about logical authorization only; it never touches the filesystem or
starts a process.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

SPECIFICATION_ID = "AUTH-COVERAGE-001-AUTHORIZATION-SPEC@1"


class Decision(StrEnum):
    """The complete hard-authorization decision range."""

    ALLOW = "ALLOW"
    DENY = "DENY"


class Tool(StrEnum):
    """Mediators supported by benchmark version 1."""

    FILESYSTEM = "FILESYSTEM"
    PROCESS = "PROCESS"


@dataclass(frozen=True, slots=True)
class Capability:
    """One indivisible action/resource authority object.

    ``resource`` is either an exact identifier or an absolute canonical path
    subtree written ``/root/**``.  The generic production capability matcher
    permits canonical subtrees for any action; benchmark process families use
    exact resources as a corpus constraint.  Task binding is supplied only by
    the containing :class:`Contract`, matching the production kernel.
    """

    capability_id: str
    action: str
    resource: str


@dataclass(frozen=True, slots=True)
class Component:
    """One atomic authorization subdecision."""

    name: str
    action: str
    resource: str


@dataclass(frozen=True, slots=True)
class Request:
    """A normalized authorization request.

    ``argv`` and ``context`` are recorded operation/analysis data.  Neither is
    an authority input.  Subject and session are explanation facts in version 1;
    authenticated subject/session authority binding remains a non-claim.
    """

    request_id: str
    subject: str
    session_id: str
    task_id: str
    tool: Tool
    components: tuple[Component, ...]
    argv: tuple[str, ...] = ()
    context: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Contract:
    """A task-bound immutable authority snapshot."""

    contract_id: str
    task_id: str
    capabilities: tuple[Capability, ...]


@dataclass(frozen=True, slots=True)
class ComponentDecision:
    """Mechanically complete explanation for one atomic decision."""

    subject: str
    session_id: str
    task_id: str
    action: str
    resource: str
    capability_id: str | None
    rule: str
    authority_source: str
    component: str
    decision: Decision
    reason: str

    def explanation(self) -> Mapping[str, str | None]:
        return {
            "subject": self.subject,
            "session": self.session_id,
            "task": self.task_id,
            "action": self.action,
            "resource": self.resource,
            "capability": self.capability_id,
            "rule": self.rule,
            "authority_source": self.authority_source,
            "component": self.component,
            "decision": self.decision.value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """Top-level conjunctive result and its atomic evidence."""

    specification_id: str
    request_id: str
    contract_id: str
    decision: Decision
    rule: str
    reason: str
    subdecisions: tuple[ComponentDecision, ...]


@dataclass(frozen=True, slots=True)
class DelegationAuthority:
    """Synthetic model-level authority used only for delegation precursors."""

    authority_id: str
    task_id: str
    capabilities: tuple[Capability, ...]
    parent_authority: str | None = None


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def is_canonical_absolute_path(value: str) -> bool:
    """Recognize the frozen lexical logical-path representation."""
    if not value.startswith("/") or value == "/":
        return False
    return all(segment not in {"", ".", ".."} for segment in value[1:].split("/"))


def _is_subtree(resource: str) -> bool:
    return resource.endswith("/**")


def _subtree_root(resource: str) -> str:
    return resource.removesuffix("/**")


def resource_matches(scope: str, resource: str) -> bool:
    """Apply exact matching or canonical filesystem descendant matching.

    A ``/**`` scope does not include its root.  There is no I/O, symlink
    resolution, case folding, or Unicode normalization.
    """
    if _is_subtree(scope):
        root = _subtree_root(scope)
        return (
            is_canonical_absolute_path(root)
            and is_canonical_absolute_path(resource)
            and resource.startswith(f"{root}/")
        )
    return scope == resource


def _valid_capability(capability: Capability) -> bool:
    if not all(
        _is_nonempty_string(value)
        for value in (
            capability.capability_id,
            capability.action,
            capability.resource,
        )
    ):
        return False
    if _is_subtree(capability.resource):
        return is_canonical_absolute_path(_subtree_root(capability.resource))
    if capability.resource.startswith("/"):
        return is_canonical_absolute_path(capability.resource)
    return True


def _valid_component(component: Component) -> bool:
    if not all(
        _is_nonempty_string(value)
        for value in (component.name, component.action, component.resource)
    ):
        return False
    if component.resource.startswith("/"):
        return is_canonical_absolute_path(component.resource)
    return not _is_subtree(component.resource)


def _valid_shape(request: Request) -> bool:
    if not all(
        _is_nonempty_string(value)
        for value in (
            request.request_id,
            request.subject,
            request.session_id,
            request.task_id,
        )
    ):
        return False
    if request.tool is Tool.FILESYSTEM:
        return (
            len(request.components) == 1
            and request.components[0].name == "filesystem"
            and request.components[0].action.startswith("filesystem.")
        )
    if request.tool is Tool.PROCESS:
        return (
            len(request.components) == 2
            and request.components[0].name == "exec"
            and request.components[0].action == "process.exec"
            and request.components[1].name == "cwd"
            and request.components[1].action == "process.cwd"
        )
    return False


def _deny(
    request: Request,
    contract: Contract,
    component: Component,
    rule: str,
    reason: str,
) -> ComponentDecision:
    return ComponentDecision(
        subject=request.subject,
        session_id=request.session_id,
        task_id=request.task_id,
        action=component.action,
        resource=component.resource,
        capability_id=None,
        rule=rule,
        authority_source=f"TaskContract:{contract.contract_id}",
        component=component.name,
        decision=Decision.DENY,
        reason=reason,
    )


def authorize(request: Request, contract: Contract) -> AuthorizationDecision:
    """Evaluate the normative version-1 authorization function.

    No partial capability synthesis occurs: each component must be completely
    covered by one valid capability.  Compound PROCESS authority is the logical
    conjunction of its two independently retained subdecisions.
    """
    request_shape_valid = _valid_shape(request) and all(
        _valid_component(component) for component in request.components
    )
    contract_valid = (
        _is_nonempty_string(contract.contract_id)
        and _is_nonempty_string(contract.task_id)
        and len({item.capability_id for item in contract.capabilities})
        == len(contract.capabilities)
        and all(_valid_capability(item) for item in contract.capabilities)
    )

    if not request.components:
        placeholder = Component("invalid", "invalid", "invalid")
        subdecisions = (
            _deny(
                request,
                contract,
                placeholder,
                "AUTH.INVALID_STRUCTURE",
                "Malformed request or authority structure fails closed.",
            ),
        )
    elif not request_shape_valid or not contract_valid:
        subdecisions = tuple(
            _deny(
                request,
                contract,
                component,
                "AUTH.INVALID_STRUCTURE",
                "Malformed request or authority structure fails closed.",
            )
            for component in request.components
        )
    elif request.task_id != contract.task_id:
        subdecisions = tuple(
            _deny(
                request,
                contract,
                component,
                "AUTH.TASK_MISMATCH",
                "Request task does not match the authority contract task.",
            )
            for component in request.components
        )
    else:
        results: list[ComponentDecision] = []
        for component in request.components:
            matching = sorted(
                (
                    capability
                    for capability in contract.capabilities
                    if capability.action == component.action
                    and resource_matches(capability.resource, component.resource)
                ),
                key=lambda item: item.capability_id,
            )
            if not matching:
                results.append(
                    _deny(
                        request,
                        contract,
                        component,
                        "AUTH.NO_MATCHING_CAPABILITY",
                        "No single capability covers task, action, and resource.",
                    )
                )
                continue
            selected = matching[0]
            results.append(
                ComponentDecision(
                    subject=request.subject,
                    session_id=request.session_id,
                    task_id=request.task_id,
                    action=component.action,
                    resource=component.resource,
                    capability_id=selected.capability_id,
                    rule="AUTH.EXPLICIT_CAPABILITY",
                    authority_source=f"TaskContract:{contract.contract_id}",
                    component=component.name,
                    decision=Decision.ALLOW,
                    reason="One task-bound capability covers the complete component.",
                )
            )
        subdecisions = tuple(results)

    allowed = bool(subdecisions) and all(item.decision is Decision.ALLOW for item in subdecisions)
    return AuthorizationDecision(
        specification_id=SPECIFICATION_ID,
        request_id=request.request_id,
        contract_id=contract.contract_id,
        decision=Decision.ALLOW if allowed else Decision.DENY,
        rule="AUTH.ALL_COMPONENTS_ALLOWED" if allowed else "AUTH.ANY_COMPONENT_DENIED",
        reason=(
            "Every required component is independently authorized."
            if allowed
            else "At least one required component is unauthorized."
        ),
        subdecisions=subdecisions,
    )


def capability_is_subset(child: Capability, parent: Capability) -> bool:
    """Return whether one child capability is no broader than one parent."""
    if child.action != parent.action:
        return False
    child_tree = _is_subtree(child.resource)
    parent_tree = _is_subtree(parent.resource)
    if not child_tree:
        return resource_matches(parent.resource, child.resource)
    if not parent_tree:
        return False
    child_root = _subtree_root(child.resource)
    parent_root = _subtree_root(parent.resource)
    return child_root == parent_root or resource_matches(parent.resource, child_root)


def authority_is_attenuation(child: DelegationAuthority, parent: DelegationAuthority) -> bool:
    """Check the version-1 task/action/resource attenuation precursor.

    Every child capability must be contained by one parent capability.  Time,
    usage-count, and destination dimensions are reserved and not implemented.
    """
    if child.parent_authority != parent.authority_id or child.task_id != parent.task_id:
        return False
    if not all(_valid_capability(item) for item in child.capabilities):
        return False
    if not all(_valid_capability(item) for item in parent.capabilities):
        return False
    return all(
        any(capability_is_subset(child_cap, parent_cap) for parent_cap in parent.capabilities)
        for child_cap in child.capabilities
    )


def validate_delegation_chain(authorities: Iterable[DelegationAuthority]) -> bool:
    """Validate a root-first, acyclic, strictly linked attenuation chain."""
    chain = tuple(authorities)
    if not chain or chain[0].parent_authority is not None:
        return False
    if len({authority.authority_id for authority in chain}) != len(chain):
        return False
    return all(
        authority_is_attenuation(child, parent)
        for parent, child in zip(chain, chain[1:], strict=False)
    )


def explanation_complete(decision: AuthorizationDecision) -> bool:
    """Mechanically score required explanation field presence."""
    required = {
        "subject",
        "session",
        "task",
        "action",
        "resource",
        "capability",
        "rule",
        "authority_source",
        "component",
        "decision",
        "reason",
    }
    return bool(decision.subdecisions) and all(
        set(item.explanation()) == required
        and all(
            value is not None and value != ""
            for key, value in item.explanation().items()
            if key != "capability"
        )
        for item in decision.subdecisions
    )


def replace_non_authority_data(
    request: Request,
    *,
    argv: tuple[str, ...] | None = None,
    context: tuple[tuple[str, str], ...] | None = None,
) -> Request:
    """Construct a request differing only in explicitly non-authority data."""
    return Request(
        request_id=request.request_id,
        subject=request.subject,
        session_id=request.session_id,
        task_id=request.task_id,
        tool=request.tool,
        components=request.components,
        argv=request.argv if argv is None else argv,
        context=request.context if context is None else context,
    )


def decision_projection(decision: AuthorizationDecision) -> tuple[Any, ...]:
    """Return authority semantics while excluding selected evidence identity.

    Capability order may change which duplicate/overlapping evidence ID is
    selected.  It must never change authority outcomes or per-component rules.
    """
    return (
        decision.decision,
        decision.rule,
        tuple((item.component, item.decision, item.rule) for item in decision.subdecisions),
    )
