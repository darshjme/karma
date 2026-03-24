"""DAGValidator — cycle detection, topological sort, missing-dep discovery."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task


class DAGValidator:
    """Validates and sorts a directed acyclic graph of tasks.

    All methods accept ``tasks`` as a ``dict[str, Task]`` mapping task name →
    Task object so they remain stateless and easily testable.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def has_cycle(tasks: dict) -> bool:
        """Return ``True`` if the dependency graph contains a cycle.

        Uses iterative DFS with a three-colour marking scheme
        (WHITE / GRAY / BLACK) to correctly detect back-edges.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        colour: dict[str, int] = {name: WHITE for name in tasks}

        def dfs(node: str) -> bool:
            stack = [(node, False)]
            while stack:
                n, returning = stack.pop()
                if returning:
                    colour[n] = BLACK
                    continue
                if colour[n] == GRAY:
                    return True  # back edge → cycle
                if colour[n] == BLACK:
                    continue
                colour[n] = GRAY
                stack.append((n, True))  # schedule finalization
                for dep in tasks[n].deps:
                    if dep not in tasks:
                        continue  # missing dep — handled elsewhere
                    if colour[dep] == GRAY:
                        return True
                    if colour[dep] == WHITE:
                        stack.append((dep, False))
            return False

        for name in tasks:
            if colour[name] == WHITE:
                if dfs(name):
                    return True
        return False

    @staticmethod
    def topological_sort(tasks: dict) -> list[str]:
        """Return a topological ordering using Kahn's algorithm (BFS).

        Raises ``ValueError`` if a cycle is detected or a dependency is
        missing.
        """
        # Build in-degree map and adjacency list (dep → dependents)
        in_degree: dict[str, int] = {name: 0 for name in tasks}
        dependents: dict[str, list[str]] = {name: [] for name in tasks}

        for name, task in tasks.items():
            for dep in task.deps:
                if dep not in tasks:
                    raise ValueError(
                        f"Task '{name}' depends on unknown task '{dep}'."
                    )
                dependents[dep].append(name)
                in_degree[name] += 1

        queue: deque[str] = deque(
            name for name, deg in in_degree.items() if deg == 0
        )
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(tasks):
            remaining = [n for n in tasks if n not in order]
            raise ValueError(
                f"Cycle detected among tasks: {remaining}"
            )
        return order

    @staticmethod
    def find_missing_deps(tasks: dict) -> list[str]:
        """Return a list of dependency names that are referenced but not
        defined in ``tasks``.

        Each entry is a string of the form ``'<task> -> <missing_dep>'``.
        """
        missing: list[str] = []
        for name, task in tasks.items():
            for dep in task.deps:
                if dep not in tasks:
                    missing.append(f"{name} -> {dep}")
        return missing
