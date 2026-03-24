"""Tests for WorkflowEngine and WorkflowResult."""
import pytest
from agent_workflow import Workflow, WorkflowStep, WorkflowEngine, WorkflowResult


# --- WorkflowResult ---

def test_result_to_dict():
    r = WorkflowResult("wf", True, {"a": 1}, {}, 42.5)
    d = r.to_dict()
    assert d["workflow_name"] == "wf"
    assert d["success"] is True
    assert d["results"] == {"a": 1}
    assert d["errors"] == {}
    assert d["duration_ms"] == 42.5


# --- Engine construction ---

def test_engine_rejects_non_workflow():
    with pytest.raises(TypeError):
        WorkflowEngine("not a workflow")


# --- Simple sequential run ---

def test_engine_run_single_step():
    wf = Workflow("single")
    wf.add(WorkflowStep("a", lambda ctx: 42))
    result = WorkflowEngine(wf).run()
    assert result.success is True
    assert result.results["a"] == 42
    assert result.errors == {}


def test_engine_run_sequential_chain():
    wf = Workflow("chain")
    wf.add(WorkflowStep("a", lambda ctx: 1))
    wf.add(WorkflowStep("b", lambda ctx: ctx["a"] + 1, depends_on=["a"]))
    wf.add(WorkflowStep("c", lambda ctx: ctx["b"] + 1, depends_on=["b"]))
    result = WorkflowEngine(wf).run()
    assert result.success is True
    assert result.results == {"a": 1, "b": 2, "c": 3}


# --- Failure handling ---

def test_engine_failing_step():
    wf = Workflow("fail")
    wf.add(WorkflowStep("a", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))))
    result = WorkflowEngine(wf).run()
    assert result.success is False
    assert "a" in result.errors
    assert "boom" in result.errors["a"]


def test_engine_downstream_skipped_on_failure():
    wf = Workflow("cascade")
    wf.add(WorkflowStep("a", lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))))
    wf.add(WorkflowStep("b", lambda ctx: "ok", depends_on=["a"]))
    result = WorkflowEngine(wf).run()
    assert result.success is False
    assert "b" not in result.results


# --- Conditional steps ---

def test_engine_condition_skip():
    wf = Workflow("cond")
    wf.add(WorkflowStep("a", lambda ctx: "done"))
    wf.add(WorkflowStep(
        "b",
        lambda ctx: "should_not_run",
        depends_on=["a"],
        condition=lambda ctx: False,
    ))
    result = WorkflowEngine(wf).run()
    assert result.success is True
    assert "b" not in result.results
    assert wf.steps["b"].status == "skipped"


def test_engine_condition_run():
    wf = Workflow("cond2")
    wf.add(WorkflowStep("a", lambda ctx: 10))
    wf.add(WorkflowStep(
        "b",
        lambda ctx: ctx["a"] * 2,
        depends_on=["a"],
        condition=lambda ctx: ctx.get("a", 0) > 5,
    ))
    result = WorkflowEngine(wf).run()
    assert result.success is True
    assert result.results["b"] == 20


# --- run_step ---

def test_run_step_success():
    wf = Workflow("rs")
    wf.add(WorkflowStep("x", lambda ctx: "xval"))
    engine = WorkflowEngine(wf)
    ok = engine.run_step("x")
    assert ok is True
    assert wf.steps["x"].status == "completed"
    assert wf.steps["x"].result == "xval"


def test_run_step_failure():
    wf = Workflow("rs")
    wf.add(WorkflowStep("x", lambda ctx: (_ for _ in ()).throw(ValueError("bad"))))
    engine = WorkflowEngine(wf)
    ok = engine.run_step("x")
    assert ok is False
    assert wf.steps["x"].status == "failed"
    assert "bad" in wf.steps["x"].error


def test_run_step_unknown_name_raises():
    wf = Workflow("rs")
    engine = WorkflowEngine(wf)
    with pytest.raises(KeyError):
        engine.run_step("ghost")


# --- Context propagation ---

def test_context_propagated_between_steps():
    wf = Workflow("ctx")
    wf.add(WorkflowStep("init", lambda ctx: {"user": "alice"}))
    wf.add(WorkflowStep(
        "greet",
        lambda ctx: f"Hello, {ctx['init']['user']}",
        depends_on=["init"],
    ))
    result = WorkflowEngine(wf).run(context={"env": "test"})
    assert result.results["greet"] == "Hello, alice"


# --- duration_ms ---

def test_result_has_positive_duration():
    wf = Workflow("timing")
    wf.add(WorkflowStep("a", lambda ctx: None))
    result = WorkflowEngine(wf).run()
    assert result.duration_ms >= 0
