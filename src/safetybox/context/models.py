"""Immutable trusted semantic context declarations for M5.1-A."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

from safetybox.capabilities import is_valid_resource_scope, resource_matches


class ContextValidationError(ValueError):
    """Raised when trusted context is malformed, conflicting, or untrusted."""


class AmbiguousContextError(ContextValidationError):
    """Raised when a lookup matches more than one declaration."""


class ContextAuthority(StrEnum):
    """Authorities recognized by the registered context trust boundary."""

    TASK_CONTRACT = "TASK_CONTRACT"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    RESOURCE_REGISTRY = "RESOURCE_REGISTRY"
    TOOL_ADAPTER = "TOOL_ADAPTER"
    AGENT_SELF_REPORT = "AGENT_SELF_REPORT"

    @property
    def is_trusted(self) -> bool:
        """Return whether this authority may contribute trusted context."""
        return self is not ContextAuthority.AGENT_SELF_REPORT


@dataclass(frozen=True, slots=True)
class ContextSource:
    """Immutable provenance for one context declaration."""

    authority: ContextAuthority
    immutable_reference: str

    def __post_init__(self) -> None:
        if not self.immutable_reference:
            raise ContextValidationError("Context source immutable_reference must not be empty.")


@dataclass(frozen=True, slots=True)
class TaskPurpose:
    """Externally declared, machine-usable task purpose."""

    purpose_id: str
    source: ContextSource
    description: str = ""

    def __post_init__(self) -> None:
        _require_identifier("Task purpose purpose_id", self.purpose_id)
        _require_trusted(self.source, "task purpose")


@dataclass(frozen=True, slots=True)
class AllowedOutcome:
    """A legitimate result declared for a task."""

    outcome_id: str
    source: ContextSource

    def __post_init__(self) -> None:
        _require_identifier("Allowed outcome outcome_id", self.outcome_id)
        _require_trusted(self.source, "allowed outcome")


@dataclass(frozen=True, slots=True)
class DataRole:
    """A lightweight logical data class; no payload classification is implied."""

    role_id: str
    source: ContextSource
    description: str = ""

    def __post_init__(self) -> None:
        _require_identifier("Data role role_id", self.role_id)
        _require_trusted(self.source, "data role")


@dataclass(frozen=True, slots=True)
class ResourceRole:
    """Trusted semantic binding from an M2 resource scope to a role."""

    resource_scope: str
    role_id: str
    source: ContextSource
    data_role_id: str | None = None

    def __post_init__(self) -> None:
        if not is_valid_resource_scope(self.resource_scope):
            raise ContextValidationError(
                f"Resource role has invalid resource scope: {self.resource_scope!r}."
            )
        _require_identifier("Resource role role_id", self.role_id)
        if self.data_role_id is not None:
            _require_identifier("Resource role data_role_id", self.data_role_id)
        _require_trusted(self.source, "resource role")


@dataclass(frozen=True, slots=True)
class DestinationConstraint:
    """Declared semantic constraints for one outbound action and destination scope."""

    action: str
    destination_scope: str
    destination_id: str
    destination_purpose_id: str
    source: ContextSource
    allowed_data_role_ids: frozenset[str] = field(default_factory=frozenset)
    allowed_outcome_ids: frozenset[str] = field(default_factory=frozenset)
    allowed_action_purpose_ids: frozenset[str] = field(default_factory=frozenset)

    def __init__(
        self,
        action: str,
        destination_scope: str,
        destination_id: str,
        destination_purpose_id: str,
        source: ContextSource,
        allowed_data_role_ids: Iterable[str] = (),
        allowed_outcome_ids: Iterable[str] = (),
        allowed_action_purpose_ids: Iterable[str] = (),
    ) -> None:
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "destination_scope", destination_scope)
        object.__setattr__(self, "destination_id", destination_id)
        object.__setattr__(self, "destination_purpose_id", destination_purpose_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "allowed_data_role_ids", frozenset(allowed_data_role_ids))
        object.__setattr__(self, "allowed_outcome_ids", frozenset(allowed_outcome_ids))
        object.__setattr__(
            self, "allowed_action_purpose_ids", frozenset(allowed_action_purpose_ids)
        )
        self._validate()

    def _validate(self) -> None:
        _require_identifier("Destination action", self.action)
        if not is_valid_resource_scope(self.destination_scope):
            raise ContextValidationError(
                f"Destination has invalid resource scope: {self.destination_scope!r}."
            )
        _require_identifier("Destination destination_id", self.destination_id)
        _require_identifier("Destination destination_purpose_id", self.destination_purpose_id)
        _require_identifiers("Destination allowed_data_role_ids", self.allowed_data_role_ids)
        _require_identifiers("Destination allowed_outcome_ids", self.allowed_outcome_ids)
        _require_identifiers(
            "Destination allowed_action_purpose_ids", self.allowed_action_purpose_ids
        )
        _require_trusted(self.source, "destination constraint")


@dataclass(frozen=True, slots=True)
class DataFlowConstraint:
    """A permitted logical derivation and destination relationship."""

    source_resource_role_ids: frozenset[str]
    derived_data_role_id: str
    destination_purpose_id: str
    allowed_action_purpose_ids: frozenset[str]
    source: ContextSource

    def __init__(
        self,
        source_resource_role_ids: Iterable[str],
        derived_data_role_id: str,
        destination_purpose_id: str,
        allowed_action_purpose_ids: Iterable[str],
        source: ContextSource,
    ) -> None:
        object.__setattr__(
            self, "source_resource_role_ids", frozenset(source_resource_role_ids)
        )
        object.__setattr__(self, "derived_data_role_id", derived_data_role_id)
        object.__setattr__(self, "destination_purpose_id", destination_purpose_id)
        object.__setattr__(
            self, "allowed_action_purpose_ids", frozenset(allowed_action_purpose_ids)
        )
        object.__setattr__(self, "source", source)
        if not self.source_resource_role_ids:
            raise ContextValidationError("Data flow must declare a source resource role.")
        _require_identifiers("Data flow source_resource_role_ids", self.source_resource_role_ids)
        _require_identifier("Data flow derived_data_role_id", self.derived_data_role_id)
        _require_identifier("Data flow destination_purpose_id", self.destination_purpose_id)
        if not self.allowed_action_purpose_ids:
            raise ContextValidationError("Data flow must declare an allowed action purpose.")
        _require_identifiers(
            "Data flow allowed_action_purpose_ids", self.allowed_action_purpose_ids
        )
        _require_trusted(self.source, "data flow constraint")


@dataclass(frozen=True, slots=True)
class ExpectedActionPurpose:
    """A task-scoped declaration of why an action is expected."""

    action: str
    purpose_id: str
    source: ContextSource

    def __post_init__(self) -> None:
        _require_identifier("Expected action", self.action)
        _require_identifier("Expected action purpose_id", self.purpose_id)
        _require_trusted(self.source, "expected action purpose")


@dataclass(frozen=True, slots=True)
class FallbackPattern:
    """Bounded expected fallback behavior, independent of detector thresholds."""

    action: str
    candidate_resource_scopes: tuple[str, ...]
    candidate_resource_role_ids: frozenset[str]
    purpose_id: str
    behavior_id: str
    source: ContextSource
    maximum_attempts: int | None = None
    termination_condition_id: str | None = None

    def __init__(
        self,
        action: str,
        candidate_resource_scopes: Iterable[str],
        candidate_resource_role_ids: Iterable[str],
        purpose_id: str,
        behavior_id: str,
        source: ContextSource,
        maximum_attempts: int | None = None,
        termination_condition_id: str | None = None,
    ) -> None:
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "candidate_resource_scopes", tuple(candidate_resource_scopes))
        object.__setattr__(
            self, "candidate_resource_role_ids", frozenset(candidate_resource_role_ids)
        )
        object.__setattr__(self, "purpose_id", purpose_id)
        object.__setattr__(self, "behavior_id", behavior_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "maximum_attempts", maximum_attempts)
        object.__setattr__(self, "termination_condition_id", termination_condition_id)
        self._validate()

    def _validate(self) -> None:
        _require_identifier("Fallback action", self.action)
        if not self.candidate_resource_scopes:
            raise ContextValidationError("Fallback must declare candidate resource scopes.")
        for scope in self.candidate_resource_scopes:
            if not is_valid_resource_scope(scope):
                raise ContextValidationError(f"Fallback has invalid resource scope: {scope!r}.")
        _require_identifiers(
            "Fallback candidate_resource_role_ids", self.candidate_resource_role_ids
        )
        _require_identifier("Fallback purpose_id", self.purpose_id)
        _require_identifier("Fallback behavior_id", self.behavior_id)
        if self.maximum_attempts is None and self.termination_condition_id is None:
            raise ContextValidationError(
                "Fallback must declare maximum_attempts or termination_condition_id."
            )
        if self.maximum_attempts is not None and self.maximum_attempts < 1:
            raise ContextValidationError("Fallback maximum_attempts must be positive.")
        if self.termination_condition_id is not None:
            _require_identifier(
                "Fallback termination_condition_id", self.termination_condition_id
            )
        _require_trusted(self.source, "fallback pattern")


class ContextField(StrEnum):
    """Semantic dimensions a future evaluation may require."""

    PURPOSE = "purpose"
    ALLOWED_OUTCOMES = "allowed_outcomes"
    DATA_ROLES = "data_roles"
    RESOURCE_ROLES = "resource_roles"
    DESTINATION_CONSTRAINTS = "destination_constraints"
    DATA_FLOW_CONSTRAINTS = "data_flow_constraints"
    EXPECTED_ACTION_PURPOSES = "expected_action_purposes"
    FALLBACK_PATTERNS = "fallback_patterns"


class ContextStatus(StrEnum):
    """Protocol terminology for presence of required semantic context."""

    SUFFICIENT_CONTEXT = "SUFFICIENT_CONTEXT"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    """Deterministic result of checking explicitly required context fields."""

    status: ContextStatus
    missing_fields: tuple[ContextField, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskContext:
    """Immutable, externally trusted semantic context for one task."""

    schema_version: str
    task_id: str
    purpose: TaskPurpose
    allowed_outcomes: tuple[AllowedOutcome, ...] = ()
    data_roles: tuple[DataRole, ...] = ()
    resource_roles: tuple[ResourceRole, ...] = ()
    destination_constraints: tuple[DestinationConstraint, ...] = ()
    data_flow_constraints: tuple[DataFlowConstraint, ...] = ()
    expected_action_purposes: tuple[ExpectedActionPurpose, ...] = ()
    fallback_patterns: tuple[FallbackPattern, ...] = ()

    def __init__(
        self,
        schema_version: str,
        task_id: str,
        purpose: TaskPurpose,
        allowed_outcomes: Iterable[AllowedOutcome] = (),
        data_roles: Iterable[DataRole] = (),
        resource_roles: Iterable[ResourceRole] = (),
        destination_constraints: Iterable[DestinationConstraint] = (),
        data_flow_constraints: Iterable[DataFlowConstraint] = (),
        expected_action_purposes: Iterable[ExpectedActionPurpose] = (),
        fallback_patterns: Iterable[FallbackPattern] = (),
    ) -> None:
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "allowed_outcomes", tuple(allowed_outcomes))
        object.__setattr__(self, "data_roles", tuple(data_roles))
        object.__setattr__(self, "resource_roles", tuple(resource_roles))
        object.__setattr__(self, "destination_constraints", tuple(destination_constraints))
        object.__setattr__(self, "data_flow_constraints", tuple(data_flow_constraints))
        object.__setattr__(
            self, "expected_action_purposes", tuple(expected_action_purposes)
        )
        object.__setattr__(self, "fallback_patterns", tuple(fallback_patterns))
        self._validate()

    def _validate(self) -> None:
        if self.schema_version != "1":
            raise ContextValidationError(
                f"Unsupported context schema version: {self.schema_version!r}."
            )
        _require_identifier("Task context task_id", self.task_id)
        _reject_duplicate_ids(
            "allowed outcome", (item.outcome_id for item in self.allowed_outcomes)
        )
        _reject_duplicate_ids("data role", (item.role_id for item in self.data_roles))
        _reject_conflicting_scopes(self.resource_roles)
        _reject_duplicate_destination_bindings(self.destination_constraints)
        _reject_duplicate_declarations("data flow", self.data_flow_constraints)
        _reject_duplicate_declarations(
            "expected action purpose", self.expected_action_purposes
        )
        _reject_overlapping_fallbacks(self.fallback_patterns)

        outcome_ids = {item.outcome_id for item in self.allowed_outcomes}
        data_role_ids = {item.role_id for item in self.data_roles}
        resource_role_ids = {item.role_id for item in self.resource_roles}
        destination_purpose_ids = {
            item.destination_purpose_id for item in self.destination_constraints
        }
        action_purpose_ids = {
            item.purpose_id for item in self.expected_action_purposes
        }
        action_purpose_pairs = {
            (item.action, item.purpose_id) for item in self.expected_action_purposes
        }
        for destination in self.destination_constraints:
            _require_known(
                "destination data role", destination.allowed_data_role_ids, data_role_ids
            )
            _require_known(
                "destination outcome", destination.allowed_outcome_ids, outcome_ids
            )
            _require_known(
                "destination action purpose",
                destination.allowed_action_purpose_ids,
                action_purpose_ids,
            )
            _require_action_purposes(
                "destination",
                destination.action,
                destination.allowed_action_purpose_ids,
                action_purpose_pairs,
            )
        for resource in self.resource_roles:
            if resource.data_role_id is not None:
                _require_known("resource data role", {resource.data_role_id}, data_role_ids)
        for flow in self.data_flow_constraints:
            _require_known(
                "data flow resource role", flow.source_resource_role_ids, resource_role_ids
            )
            _require_known(
                "data flow derived data role", {flow.derived_data_role_id}, data_role_ids
            )
            _require_known(
                "data flow destination purpose",
                {flow.destination_purpose_id},
                destination_purpose_ids,
            )
            _require_known(
                "data flow action purpose",
                flow.allowed_action_purpose_ids,
                action_purpose_ids,
            )
        for fallback in self.fallback_patterns:
            _require_known(
                "fallback resource role",
                fallback.candidate_resource_role_ids,
                resource_role_ids,
            )
            _require_known(
                "fallback action purpose", {fallback.purpose_id}, action_purpose_ids
            )
            _require_action_purposes(
                "fallback",
                fallback.action,
                {fallback.purpose_id},
                action_purpose_pairs,
            )

    def role_for(self, resource: str) -> ResourceRole | None:
        """Return the sole matching role using canonical M2 scope semantics."""
        matches = tuple(
            binding
            for binding in self.resource_roles
            if resource_matches(binding.resource_scope, resource)
        )
        return _sole_match("resource role", resource, matches)

    def destination_policy_for(
        self, action: str, destination: str
    ) -> DestinationConstraint | None:
        """Return the sole matching destination constraint."""
        matches = tuple(
            constraint
            for constraint in self.destination_constraints
            if constraint.action == action
            and resource_matches(constraint.destination_scope, destination)
        )
        return _sole_match("destination constraint", destination, matches)

    def fallback_for(self, action: str, resource: str) -> FallbackPattern | None:
        """Return the sole declared fallback matching an action and candidate resource."""
        matches = tuple(
            pattern
            for pattern in self.fallback_patterns
            if pattern.action == action
            and any(
                resource_matches(scope, resource)
                for scope in pattern.candidate_resource_scopes
            )
        )
        return _sole_match("fallback pattern", resource, matches)

    def assess(self, required_fields: Iterable[ContextField]) -> ContextAssessment:
        """Check presence only for semantic dimensions explicitly required by a caller."""
        required = frozenset(required_fields)
        present = {
            ContextField.PURPOSE: bool(self.purpose.purpose_id),
            ContextField.ALLOWED_OUTCOMES: bool(self.allowed_outcomes),
            ContextField.DATA_ROLES: bool(self.data_roles),
            ContextField.RESOURCE_ROLES: bool(self.resource_roles),
            ContextField.DESTINATION_CONSTRAINTS: bool(self.destination_constraints),
            ContextField.DATA_FLOW_CONSTRAINTS: bool(self.data_flow_constraints),
            ContextField.EXPECTED_ACTION_PURPOSES: bool(self.expected_action_purposes),
            ContextField.FALLBACK_PATTERNS: bool(self.fallback_patterns),
        }
        missing = tuple(field for field in ContextField if field in required and not present[field])
        status = (
            ContextStatus.INSUFFICIENT_CONTEXT
            if missing
            else ContextStatus.SUFFICIENT_CONTEXT
        )
        return ContextAssessment(status, missing)


def _require_identifier(label: str, value: str) -> None:
    if not value or value.strip() != value or any(character.isspace() for character in value):
        raise ContextValidationError(
            f"{label} must be a non-empty identifier without whitespace."
        )


def _require_identifiers(label: str, values: Iterable[str]) -> None:
    for value in values:
        _require_identifier(label, value)


def _require_trusted(source: ContextSource, declaration: str) -> None:
    if not source.authority.is_trusted:
        raise ContextValidationError(
            f"Untrusted authority {source.authority.value} cannot declare {declaration}."
        )


def _reject_duplicate_ids(label: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ContextValidationError(f"Duplicate {label} identifier: {value!r}.")
        seen.add(value)


def _reject_conflicting_scopes(bindings: tuple[ResourceRole, ...]) -> None:
    for index, binding in enumerate(bindings):
        for existing in bindings[:index]:
            if _scopes_overlap(existing.resource_scope, binding.resource_scope):
                if existing.resource_scope != binding.resource_scope:
                    raise ContextValidationError(
                        "Overlapping resource role scopes are ambiguous: "
                        f"{existing.resource_scope!r} and {binding.resource_scope!r}."
                    )
                if existing != binding:
                    raise ContextValidationError(
                        f"Conflicting resource roles for scope {binding.resource_scope!r}."
                    )
                raise ContextValidationError(
                    f"Duplicate resource role declaration for scope {binding.resource_scope!r}."
                )


def _reject_duplicate_destination_bindings(
    bindings: tuple[DestinationConstraint, ...],
) -> None:
    for index, binding in enumerate(bindings):
        for existing in bindings[:index]:
            if binding.action == existing.action and _scopes_overlap(
                binding.destination_scope, existing.destination_scope
            ):
                raise ContextValidationError(
                    "Duplicate, conflicting, or overlapping destination constraint for "
                    f"action {binding.action!r}."
                )


def _reject_duplicate_declarations(label: str, declarations: tuple[object, ...]) -> None:
    if len(set(declarations)) != len(declarations):
        raise ContextValidationError(f"Duplicate {label} declaration.")


def _reject_overlapping_fallbacks(bindings: tuple[FallbackPattern, ...]) -> None:
    for index, binding in enumerate(bindings):
        for existing in bindings[:index]:
            if binding.action != existing.action:
                continue
            if any(
                _scopes_overlap(scope, existing_scope)
                for scope in binding.candidate_resource_scopes
                for existing_scope in existing.candidate_resource_scopes
            ):
                raise ContextValidationError(
                    "Overlapping fallback patterns are ambiguous for action "
                    f"{binding.action!r}."
                )


def _require_known(label: str, referenced: Iterable[str], known: set[str]) -> None:
    unknown = sorted(set(referenced) - known)
    if unknown:
        raise ContextValidationError(f"Unknown {label} identifier(s): {unknown!r}.")


def _require_action_purposes(
    label: str,
    action: str,
    purpose_ids: Iterable[str],
    known_pairs: set[tuple[str, str]],
) -> None:
    unknown = sorted(
        purpose_id
        for purpose_id in purpose_ids
        if (action, purpose_id) not in known_pairs
    )
    if unknown:
        raise ContextValidationError(
            f"Unknown {label} purpose(s) for action {action!r}: {unknown!r}."
        )


def _scopes_overlap(first: str, second: str) -> bool:
    if first == second:
        return True
    if first.endswith("/**") and second.endswith("/**"):
        first_probe = f"{first.removesuffix('/**')}/__context_probe__"
        second_probe = f"{second.removesuffix('/**')}/__context_probe__"
        return resource_matches(first, second_probe) or resource_matches(second, first_probe)
    return resource_matches(first, second) or resource_matches(second, first)


_Declaration = TypeVar("_Declaration")


def _sole_match(
    label: str, resource: str, matches: tuple[_Declaration, ...]
) -> _Declaration | None:
    if len(matches) > 1:
        raise AmbiguousContextError(
            f"Ambiguous {label} lookup for resource {resource!r}: {len(matches)} matches."
        )
    return matches[0] if matches else None
