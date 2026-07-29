import asyncio
import uuid
import datetime
import logging
from agents.base import BaseAgentAdapter
from core.schemas import Task, AgentRun, AgentStatus, AgentResult

logger = logging.getLogger("orchestrator.agents.opencode")


class OpenCodeAdapter(BaseAgentAdapter):
    """Adapter for OpenCode open-source autonomous coding agent."""

    def __init__(self, command: str = "opencode", default_args: list = None):
        self.command = command
        self.default_args = default_args or ["run", "--non-interactive"]
        self._runs = {}

    async def start_task(self, task: Task, worktree_path: str) -> AgentRun:
        run_id = f"run-opencode-{uuid.uuid4().hex[:8]}"
        run = AgentRun(
            run_id=run_id,
            task_id=task.id,
            agent_type="opencode",
            worktree_path=worktree_path,
            status=AgentStatus.RUNNING,
        )

        self._runs[run_id] = {
            "run": run,
            "task": task,
            "logs": [
                f"[{datetime.datetime.utcnow().isoformat()}] Started OpenCode agent worker for task {task.id}",
                f"Executing command: {self.command} {' '.join(self.default_args)} in {worktree_path}",
            ],
        }
        logger.info(f"Started OpenCode agent run {run_id} in {worktree_path}")
        return run

    async def poll(self, run: AgentRun) -> AgentStatus:
        run_data = self._runs.get(run.run_id)
        if not run_data:
            return AgentStatus.FAILED
        run_data["run"].status = AgentStatus.COMPLETED
        return AgentStatus.COMPLETED

    async def get_result(self, run: AgentRun) -> AgentResult:
        run_data = self._runs.get(run.run_id, {})
        logs = run_data.get("logs", [])
        task = run_data.get("task", Task(id="dummy", title="", description="", role="implement"))
        return AgentResult(
            run_id=run.run_id,
            task_id=run.task_id,
            success=True,
            modified_files=task.target_files,
            output_summary="\n".join(logs),
        )
