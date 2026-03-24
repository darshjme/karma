# Changelog

All notable changes to **agent-workflow** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2026-03-24

### Added
- `Task` — callable unit of work with dependency declarations and retry support.
- `TaskResult` — dataclass capturing output, error, and timing for a single task.
- `Workflow` — DAG-based orchestrator with parallel execution via `ThreadPoolExecutor`.
- `WorkflowResult` — aggregated result of a complete workflow run.
- `DAGValidator` — cycle detection (DFS), topological sort (Kahn's algorithm), and missing-dependency discovery.
- 22+ pytest tests with 100 % pass rate.
- Zero runtime dependencies — only Python ≥ 3.10 standard library.
