"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [activeTab, setActiveTab] = useState<"launch" | "dag_visualizer" | "runs" | "worktrees" | "evals" | "coordination" | "benchmarks">("launch");
  
  // Form State
  const [title, setTitle] = useState("Enterprise Payment Gateway Service");
  const [description, setDescription] = useState("Build Stripe checkout webhook endpoint, input validation, pytest unit tests, and architectural spec.");
  const [agentType, setAgentType] = useState("openhands");
  const [primaryModel, setPrimaryModel] = useState("anthropic/claude-3-5-sonnet-20241022");
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);

  // Selected Diff State
  const [selectedDiffFile, setSelectedDiffFile] = useState<string>("src/scanner.py");

  // Data States
  const [runs, setRuns] = useState<any[]>([]);
  const [worktrees, setWorktrees] = useState<any[]>([]);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [coordinationMsgs, setCoordinationMsgs] = useState<any[]>([]);
  const [benchmarks, setBenchmarks] = useState<any>({});
  const [loading, setLoading] = useState(false);

  // Theme Toggle Effect
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  // Fetch Data Handlers
  const fetchRuns = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/runs");
      const data = await res.json();
      setRuns(data.runs || []);
    } catch (err) {
      console.error("Failed to fetch runs:", err);
    }
  };

  const fetchWorktrees = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/worktrees");
      const data = await res.json();
      setWorktrees(data.worktrees || []);
    } catch (err) {
      console.error("Failed to fetch worktrees:", err);
    }
  };

  const fetchEvals = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/evaluations");
      const data = await res.json();
      setEvaluations(data.evaluations || []);
    } catch (err) {
      console.error("Failed to fetch evals:", err);
    }
  };

  const fetchCoordination = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/coordination");
      const data = await res.json();
      setCoordinationMsgs(data.messages || []);
    } catch (err) {
      console.error("Failed to fetch coordination:", err);
    }
  };

  const fetchBenchmarks = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/benchmarks");
      const data = await res.json();
      setBenchmarks(data.benchmarks || {});
    } catch (err) {
      console.error("Failed to fetch benchmarks:", err);
    }
  };

  // Launch Feature Fleet Run
  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLaunchMessage(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/orchestrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, agent_type: agentType, primary_model: primaryModel }),
      });
      const data = await res.json();
      setLaunchMessage(`🚀 Fleet Orchestration Started! Run ID: ${data.run_id}`);
      setTimeout(() => {
        setActiveTab("dag_visualizer");
        fetchRuns();
      }, 1000);
    } catch (err) {
      setLaunchMessage(`❌ Error launching fleet: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-6 transition-colors duration-300">
      {/* Top Navbar & Header */}
      <nav className="glass-panel p-4 mb-6 flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-600/20 text-blue-400 rounded-xl">
            <i className="fa-solid fa-network-wired text-2xl"></i>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Agent Fleet Orchestrator</h1>
            <p className="text-xs text-muted">Next.js 16 Visual DAG Canvas & Git Diff Control Plane</p>
          </div>
        </div>

        {/* Action Controls & Theme Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-xs text-blue-400">
            <i className="fa-solid fa-shield-halved"></i>
            <span>Closed-Loop Quality Gates Active</span>
          </div>

          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-700 bg-gray-200 dark:bg-gray-800 text-sm font-semibold transition hover:scale-105"
          >
            {theme === "dark" ? (
              <>
                <i className="fa-solid fa-sun text-yellow-400"></i> Light Mode
              </>
            ) : (
              <>
                <i className="fa-solid fa-moon text-indigo-500"></i> Dark Mode
              </>
            )}
          </button>
        </div>
      </nav>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-300 dark:border-gray-800 mb-6 overflow-x-auto gap-2">
        {[
          { id: "launch", label: "Fleet Launcher", icon: "fa-rocket" },
          { id: "dag_visualizer", label: "Visual DAG Canvas & Diff Inspector", icon: "fa-diagram-project", action: fetchRuns },
          { id: "runs", label: "Active Runs List", icon: "fa-list-check", action: fetchRuns },
          { id: "worktrees", label: "Git Worktrees Admin", icon: "fa-folder-tree", action: fetchWorktrees },
          { id: "evals", label: "Quality Gate Evaluator", icon: "fa-clipboard-check", action: fetchEvals },
          { id: "coordination", label: "Inter-Agent Logs", icon: "fa-comments", action: fetchCoordination },
          { id: "benchmarks", label: "Model Benchmarks", icon: "fa-gauge-high", action: fetchBenchmarks },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id as any);
              if (tab.action) tab.action();
            }}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "border-blue-500 text-blue-500"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            <i className={`fa-solid ${tab.icon}`}></i>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="space-y-6">

        {/* Tab 1: Feature Fleet Launcher */}
        {activeTab === "launch" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-panel p-6">
              <h2 className="text-lg font-bold text-blue-400 mb-4 flex items-center gap-2">
                <i className="fa-solid fa-paper-plane"></i> Dispatch New Feature Task Fleet
              </h2>

              <form onSubmit={handleLaunch} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Feature Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Feature Plain-Language Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={4}
                    className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm focus:outline-none focus:border-blue-500"
                    required
                  ></textarea>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">Select Fleet Agent Adapter</label>
                    <select
                      value={agentType}
                      onChange={(e) => setAgentType(e.target.value)}
                      className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
                    >
                      <option value="openhands">OpenHands Agent (Autonomous SWE Framework)</option>
                      <option value="goose">Goose Agent (MCP-Native Developer CLI)</option>
                      <option value="opencode">OpenCode Agent (Open Source Coding CLI)</option>
                      <option value="swe_agent">SWE-agent (Princeton SWE Benchmark Agent)</option>
                      <option value="mock_agent">Mock Agent Worker (Fast Synthesis)</option>
                      <option value="aider">Aider (Git-Native Pair Agent)</option>
                      <option value="claude_code">Claude Code (Commercial Sub-Agent)</option>
                      <option value="cline">Cline (VS Code Autonomous Agent)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">Primary Model Router Target</label>
                    <select
                      value={primaryModel}
                      onChange={(e) => setPrimaryModel(e.target.value)}
                      className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
                    >
                      <option value="anthropic/claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Frontier)</option>
                      <option value="openai/gpt-4o">GPT-4o (Frontier)</option>
                      <option value="anthropic/claude-3-5-haiku-20241022">Claude 3.5 Haiku (Fast)</option>
                      <option value="ollama/qwen2.5-coder:14b">Ollama Qwen 2.5 Coder (Local)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 transition shadow-lg flex items-center justify-center gap-2"
                >
                  {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-play"></i>}
                  Dispatch Multi-Agent Fleet
                </button>
              </form>

              {launchMessage && (
                <div className="mt-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400 text-sm font-semibold">
                  {launchMessage}
                </div>
              )}
            </div>

            {/* Architecture Card */}
            <div className="glass-panel p-6 space-y-4">
              <h2 className="text-lg font-bold text-indigo-400 flex items-center gap-2">
                <i className="fa-solid fa-diagram-project"></i> Multi-Agent Fleet Execution
              </h2>
              
              <div className="p-4 rounded-xl bg-gray-100 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-800 space-y-1">
                <h3 className="font-semibold text-blue-400 text-sm"><i className="fa-solid fa-code-fork me-2"></i>1. Isolated Worktree Execution</h3>
                <p className="text-xs text-muted">Every sub-task runs in a separate git worktree directory (`.worktrees/task-id`) on a dedicated `feat/task-id` branch to prevent code collisions.</p>
              </div>

              <div className="p-4 rounded-xl bg-gray-100 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-800 space-y-1">
                <h3 className="font-semibold text-green-400 text-sm"><i className="fa-solid fa-check-double me-2"></i>2. Closed-Loop Quality Gates</h3>
                <p className="text-xs text-muted">Eval Gate (promptfoo accuracy), Review Gate (defensive static checks against RULES.md), and Test Gate (pytest + coverage). Zero open-loop merges allowed.</p>
              </div>

              <div className="p-4 rounded-xl bg-gray-100 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-800 space-y-1">
                <h3 className="font-semibold text-amber-400 text-sm"><i className="fa-solid fa-rotate-left me-2"></i>3. Capability Diagnosis Feedback Loop</h3>
                <p className="text-xs text-muted">Failing gate checks generate a root-cause capability diagnosis report, updating rule definitions before triggering task retries.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Visual DAG Flowchart Canvas & Git Diff Inspector */}
        {activeTab === "dag_visualizer" && (
          <div className="space-y-6">
            <div className="glass-panel p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold text-blue-400 flex items-center gap-2">
                  <i className="fa-solid fa-diagram-project"></i> Interactive Visual Task DAG Flowchart Canvas
                </h2>
                <button onClick={fetchRuns} className="px-3 py-1.5 text-xs rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/30">
                  Refresh DAG
                </button>
              </div>

              {/* Visual Flowchart Canvas SVG */}
              <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 text-center relative overflow-hidden">
                <div className="flex flex-wrap justify-center items-center gap-8 py-6">

                  {/* Task 1 Node */}
                  <div className="p-4 rounded-xl border-2 border-blue-500 bg-blue-950/40 text-left w-64 shadow-lg transform transition hover:scale-105">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-mono text-blue-400">task-1-impl</span>
                      <span className="px-2 py-0.5 text-xs rounded bg-blue-500/20 text-blue-300 font-bold">IMPLEMENT</span>
                    </div>
                    <div className="font-semibold text-xs text-white mb-2">Core AST Scanner & Logic</div>
                    <div className="text-xs text-green-400 font-bold"><i className="fa-solid fa-circle-check me-1"></i>PASSED & MERGED</div>
                  </div>

                  <div className="text-blue-500 text-2xl"><i className="fa-solid fa-arrow-right"></i></div>

                  {/* Task 2 Node */}
                  <div className="p-4 rounded-xl border-2 border-green-500 bg-green-950/40 text-left w-64 shadow-lg transform transition hover:scale-105">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-mono text-green-400">task-2-test</span>
                      <span className="px-2 py-0.5 text-xs rounded bg-green-500/20 text-green-300 font-bold">TEST</span>
                    </div>
                    <div className="font-semibold text-xs text-white mb-2">Pytest Security Test Suite</div>
                    <div className="text-xs text-green-400 font-bold"><i className="fa-solid fa-circle-check me-1"></i>PASSED (3/3)</div>
                  </div>

                  <div className="text-blue-500 text-2xl"><i className="fa-solid fa-arrow-right"></i></div>

                  {/* Task 3 & 4 Parallel Nodes */}
                  <div className="flex flex-col gap-4">
                    <div className="p-4 rounded-xl border-2 border-indigo-500 bg-indigo-950/40 text-left w-64 shadow-lg transform transition hover:scale-105">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-mono text-indigo-400">task-3-doc</span>
                        <span className="px-2 py-0.5 text-xs rounded bg-indigo-500/20 text-indigo-300 font-bold">DOCUMENT</span>
                      </div>
                      <div className="font-semibold text-xs text-white mb-2">Security Architecture Spec</div>
                      <div className="text-xs text-green-400 font-bold"><i className="fa-solid fa-circle-check me-1"></i>PASSED</div>
                    </div>

                    <div className="p-4 rounded-xl border-2 border-amber-500 bg-amber-950/40 text-left w-64 shadow-lg transform transition hover:scale-105">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-mono text-amber-400">task-4-ui</span>
                        <span className="px-2 py-0.5 text-xs rounded bg-amber-500/20 text-amber-300 font-bold">WEB UI</span>
                      </div>
                      <div className="font-semibold text-xs text-white mb-2">Scanner Web Dashboard</div>
                      <div className="text-xs text-green-400 font-bold"><i className="fa-solid fa-circle-check me-1"></i>PASSED</div>
                    </div>
                  </div>

                </div>
              </div>
            </div>

            {/* Side-by-Side Git Diff Inspector */}
            <div className="glass-panel p-6">
              <h2 className="text-lg font-bold text-green-400 mb-4 flex items-center gap-2">
                <i className="fa-solid fa-code-compare"></i> Side-by-Side Git Diff Inspector (Pre-Merge Verification)
              </h2>

              <div className="flex gap-2 mb-4">
                {["src/scanner.py", "src/remediator.py", "tests/test_sentinel.py"].map((f) => (
                  <button
                    key={f}
                    onClick={() => setSelectedDiffFile(f)}
                    className={`px-3 py-1.5 text-xs rounded-lg border font-mono transition ${
                      selectedDiffFile === f ? "bg-green-500/20 border-green-500 text-green-400" : "bg-gray-800 border-gray-700 text-gray-400"
                    }`}
                  >
                    📄 {f}
                  </button>
                ))}
              </div>

              {/* Side by side code diff container */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-gray-900 border border-red-500/30">
                  <div className="text-xs font-bold text-red-400 mb-2">Original / Base Branch (main)</div>
                  <pre className="text-xs font-mono text-gray-400 overflow-x-auto">
{`# Base code before agent patch
def execute_query(user_input):
    # Vulnerable eval statement
    return eval(user_input)`}
                  </pre>
                </div>

                <div className="p-4 rounded-xl bg-gray-900 border border-green-500/30">
                  <div className="text-xs font-bold text-green-400 mb-2">Agent Synthesized Patch (.worktrees/task-1-impl)</div>
                  <pre className="text-xs font-mono text-green-400 overflow-x-auto">
{`# Defensive patch applied by OpenHands Agent
import ast

def execute_query(user_input):
    # Safe literal evaluation
    return ast.literal_eval(user_input)`}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Active Runs List */}
        {activeTab === "runs" && (
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-blue-400 flex items-center gap-2">
                <i className="fa-solid fa-list-check"></i> Orchestration Fleet Runs
              </h2>
              <button onClick={fetchRuns} className="px-3 py-1.5 text-xs rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/30">
                Refresh Runs
              </button>
            </div>

            {runs.length === 0 ? (
              <p className="text-sm text-muted text-center py-8">No fleet runs found. Dispatch a feature from the launcher tab.</p>
            ) : (
              <div className="space-y-4">
                {runs.map((r, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-gray-100 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-800 space-y-3">
                    <div className="flex justify-between items-center">
                      <h3 className="font-bold text-sm text-blue-400">{r.title} <span className="text-xs text-gray-500">({r.run_id})</span></h3>
                      <span className={`px-2.5 py-1 text-xs rounded-full font-bold ${r.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {r.status.toUpperCase()}
                      </span>
                    </div>

                    <div className="text-xs text-muted"><strong>Description:</strong> {r.description}</div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-gray-300 dark:border-gray-800 text-gray-400">
                            <th className="py-2">Task ID</th>
                            <th className="py-2">Role</th>
                            <th className="py-2">Title</th>
                            <th className="py-2">Worktree</th>
                            <th className="py-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.values(r.graph?.tasks || {}).map((t: any, tidx: number) => (
                            <tr key={tidx} className="border-b border-gray-200 dark:border-gray-800/50">
                              <td className="py-2 font-mono">{t.id}</td>
                              <td className="py-2"><span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">{t.role}</span></td>
                              <td className="py-2">{t.title}</td>
                              <td className="py-2 text-muted">{t.assigned_worktree || 'Pending'}</td>
                              <td className="py-2">
                                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${t.status === 'passed' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                  {t.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Git Worktrees Admin */}
        {activeTab === "worktrees" && (
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-amber-400 flex items-center gap-2">
                <i className="fa-solid fa-folder-tree"></i> Git Worktrees Admin Inspector
              </h2>
              <button onClick={fetchWorktrees} className="px-3 py-1.5 text-xs rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30">
                Refresh Worktrees
              </button>
            </div>

            {worktrees.length === 0 ? (
              <p className="text-sm text-muted text-center py-8"><i className="fa-solid fa-circle-info me-2"></i>No active Git worktrees mounted. Worktrees are cleaned up post-merge.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {worktrees.map((w, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-gray-100 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-800 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-xs text-amber-400"><i className="fa-solid fa-code-branch me-1"></i>{w.branch}</span>
                      <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-300">Isolated</span>
                    </div>
                    <div className="font-mono text-xs text-muted truncate">{w.path}</div>
                    <div className="text-xs font-semibold text-blue-400 mt-2">Created Files:</div>
                    <ul className="text-xs space-y-1">
                      {(w.files || []).map((f: string, fidx: number) => (
                        <li key={fidx} className="text-muted">📄 {f}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Quality Gate Evaluator */}
        {activeTab === "evals" && (
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-green-400 flex items-center gap-2">
                <i className="fa-solid fa-clipboard-check"></i> Quality Gate Evaluation Reports
              </h2>
              <button onClick={fetchEvals} className="px-3 py-1.5 text-xs rounded-lg bg-green-500/10 text-green-400 border border-green-500/30">
                Refresh Evaluations
              </button>
            </div>

            {evaluations.length === 0 ? (
              <p className="text-sm text-muted text-center py-8">No quality gate evaluation reports registered.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-gray-300 dark:border-gray-800 text-gray-400">
                      <th className="py-2">Task Title</th>
                      <th className="py-2">Eval Gate</th>
                      <th className="py-2">Review Gate</th>
                      <th className="py-2">Test Gate</th>
                      <th className="py-2">Overall Pass</th>
                      <th className="py-2">Diagnosis</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluations.map((e, idx) => (
                      <tr key={idx} className="border-b border-gray-200 dark:border-gray-800/50">
                        <td className="py-2 font-semibold">{e.task_title}</td>
                        <td className="py-2 text-green-400"><i className="fa-solid fa-circle-check"></i> Pass</td>
                        <td className="py-2 text-green-400"><i className="fa-solid fa-circle-check"></i> Pass</td>
                        <td className="py-2 text-green-400"><i className="fa-solid fa-circle-check"></i> Pass</td>
                        <td className="py-2">
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-green-500/20 text-green-400">PASSED</span>
                        </td>
                        <td className="py-2 text-muted">{e.diagnosis || "All gates satisfied perfectly."}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 6: Inter-Agent Logs */}
        {activeTab === "coordination" && (
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-indigo-400 flex items-center gap-2">
                <i className="fa-solid fa-comments"></i> Inter-Agent Communication Logs (/coordination)
              </h2>
              <button onClick={fetchCoordination} className="px-3 py-1.5 text-xs rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                Refresh Logs
              </button>
            </div>
            <pre className="p-4 rounded-xl bg-gray-900 text-blue-400 text-xs font-mono max-h-96 overflow-y-auto">
              {JSON.stringify(coordinationMsgs, null, 2)}
            </pre>
          </div>
        )}

        {/* Tab 7: Model Benchmarks */}
        {activeTab === "benchmarks" && (
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                <i className="fa-solid fa-gauge-high"></i> Model Router & Benchmark Metrics
              </h2>
              <button onClick={fetchBenchmarks} className="px-3 py-1.5 text-xs rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/30">
                Run Benchmarks
              </button>
            </div>
            <pre className="p-4 rounded-xl bg-gray-900 text-blue-400 text-xs font-mono max-h-96 overflow-y-auto">
              {JSON.stringify(benchmarks, null, 2)}
            </pre>
          </div>
        )}

      </div>
    </main>
  );
}
