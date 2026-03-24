"""WorkflowStep — a single unit of work in a workflow DAG."""

from __future__ import annotations
from typing import Any, Callable


class WorkflowStep:
    """A single workflow step with optional dependencies and conditions."""

    def __init__(
        self,
        name: str,
        handler: Callable,
        depends_on: list[str] | None = None,
        condition: Callable[[dict], bool] | None = None,
        metadata: dict | None = None,
    ) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Step name must be a non-empty string.")
        if not callable(handler):
            raise TypeError(f"handler for step '{name}' must be callable.")

        self.name = name
        self.handler = handler
        self.depends_on: list[str] = depends_on or []
        self.condition: Callable[[dict], bool] | None = condition
        self.metadata: dict = metadata or {}

        # Mutable state (reset per run)
        self.status: str = "pending"   # pending | running | completed | failed | skipped
        self.result: Any = None
        self.error: str | None = None

    # ------------------------------------------------------------------
    # Readiness
    # ------------------------------------------------------------------

    def is_ready(self, completed: set[str], context: dict | None = None) -> bool:
        """Return True if all dependencies are completed and condition passes."""
        if self.status != "pending":
            return False
        if not set(self.depends_on).issubset(completed):
            return False
        if self.condition is not None:
            try:
                return bool(self.condition(context or {}))
            except Exception:
                return False
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset mutable state for a fresh run."""
        self.status = "pending"
        self.result = None
        self.error = None

    def __repr__(self) -> str:
        return f"WorkflowStep(name={self.name!r}, status={self.status!r})"
