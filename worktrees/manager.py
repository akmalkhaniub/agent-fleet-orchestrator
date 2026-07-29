import os
import json
import shutil
import subprocess
import logging
import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("orchestrator.worktrees")


class WorktreeManager:
    """Manages parallel Git Worktrees and inter-agent file-based communication in /coordination."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self.worktree_base_dir = os.path.join(self.repo_path, ".worktrees")
        self.coordination_dir = os.path.join(self.repo_path, "coordination")

        os.makedirs(self.worktree_base_dir, exist_ok=True)
        os.makedirs(self.coordination_dir, exist_ok=True)
        self._ensure_git_repo()

    def _ensure_git_repo(self):
        """Ensure git repository is initialized with a main branch and initial commit."""
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            logger.info("Initializing Git repository...")
            self._run_git(["init", "-b", "main"])
            self._run_git(["config", "user.name", "Fleet Orchestrator"])
            self._run_git(["config", "user.email", "orchestrator@local"])
            self._run_git(["add", "-A"])
            self._run_git(["commit", "--allow-empty", "-m", "Initial commit for Agent Fleet Orchestrator"])
        else:
            # Check if repo has any commits, if not make one
            res = self._run_git(["rev-parse", "HEAD"])
            if res.returncode != 0:
                self._run_git(["config", "user.name", "Fleet Orchestrator"])
                self._run_git(["config", "user.email", "orchestrator@local"])
                self._run_git(["add", "-A"])
                self._run_git(["commit", "--allow-empty", "-m", "Initial commit for Agent Fleet Orchestrator"])

    def _run_git(self, args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        cwd = cwd or self.repo_path
        cmd = ["git"] + args
        logger.debug(f"Running git command: {' '.join(cmd)} in {cwd}")
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)

    def create_worktree(self, task_id: str) -> str:
        """Create a dedicated git worktree on branch feat/task-<task_id>."""
        safe_task_id = task_id.replace(" ", "_").lower()
        branch_name = f"feat/{safe_task_id}"
        worktree_path = os.path.join(self.worktree_base_dir, safe_task_id)



        # Ensure clean state by calling cleanup first
        self.cleanup(task_id)

        # Create new branch and worktree
        res = self._run_git(["worktree", "add", "-b", branch_name, worktree_path, "HEAD"])
        if res.returncode != 0 and ("already exists" in res.stderr or "already checked out" in res.stderr):
            res = self._run_git(["worktree", "add", worktree_path, branch_name])

        logger.info(f"Created worktree for task {task_id} at {worktree_path} on branch {branch_name}")
        return worktree_path

    def list_active(self) -> List[Dict[str, str]]:
        """List active worktrees managed by git."""
        res = self._run_git(["worktree", "list", "--porcelain"])
        if res.returncode != 0:
            return []

        worktrees = []
        current = {}
        for line in res.stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line.split(" ", 1)[1]}
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1]
        if current:
            worktrees.append(current)
        return worktrees

    def merge(self, task_id: str) -> bool:
        """Merge task branch back to current main HEAD after quality gates pass."""
        safe_task_id = task_id.replace(" ", "_").lower()
        branch_name = f"feat/{safe_task_id}"
        worktree_path = os.path.join(self.worktree_base_dir, safe_task_id)

        # 1. Commit changes in the worktree
        self._run_git(["add", "-A"], cwd=worktree_path)
        self._run_git(["commit", "--allow-empty", "-m", f"feat: completed task {task_id}"], cwd=worktree_path)

        # 2. Merge branch into root repo
        res = self._run_git(["merge", "--no-ff", branch_name, "-m", f"Orchestrator: auto-merge passing task {task_id}"])
        if res.returncode == 0:
            logger.info(f"Successfully merged branch {branch_name} into main.")
            self.cleanup(task_id)
            return True
        else:
            logger.error(f"Merge conflict or failure for task {task_id}: {res.stderr}")
            # Force fast-forward/checkout merge fallback for testing environments
            ff_res = self._run_git(["merge", branch_name])
            if ff_res.returncode == 0:
                self.cleanup(task_id)
                return True
            return False

    def cleanup(self, task_id: str) -> None:
        """Clean up worktree and delete task branch."""
        safe_task_id = task_id.replace(" ", "_").lower()
        branch_name = f"feat/{safe_task_id}"
        worktree_path = os.path.join(self.worktree_base_dir, safe_task_id)

        self._run_git(["worktree", "remove", "--force", worktree_path])
        self._run_git(["branch", "-D", branch_name])
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)
        logger.info(f"Cleaned up worktree and branch for task {task_id}")

    def post_coordination_message(self, sender_id: str, payload: Dict[str, Any]) -> str:
        """Drop status message in /coordination directory for file-based agent communication."""
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"msg_{ts}_{sender_id}.json"
        filepath = os.path.join(self.coordination_dir, filename)

        data = {
            "sender": sender_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": payload,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Agent {sender_id} posted coordination message {filename}")
        return filepath

    def read_coordination_messages(self) -> List[Dict[str, Any]]:
        """Read all messages dropped in /coordination."""
        messages = []
        if not os.path.exists(self.coordination_dir):
            return messages

        for fname in sorted(os.listdir(self.coordination_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(self.coordination_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        messages.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Failed to read coordination msg {fname}: {e}")
        return messages
