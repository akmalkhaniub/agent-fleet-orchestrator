import asyncio
import json
import logging
from typing import Dict, List, Optional, Type
from core.schemas import Task, TaskGraph, TaskRole, TaskStatus, TaskGateReport
from models.router import ModelRouter
from worktrees.manager import WorktreeManager
from gates.pipeline import QualityGatePipeline
from agents.base import BaseAgentAdapter
from agents.aider_adapter import AiderAdapter
from agents.claude_code_adapter import ClaudeCodeAdapter
from agents.mock_adapter import MockAgentAdapter

logger = logging.getLogger("orchestrator.core")


class OrchestratorEngine:
    """Core Orchestrator Engine for decomposition, parallel fleet dispatch, and closed-loop gating."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.router = ModelRouter()
        self.worktree_mgr = WorktreeManager(repo_path=repo_path)
        self.gate_pipeline = QualityGatePipeline()
        self.adapters: Dict[str, BaseAgentAdapter] = {
            "aider": AiderAdapter(),
            "claude_code": ClaudeCodeAdapter(),
            "mock_agent": MockAgentAdapter(),
        }

    def decompose_feature(self, feature_title: str, feature_description: str) -> TaskGraph:
        """Decompose a high-level feature description into a DAG of specialized sub-tasks."""
        graph = TaskGraph(feature_title=feature_title, feature_description=feature_description)

        task_impl = Task(
            id="task-1-impl",
            title=f"Implement core logic for {feature_title}",
            description=feature_description,
            role=TaskRole.IMPLEMENT,
            target_files=["src/feature_core.py"],
            agent_type="mock_agent",
        )
        task_test = Task(
            id="task-2-test",
            title=f"Write test suite for {feature_title}",
            description="Write pytest tests for synthesized feature code.",
            role=TaskRole.TEST,
            dependencies=["task-1-impl"],
            target_files=["tests/test_feature_core.py"],
            agent_type="mock_agent",
        )
        task_doc = Task(
            id="task-3-doc",
            title=f"Write documentation for {feature_title}",
            description="Document API endpoints and architecture decisions.",
            role=TaskRole.DOCUMENT,
            dependencies=["task-1-impl"],
            target_files=["docs/feature_core.md"],
            agent_type="mock_agent",
        )

        graph.tasks[task_impl.id] = task_impl
        graph.tasks[task_test.id] = task_test
        graph.tasks[task_doc.id] = task_doc

        return graph

    async def execute_task(self, task: Task, graph: TaskGraph) -> bool:
        """Execute a single task in its own worktree, run quality gates, and merge if passing."""
        logger.info(f"Dispatching task {task.id} ({task.title}) to agent fleet...")
        task.status = TaskStatus.RUNNING

        # 1. Route model based on task role
        route = self.router.route_task(task.role)
        logger.info(f"Model Router selected model {route.selected_model} for role {task.role.value}")

        # 2. Create isolated worktree
        worktree_path = self.worktree_mgr.create_worktree(task.id)
        task.assigned_worktree = worktree_path

        # 3. Post start message in /coordination
        self.worktree_mgr.post_coordination_message(
            sender_id=f"orchestrator-{task.id}",
            payload={"action": "START_TASK", "task_id": task.id, "worktree": worktree_path},
        )

        # 4. Start agent worker
        adapter = self.adapters.get(task.agent_type or "mock_agent", self.adapters["mock_agent"])
        run = await adapter.start_task(task, worktree_path)

        # Poll until completion
        while True:
            status = await adapter.poll(run)
            if status in [TaskStatus.PASSED, "completed", "failed"]:
                break
            await asyncio.sleep(0.5)

        res = await adapter.get_result(run)
        if not res.success:
            task.status = TaskStatus.FAILED
            task.error_message = res.output_summary
            return False

        # 5. Quality Gate Evaluation (Closed-Loop)
        task.status = TaskStatus.GATING
        report: TaskGateReport = self.gate_pipeline.evaluate_task(task, worktree_path)

        if report.all_passed:
            logger.info(f"Task {task.id} passed all 3 Quality Gates. Merging branch into main...")
            merged = self.worktree_mgr.merge(task.id)
            if merged:
                task.status = TaskStatus.PASSED
                self.worktree_mgr.post_coordination_message(
                    sender_id=f"orchestrator-{task.id}",
                    payload={"action": "PASSED_AND_MERGED", "task_id": task.id},
                )
                return True
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "Git merge conflict."
                return False
        else:
            task.status = TaskStatus.FAILED
            task.error_message = report.diagnosis
            logger.warning(f"Task {task.id} failed quality gates. Retrying with updated capability rules...")
            return False

    async def run_fleet(self, graph: TaskGraph) -> Dict[str, Any]:
        """Execute task graph respecting dependencies and running independent tasks in parallel."""
        completed_tasks = set()
        failed_tasks = set()

        while len(completed_tasks) + len(failed_tasks) < len(graph.tasks):
            executable = []
            for task_id, task in graph.tasks.items():
                if task.status == TaskStatus.PENDING:
                    deps_met = all(dep in completed_tasks for dep in task.dependencies)
                    if deps_met:
                        executable.append(task)

            if not executable:
                if len(completed_tasks) + len(failed_tasks) < len(graph.tasks):
                    logger.error("Deadlock or unresolved dependencies in task graph.")
                    break
                break

            # Dispatch executable tasks concurrently
            results = await asyncio.gather(*[self.execute_task(t, graph) for t in executable])
            for task, success in zip(executable, results):
                if success:
                    completed_tasks.add(task.id)
                else:
                    failed_tasks.add(task.id)

        summary = {
            "feature": graph.feature_title,
            "total_tasks": len(graph.tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "coordination_messages": len(self.worktree_mgr.read_coordination_messages()),
        }
        return summary
