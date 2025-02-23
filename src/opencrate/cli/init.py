import os
import sys
from pathlib import Path
from shutil import copy, copytree, rmtree

import questionary
from rich.console import Console
from rich.table import Table

from . import utils
from .app import app
from .settings import ConfigSetting

console = Console()

DATATYPES = ["Image", "Text", "Video", "Audio", "Tabular"]
ML_FRAMEWORKS = ["PyTorch", "Tensorflow", "Default"]
LOGGING_FRAMEWORKS = {
    "WandB": "wandb",
    "Comet": "comet-ml",
    "Neptune": "neptune",
    "TensorBoard": "tensorboard",
    "MLflow": "mlflow",
}
PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/template"
REQUIREMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/requirements"
GIT_BASH_SCRIPT = Path(__file__).resolve().parent.parent.parent / "opencrate/cli/bash/git_init.sh"

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
    ],
    "Video": ["Video Classification", "Video-to-Text", "Text-to-Video"],
    "Text": [
        "Text Classification",
        "Context Question Answering",
        "Zero-Shot Classification",
        "Translation",
        "Summarization",
        "Feature Extraction",
    ],
    "Audio": ["Text-to-Audio", "Audio-to-Text", "Audio-to-Audio", "Audio Classification"],
    "Tabular": ["Tabular Classification", "Tabular Regression", "Time Series Forecasting"],
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
            validate=lambda text: True if len(text) > 0 else "Please enter Project Name, can't be empty.",
        ).ask()
    )
    project_name = project_title.lower().replace(" - ", " ").replace("-", " ").replace(" ", "_")

    overwrite = True

    if os.path.exists(project_name):
        if not questionary.confirm(
            f"● OpenCrate with the name '{project_name}' already exists. Do you want to overwrite it?",
            qmark="",
        ).ask():
            sys.exit(0)

    project_description = safe_prompt(
        lambda: questionary.text("● Give a brief description of your project:", multiline=True, qmark="").ask()
    )

    project_datatypes = safe_prompt(
        lambda: questionary.checkbox(
            "● Select the types of datasets you're gonna be dealing with:",
            choices=[
                {"name": f"{data_type}", "value": data_type, "checked": data_type == "Image"}
                for data_type in DATATYPES
            ],
            qmark="",
        ).ask()
    )

    project_task = safe_prompt(
        lambda: questionary.select(
            f"● Select the specific task for your {' '.join(project_datatypes)} data type:",
            choices=[task for datatype in project_datatypes for task in DATATYPE_TASKS[datatype]],
            qmark="",
        ).ask()
    )

    project_framework = safe_prompt(
        lambda: questionary.select(
            "● Select pre-baked opencrate containers for your framework:",
            choices=[{"name": f"{framework}", "value": framework} for framework in ML_FRAMEWORKS],
            qmark="",
            default={"name": f"{'PyTorch'}", "value": "PyTorch"},
        ).ask()
    )

    project_logging = safe_prompt(
        lambda: questionary.select(
            "● Select your logging framework of choice:",
            choices=[{"name": f"{framework}", "value": framework} for framework in LOGGING_FRAMEWORKS.keys()],
            qmark="",
            default={"name": f"{'WandB'}", "value": "WandB"},
        ).ask()
    )

    project_python_version = safe_prompt(
        lambda: questionary.select(
            "● Select your python environment version:",
            choices=[{"name": f"{version}", "value": f"{version}"} for version in PYTHON_VERSIONS],
            qmark="",
            default={"name": "3.10", "value": "3.10"},
        ).ask()
    )

    project_runtime = safe_prompt(
        lambda: questionary.select(
            "● Select your runtime environment:",
            choices=[{"name": "CUDA", "value": "cuda"}, {"name": "CPU", "value": "cpu"}],
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
            questionary.path("● Enter the path to the root project directory:", qmark="").ask(),
            project_name,
        )
    else:
        project_dir = project_name

    git_remote_url = safe_prompt(lambda: questionary.path("● Set Git Remote URL:", qmark="", default="").ask())

    project_docker_image = f"oc-{project_name}:v0"
    project_docker_container = f"{project_docker_image.replace(':', '-')}-container"

    return {
        "overwrite": overwrite,
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
            version="v0",
            description=config["project_description"],
            datatypes=config["project_datatypes"],
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
    utils.run_command(f"cd {project_dir} && bash {GIT_BASH_SCRIPT} {git_remote_url} && cd ..", show_output=True)


def display_summary(config):
    result_table = Table(
        title="\n🚀 Project Summary 🚀",
        title_justify="left",
        show_header=True,
        header_style="bold magenta",
    )
    result_table.add_column("Property", style="cyan", no_wrap=True)
    result_table.add_column("Value", style="green")

    result_table.add_row("Project Name", config["project_name"])
    result_table.add_row("Project Title", config["project_title"])
    result_table.add_row("Description", config["project_description"])
    result_table.add_row(
        "Data Types",
        f"{' '.join([EMOJIS[datatype] + ' ' + datatype for datatype in config['project_datatypes']])}",
    )
    result_table.add_row("Optimization Task", config["project_task"])
    result_table.add_row("Framework", f"{EMOJIS[config['project_framework']]} {config['project_framework']}")
    result_table.add_row(
        "Logging Framework", f"{EMOJIS[config['project_logging']]} {config['project_logging']}"
    )
    result_table.add_row("Python Version", f"🐍 {config['project_python_version']}")
    result_table.add_row("Runtime Environment", config["project_runtime"].upper())
    result_table.add_row("Docker Image", f"🐳 {config['project_docker_image']}")
    result_table.add_row("Docker Container", config["project_docker_container"])
    result_table.add_row("Git Remote URL", config["git_remote_url"] or "Not Set")
    result_table.add_row("Project Directory", f"👉🏻 {os.path.abspath(config['project_dir'])}")

    console.print(result_table)


def start_project(config):
    utils.run_command(f"cd {config['project_dir']} && oc build", show_output=True)
    utils.run_command(f"cd {config['project_dir']} && oc start", show_output=True)


@app.command()
@utils.handle_exceptions(console)
def init():
    config = prompt_project_details()
    try:
        create_project_structure(config)
        setup_git_repository(config["project_dir"], config["git_remote_url"])
        start_project(config)
    except Exception as e:
        rmtree(config["project_name"])
        console.print(f" ⊝ [ERROR] > {type(e).__name__}: {e}", style="bold red")

    # display_summary(config)
