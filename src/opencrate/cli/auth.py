import typer

from .app import auth_app


@auth_app.command()
def login():
    """Log in to Opencrate"""

    typer.echo("Logging in...")


@auth_app.command()
def logout():
    """Log out"""

    typer.echo("Logging out...")
