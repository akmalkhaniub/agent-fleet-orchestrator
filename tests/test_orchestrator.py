import pytest
import os
import json
import time
import uuid
import asyncio
from typer.testing import CliRunner
from core.schemas import Task, TaskGraph, TaskRole, TaskStatus, AgentRun, AgentStatus, AgentResult
from core.orchestrator import OrchestratorEngine
from core.backlog import run_backlog_daemon
from core.telemetry import parse_traceparent
from worktrees.manager import WorktreeManager
from models.router import ModelRouter
from gates.pipeline import QualityGatePipeline
from agents.base import BaseAgentAdapter
from cli import app as cli_app


@pytest.fixture
def repo_dir(tmp_path):
    repo = tmp_path / "test_repo"
    repo.mkdir()
    return str(repo)


def test_model_router():
    router = ModelRouter()
    route = router.route_task(TaskRole.IMPLEMENT)
    assert route.selected_model is not None
    assert route.provider is not None


def test_worktree_manager(repo_dir):
    mgr = WorktreeManager(repo_path=repo_dir)
    assert os.path.exists(os.path.join(repo_dir, ".git"))

    worktree_path = mgr.create_worktree("test-task-1")
    assert os.path.exists(worktree_path)

    active = mgr.list_active()
    assert len(active) >= 1

    msg_path = mgr.post_coordination_message("agent-1", {"status": "testing"})
    assert os.path.exists(msg_path)

    msgs = mgr.read_coordination_messages()
    assert len(msgs) >= 1

    merged = mgr.merge("test-task-1")
    assert merged is True


def test_quality_gate_pipeline(repo_dir):
    pipeline = QualityGatePipeline()
    task = Task(
        id="gate-test",
        title="Gate Test Task",
        description="Testing gates",
        role=TaskRole.IMPLEMENT,
        target_files=["sample.py"],
    )

    # Create dummy target file
    sample_file = os.path.join(repo_dir, "sample.py")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("def hello():\n    return 'world'\n")

    report = pipeline.evaluate_task(task, repo_dir)
    assert report.all_passed is True


@pytest.mark.asyncio
async def test_orchestrator_fleet_run(repo_dir):
    engine = OrchestratorEngine(repo_path=repo_dir)
    graph = engine.decompose_feature("Auth Microservice", "Build authentication REST endpoints.")
    assert len(graph.tasks) == 4

    summary = await engine.run_fleet(graph)
    assert summary["completed"] == 4
    assert summary["failed"] == 0
    assert summary["quarantined"] == 0
    assert "trace_id" in summary and len(summary["trace_id"]) == 32

    trace_file = os.path.join(repo_dir, "coordination", "traces.jsonl")
    assert os.path.exists(trace_file)
    with open(trace_file, "r", encoding="utf-8") as f:
        spans = [json.loads(line) for line in f if line.strip()]
    assert any(s["name"] == "orchestrator.run_fleet" and s["trace_id"] == summary["trace_id"] for s in spans)


class HealingAdapter(BaseAgentAdapter):
    """Test adapter that injects an eval() violation on early attempts, then heals when traceback arrives."""

    def __init__(self, heal_on_attempt: int = 2):
        self.heal_on_attempt = heal_on_attempt
        self.seen_descriptions = []
        self._runs = {}

    async def start_task(self, task: Task, worktree_path: str) -> AgentRun:
        self.seen_descriptions.append(task.description)
        run_id = f"run-heal-{uuid.uuid4().hex[:8]}"
        target = os.path.join(worktree_path, task.target_files[0])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            if task.retry_count < self.heal_on_attempt:
                f.write("def unsafe():\n    return eval('1 + 1')\n")
            else:
                f.write("def safe():\n    return 1 + 1\n")
        run = AgentRun(
            run_id=run_id,
            task_id=task.id,
            agent_type="healing_test",
            worktree_path=worktree_path,
            status=AgentStatus.COMPLETED,
        )
        self._runs[run_id] = (run, task)
        return run

    async def poll(self, run: AgentRun) -> AgentStatus:
        return AgentStatus.COMPLETED

    async def get_result(self, run: AgentRun) -> AgentResult:
        _, task = self._runs[run.run_id]
        return AgentResult(run_id=run.run_id, task_id=task.id, success=True, modified_files=task.target_files)


