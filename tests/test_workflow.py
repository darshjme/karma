"""Tests for Workflow."""
import pytest
from agent_workflow import Workflow, WorkflowStep


def noop(ctx): return "ok"


# --- Construction ---

def test_workflow_basic():
    wf = Workflow("test")
    assert wf.name == "test"
    assert wf.steps == {}


def test_workflow_empty_name_raises():
    with pytest.raises(ValueError):
        Workflow("")


# --- add() ---

def test_workflow_add_fluent():
    wf = Workflow("wf")
    result = wf.add(WorkflowStep("a", noop))
    assert result is wf
    assert "a" in wf.steps


def test_workflow_add_duplicate_raises():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    with pytest.raises(ValueError, match="already exists"):
        wf.add(WorkflowStep("a", noop))


def test_workflow_add_non_step_raises():
    wf = Workflow("wf")
    with pytest.raises(TypeError):
        wf.add("not_a_step")


# --- step() decorator ---

def test_workflow_decorator():
    wf = Workflow("wf")

    @wf.step("fetch")
    def fetch(ctx):
        return "fetched"

    assert "fetch" in wf.steps
    assert callable(fetch)


def test_workflow_decorator_with_deps():
    wf = Workflow("wf")

    @wf.step("a")
    def a(ctx): return 1

    @wf.step("b", depends_on=["a"])
    def b(ctx): return 2

    assert wf.steps["b"].depends_on == ["a"]


# --- ready_steps() ---

def test_ready_steps_no_deps():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    assert len(wf.ready_steps()) == 1


def test_ready_steps_dep_not_met():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    wf.add(WorkflowStep("b", noop, depends_on=["a"]))
    ready = wf.ready_steps()
    assert len(ready) == 1
    assert ready[0].name == "a"


def test_ready_steps_after_completion():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    wf.add(WorkflowStep("b", noop, depends_on=["a"]))
    wf.steps["a"].status = "completed"
    ready = wf.ready_steps()
    assert any(s.name == "b" for s in ready)


# --- is_complete / is_failed ---

def test_is_complete_false_initially():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    assert wf.is_complete is False


def test_is_complete_true_when_all_terminal():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    wf.steps["a"].status = "completed"
    assert wf.is_complete is True


def test_is_failed():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    wf.steps["a"].status = "failed"
    assert wf.is_failed is True


def test_is_failed_false_when_all_ok():
    wf = Workflow("wf")
    wf.add(WorkflowStep("a", noop))
    wf.steps["a"].status = "completed"
    assert wf.is_failed is False


# --- summary() ---

def test_summary():
    wf = Workflow("mywf")
    wf.add(WorkflowStep("a", noop))
    wf.add(WorkflowStep("b", noop))
    wf.steps["a"].status = "completed"
    s = wf.summary()
    assert s["workflow"] == "mywf"
    assert s["total"] == 2
    assert s["status_counts"]["completed"] == 1
    assert s["status_counts"]["pending"] == 1


# --- _validate() ---

def test_validate_missing_dep_raises():
    wf = Workflow("wf")
    wf.add(WorkflowStep("b", noop, depends_on=["nonexistent"]))
    with pytest.raises(ValueError, match="unknown step"):
        wf._validate()
