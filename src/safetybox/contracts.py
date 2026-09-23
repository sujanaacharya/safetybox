"""Immutable task-scoped authority definitions for M2."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from safetybox.capabilities import Capability


@dataclass(frozen=True, slots=True)
class TaskContract:
    """The immutable authority ceiling for one task in the M2 abstraction."""

    task_id: str
    description: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)

    def __init__(
        self,
        task_id: str,
        description: str,
        capabilities: Iterable[Capability] = (),
    ) -> None:
        if not task_id:
            raise ValueError("Task contract task_id must not be empty.")
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "capabilities", frozenset(capabilities))
