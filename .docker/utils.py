import re
from contextlib import contextmanager
from typing import List, Optional, Union

from rich.console import Console


class CLInstall:
    def __init__(
        self,
        install_cmd: Optional[str] = None,
        packages: Union[str, List[str]] = [],
        pre_installation_steps: List[str] = [],
        post_installation_steps: List[str] = [],
    ):
        self.install_cmd = install_cmd
        self.packages = packages if isinstance(packages, list) else [packages]
        self.pre_installation_steps = pre_installation_steps
        self.post_installation_steps = post_installation_steps

        self.packages = [pkg for pkg in self.packages if len(pkg)]
        self.pre_installation_steps = [
            step for step in self.pre_installation_steps if len(step)
        ]
        self.post_installation_steps = [
            step for step in self.post_installation_steps if len(step)
        ]

    def __call__(self):
        dockerfile_block = ""

        if all("COPY" in step for step in self.pre_installation_steps):
            dockerfile_block += f"{' && '.join(self.pre_installation_steps)}"
        else:
            dockerfile_block += " &&\\\n    ".join(self.pre_installation_steps)

        if (
            len(self.pre_installation_steps)
            and "COPY" in self.pre_installation_steps[-1]
        ):
            dockerfile_block += "\nRUN "
        elif len(self.pre_installation_steps):
            dockerfile_block += " &&\\\n    "

        if self.install_cmd:
            self.packages = [pkg for pkg in self.packages if pkg]
            dockerfile_block += f"{self.install_cmd} {' '.join(self.packages)}"

            # if "apt install" in self.install_cmd:
            #     dockerfile_block += " &&\\\n    apt clean && rm -rf /var/lib/apt/lists/*"

        if self.post_installation_steps:
            for step in self.post_installation_steps:
                if step.startswith("ENV"):
                    dockerfile_block += f"\n{step}"
                else:
                    dockerfile_block += f" &&\\\n    {step}"

        return dockerfile_block


@contextmanager
def spinner(console: Console, message: str):
    with console.status(message, spinner="dots"):
        try:
            yield
        finally:
            pass


def stream_docker_logs(console: Console, command: Union[List[str], dict[str, str]]):
    try:
        for line in command:  # type: ignore
            if "stream" in line:
                clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line["stream"]).strip()  # type: ignore
                console.print(f"[dim]{clean_line}[/]")
            elif "status" in line:
                clean_status = re.sub(r"\x1b\[[0-9;]*m", "", line["status"]).strip()  # type: ignore
                console.print(f"[dim]{clean_status}[/]")
            elif "error" in line:
                raise Exception(f"{line['error']}")  # type: ignore
        console.print("    >> ● Build successful")
        return "Success"
    except Exception as e:
        console.print(f"\n    >> [red]●[red] Build failed:{e}", style="bold red")
        return "Failed"


def write_python_version(python_version: str):
    # Update .aliases.sh with the specified Python version

    aliases_file_path = "./.docker/cli/zsh/.aliases.sh"
    with open(aliases_file_path, "r") as file:
        aliases_content = file.read()
    aliases_content = re.sub(
        r"python\d+\.\d+", f"python{python_version}", aliases_content
    )
    with open(aliases_file_path, "w") as file:
        file.write(aliases_content)
