import shlex
import subprocess
from collections import deque
from contextlib import contextmanager
from typing import Deque

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


@contextmanager
def spinner(console: Console, message: str):
    # This function is fine and remains the same
    with console.status(message, spinner="dots"):
        try:
            yield
        finally:
            pass


def stream_shell_command_logs(logger, console: Console, command_str: str, log_level: str = "DEBUG"):
    """
    Executes a shell command and streams its output live to the console.
    This is used to run `docker buildx` and provide rich, real-time feedback.
    """
    log_lines: Deque[Text] = deque(maxlen=15)

    def create_log_panel():
        log_text = Text("\n").join(log_lines)

        return Panel(
            log_text,
            title="[bold blue]Docker Buildx Logs[/bold blue]",
            border_style="dim blue",
            title_align="left",
        )

    try:
        cmd_list = shlex.split(command_str)

        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        if log_level == "DEBUG":
            with Live(create_log_panel(), refresh_per_second=10, console=console) as live:
                if process.stdout is not None:
                    for line in process.stdout:
                        clean_line = line.strip()
                        if clean_line:
                            logger.debug(clean_line)

                            line_text = Text()
                            line_text.append("▶ ", style="dim blue")
                            line_text.append(clean_line, style="dim")

                            log_lines.append(line_text)

                            live.update(create_log_panel())
        else:
            if process.stdout is not None:
                for line in process.stdout:
                    print(line.strip())

        return_code = process.wait()
        if return_code != 0:
            error_msg = f"Build command failed with exit code {return_code}."
            logger.error(error_msg)
            console.print(f"[bold red]======== 𐄂 {error_msg} ========[/bold red]")
            raise subprocess.CalledProcessError(return_code, cmd_list)

        return "Success"
    except (Exception, subprocess.CalledProcessError, KeyboardInterrupt) as e:
        logger.exception(str(e))
        return "Failed"
