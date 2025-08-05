import os
import sys
import traceback
from pathlib import Path
from shutil import copytree, rmtree

import questionary
from rich.console import Console
from rich.tree import Tree

from . import utils
from .app import app
from .settings import ConfigSetting

console = Console()

DATATYPES = ["Image", "Text", "Video", "Audio", "Tabular"]
ML_FRAMEWORKS = ["PyTorch", "Tensorflow", "Default"]
PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/template"
GIT_BASH_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / "opencrate/cli/bash/git_init.sh"
)


def safe_prompt(prompt_func):
    try:
        result = prompt_func()
        if result is None:
            sys.exit(0)
        return result
    except KeyboardInterrupt:
        sys.exit(0)


def prompt_project_details():
    project_title = safe_prompt(
        lambda: questionary.text(
            "● Project Name:",
            qmark="",
            validate=lambda text: True
            if len(text) > 0
            else "Please enter Project Name, can't be empty.",
        ).ask()
    )
    project_name = (
        project_title.lower().replace(" - ", " ").replace("-", " ").replace(" ", "_")
    )

    project_description = safe_prompt(
        lambda: questionary.text(
            "● Give a brief description of your project:", multiline=True, qmark=""
        ).ask()
    )

    project_datatypes = safe_prompt(
        lambda: questionary.checkbox(
            "● Select the types of datasets you're gonna be dealing with:",
            choices=[
                {
                    "name": f"{data_type}",
                    "value": data_type,
                    "checked": data_type == "Image",
                }
                for data_type in DATATYPES
            ],
            qmark="",
            validate=lambda x: True
            if len(x) > 0
            else "Please select at least one datatype",
        ).ask(),
    )

    if len(project_datatypes) == 0:
        while len(project_datatypes) == 0:
            console.print("\nPlease select at least one datatype")
            project_datatypes = safe_prompt(
                lambda: questionary.checkbox(
                    "● Select the types of datasets you're gonna be dealing with:",
                    choices=[
                        {
                            "name": f"{data_type}",
                            "value": data_type,
                            "checked": data_type == "Image",
                        }
                        for data_type in DATATYPES
                    ],
                    qmark="",
                    validate=lambda x: True
                    if len(x) > 0
                    else "Please select at least one datatype",
                ).ask(),
            )

    project_framework = safe_prompt(
        lambda: questionary.select(
            "● Select pre-baked opencrate containers for your framework:",
            choices=[
                {"name": f"{framework}", "value": framework}
                for framework in ML_FRAMEWORKS
            ],
            qmark="",
            default={"name": "PyTorch", "value": "PyTorch"},
        ).ask()
    )

    project_python_version = safe_prompt(
        lambda: questionary.select(
            "● Select your python environment version:",
            choices=[
                {"name": f"{version}", "value": f"{version}"}
                for version in PYTHON_VERSIONS
            ],
            qmark="",
            default={"name": "3.10", "value": "3.10"},
        ).ask()
    )

    project_runtime = safe_prompt(
        lambda: questionary.select(
            "● Select your runtime environment:",
            choices=[
                {"name": "CUDA", "value": "cuda"},
                {"name": "CPU", "value": "cpu"},
            ],
            qmark="",
            default={"name": "CUDA", "value": "cuda"},
        ).ask()
    )

    if project_runtime == "cuda" and project_framework == "PyTorch":
        project_framework_runtime = safe_prompt(
            lambda: questionary.select(
                "● Select your cuda driver version",
                choices=[
                    {"name": "CUDA 12.4 [Latest]", "value": "12.4"},
                    {"name": "CUDA 12.1", "value": "12.1"},
                    {"name": "CUDA 11.8", "value": "11.8"},
                    {"name": "CUDA 11.7", "value": "11.7"},
                    {"name": "CUDA 11.3", "value": "11.3"},
                    {"name": "CUDA 10.2", "value": "10.2"},
                ],
                qmark="",
                default={"name": "CUDA 12.4 [Latest]", "value": "12.4"},
            ).ask()
        )
    else:
        project_framework_runtime = "cpu"

    if not safe_prompt(
        lambda: questionary.confirm(
            "● Initialize project in current directory?",
            qmark="",
        ).ask()
    ):
        project_dir = os.path.join(
            questionary.path(
                "● Enter the path to the root project directory:", qmark=""
            ).ask(),
            project_name,
        )
    else:
        project_dir = project_name

    if os.path.exists(project_dir):
        if not questionary.confirm(
            f"● OpenCrate with the name '{project_name}' already exists. Do you want to overwrite it?",
            qmark="",
        ).ask():
            sys.exit(0)

    git_remote_url = safe_prompt(
        lambda: questionary.path(
            "● Set Git Remote URL (optional):", qmark="", default=""
        ).ask()
    )

    project_docker_image = f"oc-{project_name}:main-v0"
    project_docker_container = f"{project_docker_image.replace(':', '-')}-container"

    return {
        "project_title": project_title,
        "project_name": project_name,
        "project_description": project_description,
        "project_datatypes": project_datatypes,
        "project_framework": project_framework,
        "project_python_version": project_python_version,
        "project_runtime": project_runtime,
        "project_framework_runtime": project_framework_runtime,
        "project_dir": project_dir,
        "git_remote_url": git_remote_url,
        "project_docker_image": project_docker_image,
        "project_docker_container": project_docker_container,
    }


