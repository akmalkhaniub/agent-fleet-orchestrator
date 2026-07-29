import pytest
import os
import asyncio
from core.schemas import Task, TaskRole, TaskStatus
from core.orchestrator import OrchestratorEngine
from worktrees.manager import WorktreeManager
from models.router import ModelRouter
from gates.pipeline import QualityGatePipeline


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
    assert len(graph.tasks) == 3

    summary = await engine.run_fleet(graph)
    assert summary["completed"] == 3
    assert summary["failed"] == 0
