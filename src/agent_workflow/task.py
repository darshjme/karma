"""Task and TaskResult — the atomic units of a workflow."""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class TaskResult:
    """Result of a single task execution."""

    task_name: str
    success: bool
    output: Any
    error: Optional[str]
    duration_ms: float

    def to_dict(self) -> dict:
        return {
            "task_name": self.task_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class Task:
    """A unit of work in a workflow.

    Parameters
    ----------
    name:
        Unique identifier for this task within a workflow.
    func:
        Callable that performs the work.  It receives ``context`` as its first
        positional argument followed by any ``*args``/``**kwargs`` passed to
        :meth:`execute`.
    deps:
        Names of tasks that must complete successfully before this task runs.
    retry:
        Number of *extra* attempts on failure (0 = try once total).
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        deps: Optional[list[str]] = None,
        retry: int = 0,
    ) -> None:
        if not name:
            raise ValueError("Task name must be a non-empty string.")
        if not callable(func):
            raise TypeError(f"func must be callable, got {type(func)!r}.")
        if retry < 0:
            raise ValueError("retry must be >= 0.")

        self._name = name
        self._func = func
        self._deps: list[str] = list(deps) if deps else []
        self._retry = retry
        self._status: str = "pending"

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return self._name

    @property
    def deps(self) -> list[str]:
        return list(self._deps)

    @property
    def status(self) -> str:
        return self._status

    @property
    def retry(self) -> int:
        return self._retry

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def execute(self, *args: Any, **kwargs: Any) -> TaskResult:
        """Execute the task, honouring the retry count.

        Returns a :class:`TaskResult` regardless of success/failure.
        """
        self._status = "running"
        last_error: Optional[str] = None
        output: Any = None
        attempts = self._retry + 1

        start = time.perf_counter()
        for attempt in range(attempts):
            try:
                output = self._func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._status = "done"
                return TaskResult(
                    task_name=self._name,
                    success=True,
                    output=output,
                    error=None,
                    duration_ms=round(elapsed_ms, 3),
                )
            except Exception:  # noqa: BLE001
                last_error = traceback.format_exc()

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._status = "failed"
        return TaskResult(
            task_name=self._name,
            success=False,
            output=None,
            error=last_error,
            duration_ms=round(elapsed_ms, 3),
        )

    def reset(self) -> None:
        """Reset task status back to 'pending'."""
        self._status = "pending"

    def __repr__(self) -> str:
        return f"Task(name={self._name!r}, deps={self._deps!r}, status={self._status!r})"