def create_project_structure(config):
    with utils.spinner(console, ">>"):
        if os.path.exists(config["project_name"]):
            rmtree(
                config["project_name"],
            )

        pull_docker_image = f"opencrate-{config['project_framework'].lower()}"

        if config["project_runtime"] == "cuda":
            pull_docker_image += "-cuda"
        else:
            pull_docker_image += "-cpu"
        pull_docker_image += f"-py{config['project_python_version']}"

        entry_command = "zsh"

        copytree(TEMPLATE_DIR, config["project_dir"])

        config_setting = ConfigSetting(
            title=config["project_title"],
            name=config["project_name"],
            version="main-v0",
            description=config["project_description"],
            datatypes=", ".join(config["project_datatypes"]),
            framework=config["project_framework"],
            python_version=config["project_python_version"],
            docker_image=config["project_docker_image"],
            pull_docker_image=pull_docker_image,
            entry_command=entry_command,
            docker_container=config["project_docker_container"],
            runtime=config["project_runtime"],
            framework_runtime=config["project_framework_runtime"],
            git_remote_url=config["git_remote_url"],
        )
        config_setting.write_template_settings(
            config=config,
            template_item_paths=[
                ".devcontainer/devcontainer.json",
                "docker-compose.yml",
                "Dockerfile",
                "README.md",
            ],
        )


def setup_git_repository(project_dir, git_remote_url):
    utils.run_command(
        f"cd {project_dir} && bash {GIT_BASH_SCRIPT} {git_remote_url} && cd ..",
        show_output=True,
    )


def start_project(config):
    utils.run_command(f"cd {config['project_dir']} && oc build", show_output=True)
    utils.run_command(f"cd {config['project_dir']} && oc start", show_output=True)


def display_summary(path: str):
    """
    Prints the tree folder structure of a given path without expanding subdirectories,
    using the rich library for a beautiful display with emojis before filenames.
    Displays folders first and excludes hidden folders/files.

    Args:
        path (str): The path to the directory to display.
    """

    print()

    def add_files(tree: Tree, path: str):
        """Adds files and directories to the tree without recursion."""
        try:
            folders = []
            files = []

            for entry in os.scandir(path):
                if entry.is_dir():
                    folders.append(entry)
                else:
                    files.append(entry)

            # Add folders first
            for entry in folders:
                tree.add(f"🖿  {entry.name}/")

            # Then add files
            for entry in files:
                tree.add(f"/{entry.name}")

        except OSError as e:
            console.print(f"[ERROR] > Unable to access {path}: {e}")
            return

    tree = Tree(f"[bold]{os.path.basename(path)}[/bold]")  # Root node
    add_files(tree, path)
    console.print(tree)


@app.command()
@utils.handle_exceptions(console)
def init():
    console.print("\n░▒▓█ [[bold]Initializing[/bold]]\n")

    config = prompt_project_details()
    try:
        create_project_structure(config)
        start_project(config)
        display_summary(config["project_dir"])
        # utils.run_command(
        #     f"docker exec {config['project_docker_container']} pip freeze > {config['project_dir']}/.opencrate/requirements.txt",
        # )

        setup_git_repository(config["project_dir"], config["git_remote_url"])

        console.print("\n✔ [bold]OpenCrate initialized successfully![/]")
    except Exception as e:
        error_traceback = traceback.format_exc()
        if os.path.exists(config["project_name"]):
            rmtree(config["project_name"])
        console.print(f"[ERROR] > Initializing the project: {e}")
        console.print(f"[dim]\n{error_traceback}[/dim]")
