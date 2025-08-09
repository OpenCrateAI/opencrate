import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, List, Tuple

from jinja2 import Template
from rich.ansi import AnsiDecoder
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.tree import Tree


@contextmanager
def spinner(console: Console, message: str):
    with console.status(message, spinner="dots"):
        try:
            yield
        finally:
            pass


PROGRESS_KEYWORDS = ("Downloading", "Extracting", "Pushing", "Pulling", "Waiting")


def stream_docker_logs(command, console: Console, is_build=False):
    """
    Streams Docker logs with intelligent line handling. Progress lines update
    in-place without a decorative panel.
    """

    decoder = AnsiDecoder()

    if is_build:
        with Live(console=console, transient=True, refresh_per_second=10) as live:
            permanent_lines = []
            current_progress = Text("")

            try:
                for line_data in command:
                    if "error" in line_data:
                        raise Exception(line_data["error"])

                    raw_text = line_data.get("stream") or line_data.get("status")
                    if not raw_text:
                        continue

                    decoded_parts = [part for part in decoder.decode(raw_text) if part]
                    if not decoded_parts:
                        continue

                    full_line_text = Text("").join(decoded_parts)
                    clean_line_str = full_line_text.plain.strip()

                    if not clean_line_str:
                        continue

                    if clean_line_str.startswith(PROGRESS_KEYWORDS):
                        current_progress = Text(
                            clean_line_str, style="dim", no_wrap=True
                        )
                    else:
                        full_line_text.stylize("dim")
                        permanent_lines.append(full_line_text)
                        current_progress = Text("")

                    all_lines = permanent_lines + [current_progress]
                    valid_lines = [line for line in all_lines if line is not None]

                    output_renderable = Text("\n").join(valid_lines)
                    live.update(output_renderable)
                    # --- END OF CHANGE ---

            except Exception as e:
                error_message = str(e) if e else "Unknown build error."
                console.print(
                    f"\n[ERROR]: Build failed > {error_message}", style="bold red"
                )
                error_message = str(e)
                console.print(
                    f"\n[ERROR]: Command failed > {error_message}", style="bold red"
                )
    else:  # This logic remains unchanged
        ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
        try:
            for stdout, stderr in command:
                if stdout:
                    clean_stdout = ansi_escape.sub("", stdout.decode("utf-8").strip())
                    if clean_stdout:
                        console.print(clean_stdout, style="dim")
                if stderr:
                    clean_stderr = ansi_escape.sub("", stderr.decode("utf-8").strip())
                    if clean_stderr:
                        console.print(clean_stderr, style="bold red")
        except Exception as e:
            error_message = str(e)
            console.print(
                f"\n[ERROR]: Command failed > {error_message}", style="bold red"
            )


def handle_exceptions(console: Console) -> Callable[[Any], Any]:
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if os.path.exists(".opencrate/config.json"):
                return func(*args, **kwargs)
            elif func.__name__ == "init":
                return func(*args, **kwargs)
            else:
                console.print(
                    "[ERROR]: This is not a OpenCrate project directory",
                    style="bold red",
                )
                sys.exit(1)

        return wrapper

    return decorator


def run_command(
    command: str,
    show_output: bool = False,
    verbose: bool = False,
    ignore_error: bool = False,
) -> str:
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
                output = process.stdout.readline()  # type: ignore
                if output == "" and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            return str(process.poll())
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=not show_output,
                text=True,
                check=True,
            )
            return result.stdout.strip() if not show_output else str(result.returncode)
    except subprocess.CalledProcessError as e:
        if not ignore_error:
            raise Exception(f"An error occurred: {e.stderr.strip()}")
        return ""


def create_file(path: str, content):
    if isinstance(content, dict):
        with open(path, "w") as json_file:
            json.dump(content, json_file, indent=4)

    elif isinstance(content, str):
        with open(path, "w") as f:
            f.write(content)


def replace_in_file(file_path, replacements: List[Tuple[str, str]]):
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
    assets_dataset = assets.add(
        "📁 dataset           [dark_cyan].........created folder"
    )
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
