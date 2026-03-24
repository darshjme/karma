"""WorkflowEngine — executes a Workflow DAG."""

from __future__ import annotations
import time
from typing import Any

from .workflow import Workflow
from .result import WorkflowResult


class WorkflowEngine:
    """Executes a Workflow, respecting dependencies and conditions."""

    def __init__(self, workflow: Workflow) -> None:
        if not isinstance(workflow, Workflow):
            raise TypeError("Expected a Workflow instance.")
        self.workflow = workflow

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, context: dict | None = None) -> WorkflowResult:
        """Execute the full workflow and return a WorkflowResult."""
        ctx = dict(context or {})
        self.workflow.reset()
        self.workflow._validate()

        start = time.monotonic()
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}

        while not self.workflow.is_complete:
            ready = self.workflow.ready_steps(ctx)

            if not ready:
                # Nothing is runnable — handle blocked / skipped steps
                if not self._resolve_blocked(ctx):
                    break   # deadlock — stop execution

            for step in ready:
                self.run_step(step.name, ctx)
                if step.status == "completed":
                    results[step.name] = step.result
                    # Inject result into context for downstream steps
                    ctx[step.name] = step.result
                elif step.status == "failed":
                    errors[step.name] = step.error or "Unknown error"
                elif step.status == "skipped":
                    pass

        elapsed_ms = (time.monotonic() - start) * 1000
        success = not self.workflow.is_failed and self.workflow.is_complete

        return WorkflowResult(
            workflow_name=self.workflow.name,
            success=success,
            results=results,
            errors=errors,
            duration_ms=elapsed_ms,
        )

    def run_step(self, name: str, context: dict | None = None) -> bool:
        """Execute a single named step. Returns True on success."""
        ctx = context or {}
        step = self.workflow.steps.get(name)
        if step is None:
            raise KeyError(f"No step named '{name}' in workflow '{self.workflow.name}'.")

        step.status = "running"
        try:
            step.result = step.handler(ctx)
            step.status = "completed"
            return True
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_blocked(self, context: dict) -> bool:
        """
        Skip pending steps whose condition prevents them from ever running,
        or that are blocked by failed dependencies.
        Returns True if any step was resolved (skipped).
        """
        resolved = False
        completed_or_skipped = {
            s.name for s in self.workflow.steps.values()
            if s.status in ("completed", "skipped")
        }
        failed = {
            s.name for s in self.workflow.steps.values()
            if s.status == "failed"
        }

        for step in self.workflow.steps.values():
            if step.status != "pending":
                continue
            # Skip if a dependency has failed (can never run)
            if set(step.depends_on) & failed:
                step.status = "skipped"
                step.error = "Skipped due to failed dependency."
                resolved = True
                continue
            # Skip if condition explicitly returns False right now
            if step.condition is not None:
                deps_met = set(step.depends_on).issubset(completed_or_skipped)
                if deps_met:
                    try:
                        if not step.condition(context):
                            step.status = "skipped"
                            resolved = True
                    except Exception:
                        step.status = "skipped"
                        resolved = True

        return resolved
