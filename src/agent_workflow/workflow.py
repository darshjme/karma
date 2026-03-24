"""Workflow — a DAG of WorkflowSteps."""

from __future__ import annotations
from typing import Callable

from .step import WorkflowStep


class Workflow:
    """Directed Acyclic Graph of workflow steps."""

    def __init__(self, name: str) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Workflow name must be a non-empty string.")
        self.name = name
        self._steps: dict[str, WorkflowStep] = {}

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def add(self, step: WorkflowStep) -> "Workflow":
        """Add a step to the workflow. Fluent interface. Raises on duplicates."""
        if not isinstance(step, WorkflowStep):
            raise TypeError("Expected a WorkflowStep instance.")
        if step.name in self._steps:
            raise ValueError(f"Step '{step.name}' already exists in workflow '{self.name}'.")
        # Validate referenced dependencies exist (warn-only if added later; strict on run)
        self._steps[step.name] = step
        return self

    def step(
        self,
        name: str,
        depends_on: list[str] | None = None,
        condition: Callable[[dict], bool] | None = None,
        metadata: dict | None = None,
    ) -> Callable:
        """Decorator factory that creates and registers a WorkflowStep."""
        def decorator(fn: Callable) -> Callable:
            self.add(WorkflowStep(
                name=name,
                handler=fn,
                depends_on=depends_on,
                condition=condition,
                metadata=metadata,
            ))
            return fn
        return decorator

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    @property
    def steps(self) -> dict[str, WorkflowStep]:
        return self._steps

    def ready_steps(self, context: dict | None = None) -> list[WorkflowStep]:
        """Return steps whose dependencies are complete and conditions pass."""
        completed = {
            s.name for s in self._steps.values() if s.status == "completed"
        }
        # Also include skipped steps as "unblocking" (their dependents can proceed)
        skipped = {
            s.name for s in self._steps.values() if s.status == "skipped"
        }
        resolved = completed | skipped
        return [
            s for s in self._steps.values()
            if s.is_ready(resolved, context)
        ]

    @property
    def is_complete(self) -> bool:
        """True when every step is in a terminal state."""
        terminal = {"completed", "failed", "skipped"}
        return all(s.status in terminal for s in self._steps.values())

    @property
    def is_failed(self) -> bool:
        """True when any step has failed."""
        return any(s.status == "failed" for s in self._steps.values())

    def summary(self) -> dict:
        """Return status counts and workflow metadata."""
        counts: dict[str, int] = {}
        for s in self._steps.values():
            counts[s.status] = counts.get(s.status, 0) + 1
        return {
            "workflow": self.name,
            "total": len(self._steps),
            "status_counts": counts,
        }

    def reset(self) -> None:
        """Reset all steps for a fresh run."""
        for s in self._steps.values():
            s.reset()

    def _validate(self) -> None:
        """Check for missing dependencies (fail-fast before execution)."""
        names = set(self._steps)
        for step in self._steps.values():
            for dep in step.depends_on:
                if dep not in names:
                    raise ValueError(
                        f"Step '{step.name}' depends on unknown step '{dep}'."
                    )

    def __repr__(self) -> str:
        return f"Workflow(name={self.name!r}, steps={list(self._steps)})"
