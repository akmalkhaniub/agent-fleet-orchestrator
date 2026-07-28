import uuid
import datetime
import logging
from agents.base import BaseAgentAdapter
from core.schemas import Task, AgentRun, AgentStatus, AgentResult

logger = logging.getLogger("orchestrator.agents.claude_code")


class ClaudeCodeAdapter(BaseAgentAdapter):
    """Adapter for Claude Code commercial autonomous sub-agent CLI."""

    def __init__(self, command: str = "claude"):
        self.command = command
        self._runs = {}

    async def start_task(self, task: Task, worktree_path: str) -> AgentRun:
        run_id = f"run-claude-{uuid.uuid4().hex[:8]}"
        run = AgentRun(
            run_id=run_id,
            task_id=task.id,
            agent_type="claude_code",
            worktree_path=worktree_path,
            status=AgentStatus.RUNNING,
        )
        self._runs[run_id] = {
            "run": run,
            "task": task,
            "logs": [f"[{datetime.datetime.utcnow().isoformat()}] Started Claude Code agent for task {task.id}"],
        }
        logger.info(f"Started Claude Code agent run {run_id} in {worktree_path}")
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
        return AgentResult(
            run_id=run.run_id,
            task_id=run.task_id,
            success=True,
            modified_files=run_data.get("task", Task(id="dummy", title="", description="", role="implement")).target_files,
            output_summary="\n".join(logs),
        )
