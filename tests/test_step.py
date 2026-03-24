"""Tests for WorkflowStep."""
import pytest
from agent_workflow import WorkflowStep


def noop(ctx): return "ok"


# --- Construction ---

def test_step_basic_creation():
    s = WorkflowStep("fetch", noop)
    assert s.name == "fetch"
    assert s.status == "pending"
    assert s.result is None
    assert s.error is None
    assert s.depends_on == []
    assert s.metadata == {}


def test_step_with_deps_and_metadata():
    s = WorkflowStep("process", noop, depends_on=["fetch"], metadata={"key": "val"})
    assert s.depends_on == ["fetch"]
    assert s.metadata == {"key": "val"}


def test_step_empty_name_raises():
    with pytest.raises(ValueError):
        WorkflowStep("", noop)


def test_step_non_callable_handler_raises():
    with pytest.raises(TypeError):
        WorkflowStep("bad", "not_callable")


# --- is_ready ---

def test_is_ready_no_deps():
    s = WorkflowStep("a", noop)
    assert s.is_ready(set()) is True


def test_is_ready_deps_met():
    s = WorkflowStep("b", noop, depends_on=["a"])
    assert s.is_ready({"a"}) is True


def test_is_ready_deps_not_met():
    s = WorkflowStep("b", noop, depends_on=["a"])
    assert s.is_ready(set()) is False


def test_is_ready_condition_true():
    s = WorkflowStep("c", noop, condition=lambda ctx: ctx.get("flag") is True)
    assert s.is_ready(set(), {"flag": True}) is True


def test_is_ready_condition_false():
    s = WorkflowStep("c", noop, condition=lambda ctx: ctx.get("flag") is True)
    assert s.is_ready(set(), {"flag": False}) is False


def test_is_ready_condition_exception_returns_false():
    def bad_cond(ctx): raise RuntimeError("boom")
    s = WorkflowStep("c", noop, condition=bad_cond)
    assert s.is_ready(set()) is False


def test_is_ready_already_completed_returns_false():
    s = WorkflowStep("a", noop)
    s.status = "completed"
    assert s.is_ready(set()) is False


# --- reset ---

def test_step_reset():
    s = WorkflowStep("a", noop)
    s.status = "failed"
    s.result = 42
    s.error = "oops"
    s.reset()
    assert s.status == "pending"
    assert s.result is None
    assert s.error is None
