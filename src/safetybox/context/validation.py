"""Cross-object validation for task context and authorization authority."""

from __future__ import annotations

from safetybox.context.models import ContextValidationError, TaskContext
from safetybox.contracts import TaskContract


def validate_task_binding(contract: TaskContract, context: TaskContext) -> None:
    """Reject a semantic context bound to a different authorization task."""
    if context.task_id != contract.task_id:
        raise ContextValidationError(
            "Task context task_id does not match the task contract task_id."
        )
