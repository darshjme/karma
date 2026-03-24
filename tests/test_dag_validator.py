"""Tests for DAGValidator."""

import pytest
from agent_workflow import Task, DAGValidator


def noop(ctx):
    return None


def make_tasks(*specs):
    """specs: list of (name, deps) tuples."""
    return {name: Task(name, noop, deps=deps) for name, deps in specs}


class TestHasCycle:
    def test_no_cycle_linear(self):
        tasks = make_tasks(("a", []), ("b", ["a"]), ("c", ["b"]))
        assert DAGValidator.has_cycle(tasks) is False

    def test_no_cycle_diamond(self):
        tasks = make_tasks(("a", []), ("b", ["a"]), ("c", ["a"]), ("d", ["b", "c"]))
        assert DAGValidator.has_cycle(tasks) is False

    def test_simple_cycle(self):
        tasks = make_tasks(("a", ["b"]), ("b", ["a"]))
        assert DAGValidator.has_cycle(tasks) is True

    def test_self_loop(self):
        tasks = make_tasks(("a", ["a"]))
        assert DAGValidator.has_cycle(tasks) is True

    def test_longer_cycle(self):
        tasks = make_tasks(("a", []), ("b", ["a"]), ("c", ["b"]), ("d", ["c", "b"]), ("a2", ["d"]))
        # No cycle here
        assert DAGValidator.has_cycle(tasks) is False

    def test_isolated_nodes(self):
        tasks = make_tasks(("a", []), ("b", []), ("c", []))
        assert DAGValidator.has_cycle(tasks) is False


class TestTopologicalSort:
    def test_linear_order(self):
        tasks = make_tasks(("a", []), ("b", ["a"]), ("c", ["b"]))
        order = DAGValidator.topological_sort(tasks)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_order(self):
        tasks = make_tasks(("a", []), ("b", ["a"]), ("c", ["a"]), ("d", ["b", "c"]))
        order = DAGValidator.topological_sort(tasks)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_all_independent(self):
        tasks = make_tasks(("a", []), ("b", []), ("c", []))
        order = DAGValidator.topological_sort(tasks)
        assert set(order) == {"a", "b", "c"}

    def test_missing_dep_raises(self):
        tasks = make_tasks(("b", ["a"]))  # 'a' not defined
        with pytest.raises(ValueError, match="unknown task"):
            DAGValidator.topological_sort(tasks)

    def test_cycle_raises(self):
        tasks = make_tasks(("a", ["b"]), ("b", ["a"]))
        with pytest.raises(ValueError, match="Cycle"):
            DAGValidator.topological_sort(tasks)


class TestFindMissingDeps:
    def test_no_missing(self):
        tasks = make_tasks(("a", []), ("b", ["a"]))
        assert DAGValidator.find_missing_deps(tasks) == []

    def test_one_missing(self):
        tasks = make_tasks(("b", ["a"]))  # 'a' missing
        missing = DAGValidator.find_missing_deps(tasks)
        assert len(missing) == 1
        assert "b -> a" in missing

    def test_multiple_missing(self):
        tasks = make_tasks(("c", ["a", "b"]))
        missing = DAGValidator.find_missing_deps(tasks)
        assert "c -> a" in missing
        assert "c -> b" in missing
