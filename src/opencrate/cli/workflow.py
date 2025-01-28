import typer

from .app import workflow_app


@workflow_app.command()
def launch():
    """Launch a specific workflow on your custom data"""

    typer.echo("Launching workflow...")


@workflow_app.command()
def list():
    """List out list of all the available workflows"""

    typer.echo("List of workflows...")
