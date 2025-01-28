import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    help="🚀 Opencrate Project Initialization",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

auth_app = typer.Typer(help="Authentication for executing models and workflows locally")
workflow_app = typer.Typer(help="Execute custom workflow locally")
