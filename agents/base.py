from abc import ABC, abstractmethod
from core.schemas import Task, AgentRun, AgentStatus, AgentResult


class BaseAgentAdapter(ABC):
    """Abstract interface for swappable fleet worker agents."""

    @abstractmethod
    async def start_task(self, task: Task, worktree_path: str) -> AgentRun:
        """Initialize and start an agent worker execution in a specific worktree."""
        pass

    @abstractmethod
    async def poll(self, run: AgentRun) -> AgentStatus:
        """Poll current execution status of an active agent run."""
        pass

    @abstractmethod
    async def get_result(self, run: AgentRun) -> AgentResult:
        """Retrieve execution logs and results upon task completion."""
        pass
