import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type
from core.schemas import Task, TaskGraph, TaskRole, TaskStatus, TaskGateReport
from core.telemetry import TelemetryTracer
from models.router import ModelRouter
from worktrees.manager import WorktreeManager
from gates.pipeline import QualityGatePipeline
from agents.base import BaseAgentAdapter
from agents.aider_adapter import AiderAdapter
from agents.claude_code_adapter import ClaudeCodeAdapter
from agents.opencode_adapter import OpenCodeAdapter
from agents.openhands_adapter import OpenHandsAdapter
from agents.goose_adapter import GooseAdapter
from agents.swe_agent_adapter import SWEAgentAdapter
from agents.mock_adapter import MockAgentAdapter

logger = logging.getLogger("orchestrator.core")


class OrchestratorEngine:
    """Core Orchestrator Engine for decomposition, parallel fleet dispatch, and closed-loop gating."""

    def __init__(self, repo_path: str = ".", max_retries: int = 3):
        self.repo_path = repo_path
        self.max_retries = max_retries
        self.router = ModelRouter()
        self.worktree_mgr = WorktreeManager(repo_path=repo_path)
        self.gate_pipeline = QualityGatePipeline()
        self.tracer = TelemetryTracer(coordination_dir=self.worktree_mgr.coordination_dir)
        self.adapters: Dict[str, BaseAgentAdapter] = {
            "openhands": OpenHandsAdapter(),
            "goose": GooseAdapter(),
            "opencode": OpenCodeAdapter(),
            "swe_agent": SWEAgentAdapter(),
            "aider": AiderAdapter(),
            "claude_code": ClaudeCodeAdapter(),
            "mock_agent": MockAgentAdapter(),
        }

    def decompose_feature(
        self,
        feature_title: str,
        feature_description: str,
        custom_tasks: Optional[List[Task]] = None,
    ) -> TaskGraph:
        """Decompose a high-level feature description into a DAG of specialized sub-tasks."""
        graph = TaskGraph(feature_title=feature_title, feature_description=feature_description)

        if custom_tasks:
            for t in custom_tasks:
                graph.tasks[t.id] = t
            return graph

        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in feature_title).strip("_") or "feature"
        default_targets = (
            ["demo-apps/sentinel-security/src/scanner.py", "demo-apps/sentinel-security/src/remediator.py"]
            if "sentinel" in slug or "security" in slug or "jwt" in slug
            else [f"src/{slug}/service.py", f"src/{slug}/models.py"]
        )

        task_impl = Task(
            id="task-1-impl",
            title=f"Implement core AST scanner & logic for {feature_title}",
            description=feature_description,
            role=TaskRole.IMPLEMENT,
            target_files=default_targets,
            agent_type="mock_agent",
        )
        task_test = Task(
            id="task-2-test",
            title=f"Write pytest security suite for {feature_title}",
            description="Write pytest tests verifying scanner accuracy and patch generation.",
            role=TaskRole.TEST,
            dependencies=["task-1-impl"],
            target_files=["demo-apps/sentinel-security/tests/test_sentinel.py"],
            agent_type="mock_agent",
        )
        task_doc = Task(
            id="task-3-doc",
            title=f"Write security spec & docs for {feature_title}",
            description="Document vulnerability taxonomy and remediation guidelines.",
            role=TaskRole.DOCUMENT,
            dependencies=["task-1-impl"],
            target_files=["demo-apps/sentinel-security/docs/sentinel_spec.md"],
            agent_type="mock_agent",
        )
        task_ui = Task(
            id="task-4-ui",
            title=f"Build web dashboard for {feature_title}",
            description="Create interactive scanner UI with live patch preview.",
            role=TaskRole.IMPLEMENT,
            dependencies=["task-1-impl"],
            target_files=["demo-apps/sentinel-security/web/app.py"],
            agent_type="mock_agent",
        )

        graph.tasks[task_impl.id] = task_impl
        graph.tasks[task_test.id] = task_test
        graph.tasks[task_doc.id] = task_doc
        graph.tasks[task_ui.id] = task_ui

        return graph

    async def execute_task(self, task: Task, graph: TaskGraph) -> bool:
        """Execute a single task in its own worktree, run closed-loop quality gates with self-healing retries, and merge if passing."""
        logger.info(f"Dispatching task {task.id} ({task.title}) to agent fleet...")
        task.status = TaskStatus.RUNNING

        # 1. Route model based on task role
        route = self.router.route_task(task.role)
        logger.info(f"Model Router selected model {route.selected_model} for role {task.role.value}")

        with self.tracer.start_span(
            "orchestrator.execute_task",
            parent_traceparent=task.traceparent,
            attributes={
                "orchestrator.task.id": task.id,
                "orchestrator.task.role": task.role.value,
                "gen_ai.request.model": route.selected_model,
                "gen_ai.system": route.provider,
            },
        ) as task_span:
            task.traceparent = task_span["traceparent"]

            # 2. Create isolated worktree
            worktree_path = self.worktree_mgr.create_worktree(task.id)
            task.assigned_worktree = worktree_path
            task_span["attributes"]["orchestrator.worktree"] = worktree_path

            # 3. Post start message in /coordination with W3C traceparent
            self.worktree_mgr.post_coordination_message(
                sender_id=f"orchestrator-{task.id}",
                payload={
                    "action": "START_TASK",
                    "task_id": task.id,
                    "worktree": worktree_path,
                    "traceparent": task.traceparent,
                },
            )

            adapter = self.adapters.get(task.agent_type or "mock_agent", self.adapters["mock_agent"])
            base_description = task.description

            for attempt in range(self.max_retries + 1):
                task.retry_count = attempt
                task_span["attributes"]["orchestrator.retry_count"] = attempt

                with self.tracer.start_span(
                    "orchestrator.agent_attempt",
                    parent_traceparent=task.traceparent,
                    attributes={"orchestrator.attempt": attempt + 1, "orchestrator.agent_type": task.agent_type or "mock_agent"},
                ) as attempt_span:
                    run = await adapter.start_task(task, worktree_path)

                    # Poll until completion
                    while True:
                        status = await adapter.poll(run)
                        if status in [TaskStatus.PASSED, "completed", "failed"]:
                            break
                        await asyncio.sleep(0.05)

                    res = await adapter.get_result(run)
                    if not res.success:
                        diag = res.error_log or res.output_summary or "Agent execution failed."
                        task.error_message = diag
                        attempt_span["status"] = "ERROR"
                        attempt_span["attributes"]["orchestrator.failure_reason"] = diag
                        if attempt < self.max_retries:
                            task.description = (
                                f"{base_description}\n\n[SELF-HEALING RETRY #{attempt + 1} TRACEBACK]:\n{diag}"
                            )
                            continue
                        task.status = TaskStatus.QUARANTINED
                        task_span["status"] = "ERROR"
                        task_span["attributes"]["orchestrator.quarantined"] = True
                        self.worktree_mgr.post_coordination_message(
                            sender_id=f"orchestrator-{task.id}",
                            payload={
                                "action": "TASK_QUARANTINED",
                                "task_id": task.id,
                                "attempts": attempt + 1,
                                "reason": diag,
                                "traceparent": task.traceparent,
                            },
                        )
                        return False

                    # 5. Quality Gate Evaluation (Closed-Loop)
                    task.status = TaskStatus.GATING
                    report: TaskGateReport = self.gate_pipeline.evaluate_task(task, worktree_path)
                    attempt_span["attributes"]["orchestrator.gate.all_passed"] = report.all_passed

                    if report.all_passed:
                        logger.info(f"Task {task.id} passed all 3 Quality Gates. Merging branch into main...")
                        merged = self.worktree_mgr.merge(task.id)
                        if merged:
                            task.status = TaskStatus.PASSED
                            self.worktree_mgr.post_coordination_message(
                                sender_id=f"orchestrator-{task.id}",
                                payload={
                                    "action": "PASSED_AND_MERGED",
                                    "task_id": task.id,
                                    "attempts": attempt + 1,
                                    "traceparent": task.traceparent,
                                },
                            )
                            return True
                        task.status = TaskStatus.FAILED
                        task.error_message = "Git merge conflict."
                        task_span["status"] = "ERROR"
                        return False

                    # Self-healing feedback loop if retries remain
                    gate_failures = [
                        f"{r.gate_type.value}: {', '.join(r.violations)}"
                        for r in report.results
                        if not r.passed and r.violations
                    ]
                    diag_text = report.diagnosis or " | ".join(gate_failures) or "Quality gate violation"
                    task.error_message = diag_text
                    attempt_span["status"] = "ERROR"
                    attempt_span["attributes"]["orchestrator.gate.violations"] = gate_failures

                    if attempt < self.max_retries:
                        logger.warning(
                            f"Task {task.id} failed quality gates (attempt {attempt + 1}/{self.max_retries + 1}). "
                            f"Feeding diagnosis back to worker for self-healing: {diag_text}"
                        )
                        task.description = (
                            f"{base_description}\n\n[SELF-HEALING RETRY #{attempt + 1} TRACEBACK]:\n{diag_text}"
                        )
                        task.status = TaskStatus.RUNNING
                    else:
                        task.status = TaskStatus.QUARANTINED
                        task_span["status"] = "ERROR"
                        task_span["attributes"]["orchestrator.quarantined"] = True
                        self.worktree_mgr.post_coordination_message(
                            sender_id=f"orchestrator-{task.id}",
                            payload={
                                "action": "TASK_QUARANTINED",
                                "task_id": task.id,
                                "attempts": attempt + 1,
                                "reason": diag_text,
                                "traceparent": task.traceparent,
                            },
                        )
                        logger.error(
                            f"Task {task.id} exhausted {self.max_retries + 1} attempts. Marking QUARANTINED."
                        )
                        return False

            return False

    async def run_fleet(self, graph: TaskGraph) -> Dict[str, Any]:
        """Execute task graph respecting dependencies, cascading blocked states, and running independent tasks in parallel."""
        completed_tasks = set()
        failed_tasks = set()
        blocked_tasks = set()

        with self.tracer.start_span(
            "orchestrator.run_fleet",
            attributes={"orchestrator.feature": graph.feature_title, "orchestrator.total_tasks": len(graph.tasks)},
        ) as fleet_span:
            root_traceparent = fleet_span["traceparent"]
            for t in graph.tasks.values():
                if not t.traceparent:
                    t.traceparent = root_traceparent

            while len(completed_tasks) + len(failed_tasks) + len(blocked_tasks) < len(graph.tasks):
                executable = []
                made_progress = False

                for task_id, task in graph.tasks.items():
                    if task.status == TaskStatus.PENDING:
                        failed_deps = [dep for dep in task.dependencies if dep in failed_tasks or dep in blocked_tasks]
                        if failed_deps:
                            task.status = TaskStatus.BLOCKED
                            task.error_message = f"Blocked by failed upstream dependency: {', '.join(failed_deps)}"
                            blocked_tasks.add(task_id)
                            made_progress = True
                            continue

                        deps_met = all(dep in completed_tasks for dep in task.dependencies)
                        if deps_met:
                            executable.append(task)

                if not executable:
                    if made_progress:
                        continue
                    if len(completed_tasks) + len(failed_tasks) + len(blocked_tasks) < len(graph.tasks):
                        logger.error("Deadlock or unresolved cyclic dependencies in task graph.")
                    break

                # Dispatch executable tasks concurrently
                results = await asyncio.gather(*[self.execute_task(t, graph) for t in executable])
                for task, success in zip(executable, results):
                    if success:
                        completed_tasks.add(task.id)
                    else:
                        failed_tasks.add(task.id)

            quarantined_count = sum(
                1 for tid in failed_tasks if graph.tasks[tid].status == TaskStatus.QUARANTINED
            )
            summary = {
                "feature": graph.feature_title,
                "total_tasks": len(graph.tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "quarantined": quarantined_count,
                "blocked": len(blocked_tasks),
                "coordination_messages": len(self.worktree_mgr.read_coordination_messages()),
                "trace_id": fleet_span["trace_id"],
            }
            fleet_span["attributes"].update(
                {
                    "orchestrator.completed": summary["completed"],
                    "orchestrator.failed": summary["failed"],
                    "orchestrator.quarantined": summary["quarantined"],
                    "orchestrator.blocked": summary["blocked"],
                }
            )
            return summary
