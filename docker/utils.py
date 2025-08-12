import re
from contextlib import contextmanager
from typing import Literal

from rich.console import Console


@contextmanager
def spinner(console: Console, message: str):
    with console.status(message, spinner="dots"):
        try:
            yield
        finally:
            pass


def stream_docker_logs(
    logger, console: Console, command: str
) -> Literal["Success"] | Literal["Failed"]:
    import subprocess

    try:
        # Use shell=True for complex commands, passed as a single string.
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            universal_newlines=True,
            bufsize=1,  # Line-buffered
        )
        logs = []

        # Continuously read from the process's stdout
        for line in iter(process.stdout.readline, ""):
            clean_line = line.strip()
            if not clean_line:
                continue
            logs.append(clean_line)
            logs = logs[-50:]
            # Docker buildx often prints progress to what would be stderr.
            # Since we redirected it, we check all lines for error keywords.
            if (
                "error:" in clean_line.lower()
                or "failed to build" in clean_line.lower()
                or "failed to solve" in clean_line.lower()
                or "error response from daemon" in clean_line.lower()
            ):
                logger.error(clean_line)
                console.print(
                    f"[red]======== 𐄂 Build failed: {clean_line} ========[/red]",
                    style="bold red",
                )
                console.print("[red]" + "\n".join(logs) + "[/red]")
            else:
                # Log all other output as debug
                logger.debug(clean_line)

        # Wait for the process to complete and get the return code
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        return "Success"
    except subprocess.CalledProcessError as e:
        logger.error(f"Build command failed with exit code {e.returncode}")
        return "Failed"
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return "Failed"


def write_python_version(python_version: str):
    # Update .aliases.sh with the specified Python version

    aliases_file_path = "./docker/cli/zsh/.aliases.sh"
    with open(aliases_file_path, "r") as file:
        aliases_content = file.read()
    aliases_content = re.sub(
        r"python\d+\.\d+", f"python{python_version}", aliases_content
    )
    with open(aliases_file_path, "w") as file:
        file.write(aliases_content)
