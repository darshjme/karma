"""Tests for Task."""

import pytest
from agent_workflow import Task, TaskResult


def ok_func(ctx):
    return "ok"


def fail_func(ctx):
    raise RuntimeError("boom")


def ctx_func(ctx):
    return ctx.get("value", 0) * 2


class TestTaskInit:
    def test_basic_properties(self):
        t = Task("t1", ok_func)
        assert t.name == "t1"
        assert t.deps == []
        assert t.status == "pending"
        assert t.retry == 0

    def test_deps_stored(self):
        t = Task("t2", ok_func, deps=["t1"])
        assert t.deps == ["t1"]

    def test_deps_not_mutated(self):
        deps = ["a", "b"]
        t = Task("t3", ok_func, deps=deps)
        deps.append("c")
        assert "c" not in t.deps

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            Task("", ok_func)

    def test_non_callable_raises(self):
        with pytest.raises(TypeError):
            Task("t", "not_callable")

    def test_negative_retry_raises(self):
        with pytest.raises(ValueError):
            Task("t", ok_func, retry=-1)


class TestTaskExecute:
    def test_successful_execution(self):
        t = Task("t1", ok_func)
        r = t.execute({})
        assert isinstance(r, TaskResult)
        assert r.success is True
        assert r.output == "ok"
        assert r.error is None
        assert t.status == "done"

    def test_failed_execution(self):
        t = Task("t1", fail_func)
        r = t.execute({})
        assert r.success is False
        assert r.output is None
        assert "RuntimeError" in r.error
        assert t.status == "failed"

    def test_duration_recorded(self):
        t = Task("t1", ok_func)
        r = t.execute({})
        assert r.duration_ms >= 0

    def test_context_passed_through(self):
        t = Task("t1", ctx_func)
        r = t.execute({"value": 21})
        assert r.output == 42

    def test_retry_on_failure(self):
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ValueError("not yet")
            return "finally"

        t = Task("t1", flaky, retry=2)
        r = t.execute({})
        assert r.success is True
        assert r.output == "finally"
        assert call_count["n"] == 3

    def test_retry_exhausted_returns_failure(self):
        t = Task("t1", fail_func, retry=2)
        r = t.execute({})
        assert r.success is False

    def test_reset_restores_pending(self):
        t = Task("t1", ok_func)
        t.execute({})
        assert t.status == "done"
        t.reset()
        assert t.status == "pending"

    def test_task_name_in_result(self):
        t = Task("my_task", ok_func)
        r = t.execute({})
        assert r.task_name == "my_task"
