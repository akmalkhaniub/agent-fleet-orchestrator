import os
from typing import Dict, Any

try:
    from fastmcp import FastMCP
    mcp_eval = FastMCP("eval-runner-server")
except ImportError:
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
        def tool(self):
            def decorator(func):
                return func
            return decorator
    mcp_eval = FastMCP("eval-runner-server")

from gates.pipeline import QualityGatePipeline
from core.schemas import Task, TaskRole


@mcp_eval.tool()
def precheck_quality_gates(worktree_path: str, target_files: list) -> Dict[str, Any]:
    """Expose quality gate checks to agents so they can self-verify before submitting for merge."""
    pipeline = QualityGatePipeline()
    dummy_task = Task(
        id="precheck",
        title="Precheck Task",
        description="Self check",
        role=TaskRole.IMPLEMENT,
        target_files=target_files,
    )
    report = pipeline.evaluate_task(dummy_task, worktree_path)
    return {
        "all_passed": report.all_passed,
        "results": [r.dict() for r in report.results],
        "diagnosis": report.diagnosis,
    }


if __name__ == "__main__":
    print("FastMCP Eval Server ready.")
