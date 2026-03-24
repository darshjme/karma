"""Tests for Workflow and WorkflowResult."""

import time
import threading
import pytest
from agent_workflow import Task, Workflow, WorkflowResult


def noop(ctx):
    return "done"


def fail_func(ctx):
    raise RuntimeError("intentional failure")


def record(ctx, name):
    ctx.setdefault("order", []).append(name)
    return name


class TestWorkflowBasics:
    def test_add_task_fluent(self):
        wf = Workflow("wf")
        result = wf.add_task(Task("t1", noop))
        assert result is wf  # fluent

    def test_duplicate_task_raises(self):
        wf = Workflow("wf")
        wf.add_task(Task("t1", noop))
        with pytest.raises(ValueError, match="already registered"):
            wf.add_task(Task("t1", noop))

    def test_non_task_raises(self):
        wf = Workflow("wf")
        with pytest.raises(TypeError):
            wf.add_task("not_a_task")  # type: ignore

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            Workflow("")

    def test_validate_clean_workflow(self):
        wf = Workflow("wf")
        wf.add_task(Task("a", noop)).add_task(Task("b", noop, deps=["a"]))
        assert wf.validate() == []

    def test_validate_missing_dep(self):
        wf = Workflow("wf")
        wf.add_task(Task("b", noop, deps=["a"]))  # 'a' not registered
        errors = wf.validate()
        assert any("Missing dependency" in e for e in errors)

    def test_validate_cycle(self):
        wf = Workflow("wf")
        wf.add_task(Task("a", noop, deps=["b"]))
        wf.add_task(Task("b", noop, deps=["a"]))
        errors = wf.validate()
        assert any("Cycle" in e for e in errors)

    def test_task_order_linear(self):
        wf = (
            Workflow("wf")
            .add_task(Task("a", noop))
            .add_task(Task("b", noop, deps=["a"]))
            .add_task(Task("c", noop, deps=["b"]))
        )
        order = wf.task_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_task_order_invalid_raises(self):
        wf = Workflow("wf")
        wf.add_task(Task("b", noop, deps=["missing"]))
        with pytest.raises(ValueError):
            wf.task_order()


class TestWorkflowRun:
    def test_simple_linear_run(self):
        import threading
        lock = threading.Lock()
        order = []

        def make_step(name):
            def fn(ctx):
                with lock:
                    order.append(name)
                return name
            return fn

        wf = (
            Workflow("wf")
            .add_task(Task("a", make_step("a")))
            .add_task(Task("b", make_step("b"), deps=["a"]))
            .add_task(Task("c", make_step("c"), deps=["b"]))
        )
        result = wf.run()
        assert result.success is True
        assert isinstance(result, WorkflowResult)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_result_contains_all_tasks(self):
        wf = (
            Workflow("wf")
            .add_task(Task("a", noop))
            .add_task(Task("b", noop, deps=["a"]))
        )
        result = wf.run()
        assert "a" in result.task_results
        assert "b" in result.task_results

    def test_context_passed_to_tasks(self):
        def use_ctx(ctx):
            return ctx["greeting"]

        wf = Workflow("wf").add_task(Task("t", use_ctx))
        result = wf.run(context={"greeting": "hello"})
        assert result.task_results["t"].output == "hello"

    def test_failed_task_skips_dependents(self):
        wf = (
            Workflow("wf")
            .add_task(Task("a", fail_func))
            .add_task(Task("b", noop, deps=["a"]))
            .add_task(Task("c", noop, deps=["b"]))
        )
        result = wf.run()
        assert result.success is False
        assert "a" in result.failed_tasks
        assert result.task_results["b"].success is False
        assert "Skipped" in result.task_results["b"].error
        assert result.task_results["c"].success is False

    def test_parallel_independent_tasks(self):
        """Independent tasks should run concurrently."""
        start_times = {}
        barrier = threading.Barrier(3)

        def make_parallel(name):
            def fn(ctx):
                start_times[name] = time.perf_counter()
                barrier.wait(timeout=5)
                return name
            return fn

        wf = (
            Workflow("wf", max_workers=4)
            .add_task(Task("p1", make_parallel("p1")))
            .add_task(Task("p2", make_parallel("p2")))
            .add_task(Task("p3", make_parallel("p3")))
        )
        result = wf.run()
        assert result.success is True
        # All three met the barrier → they ran concurrently
        assert len(start_times) == 3

    def test_workflow_result_duration(self):
        def slow(ctx):
            time.sleep(0.05)
            return "ok"

        wf = Workflow("wf").add_task(Task("t", slow))
        result = wf.run()
        assert result.duration_ms >= 50

    def test_run_invalid_workflow_raises(self):
        wf = Workflow("wf")
        wf.add_task(Task("b", noop, deps=["missing"]))
        with pytest.raises(ValueError):
            wf.run()

    def test_workflow_result_to_dict(self):
        wf = Workflow("wf").add_task(Task("t", noop))
        result = wf.run()
        d = result.to_dict()
        assert "success" in d
        assert "task_results" in d
        assert "duration_ms" in d
        assert "failed_tasks" in d

    def test_partial_failure_unaffected_branch_succeeds(self):
        """Branch B fails; independent branch C should still succeed."""

        def branch_b(ctx):
            raise RuntimeError("branch B failed")

        wf = (
            Workflow("wf")
            .add_task(Task("root", noop))
            .add_task(Task("b", branch_b, deps=["root"]))
            .add_task(Task("c", noop, deps=["root"]))
        )
        result = wf.run()
        assert result.task_results["c"].success is True
        assert result.task_results["b"].success is False
        assert result.success is False  # overall fails because b failed

    def test_default_context_is_empty_dict(self):
        def check_ctx(ctx):
            assert isinstance(ctx, dict)
            return "ok"

        wf = Workflow("wf").add_task(Task("t", check_ctx))
        result = wf.run()  # no context argument
        assert result.success is True
