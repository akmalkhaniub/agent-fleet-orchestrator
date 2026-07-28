# Agent Fleet Orchestrator 🚀

> **Build the Leverage System, Not Just an App**

An enterprise-grade multi-agent fleet orchestration system demonstrating parallel git worktree isolation, closed-loop quality gates, custom Model Context Protocol (MCP) servers, and cost/latency model routing.

---

## 🌟 Core Architecture & Key Features

1. **Agent Fleet Orchestration**:
   - Decomposes plain-language feature requests into a Task DAG (`implement`, `test`, `review`, `document`).
   - Dispatches sub-tasks to specialized agent workers running in parallel.

2. **Parallel Execution via Git Worktrees**:
   - Each agent operates in its own isolated `.worktrees/task-<id>` directory on a dedicated `feat/task-<id>` git branch.
   - Eliminates filesystem and git collisions.

3. **Closed-Loop Quality Gates (Zero Open-Loop Merges)**:
   - **Eval Gate**: Semantic accuracy scoring.
   - **Review Gate**: Automated defensive coding & security rule validation against `RULES.md`.
   - **Test Gate**: Pytest & coverage enforcement.
   - Branches merge into `main` **only when 100% of quality gates pass**.

4. **Swappable Agent Workers & Model Routing**:
   - `AgentAdapter` interface supporting **Aider** (open-source default), **Claude Code**, **Cline**, and **MockAgent**.
   - Model routing powered by `LiteLLM` across OpenAI, Anthropic, Gemini, and local **Ollama** models via `config/models.yaml`.

5. **Custom MCP Servers**:
   - `project-context`: Serves project rules, architecture, and schemas to agents.
   - `eval-runner`: Enables agents to self-check quality gates pre-merge.

6. **Web Control Plane & CLI**:
   - FastAPI + Bootstrap real-time dashboard.
   - Typer + Rich CLI interface.

---

## 🚀 Quickstart Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Feature Orchestration via CLI
```bash
python cli.py run --title "User Authentication API" --description "Implement JWT auth endpoints with input validation and pytest unit tests."
```

### 3. View Git Worktrees & Coordination
```bash
python cli.py worktrees
python cli.py coordination
```

### 4. Launch Interactive Web Dashboard
```bash
python cli.py dashboard --port 8000
```
Then navigate to `http://localhost:8000` in your browser.
