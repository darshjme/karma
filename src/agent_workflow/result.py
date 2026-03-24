"""WorkflowResult — the outcome of a workflow execution."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowResult:
    """Immutable record of a completed workflow run."""

    workflow_name: str
    success: bool
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "success": self.success,
            "results": self.results,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }

    def __repr__(self) -> str:
        return (
            f"WorkflowResult(workflow={self.workflow_name!r}, "
            f"success={self.success}, duration_ms={self.duration_ms:.1f})"
        )
