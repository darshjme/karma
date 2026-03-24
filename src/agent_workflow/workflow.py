"""Workflow and WorkflowResult — DAG-based orchestration engine."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Optional

from .dag import DAGValidator
from .task import Task, TaskResult


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""

    success: bool
    task_results: dict[str, TaskResult]
    duration_ms: float
    failed_tasks: list[str]

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_results": {k: v.to_dict() for k, v in self.task_results.items()},
            "duration_ms": self.duration_ms,
            "failed_tasks": self.failed_tasks,
        }


class Workflow:
    """DAG-based workflow that executes tasks in dependency order.

    Independent tasks (no unresolved dependencies at a given wave) are run
    in parallel using a :class:`~concurrent.futures.ThreadPoolExecutor`.

    Parameters
    ----------
    name:
        Human-readable workflow identifier.
    max_workers:
        Maximum thread-pool size for parallel task execution.
    """

    def __init__(self, name: str, max_workers: int = 8) -> None:
        if not name:
            raise ValueError("Workflow name must be a non-empty string.")
        self._name = name
        self._tasks: dict[str, Task] = {}
        self._max_workers = max_workers

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return self._name

    def add_task(self, task: Task) -> "Workflow":
        """Register a task and return *self* for fluent chaining."""
        if not isinstance(task, Task):
            raise TypeError(f"Expected Task, got {type(task)!r}.")
        if task.name in self._tasks:
            raise ValueError(f"Task '{task.name}' is already registered.")
        self._tasks[task.name] = task
        return self

    def validate(self) -> list[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors: list[str] = []

        missing = DAGValidator.find_missing_deps(self._tasks)
        for m in missing:
            errors.append(f"Missing dependency: {m}")

        if not missing and DAGValidator.has_cycle(self._tasks):
            errors.append("Cycle detected in the dependency graph.")

        return errors

    def task_order(self) -> list[str]:
        """Return task names in a valid topological execution order."""
        errors = self.validate()
        if errors:
            raise ValueError(
                "Workflow is invalid — fix errors before ordering:\n"
                + "\n".join(errors)
            )
        return DAGValidator.topological_sort(self._tasks)

    def run(self, context: Optional[dict] = None) -> WorkflowResult:
        """Execute the workflow.

        Tasks with all dependencies satisfied are dispatched in parallel.
        If a task fails its result is recorded, all tasks that (transitively)
        depend on it are skipped, and execution continues for unaffected
        branches.

        Parameters
        ----------
        context:
            Shared dictionary passed as the first argument to every task
            function.  Defaults to an empty dict.
        """
        if context is None:
            context = {}

        errors = self.validate()
        if errors:
            raise ValueError(
                "Cannot run an invalid workflow:\n" + "\n".join(errors)
            )

        # Reset all task statuses
        for task in self._tasks.values():
            task.reset()

        results: dict[str, TaskResult] = {}
        failed_tasks: list[str] = []
        skipped: set[str] = set()

        # Build in-degree and reverse-adjacency for wave-based scheduling
        in_degree: dict[str, int] = {}
        dependents: dict[str, list[str]] = {n: [] for n in self._tasks}
        for name, task in self._tasks.items():
            in_degree[name] = len(task.deps)
            for dep in task.deps:
                dependents[dep].append(name)

        ready: list[str] = [n for n, d in in_degree.items() if d == 0]

        wf_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            while ready:
                # Submit all currently-ready tasks in parallel
                future_to_name = {
                    executor.submit(
                        self._tasks[name].execute, context
                    ): name
                    for name in ready
                    if name not in skipped
                }
                ready = []

                for future in as_completed(future_to_name):
                    name = future_to_name[future]
                    result: TaskResult = future.result()
                    results[name] = result

                    if not result.success:
                        failed_tasks.append(name)
                        # Transitively skip dependents
                        self._mark_skipped(name, dependents, skipped, results)
                    else:
                        # Decrement in-degree of dependents; queue those ready
                        for dep_name in dependents[name]:
                            if dep_name in skipped:
                                continue
                            in_degree[dep_name] -= 1
                            if in_degree[dep_name] == 0:
                                ready.append(dep_name)

        wf_duration_ms = round((time.perf_counter() - wf_start) * 1000, 3)

        return WorkflowResult(
            success=len(failed_tasks) == 0,
            task_results=results,
            duration_ms=wf_duration_ms,
            failed_tasks=failed_tasks,
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _mark_skipped(
        failed: str,
        dependents: dict[str, list[str]],
        skipped: set[str],
        results: dict[str, TaskResult],
    ) -> None:
        """Recursively mark all tasks that depend on *failed* as skipped."""
        queue = list(dependents.get(failed, []))
        while queue:
            dep_name = queue.pop()
            if dep_name in skipped:
                continue
            skipped.add(dep_name)
            results[dep_name] = TaskResult(
                task_name=dep_name,
                success=False,
                output=None,
                error=f"Skipped: upstream task '{failed}' failed.",
                duration_ms=0.0,
            )
            queue.extend(dependents.get(dep_name, []))

    def __repr__(self) -> str:
        return f"Workflow(name={self._name!r}, tasks={list(self._tasks)!r})"
