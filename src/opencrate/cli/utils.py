import json
import subprocess
import sys
from contextlib import contextmanager
from functools import wraps
from typing import Callable

from jinja2 import Template
from rich.tree import Console, Tree


@contextmanager
def spinner(console, message):
    with console.status(message, spinner="point"):
        try:
            yield
        finally:
            pass


def global_inits(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        global CONFIG
        config_path = ".opencrate/config.json"
        with open(config_path, "r") as config_file:
            CONFIG = json.load(config_file)
        return func(*args, **kwargs)

    return wrapper


def handle_exceptions(console: Console) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if str(e) == "'NoneType' object is not subscriptable":
                    console.print(f" ⊝ [ERROR]: This is not a OpenCrate project directory", style="bold red")
                    console.print(
                        f" [yellow]●[/yellow] Use `[bold blue]oc init[/bold blue]` to initialize the project"
                    )
                else:
                    console.print(f" ⊝ [ERROR]: {e}", style="bold red")
                sys.exit(1)

        return wrapper

    return decorator


def run_command(command: str, show_output: bool = False, verbose: bool = False, ignore_error: bool = False):
    try:
        if verbose:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
            )
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            return process.poll()
        else:
            result = subprocess.run(command, shell=True, capture_output=not show_output, text=True, check=True)
            return result.stdout.strip() if not show_output else result.returncode
    except subprocess.CalledProcessError as e:
        if not ignore_error:
            raise Exception(f"An error occurred: {e.stderr.strip()}")


def create_file(path: str, content):
    if isinstance(content, dict):
        with open(path, "w") as json_file:
            json.dump(content, json_file, indent=4)

    elif isinstance(content, str):
        with open(path, "w") as f:
            f.write(content)


def replace_in_file(file_path, replacements: list):
    with open(file_path, "r") as file:
        file_contents = file.read()

    for old_string, new_string in replacements:
        file_contents = file_contents.replace(old_string, new_string)

    with open(file_path, "w") as file:
        file.write(file_contents)


def write_template(filepath, settings):
    with open(filepath, "r") as file:
        template_content = file.read()

    template = Template(template_content)
    rendered_content = template.render(**settings.model_dump())

    with open(filepath, "w") as f:
        f.write(rendered_content)


def show_project_structure(console):
    # Initialize the console
    tree = Tree("📂         	             [dark_cyan].........created folder")

    # Add subdirectories and files
    assets = tree.add("📁 assets                [dark_cyan].........created folder")
    assets_dataset = assets.add("📁 dataset           [dark_cyan].........created folder")
    assets_dataset.add("📁 raw           [dark_cyan].........created folder")
    assets_dataset.add("📁 train         [dark_cyan].........created folder")
    assets_dataset.add("📁 val           [dark_cyan].........created folder")
    assets_dataset.add("📁 test          [dark_cyan].........created folder")
    assets.add("📁 deploy            [dark_cyan].........created folder")
    assets.add("📁 train             [dark_cyan].........created folder")
    assets.add("📁 test              [dark_cyan].........created folder")

    logs = tree.add("📁 logs                  [dark_cyan].........created folder")
    logs.add("📜 train.log         [dark_cyan].........created file")
    logs.add("📜 test.log          [dark_cyan].........created file")
    logs.add("📜 deploy.log        [dark_cyan].........created file")
    logs.add("📜 infer.log         [dark_cyan].........created file")

    config = tree.add("⚙️ config                [dark_cyan].........created folder")
    config.add("📝 model.py          [dark_cyan].........created file")
    config.add("📝 train.py          [dark_cyan].........created file")
    config.add("📝 val.py            [dark_cyan].........created file")
    config.add("📝 test.py           [dark_cyan].........created file")
    config.add("📝 deploy.py         [dark_cyan].........created file")
    config.add("📝 infer.py          [dark_cyan].........created file")

    tree.add("📁 dataset               [dark_cyan].........created folder")
    tree.add("📁 model                 [dark_cyan].........created folder")
    tree.add("📁 loss                  [dark_cyan].........created folder")

    # Add main files
    tree.add("🚫 .gitignore            [dark_cyan].........created file")
    tree.add("📝 train.py              [dark_cyan].........created file")
    tree.add("📝 test.py               [dark_cyan].........created file")
    tree.add("📝 deploy.py             [dark_cyan].........created file")
    tree.add("📝 infer.py              [dark_cyan].........created file")
    tree.add("🐳 Dockerfile            [dark_cyan].........created file")
    tree.add("⚙️ docker-compose.yml    [dark_cyan].........created file")
    tree.add("📜 requirements.txt      [dark_cyan].........created file")
    tree.add("📄 README.md         	 [dark_cyan].........created file")

    # Print the tree structure
    console.print(tree)
