import os
import sys
import traceback
from pathlib import Path
from shutil import copytree, rmtree

import questionary
import yaml
from questionary import Style
from rich.console import Console
from rich.tree import Tree

from . import utils
from .app import app
from .settings import ConfigSetting

console = Console()

DATATYPES = ["Image", "Text", "Video", "Audio", "Tabular"]
PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/template"
GIT_BASH_SCRIPT = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/bash/git_init.sh"

CUSTOM_STYLE = Style(
    [
        # Answer = User input text
        ("answer", "bold fg:#ffffff"),
        # Input field = Background for typing area
        ("input", "bg:#000000"),
        # Question = Prompt text
        ("question", "fg:#bfbfbf"),
        # Selected item = For selection prompts
        ("selected", "bg:#000"),
        # Pointer = Cursor indicator
        ("pointer", "fg:#fff bold"),
    ]
)


def safe_prompt(prompt_func):
    try:
        result = prompt_func()
        if result is None:
            sys.exit(0)
        return result
    except KeyboardInterrupt:
        sys.exit(0)


def _validate_project_name(name: str):
    """
    Validates the project name to ensure it is not empty and does not contain invalid characters.
    """

    if len(name) == 0:
        return "Please enter Project Name, can't be empty."
    else:
        project_dir = name.lower().replace(" - ", " ").replace("-", " ").replace(" ", "_")
        if os.path.exists(project_dir):
            return f"Project {project_dir} already exists in current directory, please choose another name."

    return True


def prompt_project_details():
    project_title = safe_prompt(
        lambda: questionary.text(
            "● Project Name:",
            qmark="",
            validate=_validate_project_name,
            style=CUSTOM_STYLE,
        ).ask()
    )
    project_name = project_title.lower().replace(" - ", " ").replace("-", " ").replace(" ", "_")

    # if not safe_prompt(
    #     lambda: questionary.confirm(
    #         "● Initialize project in current directory?",
    #         qmark="",
    #     ).ask()
    # ):
    #     project_dir = os.path.join(
    #         questionary.path(
    #             "● Enter the path to the root project directory:", qmark=""
    #         ).ask(),
    #         project_name,
    #     )
    # else:
    project_dir = project_name

    # if os.path.exists(project_dir):
    #     if not questionary.confirm(
    #         f"● OpenCrate with the name '{project_name}' already exists. Do you want to overwrite it?",
    #         qmark="",
    #     ).ask():
    #         sys.exit(0)

    project_description = safe_prompt(
        lambda: questionary.text(
            "● Give a brief description of your project:",
            multiline=True,
            qmark="",
            style=CUSTOM_STYLE,
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
            validate=lambda x: True if len(x) > 0 else "Please select at least one datatype",
            style=CUSTOM_STYLE,
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
                    validate=lambda x: True if len(x) > 0 else "Please select at least one datatype",
                    style=CUSTOM_STYLE,
                ).ask(),
            )

    project_python_version = safe_prompt(
        lambda: questionary.select(
            "● Select your python environment version:",
            choices=[{"name": f"{version}", "value": f"{version}"} for version in PYTHON_VERSIONS],
            qmark="",
            default={"name": "3.10", "value": "3.10"},
            style=CUSTOM_STYLE,
        ).ask()
    )

    project_runtime = safe_prompt(
        lambda: questionary.select(
            "● Select your runtime environment:",
            choices=[
                {"name": "CPU", "value": "cpu"},
                {"name": "CUDA", "value": "cuda"},
            ],
            qmark="",
            default={"name": "CPU", "value": "cpu"},
            style=CUSTOM_STYLE,
        ).ask()
    )

    # if project_runtime == "cuda":
    #     project_framework_runtime = safe_prompt(
    #         lambda: questionary.select(
    #             "● Select your cuda driver version",
    #             choices=[
    #                 {"name": "CUDA 12.4 [Latest]", "value": "12.4"},
    #                 {"name": "CUDA 12.1", "value": "12.1"},
    #                 {"name": "CUDA 11.8", "value": "11.8"},
    #                 {"name": "CUDA 11.7", "value": "11.7"},
    #                 {"name": "CUDA 11.3", "value": "11.3"},
    #                 {"name": "CUDA 10.2", "value": "10.2"},
    #             ],
    #             qmark="",
    #             default={"name": "CUDA 12.4 [Latest]", "value": "12.4"},
    #             style=CUSTOM_STYLE,
    #         ).ask()
    #     )
    # else:
    #     project_framework_runtime = "cpu"

    git_remote_url = safe_prompt(
        lambda: questionary.path(
            "● Set Git Remote URL (optional):",
            qmark="",
            default="",
            style=CUSTOM_STYLE,
        ).ask()
    )

    project_docker_image = f"oc-{project_name}:main-v0"
    project_docker_container = f"{project_docker_image.replace(':', '-')}-container"

    return {
        "project_title": project_title,
        "project_name": project_name,
        "project_description": project_description,
        "project_datatypes": project_datatypes,
        "project_python_version": project_python_version,
        "project_runtime": project_runtime,
        "project_dir": project_dir,
        "git_remote_url": git_remote_url,
        "project_docker_image": project_docker_image,
        "project_docker_container": project_docker_container,
    }


class DockerComposeDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, indentless=False)


def remove_cuda_from_dockercompose(dockercompose_path: str):
    with open(dockercompose_path) as f:
        compose_data = yaml.safe_load(f)

    for service_config in compose_data.get("services", {}).values():
        if not isinstance(service_config, dict):
            continue  # Skip malformed service entries

        del service_config["deploy"]

    with open(dockercompose_path, "w") as f:
        yaml.dump(compose_data, f, Dumper=DockerComposeDumper, sort_keys=False, indent=4)


def create_project_structure(config):
    with utils.spinner(console, ">>"):
        if os.path.exists(config["project_name"]):
            rmtree(
                config["project_name"],
            )

        pull_docker_image = "opencrate"

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
            python_version=config["project_python_version"],
            docker_image=config["project_docker_image"],
            pull_docker_image=pull_docker_image,
            entry_command=entry_command,
            docker_container=config["project_docker_container"],
            runtime=config["project_runtime"],
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

        if config["project_runtime"] == "cpu":
            remove_cuda_from_dockercompose(os.path.join(config["project_dir"], "docker-compose.yml"))


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
                tree.add(f"{entry.name}/")

            # Then add files
            for entry in files:
                tree.add(f"{entry.name}")

        except OSError as e:
            console.print(f"[ERROR] > Unable to access {path}: {e}")
            return

    tree = Tree(f"[bold]{os.path.basename(path)}[/bold]")  # Root node
    add_files(tree, path)
    console.print(tree)


@app.command()
@utils.handle_exceptions(console)
def init():
    # console.print("\n░▒▓█ [[bold]Initializing[/bold]]\n")

    config = prompt_project_details()
    try:
        create_project_structure(config)
        start_project(config)
        display_summary(config["project_dir"])
        # utils.run_command(
        #     f"docker exec {config['project_docker_container']} pip freeze > {config['project_dir']}/.opencrate/requirements.txt",
        # )

        setup_git_repository(config["project_dir"], config["git_remote_url"])

        console.print("\n✓ [bold]OpenCrate initialized successfully![/]")
    except Exception as e:
        error_traceback = traceback.format_exc()
        if os.path.exists(config["project_name"]):
            rmtree(config["project_name"])
        console.print(f"[ERROR] > Initializing the project: {e}")
        console.print(f"[dim]\n{error_traceback}[/dim]")