@pytest.mark.asyncio
async def test_self_healing_retry_loop_recovery(repo_dir):
    engine = OrchestratorEngine(repo_path=repo_dir, max_retries=3)
    healer = HealingAdapter(heal_on_attempt=2)
    engine.adapters["healing_test"] = healer

    task = Task(
        id="heal-1",
        title="Self Healing Feature",
        description="Write safe arithmetic helper.",
        role=TaskRole.IMPLEMENT,
        target_files=["src/safe_math.py"],
        agent_type="healing_test",
    )
    graph = TaskGraph(feature_title="Healing Test", feature_description="Retry recovery", tasks={"heal-1": task})
    summary = await engine.run_fleet(graph)

    assert summary["completed"] == 1
    assert summary["quarantined"] == 0
    assert task.status == TaskStatus.PASSED
    assert task.retry_count == 2
    assert "[SELF-HEALING RETRY #1 TRACEBACK]" in healer.seen_descriptions[1]
    assert "eval()" in healer.seen_descriptions[2]


@pytest.mark.asyncio
async def test_self_healing_quarantine_after_max_retries_and_cascade(repo_dir):
    engine = OrchestratorEngine(repo_path=repo_dir, max_retries=3)
    never_heals = HealingAdapter(heal_on_attempt=99)
    engine.adapters["healing_test"] = never_heals

    root_task = Task(
        id="bad-root",
        title="Broken Root Task",
        description="Always fails review gate.",
        role=TaskRole.IMPLEMENT,
        target_files=["src/broken.py"],
        agent_type="healing_test",
    )
    child_task = Task(
        id="dependent-child",
        title="Dependent Child Task",
        description="Depends on bad-root.",
        role=TaskRole.TEST,
        dependencies=["bad-root"],
        target_files=["tests/test_broken.py"],
    )
    graph = TaskGraph(
        feature_title="Quarantine Test",
        feature_description="Exhaust 3 retries",
        tasks={"bad-root": root_task, "dependent-child": child_task},
    )
    summary = await engine.run_fleet(graph)

    assert len(never_heals.seen_descriptions) == 4  # initial + 3 retries
    assert root_task.status == TaskStatus.QUARANTINED
    assert root_task.retry_count == 3
    assert child_task.status == TaskStatus.BLOCKED
    assert summary["quarantined"] == 1
    assert summary["blocked"] == 1


def test_cleanup_stale_worktrees(repo_dir):
    mgr = WorktreeManager(repo_path=repo_dir)
    stale_path = mgr.create_worktree("stale-task")
    fresh_path = mgr.create_worktree("fresh-task")

    # Backdate stale worktree directory by 48 hours
    old_ts = time.time() - (48 * 3600)
    os.utime(stale_path, (old_ts, old_ts))

    gc_result = mgr.cleanup_stale_worktrees(max_age_hours=24.0)
    assert "stale-task" in gc_result["pruned_worktrees"]
    assert "feat/stale-task" in gc_result["deleted_branches"]
    assert not os.path.exists(stale_path)
    assert os.path.exists(fresh_path)

    mgr.cleanup("fresh-task")


@pytest.mark.asyncio
async def test_backlog_daemon_executes_and_persists_tasks(repo_dir):
    tasks_payload = [
        {
            "id": "DEMO-002",
            "status": "TODO",
            "priority": 2,
            "title": "Second priority task",
            "description": "Implement secondary module.",
            "acceptance_criteria": ["Module compiles"],
        },
        {
            "id": "DEMO-001",
            "status": "TODO",
            "priority": 1,
            "title": "First priority task",
            "description": "Implement primary module.",
            "acceptance_criteria": ["Module compiles"],
        },
        {
            "id": "DEMO-000",
            "status": "DONE",
            "priority": 0,
            "title": "Already finished",
            "description": "Skip me.",
            "acceptance_criteria": [],
        },
    ]
    tasks_file = os.path.join(repo_dir, "TASKS.json")
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks_payload, f)

    result = await run_backlog_daemon(repo_path=repo_dir, max_retries=3)
    assert result["processed"] == 2
    assert result["completed"] == 2
    assert result["quarantined"] == 0
    assert [item["id"] for item in result["items"]] == ["DEMO-001", "DEMO-002"]
    assert parse_traceparent(result["items"][0]["traceparent"]) is not None

    with open(tasks_file, "r", encoding="utf-8") as f:
        updated = {item["id"]: item for item in json.load(f)}
    assert updated["DEMO-001"]["status"] == "COMPLETED"
    assert updated["DEMO-002"]["status"] == "COMPLETED"
    assert updated["DEMO-000"]["status"] == "DONE"


def test_cli_daemon_and_gc_help():
    runner = CliRunner()
    res = runner.invoke(cli_app, ["--help"])
    assert res.exit_code == 0
    assert "daemon" in res.stdout
    assert "gc" in res.stdout
