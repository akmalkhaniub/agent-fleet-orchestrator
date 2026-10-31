# AGENTS.md — Autonomous Agent Operating Contract

## 🎯 Repository Purpose & Architecture
`agent-fleet-orchestrator` is an enterprise multi-agent fleet orchestration engine that decomposes natural language feature requests into task DAGs executed concurrently across isolated git worktrees (`.worktrees/task-<id>`), enforcing closed-loop quality gates (AST review, test coverage, and semantic eval scoring) before branch merge into `main`.

### Tech Stack
- **Language**: Python 3.10+
- **Architecture Modules**:
  - `core/`: Task DAG engine, state management, and orchestrator loops (`orchestrator.py`, `schemas.py`)
  - `worktrees/`: Git worktree manager (`manager.py`)
  - `gates/`: Quality gate pipeline (`pipeline.py`, `ast_reviewer.py`, `coverage_gate.py`)
  - `models/`: LiteLLM model routing engine (`router.py`)
  - `mcp/`: Custom MCP servers (`project_context.py`, `eval_runner.py`)
  - `cli.py` & `dashboard/`: Typer CLI and FastAPI web dashboard

---

## ⚡ Autonomous Execution Protocol
1. Pull next task from `TASKS.json`.
2. Inspect target module in `core/`, `worktrees/`, `gates/`, or `models/`.
3. Implement changes adhering strictly to `RULES.md` and Pydantic schemas.
4. Execute single quality gate verification:
   ```bash
   python -m pytest tests/ -v
   ```
5. If tests fail, iterate and self-heal until exit code is 0.
6. Commit with conventional commit message: `feat(task-id): description`.

---

## 🛡️ Non-Negotiable Quality Rules
- **Worktree Hermeticity**: Never modify the parent repository root directly during task execution; all actions must occur inside `.worktrees/task-<id>`.
- **Zero Open-Loop Merges**: No branch is ever merged into `main` unless 100% of quality gates pass (`AST review`, `test coverage >= 80%`, `pytest passes`).
- **No eval/exec**: Never use dynamic execution (`eval()`, `exec()`).
- **Schema Strictness**: All inter-agent coordination messages and task states must serialize to Pydantic models in `core/schemas.py`.

---

## 🧪 Verification Commands
- **Full Test Suite**: `python -m pytest tests/ -v`
- **CLI Self-Test**: `python cli.py --help`
