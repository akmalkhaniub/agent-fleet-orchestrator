import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from core.orchestrator import OrchestratorEngine
from worktrees.manager import WorktreeManager
from models.router import ModelRouter

app = FastAPI(
    title="Agent Fleet Orchestrator Control Plane",
    description="Real-time monitoring dashboard for agent fleets, worktrees, quality gates, and model benchmarks.",
    version="1.0.0",
)

engine = OrchestratorEngine()
worktree_mgr = WorktreeManager()
model_router = ModelRouter()


@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "Agent Fleet Orchestrator"}


@app.get("/api/worktrees")
def list_worktrees():
    return {"worktrees": worktree_mgr.list_active()}


@app.get("/api/coordination")
def list_coordination():
    return {"messages": worktree_mgr.read_coordination_messages()}


@app.get("/api/benchmarks")
def model_benchmarks():
    return {"benchmarks": model_router.benchmark_models()}


@app.post("/api/orchestrate")
async def start_orchestration(title: str, description: str):
    graph = engine.decompose_feature(title, description)
    summary = await engine.run_fleet(graph)
    return {"status": "success", "summary": summary}


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Agent Fleet Orchestrator Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; }
            .badge-active { background-color: #38bdf8; color: #0f172a; }
            .badge-success { background-color: #4ade80; color: #0f172a; }
            .badge-failed { background-color: #f87171; color: #0f172a; }
            .header-banner { background: linear-gradient(135deg, #3b82f6, #8b5cf6); padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }
            pre { background-color: #0f172a; color: #38bdf8; padding: 1rem; border-radius: 8px; font-size: 0.85rem; }
        </style>
    </head>
    <body class="p-4">
        <div class="container-fluid">
            <div class="header-banner shadow-lg text-white">
                <h1 class="display-5 fw-bold">Agent Fleet Orchestrator</h1>
                <p class="lead mb-0">Multi-Agent Task Decomposition, Git Worktree Isolation & Closed-Loop Quality Gates</p>
            </div>

            <div class="row g-4">
                <!-- Launch Control -->
                <div class="col-md-5">
                    <div class="card p-4 shadow">
                        <h4 class="card-title text-info mb-3">🚀 Launch Feature Orchestration</h4>
                        <form id="orchForm">
                            <div class="mb-3">
                                <label class="form-label text-slate-300">Feature Title</label>
                                <input type="text" id="featTitle" class="form-control bg-dark text-light border-secondary" value="Build User Auth Service" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-slate-300">Description</label>
                                <textarea id="featDesc" class="form-control bg-dark text-light border-secondary" rows="3" required>Implement JWT authentication with input validation, pytest test suite, and architectural docs.</textarea>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 fw-bold">Dispatch Fleet Engine</button>
                        </form>
                        <div id="orchResult" class="mt-3"></div>
                    </div>
                </div>

                <!-- Live Metrics & Worktrees -->
                <div class="col-md-7">
                    <div class="card p-4 shadow mb-4">
                        <h4 class="card-title text-purple mb-3">🌳 Git Worktree Isolation (.worktrees/)</h4>
                        <button class="btn btn-outline-info btn-sm mb-3" onclick="fetchWorktrees()">Refresh Worktrees</button>
                        <div id="worktreeList">Loading worktrees...</div>
                    </div>

                    <div class="card p-4 shadow">
                        <h4 class="card-title text-success mb-3">💬 Inter-Agent Coordination (/coordination)</h4>
                        <button class="btn btn-outline-success btn-sm mb-3" onclick="fetchCoordination()">Refresh Messages</button>
                        <div id="coordList">Loading inter-agent communications...</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function fetchWorktrees() {
                const res = await fetch('/api/worktrees');
                const data = await res.json();
                let html = '<ul class="list-group list-group-flush bg-transparent">';
                if (!data.worktrees || data.worktrees.length === 0) {
                    html += '<li class="list-group-item bg-transparent text-muted">No active worktrees running.</li>';
                } else {
                    data.worktrees.forEach(w => {
                        html += `<li class="list-group-item bg-transparent text-light border-secondary">
                            <strong>${w.branch || 'main'}</strong> - <span class="text-info">${w.path}</span>
                        </li>`;
                    });
                }
                html += '</ul>';
                document.getElementById('worktreeList').innerHTML = html;
            }

            async function fetchCoordination() {
                const res = await fetch('/api/coordination');
                const data = await res.json();
                if (!data.messages || data.messages.length === 0) {
                    document.getElementById('coordList').innerHTML = '<span class="text-muted">No coordination messages logged.</span>';
                } else {
                    document.getElementById('coordList').innerHTML = `<pre>${JSON.stringify(data.messages, null, 2)}</pre>`;
                }
            }

            document.getElementById('orchForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const title = document.getElementById('featTitle').value;
                const description = document.getElementById('featDesc').value;
                document.getElementById('orchResult').innerHTML = '<div class="spinner-border text-info" role="status"></div> Running fleet...';

                const res = await fetch(`/api/orchestrate?title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}`, { method: 'POST' });
                const data = await res.json();
                document.getElementById('orchResult').innerHTML = `<div class="alert alert-success mt-2"><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
                fetchWorktrees();
                fetchCoordination();
            });

            fetchWorktrees();
            fetchCoordination();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
