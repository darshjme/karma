# Changelog

All notable changes to **agent-workflow** are documented here.

## [1.0.0] - 2026-03-24

### Added
- `WorkflowStep` with dependency tracking, conditional execution, and status management.
- `Workflow` DAG with fluent `add()`, decorator `step()`, `ready_steps()`, `is_complete`, `is_failed`, `summary()`.
- `WorkflowEngine` with `run()` and `run_step()` supporting sequential and parallel-ready execution.
- `WorkflowResult` dataclass with `to_dict()` serialization.
- Zero external dependencies — pure Python 3.10+.
- Full pytest test suite (25+ tests).
