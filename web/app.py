import os
import json
import asyncio
import datetime
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.orchestrator import OrchestratorEngine
from worktrees.manager import WorktreeManager
from models.router import ModelRouter
from gates.pipeline import QualityGatePipeline
from core.schemas import Task, TaskGraph, TaskRole, TaskStatus

logger = logging.getLogger("orchestrator.web")

app = FastAPI(
    title="Agent Fleet Orchestrator - Web Control & Admin Panel",
    description="Full Web Control Plane and Admin Evaluation Suite for Multi-Agent Fleets",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = OrchestratorEngine()
worktree_mgr = WorktreeManager()
model_router = ModelRouter()
gate_pipeline = QualityGatePipeline()

# In-memory store for orchestration runs
runs_db: Dict[str, Dict[str, Any]] = {}


class LaunchFeatureRequest(BaseModel):
    title: str
    description: str
    agent_type: str = "mock_agent"
    primary_model: str = "anthropic/claude-3-5-sonnet-20241022"


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "repo_path": worktree_mgr.repo_path,
        "active_worktrees": len(worktree_mgr.list_active()),
    }


@app.post("/api/orchestrate")
async def launch_orchestration(req: LaunchFeatureRequest):
    graph = engine.decompose_feature(req.title, req.description)
    
    # Assign selected agent type to tasks
    for task in graph.tasks.values():
        task.agent_type = req.agent_type

    run_id = f"fleet-run-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    run_entry = {
        "run_id": run_id,
        "title": req.title,
        "description": req.description,
        "agent_type": req.agent_type,
        "primary_model": req.primary_model,
        "status": "running",
        "graph": graph.dict(),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "summary": None,
    }
    runs_db[run_id] = run_entry

    # Execute fleet task graph in background task loop
    async def run_in_background():
        summary = await engine.run_fleet(graph)
        runs_db[run_id]["status"] = "completed"
        runs_db[run_id]["summary"] = summary
        runs_db[run_id]["graph"] = graph.dict()

    asyncio.create_task(run_in_background())

    return {
        "run_id": run_id,
        "status": "started",
        "message": f"Orchestration initiated for feature '{req.title}'",
        "tasks_count": len(graph.tasks),
    }


@app.get("/api/runs")
def list_runs():
    return {"runs": list(runs_db.values())}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs_db[run_id]


@app.get("/api/worktrees")
def list_worktrees():
    trees = worktree_mgr.list_active()
    detailed_trees = []
    for t in trees:
        path = t.get("path", "")
        files = []
        if os.path.exists(path):
            for root, _, fnames in os.walk(path):
                if ".git" in root:
                    continue
                for f in fnames:
                    rel = os.path.relpath(os.path.join(root, f), path)
                    files.append(rel)
        detailed_trees.append({
            "branch": t.get("branch", "unknown"),
            "path": path,
            "files": files,
        })
    return {"worktrees": detailed_trees}


@app.get("/api/coordination")
def list_coordination():
    return {"messages": worktree_mgr.read_coordination_messages()}


@app.get("/api/evaluations")
def get_evaluations():
    """Retrieve quality gate evaluations & capability diagnostic reports."""
    # Synthesize sample evaluation report for dashboard inspection
    reports = []
    for run_id, run_data in runs_db.items():
        graph = run_data.get("graph", {})
        tasks = graph.get("tasks", {})
        for task_id, task in tasks.items():
            task_obj = Task(**task)
            report = gate_pipeline.evaluate_task(task_obj, task_obj.assigned_worktree or ".")
            reports.append({
                "run_id": run_id,
                "task_id": task_id,
                "task_title": task_obj.title,
                "all_passed": report.all_passed,
                "results": [r.dict() for r in report.results],
                "diagnosis": report.diagnosis,
            })
    return {"evaluations": reports}


@app.get("/api/benchmarks")
def model_benchmarks():
    return {"benchmarks": model_router.benchmark_models()}


