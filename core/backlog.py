import json
import os
from typing import Any, Dict, List, Optional

from core.orchestrator import OrchestratorEngine
from core.schemas import Task, TaskGraph, TaskRole, TaskStatus


def _infer_target_files(item: Dict[str, Any]) -> List[str]:
    if item.get("target_files"):
        return list(item["target_files"])
    safe_id = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(item["id"])).strip("_")
    return [f"src/backlog/{safe_id}.py"]


def load_backlog(repo_path: str) -> List[Dict[str, Any]]:
    """Load TASKS.json from a target repository path."""
    tasks_path = os.path.join(os.path.abspath(repo_path), "TASKS.json")
    if not os.path.exists(tasks_path):
        raise FileNotFoundError(f"TASKS.json not found at {tasks_path}")
    with open(tasks_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("TASKS.json must contain a JSON array of task objects.")
    return data


def save_backlog(repo_path: str, items: List[Dict[str, Any]]) -> str:
    """Persist updated TASKS.json atomically to the target repository."""
    tasks_path = os.path.join(os.path.abspath(repo_path), "TASKS.json")
    tmp_path = f"{tasks_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, tasks_path)
    return tasks_path


async def run_backlog_daemon(
    repo_path: str,
    max_retries: int = 3,
    agent_type: str = "mock_agent",
    cleanup_stale: bool = False,
    engine: Optional[OrchestratorEngine] = None,
) -> Dict[str, Any]:
    """Ingest TASKS.json, execute pending TODO items in priority order, and write COMPLETED/QUARANTINED statuses back."""
    abs_repo = os.path.abspath(repo_path)
    items = load_backlog(abs_repo)
    pending = [item for item in items if str(item.get("status", "")).upper() == "TODO"]
    pending.sort(key=lambda x: (int(x.get("priority", 9999)), str(x.get("id", ""))))

    if not pending:
        return {
            "repo_path": abs_repo,
            "processed": 0,
            "completed": 0,
            "quarantined": 0,
            "items": [],
        }

    orch = engine or OrchestratorEngine(repo_path=abs_repo, max_retries=max_retries)
    if cleanup_stale:
        orch.worktree_mgr.cleanup_stale_worktrees()

    results: List[Dict[str, Any]] = []
    completed_count = 0
    quarantined_count = 0

    for item in pending:
        task_id = str(item["id"])
        criteria = item.get("acceptance_criteria") or []
        criteria_text = "\n".join(f"- {c}" for c in criteria)
        full_description = f"{item.get('description', '')}\n\nAcceptance Criteria:\n{criteria_text}".strip()

        role_raw = str(item.get("role", "implement")).lower()
        try:
            role = TaskRole(role_raw)
        except ValueError:
            role = TaskRole.IMPLEMENT

        task = Task(
            id=task_id,
            title=str(item.get("title", task_id)),
            description=full_description,
            role=role,
            dependencies=[],
            agent_type=item.get("agent_type") or agent_type,
            target_files=_infer_target_files(item),
        )
        graph = TaskGraph(
            feature_title=f"Backlog {task_id}: {task.title}",
            feature_description=task.description,
            tasks={task.id: task},
        )
        await orch.run_fleet(graph)

        if task.status == TaskStatus.PASSED:
            item["status"] = "COMPLETED"
            completed_count += 1
        else:
            item["status"] = "QUARANTINED"
            quarantined_count += 1

        results.append(
            {
                "id": task_id,
                "status": item["status"],
                "retries": task.retry_count,
                "error": task.error_message,
                "traceparent": task.traceparent,
            }
        )

    save_backlog(abs_repo, items)
    return {
        "repo_path": abs_repo,
        "processed": len(pending),
        "completed": completed_count,
        "quarantined": quarantined_count,
        "items": results,
    }
