# agent-workflow

**Multi-step workflow orchestration for LLM agents.**

Zero dependencies · Python 3.10+ · Production-ready

---

## Problem

LLM agents need to execute complex pipelines: some steps sequential, some parallel, some conditional on runtime context.
Hard-coding this logic couples execution to structure — impossible to reuse, test, or visualize.

`agent-workflow` gives you a DAG-based, declarative workflow layer you can compose, run, and introspect.

---

## Install

```bash
pip install agent-workflow
```

---

## Quick Start — Conditional Multi-Step Workflow

```python
from agent_workflow import Workflow, WorkflowStep, WorkflowEngine

# ----- Build the workflow -----
wf = Workflow("research-pipeline")

# Step 1: Fetch raw data (no deps)
wf.add(WorkflowStep(
    name="fetch_data",
    handler=lambda ctx: {"records": [1, 2, 3], "source": "api"},
))

# Step 2: Validate — runs only if fetch succeeded (always here, but demo'd via condition)
wf.add(WorkflowStep(
    name="validate",
    handler=lambda ctx: len(ctx["fetch_data"]["records"]) > 0,
    depends_on=["fetch_data"],
    condition=lambda ctx: ctx.get("env") != "skip-validate",
))

# Step 3a: Summarize (conditional on validation passing)
wf.add(WorkflowStep(
    name="summarize",
    handler=lambda ctx: f"Found {len(ctx['fetch_data']['records'])} records",
    depends_on=["validate"],
    condition=lambda ctx: ctx.get("validate", False) is True,
))

# Step 3b: Alert on empty data (conditional — runs only if validation FAILED)
wf.add(WorkflowStep(
    name="alert_empty",
    handler=lambda ctx: "ALERT: no records",
    depends_on=["validate"],
    condition=lambda ctx: ctx.get("validate", True) is False,
))

# Step 4: Notify — depends on summarize (runs if summarize ran)
wf.add(WorkflowStep(
    name="notify",
    handler=lambda ctx: f"Notification sent: {ctx['summarize']}",
    depends_on=["summarize"],
))

# ----- Run -----
engine = WorkflowEngine(wf)
result = engine.run(context={"env": "production"})

print(result.success)           # True
print(result.results)           # {'fetch_data': ..., 'validate': True, 'summarize': '...', 'notify': '...'}
print(result.errors)            # {}
print(f"{result.duration_ms:.1f}ms")
print(result.to_dict())
```

---

## Decorator Style

```python
wf = Workflow("etl")

@wf.step("extract")
def extract(ctx):
    return ["row1", "row2"]

@wf.step("transform", depends_on=["extract"])
def transform(ctx):
    return [r.upper() for r in ctx["extract"]]

@wf.step("load", depends_on=["transform"])
def load(ctx):
    print("Loading:", ctx["transform"])
    return "ok"

result = WorkflowEngine(wf).run()
```

---

## API Reference

### `WorkflowStep(name, handler, depends_on=None, condition=None, metadata=None)`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique step identifier |
| `handler` | `callable(ctx) → any` | The step's logic; receives current context |
| `depends_on` | `list[str]` | Names of steps that must complete first |
| `condition` | `callable(ctx) → bool` | If provided, step is skipped when it returns `False` |
| `metadata` | `dict` | Arbitrary metadata for your tooling |
| `status` | `str` | `pending` / `running` / `completed` / `failed` / `skipped` |
| `result` | `any` | Return value of the handler |
| `error` | `str \| None` | Error message if the step failed |

**`is_ready(completed: set[str], context: dict = None) → bool`**
Returns `True` when all dependencies are in `completed` and the condition passes.

---

### `Workflow(name)`

| Method | Description |
|--------|-------------|
| `.add(step)` | Add a `WorkflowStep`; fluent, raises on duplicates |
| `.step(name, depends_on, condition)` | Decorator factory |
| `.ready_steps(context)` | Steps with met deps + passing conditions |
| `.is_complete` | `True` when all steps are terminal |
| `.is_failed` | `True` when any step failed |
| `.summary()` | `{"workflow": str, "total": int, "status_counts": dict}` |

---

### `WorkflowEngine(workflow)`

| Method | Description |
|--------|-------------|
| `.run(context)` | Execute all steps; returns `WorkflowResult` |
| `.run_step(name, context)` | Execute a single named step; returns `bool` |

---

### `WorkflowResult`

| Field | Type | Description |
|-------|------|-------------|
| `workflow_name` | `str` | Workflow name |
| `success` | `bool` | `True` if all non-skipped steps completed |
| `results` | `dict[str, any]` | Per-step return values |
| `errors` | `dict[str, str]` | Per-step error messages |
| `duration_ms` | `float` | Wall-clock time |

**`.to_dict()`** — Serialize to a plain dict (JSON-ready).

---

## Context Passing

Each step's return value is injected into the shared context under the step's name.
Downstream steps access it via `ctx["step_name"]`.

```python
@wf.step("load_user")
def load_user(ctx):
    return {"id": 42, "name": "Alice"}

@wf.step("greet", depends_on=["load_user"])
def greet(ctx):
    return f"Hello, {ctx['load_user']['name']}"
```

---

## Error Behavior

- A **failed** step sets its status to `"failed"` and records the exception message.
- Steps that depend on a failed step are automatically **skipped**.
- The engine continues running independent branches even after a failure.
- `WorkflowResult.success` is `False` if any step failed.

---

## Development

```bash
git clone https://github.com/your-org/agent-workflow
cd agent-workflow
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## License

MIT
