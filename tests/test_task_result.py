"""Tests for TaskResult."""

import pytest
from agent_workflow import TaskResult


def make_result(**kwargs):
    defaults = dict(
        task_name="t1",
        success=True,
        output="hello",
        error=None,
        duration_ms=12.5,
    )
    defaults.update(kwargs)
    return TaskResult(**defaults)


class TestTaskResult:
    def test_fields_stored_correctly(self):
        r = make_result()
        assert r.task_name == "t1"
        assert r.success is True
        assert r.output == "hello"
        assert r.error is None
        assert r.duration_ms == 12.5

    def test_to_dict_keys(self):
        r = make_result()
        d = r.to_dict()
        assert set(d.keys()) == {"task_name", "success", "output", "error", "duration_ms"}

    def test_to_dict_values(self):
        r = make_result(task_name="x", success=False, output=None, error="boom", duration_ms=99.0)
        d = r.to_dict()
        assert d["task_name"] == "x"
        assert d["success"] is False
        assert d["error"] == "boom"

    def test_output_can_be_any_type(self):
        r = make_result(output={"key": [1, 2, 3]})
        assert r.to_dict()["output"] == {"key": [1, 2, 3]}
