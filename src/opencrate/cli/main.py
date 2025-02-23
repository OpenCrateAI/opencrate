from . import environment  # noqa: F401 # direct command file must be imported
from . import init  # noqa: F401 # direct command file must be imported
from .app import app
from .auth import auth_app
from .workflow import workflow_app

app.add_typer(auth_app, name="auth")
app.add_typer(workflow_app, name="workflow")

if __name__ == "__main__":
    app()
