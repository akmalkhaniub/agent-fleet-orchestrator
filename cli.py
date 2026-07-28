import asyncio
import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from core.orchestrator import OrchestratorEngine
from worktrees.manager import WorktreeManager
from models.router import ModelRouter

app = typer.Typer(name="Agent Fleet Orchestrator CLI")
console = Console()
engine = OrchestratorEngine()
worktree_mgr = WorktreeManager()
model_router = ModelRouter()


@app.command("run")
def run_fleet(
    title: str = typer.Option(..., "--title", "-t", help="Feature title"),
    description: str = typer.Option(..., "--description", "-d", help="Feature plain text description"),
):
    """Decompose feature request and execute multi-agent fleet across parallel git worktrees."""
    console.print(Panel.fit(f"[bold cyan]Agent Fleet Orchestrator[/bold cyan]\nFeature: [yellow]{title}[/yellow]", border_style="blue"))
    graph = engine.decompose_feature(title, description)

    table = Table(title="Decomposed Task Graph (DAG)", show_header=True, header_style="bold magenta")
    table.add_column("Task ID", style="dim")
    table.add_column("Role", style="green")
    table.add_column("Title")
    table.add_column("Dependencies")

    for task in graph.tasks.values():
        table.add_row(task.id, task.role.value, task.title, ", ".join(task.dependencies) or "None")

    console.print(table)
    console.print("[bold green]Executing task DAG across isolated Git Worktrees...[/bold green]")

    summary = asyncio.run(engine.run_fleet(graph))

    console.print(Panel.fit(
        f"[bold green]Orchestration Complete![/bold green]\n"
        f"Completed Tasks: [cyan]{summary['completed']}/{summary['total_tasks']}[/cyan]\n"
        f"Coordination Messages: [yellow]{summary['coordination_messages']}[/yellow]",
        border_style="green",
    ))


@app.command("worktrees")
def list_worktrees():
    """List active Git Worktrees managed by the orchestrator."""
    trees = worktree_mgr.list_active()
    table = Table(title="Active Git Worktrees", show_header=True, header_style="bold cyan")
    table.add_column("Branch", style="yellow")
    table.add_column("Path", style="dim")

    for t in trees:
        table.add_row(t.get("branch", "main"), t.get("path", ""))

    console.print(table)


@app.command("coordination")
def list_coordination():
    """Display inter-agent messages posted in the /coordination directory."""
    msgs = worktree_mgr.read_coordination_messages()
    console.print(f"[bold cyan]Total Inter-Agent Coordination Messages:[/bold cyan] {len(msgs)}")
    for m in msgs:
        console.print(m)


@app.command("benchmarks")
def model_benchmarks():
    """Display LiteLLM model router live benchmark metrics."""
    bench = model_router.benchmark_models()
    table = Table(title="Model Benchmark Metrics", show_header=True, header_style="bold green")
    table.add_column("Task ID")
    table.add_column("Latency (ms)")
    table.add_column("Status")

    for k, v in bench.items():
        table.add_row(k, str(v["latency_ms"]), v["status"])

    console.print(table)


@app.command("dashboard")
def launch_dashboard(port: int = typer.Option(8000, "--port", "-p", help="Port to run dashboard")):
    """Launch the interactive web control plane dashboard."""
    console.print(f"[bold green]Starting Control Plane Dashboard on http://localhost:{port}[/bold green]")
    uvicorn.run("web.app:app", host="127.0.0.1", port=port, reload=True)


if __name__ == "__main__":
    app()
