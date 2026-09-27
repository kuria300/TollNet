"""Custom exceptions for the TollNet SDK."""

from typing import Any, Dict


class WorkRequiredException(Exception):
    """Exception raised when an AI agent lacks sufficient credits and must complete a compute work unit."""

    def __init__(self, task: Dict[str, Any]) -> None:
        """Initialize WorkRequiredException with the assigned work unit task dictionary.

        Args:
            task (Dict[str, Any]): The task/puzzle payload dictionary assigned by TollNet.
        """
        self.task: Dict[str, Any] = task
        super().__init__(
            f"Insufficient credits. Compute work unit required: {task.get('cause', 'Literature mining task')}"
        )
