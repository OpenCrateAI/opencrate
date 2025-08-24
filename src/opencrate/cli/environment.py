import datetime
import importlib.util
import inspect
import json
import os
import sys
import traceback
from typing import Any, Callable, Dict, Optional, Type, Union

import docker
from docker.errors import APIError, ImageNotFound, NotFound
from rich.console import Console

from ..core.opencrate import OpenCrate
from . import utils
from .app import app


class OpenCrateConfig:
    """
    Manages the OpenCrate configuration file.
    """

    def __init__(self, config_path: str = ".opencrate/config.json") -> None:
        self._config_path = config_path
        self._config: Dict[str, Any] = {}

    def read(self, reload: bool = False) -> None:
        """
        Read the configuration file.
        """
        if os.path.exists(self._config_path):
            if reload or len(self._config) == 0:
                with open(self._config_path) as config_file:
                    self._config = json.load(config_file)

    def write(self) -> None:
        """
        Write the configuration to the file.
        """
        with open(self._config_path, "w") as config_file:
            json.dump(self._config, config_file, indent=4)

    def get(self, key: str, default="") -> str:
        """
        Get a configuration value.
        """
        self.read()
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        """
        self.read()
        self._config[key] = value


class OpenCrateCLI:
    """
    A class to manage the OpenCrate command-line interface.

    This class encapsulates the configuration, Docker client, and commands
    for the OpenCrate environment.
    """

    def __init__(self):
        self.console = Console()
        self.config = OpenCrateConfig()
        self.docker_client = docker.from_env()

        self._helpers = {
            "build_image": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc build[/bold yellow] to build the image[/dim]"),
            "start_container": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc start[/bold yellow] to start the container[/dim]"),
            "enter_container": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc enter[/bold yellow] to enter the container[/dim]"),
            "switch_branch": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc branch --switch --name='<branch_name>'[/bold yellow] to switch to a different branch[/dim]"),
            "commit_runtime": lambda: self.console.print(
                "[dim]└─ Use [bold yellow]$ oc commit '<your message>'[/bold yellow] to commit latest container changes to the image[/dim]"
            ),
            "show_runtime": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc runtime --show[/bold yellow] to view the image commits[/dim]"),
            "switch_runtime": lambda: self.console.print(
                "[dim]└─ Use [bold yellow]$ oc runtime --switch --name='<runtime_name>'[/bold yellow] to switch to a different runtime[/dim]"
            ),
            "delete_runtime": lambda: self.console.print("[dim]└─ Use [bold yellow]$ oc runtime --delete --name='<runtime_name>'[/bold yellow] to delete a runtime[/dim]"),
        }
        self._setup_environment()

    def _setup_environment(self) -> None:
        """
        Set up the environment for the CLI.
        """

        os.environ["HOST_GIT_NAME"] = str(utils.run_command(command="git config --get user.name") or "")
        os.environ["HOST_GIT_EMAIL"] = str(utils.run_command(command="git config --get user.email") or "")

    def get_help(self, help_type: str) -> Callable[[], None]:
        """
        Returns a dictionary of helper functions.
        """
        return self._helpers[help_type]


cli = OpenCrateCLI()


@app.command()
@utils.handle_exceptions(cli.console)
def build() -> None:
    """
    Build the OpenCrate baseline image.
    """

    # cli.console.print(f"\n░▒▓█ [bold]Building[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(cli.console, f"Building {cli.config.get('version')} runtime ..."):
        utils.stream_docker_logs(
            command=cli.docker_client.api.build(path=".", tag=cli.config.get("docker_image"), rm=True, decode=True),
            console=cli.console,
            is_build=True,
        )


@app.command()
@utils.handle_exceptions(cli.console)
def start() -> None:
    """
    Start the OpenCrate container.
    """

    # cli.console.print(f"\n░▒▓█ [bold]Starting[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(cli.console, f"Starting {cli.config.get('version')} ..."):
        try:
            cli.docker_client.images.get(cli.config.get("docker_image"))
        except ImageNotFound:
            cli.console.print("× Docker image not found, skipping...")
            cli.get_help("build_image")()
            return

        try:
            container = cli.docker_client.containers.get(cli.config.get("docker_container"))
            if container.status == "running":
                cli.console.print("✓ Container is already running")
                cli.get_help("enter_container")()
                return
            elif container.status == "exited":
                container.start()
                cli.console.print("✓ Successfully restarted container")
                cli.get_help("enter_container")()
                return
        except NotFound:
            pass

        branch_name = cli.config.get("version")
        utils.run_command(f"docker compose --project-name={cli.config.get('name')} up oc_{cli.config.get('name')}_{branch_name} -d")
        cli.console.print("✓ Created and started new container")
        cli.get_help("enter_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def stop(down: bool = False, all: bool = False) -> None:
    """
    Stop the OpenCrate container.
    """

    # if not down:
    #     cli.console.print(f"\n░▒▓█ [bold]Stopping[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(
        cli.console,
        f"Stopping {cli.config.get('version')} runtime ..." if not down else f"Stopping and removing {cli.config.get('version')} runtime ...",
    ):
        try:
            container = cli.docker_client.containers.get(cli.config.get("docker_container"))
            if container.status == "exited":
                if not down:
                    cli.console.print(f"✓ {cli.config.get('version')} runtime is already stopped")
                    cli.get_help("start_container")()
                else:
                    container.remove()
                return
            elif container.status == "running":
                if not all:
                    service_name = f"oc_{cli.config.get('name')}_{cli.config.get('version')}"
                    utils.run_command(
                        f"docker compose --project-name={cli.config.get('name')} {'stop' if not down else 'down'} {service_name}",
                    )
                else:
                    utils.run_command(
                        f"docker compose --project-name={cli.config.get('name')} {'stop' if not down else 'down'}",
                    )
                cli.console.print(f"✓ Stopped {cli.config.get('version')} runtime")
                cli.get_help("start_container")()
        except NotFound:
            cli.console.print(
                f"× Runtime {cli.config.get('version')} not found, skipping...",
            )
            if not down:
                cli.get_help("start_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def enter() -> None:
    """
    Enter the OpenCrate container.
    """

    with utils.spinner(cli.console, f"Entering {cli.config.get('version')} runtime ..."):
        try:
            container = cli.docker_client.containers.get(cli.config.get("docker_container"))
            if container.status == "running":
                cli.console.print(f"✓ Entering container {cli.config.get('docker_container')}")
                os.execvp(
                    "docker",
                    [
                        "docker",
                        "exec",
                        "-it",
                        container.id,  # type: ignore
                        cli.config.get("entry_command"),
                    ],
                )
            else:
                cli.console.print("[ERROR]: Container is not running")
                cli.get_help("start_container")()
        except NotFound:
            cli.console.print("× Container not found, skipping...")
            cli.get_help("start_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def runtime(
    show: bool = False,
    commit: bool = False,
    message: Optional[str] = None,
    switch: bool = False,
    delete: bool = False,
    name: Optional[str] = None,
    reset: bool = False,
) -> None:
    """
    Manage the OpenCrate runtime environment.

    Args:
        show (bool): Show the logs of the OpenCrate container
        commit (bool): Commit changes to the OpenCrate container
        message (Optional[str]): Commit message when using --commit
        switch (bool): Restore the OpenCrate environment from a commit
        name (Optional[str]): Name/version to switch to when using --switch
        reset (bool): Reset the OpenCrate environment
    """

    if show:
        # Show logs functionality (previously log command)
        # cli.console.print(
        #     f"\n░▒▓█ [bold]Showing runtimes[/bold] > {cli.config.get('title')}"
        # )

        with utils.spinner(cli.console, "Processing & loading runtimes commits ..."):
            # Get all images for current branch
            current_branch = cli.config.get("version").split("-v")[0]
            img_prefix = f"{cli.config.get('docker_image').split(':')[0]}:{current_branch}"

            # Find matching images
            matching_images = []
            for img in cli.docker_client.images.list():
                for tag in img.tags:
                    if img_prefix in tag:
                        matching_images.append(tag)
            # Generate logs for each image
            logs = []
            for image_name in matching_images:
                try:
                    image = cli.docker_client.images.get(image_name)
                    history = cli.docker_client.api.history(image.id)

                    # Look for human commit (not build commands)
                    human_commit = None
                    for entry in history:
                        comment = entry.get("Comment", "").strip()
                        if (
                            comment
                            and not any(
                                comment.startswith(cmd)
                                for cmd in [
                                    "buildkit.dockerfile",
                                    "/bin/sh -c",
                                    "COPY",
                                    "RUN",
                                    "FROM",
                                    "WORKDIR",
                                    "ENV",
                                    "EXPOSE",
                                    "CMD",
                                    "ENTRYPOINT",
                                ]
                            )
                            and comment != "created"
                        ):
                            human_commit = entry
                            break

                    # Format log entry
                    version = image_name.split(":")[-1]
                    if image_name == cli.config.get("docker_image"):
                        version = f"* {version}"
                    if human_commit:
                        comment = human_commit.get("Comment", "No commit message")
                        commit_hash = human_commit.get("Id", "").replace("sha256:", "")[:12]
                        size_mb = human_commit.get("Size", 0) / (1024**2)
                        created = datetime.datetime.fromtimestamp(human_commit.get("Created", 0))
                        date_str = created.strftime("%d-%m-%Y %H:%M:%S")
                        logs.append(f"[bold]{version}: {comment}[/bold] -> {commit_hash} [dim][{size_mb:.2f} MB - {date_str}][/]")
                    else:
                        # No human commit found, use image info
                        commit_hash = image.id.replace("sha256:", "")[:12] if image.id else "unknown"
                        size_mb = image.attrs.get("Size", 0) / (1024**2)
                        created_str = image.attrs.get("Created", "1970-01-01T00:00:00Z")

                        # Parse ISO datetime
                        if created_str.endswith("Z"):
                            created_str = created_str[:-1] + "+00:00"
                        if "." in created_str and "+" in created_str:
                            dt_part, tz_part = created_str.split("+")
                            if "." in dt_part:
                                base_dt, fractional = dt_part.split(".")
                                fractional = fractional[:6]  # Truncate to microseconds
                                created_str = f"{base_dt}.{fractional}+{tz_part}"

                        created = datetime.datetime.fromisoformat(created_str)
                        date_str = created.strftime("%d-%m-%Y %H:%M:%S")
                        logs.append(f"[bold]{version}:[/bold] -> {commit_hash} [dim][{size_mb:.2f} MB - {date_str}][/]")

                except ImageNotFound:
                    logs.append(f"[bold]{image_name}[/bold] -> [red]Image not found[/red]")

            # Display results
            if logs:
                for idx, log in enumerate(logs):
                    prefix = "└─" if idx == len(logs) - 1 else "├─"
                    cli.console.print(f"{prefix} {log}")
            else:
                cli.console.print("[ERROR] No commit messages found.")
                cli.get_help("commit_runtime")()

    elif commit:
        # Commit functionality (previously commit command)
        if not message:
            cli.console.print("[ERROR]: --message is required when using --commit", style="bold red")
            return

        # cli.console.print(
        #     f"\n░▒▓█ [bold]Committing[/bold] > {cli.config.get('title')}\n"
        # )

        with utils.spinner(cli.console, "Commiting runtime changes ..."):
            try:
                container = cli.docker_client.containers.get(cli.config.get("docker_container"))
            except NotFound:
                cli.console.print("[ERROR]: Container not found")
                cli.get_help("start_container")()
                return
            # Create new version and commit
            current_version = cli.config.get("version")
            current_image = cli.config.get("docker_image")
            version_match = current_image.split("-v")[-1]

            new_version = f"{current_version.split('-v')[0]}-v{int(version_match) + 1}"
            new_docker_image = current_image.replace(f"-v{version_match}", f"-v{int(version_match) + 1}")
            container.commit(
                repository=new_docker_image,
                author=os.environ["HOST_GIT_NAME"],
                message=message,
            )

        stop(down=True)

        with utils.spinner(cli.console, "Updating runtime configurations ..."):
            # Update configuration files
            for file_path in [
                "docker-compose.yml",
                ".devcontainer/devcontainer.json",
                ".opencrate/config.json",
            ]:
                utils.replace_in_file(
                    file_path=file_path,
                    replacements=[(current_version, new_version)],
                )

            # Update Dockerfile FROM statement
            with open("Dockerfile") as file:
                dockerfile_content = file.read()

            dockerfile_line = next(
                (line for line in dockerfile_content.splitlines() if "FROM" in line),
                None,
            )

            if dockerfile_line:
                cli.config.read(reload=True)
                utils.replace_in_file(
                    file_path="Dockerfile",
                    replacements=[(dockerfile_line, f"FROM {cli.config.get('docker_image')}")],
                )

        with utils.spinner(cli.console, "Committing changes to git ..."):
            # Commit changes to git
            utils.run_command(
                "git add docker-compose.yml .devcontainer/devcontainer.json .opencrate/config.json Dockerfile",
            )
            utils.run_command(f'git commit -m "updated base image to {cli.config.get("version")} - {message}"')

        start()

        cli.console.print(f"✓ Successfully commited environment changes to {cli.config.get('docker_image')}")
        cli.docker_client.images.prune()

    elif switch:
        # Switch functionality (previously switch command)
        if not name:
            cli.console.print("[ERROR]: --name is required when using --switch", style="bold red")
            return

        if name.split("-v")[0] != cli.config.get("version").split("-v")[0]:
            cli.console.print(
                "[ERROR]: --name must match the current branch",
                style="bold red",
            )
            cli.get_help("show_runtime")()
            return

        # check if the docker image with the given name exists
        image_name = f"{cli.config.get('docker_image').split(':')[0]}:{name}"
        try:
            cli.docker_client.images.get(image_name)
        except ImageNotFound:
            cli.console.print(
                f"[ERROR]: No runtime '{image_name}' not found",
                style="bold red",
            )
            cli.get_help("build_image")()
            return

        stop()

        with utils.spinner(cli.console, f"Switching to {name} runtime ..."):
            # get git commit hash that has f"updated base image to {name}" in its commit message
            commit_id_tag = None
            git_log = utils.run_command("git log --oneline").strip().split("\n")
            for line in git_log:
                if "v0" not in name:
                    if f"updated base image to {name}" in line:
                        commit_id_tag = line.split()[0]
                        break
                elif name == "main-v0":
                    # For main-v0, we look for the opencrate new branch commit
                    if "opencrate initial commit" in line:
                        commit_id_tag = line.split()[0]
                        break
                else:
                    if f"opencrate new branch {name.split('-v')[0]}" in line:
                        commit_id_tag = line.split()[0]
                        break

            # run git checkout <commit_id_tag> -- Dockerfile docker-compose.yml .devcontainer/devcontainer.json .opencrate/config.json
            if not commit_id_tag:
                cli.console.print(
                    f"[ERROR]: No commit found with message 'updated base image to {name}'.",
                    style="bold red",
                )
                cli.get_help("show_runtime")()
                return

            utils.run_command(f"git checkout {commit_id_tag} -- Dockerfile docker-compose.yml .devcontainer/devcontainer.json .opencrate/config.json")

            cli.config.read(reload=True)
            # build()

        start()
        cli.docker_client.images.prune()

        cli.console.print(f"✓ Successfully restored {cli.config.get('version')} runtime")
    elif delete:
        # cli.console.print(f"\n░▒▓█ [bold]Deleting runtime[/bold] > {name}\n")

        # Delete functionality (previously delete command)
        if not name:
            cli.console.print("[ERROR]: --name is required when using --delete", style="bold red")
            cli.get_help("delete_runtime")()
            return

        # Check if trying to delete current runtime
        if name == cli.config.get("version"):
            cli.console.print(
                f"[ERROR]: Cannot delete the current runtime '{name}'. Please switch to another runtime before deleting.",
                style="bold red",
            )
            cli.get_help("switch_runtime")()
            return

        with utils.spinner(cli.console, f"Removing {name} runtime ..."):
            # Find git commit that belongs to this runtime
            commit_id_tag = None
            git_log = utils.run_command("git log --oneline").strip().split("\n")
            for line in git_log:
                if f"updated base image to {name}" in line:
                    commit_id_tag = line.split()[0]
                    break

            # Delete the running container if it exists
            try:
                container_name = f"{cli.config.get('name')}-{name}-container"
                container = cli.docker_client.containers.get(container_name)
                container.remove()
                cli.console.print(f"✓ Deleted container {container_name}")
            except NotFound:
                cli.console.print(f"× Container {container_name} not found, skipping...")

            # Delete the docker image
            try:
                image_name = f"{cli.config.get('docker_image').split(':')[0]}:{name}"
                cli.docker_client.images.remove(image_name, force=True)
                cli.console.print(f"✓ Deleted docker image {image_name}")
            except ImageNotFound:
                cli.console.print(f"× Image {image_name} not found, skipping...")

        with utils.spinner(cli.console, "Cleaning up git history ..."):
            # Delete the git commit
            if commit_id_tag:
                utils.run_command(f"git rebase --onto {commit_id_tag}^ {commit_id_tag}")
                cli.console.print(f"✓ Deleted git commit {commit_id_tag}")

            cli.docker_client.images.prune()

    elif reset:
        # Reset functionality (previously reset command)
        # cli.console.print(
        #     f"\n░▒▓█ [bold]Resetting[/bold] > {cli.config.get('title')}\n"
        # )
        try:
            stop(down=True)
            build()
            start()
        except Exception as e:
            cli.console.print(f"[ERROR]: {e}", style="bold red")

    else:
        cli.console.print(
            "[ERROR]: Please specify one of: --show, --commit, --switch, or --reset",
            style="bold red",
        )


@app.command()
@utils.handle_exceptions(cli.console)
def kill(confirm: bool = False) -> None:
    """
    Kill the OpenCrate environment.
    """
    # cli.console.print(f"\n░▒▓█ [bold]Killing[/bold] > {cli.config.get('title')}\n")

    try:
        with utils.spinner(cli.console, f"Killing {cli.config.get('version')} runtime ..."):
            # check if "FROM opencrate" is in Dockerfile
            with open("Dockerfile") as file:
                dockerfile_content = file.read()
            # get the full line that contains "FROM opencrate"
            has_commited_base_image = False
            for dockerfile_line in dockerfile_content.splitlines():
                if "FROM" in dockerfile_line and "opencrate" not in dockerfile_line:
                    has_commited_base_image = True
                    break

        if has_commited_base_image and not confirm:
            cli.console.print(
                f"[ERROR]: Your current {cli.config.get('version')} branch has commited docker image which is being referred in the Dockerfile: [bold]{dockerfile_line}[/]\
                    nKilling this image will break your branch and you will not be able to build it again.\nIf you still want to kill the image, then use `--confirm` flag.",
                style="bold red",
            )
            return

        stop(down=True, all=True)

        with utils.spinner(cli.console, f"Removing {cli.config.get('version')} runtime image ..."):
            cli.docker_client.images.remove(cli.config.get("docker_image"), force=True)
            cli.docker_client.images.prune()

        cli.console.print(f"✓ Removed {cli.config.get('version')} image")
        if not has_commited_base_image:
            cli.get_help("build_image")()
    except ImageNotFound:
        cli.console.print(
            f"× {cli.config.get('version')} runtime image not found, skipping...",
            style="bold red",
        )
    except Exception as e:
        cli.console.print(f" [ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(cli.console)
def branch(
    name: Optional[str] = None,
    show: bool = False,
    create: bool = False,
    delete: bool = False,
    switch: bool = False,
) -> None:
    """
    Create a new branch for the OpenCrate environment.

    Args:
        name (str): The name of the new branch.
        show (bool): Show existing branches and their details.
        create (bool): Create a new branch.
        delete (bool): Delete an existing branch.
        switch (bool): Switch to an existing branch.
    """

    # create, delete and show options are not allowed to be True at the same time. If any two of them are True, it will raise an assertion error > implement this
    if show:
        # Validate that conflicting options are not used together
        num_actions = sum([create, delete, switch])
        assert num_actions <= 1, "\n\nYou cannot use --create, --delete, and --switch together. Please specify only one action.\n"

        assert name is None, "\n\nFor showing branches, using --name option is not allowed.\n"

        # cli.console.print("\n░▒▓█ [bold]Showing branches[/bold]")
        git_branches = utils.run_command("git branch").strip().split("\n")

        # Get all available Docker images
        docker_images_available = []
        for img in cli.docker_client.images.list():
            if img.tags:
                docker_images_available.extend(img.tags)

        # Process each branch
        for idx, branch_line in enumerate(git_branches):
            branch_name = branch_line.strip().replace("* ", "")
            is_current = branch_line.strip().startswith("* ")

            # Find all runtime images for this branch
            branch_prefix = f"oc-{cli.config.get('name')}:{branch_name}"
            runtime_images = []

            for image_name in docker_images_available:
                if image_name.startswith(branch_prefix):
                    runtime_images.append(image_name)

            # Sort runtime images by version (v0, v1, v2, etc.)
            runtime_images.sort(key=lambda x: int(x.split("-v")[-1]) if "-v" in x else 0)

            # Display branch info
            branch_indicator = "* " if is_current else ""
            prefix = "└─" if idx == (len(git_branches) - 1) else "├─"

            cli.console.print(f"{prefix} {branch_indicator}[bold]{branch_name}[/bold]")

            if runtime_images:
                for runtime_idx, runtime_image in enumerate(runtime_images):
                    runtime_prefix = "   └─" if idx == (len(git_branches) - 1) else "│  └─"
                    if runtime_idx < len(runtime_images) - 1:
                        runtime_prefix = "   ├─" if idx == (len(git_branches) - 1) else "│  ├─"
                    cli.console.print(f"{runtime_prefix} {runtime_image}")

    elif create:
        assert name, "\n\nYou must provide a branch name to create. Use --name option.\n"

        stop()

        with utils.spinner(cli.console, f"Creating {name} branch ..."):
            utils.run_command(f"git checkout -b {name}")

            name = f"{name}-v0"
            new_docker_image = f"{cli.config.get('docker_image').split(':')[0]}:{name}"
            new_docker_container = f"{new_docker_image.replace(':', '-')}-container"

            utils.replace_in_file(
                file_path="docker-compose.yml",
                replacements=[
                    (cli.config.get("docker_image"), new_docker_image),
                    (cli.config.get("docker_container"), new_docker_container),
                    (
                        f"oc_{cli.config.get('name')}_{cli.config.get('version')}",
                        f"oc_{cli.config.get('name')}_{name}",
                    ),
                ],
            )
            utils.replace_in_file(
                file_path=".devcontainer/devcontainer.json",
                replacements=[
                    (
                        f"oc_{cli.config.get('name')}_{cli.config.get('version')}",
                        f"oc_{cli.config.get('name')}_{name}",
                    ),
                    (
                        f'"name": "{cli.config.get("name")} [{cli.config.get("version")}]"',
                        f'"name": "{cli.config.get("name")} [{name}]"',
                    ),
                ],
            )

            cli.config.set("version", name)
            cli.config.set("docker_image", new_docker_image)
            cli.config.set("docker_container", new_docker_container)
            cli.config.write()

        with utils.spinner(cli.console, f"Committing changes to git for {name} branch ..."):
            utils.run_command("git add .", ignore_error=True)
            utils.run_command(
                f"git commit -m 'opencrate new branch {name}'",
                ignore_error=True,
            )
            cli.docker_client.images.prune()

        # check if the container is running
        # if cli.config.get("docker_container") in [
        #     container.name for container in cli.docker_client.containers.list()
        # ]:
        # build only if image is not built
        with utils.spinner(cli.console, "Checking if runtime already exists ..."):
            image_exists = False
            for img in cli.docker_client.images.list():
                for tag in img.tags:
                    if cli.config.get("docker_image") == tag:
                        image_exists = True
                        break
                if image_exists:
                    break

        if not image_exists:
            build()
        start()
    elif delete:
        assert name, "\n\nYou must provide a branch name to delete. Use --name option.\n"
        assert not create, "\n\nYou cannot delete a branch while creating a new one. Remove --create option.\n"

        # cli.console.print(f"\n░▒▓█ [bold]Deleting branch[/bold]: {name}\n")

        with utils.spinner(cli.console, f"Checking {name} branch status ..."):
            current_branch = utils.run_command("git rev-parse --abbrev-ref HEAD").strip()
            branch_exists = utils.run_command(f"git branch --list {name}", ignore_error=True).strip()
            if not branch_exists:
                cli.console.print(
                    f"[ERROR]: Branch '{name}' does not exist. You can create one using [bold]`$ oc branch --create --name={name}`[/] command.",
                    style="bold red",
                )
                return
            if current_branch == name:
                cli.console.print(
                    f"[ERROR]: Cannot delete the current branch '{name}'. Please switch to another branch before deleting.",
                    style="bold red",
                )
                cli.get_help("switch_branch")()
                return

        with utils.spinner(cli.console, f"Removing {name} branch runtimes ..."):
            img_prefix = f"{cli.config.get('docker_image').split(':')[0]}:{name}"

            matching_containers = []
            for container in cli.docker_client.containers.list(all=True):
                print(f"oc_{cli.config.get('name')}-{name}", container.name)
                if f"oc_{cli.config.get('name')}-{name}" in container.name:
                    matching_containers.append(container)

            for container in matching_containers:
                container.remove(force=True)
                cli.console.print(f"✓ Deleted container {container.name}")

            try:
                # Find matching images
                matching_images = []
                for img in cli.docker_client.images.list():
                    for tag in img.tags:
                        if img_prefix in tag:
                            matching_images.append(tag)

                for image_name in matching_images:
                    try:
                        # Try to delete without force first
                        cli.docker_client.images.remove(image_name, force=False)
                        cli.console.print(f"✓ Deleted image {image_name}")
                    except APIError:
                        # If deletion fails, untag the image instead
                        cli.docker_client.api.remove_image(image_name, force=False, noprune=False)
                        cli.console.print(f"✓ Untagged image {image_name}")

                cli.docker_client.images.prune()
            except ImageNotFound:
                cli.console.print(
                    f"× Image {image_name} not found, skipping...",
                    style="bold red",
                )

        with utils.spinner(cli.console, "Removing git branch ..."):
            utils.run_command(f"git branch -D {name}")
            cli.console.print(f"✓ Deleted git branch {name}")
    elif switch:
        with utils.spinner(cli.console, f"Checking {name} branch availability ..."):
            branch_exists = utils.run_command(f"git branch --list {name}", ignore_error=True).strip()
            current_branch = utils.run_command("git rev-parse --abbrev-ref HEAD", ignore_error=True).strip()

        if branch_exists:
            if current_branch == name:
                cli.console.print(
                    f"✓ You're already on branch '{name}'.",
                )
                return

            with utils.spinner(cli.console, "Checking for uncommitted changes current branch..."):
                # Check for uncommitted changes before switching
                git_status = utils.run_command("git status --porcelain", ignore_error=True)
                if git_status.strip():
                    cli.console.print(
                        "[ERROR]: You have uncommitted changes in the current branch.\nPlease commit your changes or stash them before switching branches\n",
                        style="bold red",
                    )
                    return

            stop()
            with utils.spinner(cli.console, f"Switching to branch '{name}' ..."):
                try:
                    utils.run_command(f"git checkout {name}")
                except Exception as e:
                    cli.console.print(
                        f"[ERROR]: Failed to switch to branch '{name}': {str(e)}",
                        style="bold red",
                    )
                    return

            cli.config.read(reload=True)
            build()
            start()
        else:
            cli.console.print(
                f"[ERROR]: Branch '{name}' does not exist. You can create one using [bold]`$ oc branch --create --name={name}`[/] command.",
                style="bold red",
            )
            return


@app.command()
@utils.handle_exceptions(cli.console)
def clone(git_url: str) -> None:
    """
    Clone an OpenCrate project from a git repository.

    Args:
        git_url (str): The URL of the git repository to clone.
    """

    repo_name = git_url.split("/")[-1].replace(".git", "")
    cli.console.print(f"\n░▒▓█ [bold]Cloning[/bold] > {git_url}\n")

    try:
        # Clone the repository
        with utils.spinner(cli.console, f"Cloning {repo_name}..."):
            utils.run_command(f"git clone {git_url}")
        cli.console.print(f"✓ Successfully cloned into [bold cyan]{repo_name}[/bold cyan]!")

        # Change into the new project directory
        os.chdir(repo_name)
        cli.console.print(f"✓ Changed directory to [bold cyan]{repo_name}[/bold cyan]")

        if os.path.exists(".opencrate/cli.config.json"):
            cli.console.print("✓ Loaded project configuration")
        else:
            cli.console.print(
                "[ERROR]: Cloned repository is not a valid OpenCrate project. Missing .opencrate/cli.config.json",
                style="bold red",
            )
            return

        # Build and start the environment
        build()
        start()

    except Exception as e:
        cli.console.print(f"[ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(cli.console)
def status() -> None:
    """
    Display the status of the OpenCrate environment.
    """

    cli.console.print(f"\n░▒▓█ [bold]Status[/bold] > {cli.config.get('title')}\n")
    cli.console.print(f"- Framework:\t{cli.config.get('framework')}")
    cli.console.print(f"- Python:\t{cli.config.get('python_version')}")
    cli.console.print(f"- Version:\t{cli.config.get('version')}")

    try:
        image = cli.docker_client.images.get(cli.config.get("docker_image"))
        cli.console.print(f"- Image name:\t{', '.join(image.tags)}")
        cli.console.print(f"- Image Size:\t{image.attrs['Size'] / (1024**2):.2f} MB")
        cli.console.print(f"- Image ID:\t{image.id}")
    except ImageNotFound:
        cli.console.print(f"- Image {cli.config.get('docker_image')} [bold red]not found[/bold red]")
        cli.get_help("build_image")()
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting image info: {e}", style="bold red")

    try:
        container = cli.docker_client.containers.get(cli.config.get("docker_container"))
        cli.console.print(f"- Container Name:\t{container.name}")
        cli.console.print(f"- Container Status:\t{container.status}")
        cli.console.print(f"- Container ID:\t{container.id}")
    except NotFound:
        cli.console.print(f"- Container {cli.config.get('docker_container')} [bold red]not found[/bold red]")
        cli.get_help("start_container")()
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting container info: {e}", style="bold red")

    try:
        git_remote_url = utils.run_command("git ls-remote --get-url origin", ignore_error=True)
        git_last_commit_date = utils.run_command("git log -1 --format=%cd", ignore_error=True)
        git_pull_requests_count = utils.run_command("git log --merges --oneline | wc -l", ignore_error=True)
        cli.console.print(f"- Git Remote URL:\t{None if git_remote_url == 'origin' else git_remote_url}")
        cli.console.print(f"- Last Commit Date:\t{git_last_commit_date}")
        cli.console.print(f"- Pull Requests Count:\t{git_pull_requests_count}")
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting git info: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(cli.console)
def launch(
    workflow: Union[str, Type[OpenCrate]],
    job: Optional[str] = None,
    start: str = "new",
    tag: Optional[str] = None,
    config: str = "default",
    replace: bool = False,
    finetune: Optional[str] = None,
    finetune_tag: Optional[str] = None,
    log_level: str = "info",
):
    """
    Launch a specific OpenCrate module from the scripts in the ./src folder.

    Args:
        workflow (str): Name of the file and OpenCrate module to be launched
        start (str): Start a new version or use the latest version
        tag (str): Tag for the script
        config (str): Initial configuration to use for the new pipeline
        replace (bool): Replace the existing version
        finetune (str): Finetune the model
        finetune_tag (str): Tag for the finetuned model
        log_level (str): Logging level

    Raises:
        - AssertionError: If the script file is not found
        - AssertionError: If finetune is set with start flag other than new
        - ImportError: If the script module cannot be imported
        - Exception: If the script execution fails
        - KeyboardInterrupt: If the script execution is interrupted
    """

    # Check if the script exists
    import opencrate as oc

    if isinstance(workflow, str) and "." in workflow:
        script, class_name = workflow.split(".")
        local_script_path = f"{script}.py"
        if not os.path.isfile(local_script_path):
            cli.console.print(f"\n[ERROR]: Script {script}.py not found.\n", style="bold red")
            exit(1)

    cli.console.print(f"\n░▒▓█ [bold]Launching[/bold] > {workflow.__name__ if inspect.isclass(workflow) and issubclass(workflow, OpenCrate) else workflow}\n")

    use_config = config

    if finetune is not None:
        if not (start == "new"):
            cli.console.print(
                f"\n[ERROR]: Cannot set --finetune with --start={start}. If you want to finetune, then you must set --start=new.\n",
                style="bold red",
            )
            exit(1)

    # Dynamically import the script module
    try:
        with utils.spinner(cli.console, "Loading workflow module ..."):
            crate_classes = []
            if isinstance(workflow, str):
                # First, make sure the script's directory is in the Python path
                script_dir = os.path.dirname(os.path.abspath(local_script_path))
                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)

                # Import the module
                module_name = os.path.basename(script).replace(".py", "")
                spec = importlib.util.spec_from_file_location(module_name, local_script_path)
                if spec is None:
                    raise ImportError(f"Cannot import module {module_name}")
                module = importlib.util.module_from_spec(spec)
                if spec.loader is not None:
                    spec.loader.exec_module(module)
                else:
                    raise ImportError(f"Cannot load module {module_name}")

                # Find classes in the module that inherit from OpenCrate
                for name, inherited_class in inspect.getmembers(module):
                    if inspect.isclass(inherited_class) and issubclass(inherited_class, OpenCrate) and inherited_class != OpenCrate:
                        crate_classes.append(inherited_class)
            else:
                crate_classes.append(workflow)

        with utils.spinner(cli.console, "Validating workflow classes ..."):
            if len(crate_classes) == 0:
                if isinstance(workflow, str):
                    cli.console.print(
                        f"\n[ERROR]: No OpenCrate workflow found in {script}.py.\n",
                        style="bold red",
                    )
                    exit(1)

        with utils.spinner(cli.console, "Initializing workflow instance ..."):
            if isinstance(workflow, str):
                available_classes = [cls.__name__ for cls in crate_classes]
                assert class_name in available_classes, f"\n\nNo '{class_name}' workflow found in '{script}.py'. Available workflows: {available_classes}."
                crate_class = list(filter(lambda x: x.__name__ == class_name, crate_classes))[0]
            else:
                crate_class = workflow

            crate_class.use_config = use_config
            crate_class.start = start
            crate_class.tag = tag
            crate_class.replace = replace
            crate_class.log_level = log_level
            crate_class.finetune = finetune
            crate_class.finetune_tag = finetune_tag
            crate_instance = crate_class()

            if job:
                assert hasattr(crate_instance, job), f"\n\n{crate_class.__name__} has no job named '{job}'. Available jobs are: {crate_instance.available_jobs}\n"
                getattr(crate_instance, job)()
            else:
                return crate_instance

    except Exception as e:
        if oc.snapshot._setup_not_done:
            cli.console.print(f"[ERROR]: {traceback.format_exc()}", style="bold red")
        else:
            oc.snapshot.exception(str(e).replace("\n", ""))

    # # If we're here, either the direct import failed or no OpenCrate classes were found
    # # Fall back to the original execution method in the Docker container
    # script_path = os.path.join("/home/workspace", f"{script}.py")
    # command = f"python{cli.config.get('python_version')} {script_path}"
    # result = container.exec_run(command, stream=True, demux=True)
    # stream_docker_logs(result.output)

    # if is_exited:
    #     container.stop()


@app.command()
@utils.handle_exceptions(cli.console)
def snapshot(name: str, reset: bool = False, show: bool = False) -> None:
    """
    Create a snapshot of the OpenCrate environment.
    """

    import opencrate as oc

    cli.console.print(f"\n░▒▓█ [bold]Snapshot[/bold] > {cli.config.get('title')}\n")
    if reset:
        cli.console.print(f"✓ Resetting {name} snapshot")
        oc.snapshot.snapshot_name = name
        oc.snapshot.reset(confirm=True)

    if show:
        cli.console.print(f"✓ Showing {name} snapshot")

        # TODO: Implement `oc snapshot train --tag`

    # TODO: Implement `oc snapshot train --tag`
