import os
import sys
import traceback
from pathlib import Path
from shutil import copy, copytree, rmtree

import questionary
from rich.console import Console
from rich.tree import Tree

from . import utils
from .app import app
from .settings import ConfigSetting

console = Console()

DATATYPES = ["Image", "Text", "Video", "Audio", "Tabular"]
ML_FRAMEWORKS = ["PyTorch", "Tensorflow", "Default"]
LOGGING_FRAMEWORKS = {
    "None": "",
    "WandB": "wandb",
    "Comet": "comet-ml",
    "Neptune": "neptune",
    "TensorBoard": "tensorboard",
    "MLflow": "mlflow",
}
PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/template"
REQUIREMENTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "opencrate/cli/requirements"
)
GIT_BASH_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / "opencrate/cli/bash/git_init.sh"
)

EMOJIS = {
    "Image": "🐶",
    "Text": "📎",
    "Video": "🎥",
    "Audio": "🔊",
    "Tabular": "📑",
    "PyTorch": "🔴",
    "Tensorflow": "🟠",
    "Default": "🔵",
    "WandB": "💛",
    "Comet": "🌋",
    "Neptune": "💧",
    "TensorBoard": "🔥",
    "MLflow": "🫐",
    "Git": "📚",
    "Docker": "🐳",
}

DATATYPE_TASKS = {
    "Image": [
        "Depth Estimation",
        "Image Classification",
        "Object Detection",
        "Image Segmentation",
        "Image Generation",
        "Conditional Image Generative",
        "Image-to-Text",
        "Text-to-Image",
        "Image-to-Image",
        "Image Feature Extraction",
        "Zero-Shot Image Classification",
        "Image Feature Extraction",
    ],
    "Video": [
        "Video Classification",
        "Video-to-Text",
        "Text-to-Video",
        "Video Feature Extraction",
    ],
    "Text": [
        "Text Classification",
        "Context Question Answering",
        "Zero-Shot Classification",
        "Translation",
        "Text Summarization",
        "Text Feature Extraction",
    ],
    "Audio": [
        "Text-to-Audio",
        "Audio-to-Text",
        "Audio-to-Audio",
        "Audio Classification",
        "Audio Feature Extraction",
    ],
    "Tabular": [
        "Tabular Classification",
        "Tabular Regression",
        "Time Series Forecasting",
        "Tabular Feature Extraction",
    ],
}


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

    project_task = safe_prompt(
        lambda: questionary.select(
            f"● Select the specific task for your {' '.join(project_datatypes)} data type:",
            choices=[
                task
                for datatype in project_datatypes
                for task in DATATYPE_TASKS[datatype]
            ],
            qmark="",
        ).ask()
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

    project_logging = safe_prompt(
        lambda: questionary.select(
            "● Select your logging framework of choice:",
            choices=[
                {"name": f"{framework}", "value": framework}
                for framework in LOGGING_FRAMEWORKS.keys()
            ],
            qmark="",
            default={"name": "None", "value": "None"},
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
        lambda: questionary.path("● Set Git Remote URL:", qmark="", default="").ask()
    )

    project_docker_image = f"oc-{project_name}:main"
    project_docker_container = f"{project_docker_image.replace(':', '-')}-container"

    return {
        "project_title": project_title,
        "project_name": project_name,
        "project_description": project_description,
        "project_datatypes": project_datatypes,
        "project_task": project_task,
        "project_framework": project_framework,
        "project_logging": project_logging,
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

        requirements_name = "requirements"
        requirements_name += f"-{config['project_framework'].lower()}.txt"

        copy(
            REQUIREMENTS_DIR / requirements_name,
            os.path.join(config["project_dir"], ".opencrate", "requirements.txt"),
        )

        config_setting = ConfigSetting(
            title=config["project_title"],
            name=config["project_name"],
            version="main",
            description=config["project_description"],
            datatypes=", ".join(config["project_datatypes"]),
            task=config["project_task"],
            framework=config["project_framework"],
            logging=config["project_logging"],
            logging_package=LOGGING_FRAMEWORKS[config["project_logging"]],
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
                ".devcontainer/docker-compose.yml",
                ".opencrate/requirements.txt",
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


FILE_TYPE_EMOJIS = {
    ".py": "🐍",  # Python
    ".js": "📜",  # JavaScript
    ".html": "🌐",  # HTML
    ".css": "🎨",  # CSS
    ".md": "📝",  # Markdown
    "Dockerfile": "🐳",  # Docker
    "docker-compose.yml": "🐳",  # Docker Compose
    ".yml": "⚙️",  # YAML
    ".json": "📦",  # JSON
    ".txt": "📄",  # Text file
    ".log": "🪵",  # Log file
    ".sh": "❯",  # Shell script
    ".git": "🗄️",  # Git Repo
}


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
                # if entry.name.startswith('.'):
                #     continue

                if entry.is_dir():
                    folders.append(entry)
                else:
                    files.append(entry)

            # Add folders first
            for entry in folders:
                tree.add(f"🖿  {entry.name}/")

            # Then add files
            for entry in files:
                # ext = os.path.splitext(entry.name)[1]
                # emoji = FILE_TYPE_EMOJIS.get(ext, "📄")
                # if entry.name == "Dockerfile":
                #     emoji = FILE_TYPE_EMOJIS.get("Dockerfile", "📄")
                # elif entry.name == "docker-compose.yml":
                #     emoji = FILE_TYPE_EMOJIS.get("docker-compose.yml", "📄")
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
        utils.run_command(
            f"docker exec {config['project_docker_container']} pip freeze > {config['project_dir']}/.opencrate/requirements.txt",
        )
        requirements_path = os.path.join(
            config["project_dir"], ".opencrate", "requirements.txt"
        )
        with open(requirements_path, "r") as file:
            lines = file.readlines()
        with open(requirements_path, "w") as file:
            for line in lines:
                if (
                    "-e /home/opencrate" not in line
                    and "# Editable install with no version control" not in line
                ):
                    file.write(line)
        console.print("\n✔ [bold]OpenCrate initialized successfully![/]")

        dockerfile_path = os.path.join(config["project_dir"], "Dockerfile")
        with open(dockerfile_path, "r") as file:
            lines = file.readlines()
        with open(dockerfile_path, "w") as file:
            for line in lines:
                if "# " in line:
                    line = line.replace("# ", "")
                file.write(line)
        setup_git_repository(config["project_dir"], config["git_remote_url"])
    except Exception as e:
        error_traceback = traceback.format_exc()
        if os.path.exists(config["project_name"]):
            rmtree(config["project_name"])
        console.print(f"[ERROR] > Initializing the project: {e}")
        console.print(f"[dim]\n{error_traceback}[/dim]")
