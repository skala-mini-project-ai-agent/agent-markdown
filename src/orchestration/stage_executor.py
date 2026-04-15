"""Small stage executor wrapper for supervisor-managed stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class StageExecutionResult:
    stage_name: str
    status: str
    payload: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StageExecutor:
    def run_stage(
        self,
        stage_name: str,
        handler: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> StageExecutionResult:
        payload = handler(*args, **kwargs)
        return StageExecutionResult(stage_name=stage_name, status="passed", payload=payload)