@app.get("/", response_class=HTMLResponse)
def serve_unified_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Agent Fleet Orchestrator - Web Control & Admin Panel</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0b0f19;
                --card-bg: #151c2c;
                --card-border: #232d42;
                --accent-blue: #38bdf8;
                --accent-purple: #818cf8;
                --accent-green: #34d399;
                --accent-red: #f87171;
                --text-main: #f1f5f9;
                --text-muted: #94a3b8;
            }

            body {
                background-color: var(--bg-dark);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding-bottom: 3rem;
            }

            .navbar-custom {
                background: rgba(21, 28, 44, 0.85);
                backdrop-filter: blur(12px);
                border-bottom: 1px solid var(--card-border);
                padding: 1rem 2rem;
            }

            .card-custom {
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }

            .nav-tabs .nav-link {
                color: var(--text-muted);
                border: none;
                border-bottom: 2px solid transparent;
                font-weight: 500;
                padding: 0.75rem 1.25rem;
            }

            .nav-tabs .nav-link.active {
                color: var(--accent-blue);
                background: transparent;
                border-bottom: 2px solid var(--accent-blue);
            }

            .hero-badge {
                background: linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(129, 140, 248, 0.1));
                border: 1px solid rgba(56, 189, 248, 0.3);
                color: var(--accent-blue);
                padding: 0.35rem 0.85rem;
                border-radius: 20px;
                font-size: 0.85rem;
            }

            .badge-status-running { background-color: rgba(56, 189, 248, 0.2); color: var(--accent-blue); }
            .badge-status-passed { background-color: rgba(52, 211, 153, 0.2); color: var(--accent-green); }
            .badge-status-failed { background-color: rgba(248, 113, 113, 0.2); color: var(--accent-red); }

            pre.code-view {
                background-color: #090d16;
                border: 1px solid #1e293b;
                color: #38bdf8;
                padding: 1rem;
                border-radius: 10px;
                font-size: 0.85rem;
                max-height: 400px;
                overflow-y: auto;
            }

            .btn-accent {
                background: linear-gradient(135deg, #3b82f6, #6366f1);
                border: none;
                color: #ffffff;
                font-weight: 600;
                border-radius: 10px;
                padding: 0.65rem 1.5rem;
            }

            .btn-accent:hover {
                background: linear-gradient(135deg, #2563eb, #4f46e5);
                color: #ffffff;
            }
        </style>
    </head>
    <body>
        <!-- Header Navbar -->
        <nav class="navbar navbar-custom sticky-top mb-4">
            <div class="container-fluid d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-3">
                    <i class="fa-solid fa-network-wired text-info fs-3"></i>
                    <div>
                        <h4 class="mb-0 fw-bold">Agent Fleet Orchestrator</h4>
                        <small class="text-muted">Web Control Plane & Closed-Loop Admin Evaluation Panel</small>
                    </div>
                </div>
                <div>
                    <span class="hero-badge me-2"><i class="fa-solid fa-shield-halved me-1"></i> Closed-Loop Gates Active</span>
                    <span class="hero-badge"><i class="fa-solid fa-code-branch me-1"></i> Git Worktree Isolated</span>
                </div>
            </div>
        </nav>

        <div class="container-fluid px-4">
            <!-- Navigation Tabs -->
            <ul class="nav nav-tabs mb-4" id="mainTabs" role="tablist">
                <li class="nav-item">
                    <button class="nav-link active" id="launch-tab" data-bs-toggle="tab" data-bs-target="#launch-pane"><i class="fa-solid fa-rocket me-2"></i>Feature Fleet Launcher</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="runs-tab" data-bs-toggle="tab" data-bs-target="#runs-pane" onclick="fetchRuns()"><i class="fa-solid fa-list-check me-2"></i>Active Runs & DAG</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="worktrees-tab" data-bs-toggle="tab" data-bs-target="#worktrees-pane" onclick="fetchWorktrees()"><i class="fa-solid fa-folder-tree me-2"></i>Git Worktrees Admin</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="evals-tab" data-bs-toggle="tab" data-bs-target="#evals-pane" onclick="fetchEvals()"><i class="fa-solid fa-clipboard-check me-2"></i>Quality Gate Evaluator</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="coordination-tab" data-bs-toggle="tab" data-bs-target="#coordination-pane" onclick="fetchCoordination()"><i class="fa-solid fa-comments me-2"></i>Inter-Agent Logs</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="benchmarks-tab" data-bs-toggle="tab" data-bs-target="#benchmarks-pane" onclick="fetchBenchmarks()"><i class="fa-solid fa-gauge-high me-2"></i>Model Router & Benchmarks</button>
                </li>
            </ul>

            <!-- Tab Contents -->
            <div class="tab-content" id="mainTabContent">

                <!-- 1. Feature Fleet Launcher Pane -->
                <div class="tab-pane fade show active" id="launch-pane">
                    <div class="row g-4">
                        <div class="col-lg-6">
                            <div class="card-custom p-4">
                                <h5 class="fw-bold text-info mb-3"><i class="fa-solid fa-paper-plane me-2"></i>Dispatch New Feature Task Fleet</h5>
                                <form id="launchForm">
                                    <div class="mb-3">
                                        <label class="form-label text-muted">Feature Title</label>
                                        <input type="text" id="featTitle" class="form-control bg-dark text-light border-secondary" placeholder="e.g. Order Processing Microservice" value="Order Processing Microservice" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label text-muted">Feature Plain-Language Description</label>
                                        <textarea id="featDesc" class="form-control bg-dark text-light border-secondary" rows="4" required>Build an order processing service with input validation, pytest unit test suite, defensive rule checks, and architectural markdown documentation.</textarea>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label text-muted">Select Fleet Agent Adapter</label>
                                            <select id="agentType" class="form-select bg-dark text-light border-secondary">
                                                <option value="opencode" selected>OpenCode Agent (Open Source Autonomous SWE)</option>
                                                <option value="mock_agent">Mock Agent Worker (Fast Synthesis)</option>
                                                <option value="aider">Aider (Git-Native CLI Agent)</option>
                                                <option value="claude_code">Claude Code (Commercial Sub-Agent)</option>
                                                <option value="cline">Cline (VS Code Agent)</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label text-muted">Primary Model Router Target</label>
                                            <select id="primaryModel" class="form-select bg-dark text-light border-secondary">
                                                <option value="anthropic/claude-3-5-sonnet-20241022" selected>Claude 3.5 Sonnet (Frontier)</option>
                                                <option value="openai/gpt-4o">GPT-4o (Frontier)</option>
                                                <option value="anthropic/claude-3-5-haiku-20241022">Claude 3.5 Haiku (Fast)</option>
                                                <option value="ollama/qwen2.5-coder:14b">Ollama Qwen 2.5 Coder (Local)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <button type="submit" class="btn btn-accent w-100 mt-2"><i class="fa-solid fa-play me-2"></i>Launch Multi-Agent Fleet</button>
                                </form>
                                <div id="launchOutput" class="mt-3"></div>
                            </div>
                        </div>

                        <!-- System Architecture Overview -->
                        <div class="col-lg-6">
                            <div class="card-custom p-4">
                                <h5 class="fw-bold text-purple mb-3"><i class="fa-solid fa-diagram-project me-2"></i>Fleet Architecture & Quality Gates</h5>
                                <div class="p-3 bg-dark rounded border border-secondary mb-3">
                                    <h6 class="text-info"><i class="fa-solid fa-code-fork me-2"></i>1. Isolated Worktree Execution</h6>
                                    <p class="small text-muted mb-0">Every sub-task runs in a separate git worktree directory (`.worktrees/task-<id>`) on a dedicated `feat/task-<id>` branch to prevent merge collisions.</p>
                                </div>
                                <div class="p-3 bg-dark rounded border border-secondary mb-3">
                                    <h6 class="text-success"><i class="fa-solid fa-check-double me-2"></i>2. 3-Layer Quality Gate Pipeline</h6>
                                    <p class="small text-muted mb-0">Eval Gate (promptfoo accuracy), Review Gate (defensive static checks), and Test Gate (pytest + coverage). Zero open-loop merges allowed.</p>
                                </div>
                                <div class="p-3 bg-dark rounded border border-secondary">
                                    <h6 class="text-warning"><i class="fa-solid fa-rotate-left me-2"></i>3. Capability Diagnosis Feedback Loop</h6>
                                    <p class="small text-muted mb-0">Failed gate checks generate a root-cause diagnosis report, updating rule definitions before task retries.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 2. Active Runs & Task DAG Pane -->
                <div class="tab-pane fade" id="runs-pane">
                    <div class="card-custom p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-info mb-0"><i class="fa-solid fa-network-wired me-2"></i>Orchestration Fleet Runs</h5>
                            <button class="btn btn-outline-info btn-sm" onclick="fetchRuns()"><i class="fa-solid fa-rotate me-1"></i>Refresh Runs</button>
                        </div>
                        <div id="runsContainer">Loading runs...</div>
                    </div>
                </div>

                <!-- 3. Git Worktrees Admin Pane -->
                <div class="tab-pane fade" id="worktrees-pane">
                    <div class="card-custom p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-warning mb-0"><i class="fa-solid fa-folder-tree me-2"></i>Git Worktrees Admin Inspector</h5>
                            <button class="btn btn-outline-warning btn-sm" onclick="fetchWorktrees()"><i class="fa-solid fa-rotate me-1"></i>Refresh Worktrees</button>
                        </div>
                        <div id="worktreesContainer">Loading active worktrees...</div>
                    </div>
                </div>

                <!-- 4. Quality Gate Evaluator Pane -->
                <div class="tab-pane fade" id="evals-pane">
                    <div class="card-custom p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-success mb-0"><i class="fa-solid fa-clipboard-check me-2"></i>Quality Gate Evaluation Reports</h5>
                            <button class="btn btn-outline-success btn-sm" onclick="fetchEvals()"><i class="fa-solid fa-rotate me-1"></i>Refresh Evaluations</button>
                        </div>
                        <div id="evalsContainer">Loading gate evaluation reports...</div>
                    </div>
                </div>

                <!-- 5. Inter-Agent Coordination Pane -->
                <div class="tab-pane fade" id="coordination-pane">
                    <div class="card-custom p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-info mb-0"><i class="fa-solid fa-comments me-2"></i>Inter-Agent Communication Logs (/coordination)</h5>
                            <button class="btn btn-outline-info btn-sm" onclick="fetchCoordination()"><i class="fa-solid fa-rotate me-1"></i>Refresh Logs</button>
                        </div>
                        <div id="coordContainer">Loading inter-agent coordination logs...</div>
                    </div>
                </div>

                <!-- 6. Model Router & Benchmarks Pane -->
                <div class="tab-pane fade" id="benchmarks-pane">
                    <div class="card-custom p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-purple mb-0"><i class="fa-solid fa-gauge-high me-2"></i>Model Router & Benchmark Metrics</h5>
                            <button class="btn btn-outline-primary btn-sm" onclick="fetchBenchmarks()"><i class="fa-solid fa-rotate me-1"></i>Run Benchmark Suite</button>
                        </div>
                        <div id="benchmarksContainer">Loading model benchmark performance...</div>
                    </div>
                </div>

            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Launch Orchestration
            document.getElementById('launchForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const title = document.getElementById('featTitle').value;
                const description = document.getElementById('featDesc').value;
                const agent_type = document.getElementById('agentType').value;
                const primary_model = document.getElementById('primaryModel').value;

                document.getElementById('launchOutput').innerHTML = '<div class="alert alert-info"><div class="spinner-border spinner-border-sm me-2"></div> Initiating agent fleet decomposition...</div>';

                try {
                    const res = await fetch('/api/orchestrate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title, description, agent_type, primary_model })
                    });
                    const data = await res.json();
                    document.getElementById('launchOutput').innerHTML = `<div class="alert alert-success fw-semibold"><i class="fa-solid fa-circle-check me-2"></i>${data.message} (Run ID: ${data.run_id})</div>`;
                    
                    // Switch to active runs tab
                    setTimeout(() => {
                        const runsTab = new bootstrap.Tab(document.getElementById('runs-tab'));
                        runsTab.show();
                        fetchRuns();
                    }, 1200);
                } catch (err) {
                    document.getElementById('launchOutput').innerHTML = `<div class="alert alert-danger">Error starting orchestration: ${err}</div>`;
                }
            });

            // Fetch Runs & DAG
            async function fetchRuns() {
                const res = await fetch('/api/runs');
                const data = await res.json();
                const container = document.getElementById('runsContainer');
                if (!data.runs || data.runs.length === 0) {
                    container.innerHTML = '<div class="text-muted p-4 text-center">No active or historical fleet runs found. Dispatch a feature from the launcher tab.</div>';
                    return;
                }

                let html = '<div class="accordion" id="runsAccordion">';
                data.runs.forEach((r, idx) => {
                    const statusClass = r.status === 'completed' ? 'badge-status-passed' : 'badge-status-running';
                    const graph = r.graph || {};
                    const tasks = graph.tasks || {};

                    html += `
                    <div class="accordion-item bg-dark border-secondary text-light mb-3 rounded overflow-hidden">
                        <h2 class="accordion-header">
                            <button class="accordion-button bg-dark text-light border-0 shadow-none collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseRun${idx}">
                                <div class="d-flex justify-content-between align-items-center w-100 me-3">
                                    <div>
                                        <strong class="text-info">${r.title}</strong>
                                        <small class="text-muted ms-2">(${r.run_id})</small>
                                    </div>
                                    <span class="badge ${statusClass}">${r.status.toUpperCase()}</span>
                                </div>
                            </button>
                        </h2>
                        <div id="collapseRun${idx}" class="accordion-collapse collapse" data-bs-parent="#runsAccordion">
                            <div class="accordion-body border-top border-secondary">
                                <p class="text-muted small mb-3"><strong>Description:</strong> ${r.description}</p>
                                <div class="row g-2 mb-3">
                                    <div class="col-md-4"><small class="text-muted">Agent Worker:</small> <span class="badge bg-secondary">${r.agent_type}</span></div>
                                    <div class="col-md-4"><small class="text-muted">Primary Model:</small> <span class="badge bg-secondary">${r.primary_model}</span></div>
                                    <div class="col-md-4"><small class="text-muted">Started At:</small> <span class="badge bg-secondary">${r.created_at}</span></div>
                                </div>
                                <h6 class="fw-bold text-info">Task Execution Graph (DAG):</h6>
                                <div class="table-responsive">
                                    <table class="table table-dark table-hover table-sm border-secondary align-middle">
                                        <thead>
                                            <tr>
                                                <th>Task ID</th>
                                                <th>Role</th>
                                                <th>Title</th>
                                                <th>Worktree</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>`;
                                        Object.values(tasks).forEach(t => {
                                            const tStatusClass = t.status === 'passed' ? 'badge-status-passed' : (t.status === 'failed' ? 'badge-status-failed' : 'badge-status-running');
                                            html += `<tr>
                                                <td><code>${t.id}</code></td>
                                                <td><span class="badge bg-info text-dark">${t.role}</span></td>
                                                <td>${t.title}</td>
                                                <td><small class="text-muted">${t.assigned_worktree || 'Pending'}</small></td>
                                                <td><span class="badge ${tStatusClass}">${t.status}</span></td>
                                            </tr>`;
                                        });
                    html += `           </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>`;
                });
                html += '</div>';
                container.innerHTML = html;
            }

            // Fetch Worktrees Admin
            async function fetchWorktrees() {
                const res = await fetch('/api/worktrees');
                const data = await res.json();
                const container = document.getElementById('worktreesContainer');
                if (!data.worktrees || data.worktrees.length === 0) {
                    container.innerHTML = '<div class="text-muted p-4 text-center"><i class="fa-solid fa-circle-info me-2"></i>No active Git worktrees currently mounted. Worktrees are cleaned up post-merge.</div>';
                    return;
                }

                let html = '<div class="row g-3">';
                data.worktrees.forEach(w => {
                    html += `
                    <div class="col-md-6">
                        <div class="p-3 bg-dark border border-secondary rounded">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="fw-bold text-warning mb-0"><i class="fa-solid fa-code-branch me-2"></i>${w.branch}</h6>
                                <span class="badge bg-secondary">Isolated</span>
                            </div>
                            <p class="small text-muted mb-2"><code>${w.path}</code></p>
                            <h6 class="small fw-bold text-info">Created Files:</h6>
                            <ul class="list-group list-group-flush bg-transparent">`;
                            (w.files || []).forEach(f => {
                                html += `<li class="list-group-item bg-transparent text-light border-secondary py-1 small">📄 ${f}</li>`;
                            });
                            if ((w.files || []).length === 0) {
                                html += '<li class="list-group-item bg-transparent text-muted py-1 small">No files created yet.</li>';
                            }
                    html += `</ul>
                        </div>
                    </div>`;
                });
                html += '</div>';
                container.innerHTML = html;
            }

            // Fetch Quality Gate Evaluations
            async function fetchEvals() {
                const res = await fetch('/api/evaluations');
                const data = await res.json();
                const container = document.getElementById('evalsContainer');
                if (!data.evaluations || data.evaluations.length === 0) {
                    container.innerHTML = '<div class="text-muted p-4 text-center">No quality gate evaluation reports registered. Launch a fleet run first.</div>';
                    return;
                }

                let html = '<div class="table-responsive">';
                html += `<table class="table table-dark table-hover border-secondary align-middle">
                    <thead>
                        <tr>
                            <th>Task Title</th>
                            <th>Eval Gate</th>
                            <th>Review Gate</th>
                            <th>Test Gate</th>
                            <th>Overall Pass</th>
                            <th>Capability Diagnosis</th>
                        </tr>
                    </thead>
                    <tbody>`;
                data.evaluations.forEach(e => {
                    const passBadge = e.all_passed ? '<span class="badge badge-status-passed"><i class="fa-solid fa-check me-1"></i>PASSED</span>' : '<span class="badge badge-status-failed"><i class="fa-solid fa-xmark me-1"></i>FAILED</span>';
                    const results = e.results || [];
                    const evalGate = results.find(r => r.gate_type === 'eval') || {};
                    const reviewGate = results.find(r => r.gate_type === 'review') || {};
                    const testGate = results.find(r => r.gate_type === 'test') || {};

                    html += `<tr>
                        <td><strong>${e.task_title}</strong><br><small class="text-muted">${e.task_id}</small></td>
                        <td>${evalGate.passed ? '<span class="text-success"><i class="fa-solid fa-check-circle"></i> Pass</span>' : '<span class="text-danger"><i class="fa-solid fa-circle-xmark"></i> Fail</span>'}</td>
                        <td>${reviewGate.passed ? '<span class="text-success"><i class="fa-solid fa-check-circle"></i> Pass</span>' : '<span class="text-danger"><i class="fa-solid fa-circle-xmark"></i> Fail</span>'}</td>
                        <td>${testGate.passed ? '<span class="text-success"><i class="fa-solid fa-check-circle"></i> Pass</span>' : '<span class="text-danger"><i class="fa-solid fa-circle-xmark"></i> Fail</span>'}</td>
                        <td>${passBadge}</td>
                        <td><small class="text-muted">${e.diagnosis || 'All gates satisfied perfectly.'}</small></td>
                    </tr>`;
                });
                html += '</tbody></table></div>';
                container.innerHTML = html;
            }

            // Fetch Inter-Agent Coordination Logs
            async function fetchCoordination() {
                const res = await fetch('/api/coordination');
                const data = await res.json();
                const container = document.getElementById('coordContainer');
                if (!data.messages || data.messages.length === 0) {
                    container.innerHTML = '<div class="text-muted p-4 text-center">No inter-agent messages logged in /coordination.</div>';
                } else {
                    container.innerHTML = `<pre class="code-view">${JSON.stringify(data.messages, null, 2)}</pre>`;
                }
            }

            // Fetch Model Benchmarks
            async function fetchBenchmarks() {
                const res = await fetch('/api/benchmarks');
                const data = await res.json();
                const container = document.getElementById('benchmarksContainer');
                container.innerHTML = `<pre class="code-view">${JSON.stringify(data.benchmarks, null, 2)}</pre>`;
            }

            // Auto refresh runs tab every 5 seconds if active
            setInterval(() => {
                if (document.getElementById('runs-pane').classList.contains('show')) {
                    fetchRuns();
                }
            }, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
