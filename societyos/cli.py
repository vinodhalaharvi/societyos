import typer
import uvicorn
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="societyos", help="Run and manage multi-agent societies.", no_args_is_help=True)
console = Console()


@app.command()
def hello():
    from . import __version__
    console.print(f"[bold green]SocietyOS[/] v{__version__} — ready.")


@app.command()
def validate(
    config_path: Path = typer.Argument(..., help="Path to a society YAML config file"),
):
    from .config.loader import load_config
    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)
    console.print(f"\n[bold green]✓ Config valid:[/] {cfg.name}\n")
    table = Table(title="Agents", show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Memory")
    table.add_column("Tools")
    table.add_column("Weight")
    for agent in cfg.agents:
        table.add_row(agent.name, agent.role, agent.memory, ", ".join(agent.tools) or "—", str(agent.weight))
    console.print(table)
    console.print(f"\n[dim]Strategy:[/] {cfg.decision_strategy}   [dim]Max rounds:[/] {cfg.max_rounds}   [dim]Benchmark:[/] {cfg.benchmark_vs_single_agent}")
    if cfg.rules:
        console.print(f"\n[dim]Rules preview:[/]\n{cfg.rules[:200]}{'...' if len(cfg.rules) > 200 else ''}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to listen on"),
    reload: bool = typer.Option(True, help="Auto-reload on code changes"),
):
    console.print(f"[bold green]Starting SocietyOS server[/] on http://{host}:{port}")
    uvicorn.run("societyos.server.app:app", host=host, port=port, reload=reload)
