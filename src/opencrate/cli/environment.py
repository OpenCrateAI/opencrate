import importlib.util
import inspect
import json
import os
import re
import sys
import traceback
from typing import Any, Optional

import docker
from docker import errors
from rich.console import Console

from ..core.opencrate import OpenCrate
from . import utils
from .app import app


class OpenCrateConfig:
    """
    Manages the OpenCrate configuration file.
    """

    def __init__(self, config_path: str = ".opencrate/config.json"):
        self._config_path = config_path
        self._config: dict[str, Any] = {}

    def read(self, reload: bool = False):
        """
        Read the configuration file.
        """
        if os.path.exists(self._config_path):
            if reload or len(self._config) == 0:
                with open(self._config_path, "r") as config_file:
                    self._config = json.load(config_file)

    def write(self):
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

    def set(self, key: str, value: Any):
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
            "build_image": lambda: self.console.print(
                "[dim]└─ Use [bold yellow]$ oc build[/bold yellow] to build the image[/dim]"
            ),
            "start_container": lambda: self.console.print(
                "[dim]└─ Use [bold yellow]$ oc start[/bold yellow] to start the container[/dim]"
            ),
            "enter_container": lambda: self.console.print(
                "[dim]└─ Use [bold yellow]$ oc enter[/bold yellow] to enter the container[/dim]"
            ),
        }
        self._setup_environment()

    def _setup_environment(self):
        """
        Set up the environment for the CLI.
        """

        os.environ["HOST_GIT_NAME"] = str(
            utils.run_command(command="git config --get user.name") or ""
        )
        os.environ["HOST_GIT_EMAIL"] = str(
            utils.run_command(command="git config --get user.email") or ""
        )

    def get_help(self, help_type: str):
        """
        Returns a dictionary of helper functions.
        """
        return self._helpers[help_type]


cli = OpenCrateCLI()


@app.command()
@utils.handle_exceptions(cli.console)
def build():
    """
    Build the OpenCrate baseline image.
    """

    cli.console.print(f"\n░▒▓█ [bold]Building[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(cli.console, ">>"):
        utils.stream_docker_logs(
            command=cli.docker_client.api.build(
                path=".", tag=cli.config.get("docker_image"), rm=True, decode=True
            ),
            console=cli.console,
            is_build=True,
        )


@app.command()
@utils.handle_exceptions(cli.console)
def start():
    """
    Start the OpenCrate container.
    """

    cli.console.print(f"\n░▒▓█ [bold]Starting[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(cli.console, ">>"):
        try:
            cli.docker_client.images.get(cli.config.get("docker_image"))
        except errors.ImageNotFound:
            cli.console.print("[ERROR]: Docker image not found, skipping...")
            cli.get_help("build_image")()
            return

        try:
            container = cli.docker_client.containers.get(
                cli.config.get("docker_container")
            )
            if container.status == "running":
                cli.console.print("✔ Container is already running!")
                cli.get_help("enter_container")()
                return
            elif container.status == "exited":
                container.start()
                cli.console.print("✔ Successfully restarted container!")
                cli.get_help("enter_container")()
                return
        except errors.NotFound:
            pass

        branch_name = cli.config.get("version")
        utils.run_command(
            f"docker compose --project-name={cli.config.get('name')} up oc_{cli.config.get('name')}_{branch_name} -d"
        )
        cli.console.print("✔ Created and started new container")
        cli.get_help("enter_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def stop(down: bool = False):
    """
    Stop the OpenCrate container.
    """

    if not down:
        cli.console.print(f"\n░▒▓█ [bold]Stopping[/bold] > {cli.config.get('title')}\n")

    with utils.spinner(cli.console, ">>"):
        try:
            container = cli.docker_client.containers.get(
                cli.config.get("docker_container")
            )
            if container.status == "exited":
                if not down:
                    cli.console.print("✔ Container is already stopped")
                    cli.get_help("start_container")()
                else:
                    container.remove()
                return
            elif container.status == "running":
                utils.run_command(
                    f"docker compose --project-name={cli.config.get('name')} {'stop' if not down else 'down'}",
                )
                cli.console.print("✔ Stopped container")
                cli.get_help("start_container")()
        except errors.NotFound:
            cli.console.print(
                f"[ERROR]: Container {cli.config.get('docker_container')} not found, skipping...",
                style="bold red",
            )
            if not down:
                cli.get_help("start_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def enter():
    """
    Enter the OpenCrate container.
    """

    cli.console.print(f"\n░▒▓█ [bold]Entering[/bold] > {cli.config.get('title')}\n")
    try:
        container = cli.docker_client.containers.get(cli.config.get("docker_container"))
        if container.status == "running":
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
    except errors.NotFound:
        cli.console.print("[ERROR]: Container not found, skipping...")
        cli.get_help("start_container")()


@app.command()
@utils.handle_exceptions(cli.console)
def commit(message: str):
    """
    Commit changes to the OpenCrate container.
    """

    cli.console.print(f"\n░▒▓█ [bold]Committing[/bold] > {cli.config.get('title')}\n")
    with utils.spinner(cli.console, ">>"):
        try:
            container = cli.docker_client.containers.get(
                cli.config.get("docker_container")
            )
            container.commit(
                repository=cli.config.get("docker_image"),
                author=os.environ["HOST_GIT_NAME"],
                message=message,
            )
            cli.console.print("✔ Successfully updated changes!")
        except errors.NotFound:
            cli.console.print("[ERROR]: Container not found, skipping...")
            cli.get_help("start_container")()

        cli.docker_client.images.prune()


@app.command()
@utils.handle_exceptions(cli.console)
def reset():
    """
    Reset the OpenCrate environment.
    """

    cli.console.print(f"\n░▒▓█ [bold]Resetting[/bold] > {cli.config.get('title')}\n")
    try:
        stop(down=True)
        start()
    except Exception as e:
        cli.console.print(f" [ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(cli.console)
def kill():
    """
    Kill the OpenCrate environment.
    """
    cli.console.print(f"\n░▒▓█ [bold]Killing[/bold] > {cli.config.get('title')}\n")

    stop(down=True)
    try:
        cli.docker_client.images.remove(cli.config.get("docker_image"), force=True)
        cli.console.print(f"✔ Removed image {cli.config.get('docker_image')}")
        cli.get_help("build_image")()
    except errors.ImageNotFound:
        cli.console.print(
            f"[ERROR]: Image {cli.config.get('docker_image')} not found, skipping...",
            style="bold red",
        )
    except Exception as e:
        cli.console.print(f" [ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(cli.console)
def branch(
    name: Optional[str] = None,
    create: bool = False,
    delete: bool = False,
    show: bool = False,
):
    """
    Create a new branch for the OpenCrate environment.

    Args:
        name (str): The name of the new branch.
    """

    # create, delete and show options are not allowed to be True at the same time. If any two of them are True, it will raise an assertion error > implement this
    if show:
        assert name is None and not create and not delete, (
            "\n\nFor showing branches, using --name, --create and --delete options are not allowed.\n"
        )

        cli.console.print("\n░▒▓█ [bold]Showing branches[/bold]")
        git_branches = utils.run_command("git branch").strip().split("\n")
        docker_images = [
            f"oc-{cli.config.get('name')}:{branch.strip().replace('* ', '')}"
            for branch in git_branches
        ]
        # show the list of branches and their corresponding Docker images in a table
        cli.console.print(
            "\n".join(
                f"└─ {branch.strip().replace('* ', '')}\t-> {image}"
                for branch, image in zip(git_branches, docker_images)
            )
        )
    elif delete:
        assert name, (
            "\n\nYou must provide a branch name to delete. Use --name option.\n"
        )
        assert not create, (
            "\n\nYou cannot delete a branch while creating a new one. Remove --create option.\n"
        )

        cli.console.print(f"\n░▒▓█ [bold]Deleting branch[/bold]: {name}\n")
        with utils.spinner(cli.console, ">>"):
            current_branch = utils.run_command(
                "git rev-parse --abbrev-ref HEAD"
            ).strip()
            if current_branch == name:
                cli.console.print(
                    f"[ERROR]: Cannot delete the current branch '{name}'. Please switch to another branch before deleting.",
                    style="bold red",
                )
                return

            utils.run_command(f"git branch -D {name}")
            cli.console.print(f"✔ Deleted git branch {name}")
            try:
                image_name = f"oc-{cli.config.get('name')}:{name}"
                cli.docker_client.images.remove(image_name, force=True)
                cli.console.print(f"✔ Deleted image {image_name}")
            except errors.ImageNotFound:
                cli.console.print(
                    f"[ERROR]: Image {image_name} not found, skipping...",
                    style="bold red",
                )
    elif create:
        assert name, (
            "\n\nYou must provide a branch name to create. Use --name option.\n"
        )

        with utils.spinner(cli.console, ">>"):
            utils.run_command(f"git checkout -b {name}")
            new_docker_image = f"{cli.config.get('docker_image').split(':')[0]}:{name}"
            new_docker_container = f"{new_docker_image.replace(':', '-')}-container"

            # dockercompose_filepath = "docker-compose.yml"
            # replacements = (
            #     (cli.config.get("docker_image"), new_docker_image),
            #     (cli.config.get("docker_container"), new_docker_container),
            # )
            # with open(dockercompose_filepath, "r") as file:
            #     file_contents = file.read()
            # for old_string, new_string in replacements:
            #     file_contents = file_contents.replace(old_string, new_string)
            # with open(dockercompose_filepath, "w") as file:
            #     file.write(file_contents)

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
                ],
            )

            cli.config.set("version", name)
            cli.config.set("docker_image", new_docker_image)
            cli.config.set("docker_container", new_docker_container)
            cli.config.write()

            utils.run_command("git add .", ignore_error=True)
            utils.run_command(
                f"git commit -m 'opencrate new branch {name}'",
                ignore_error=True,
            )
            cli.docker_client.images.prune()

        # check if the container is running
        if cli.config.get("docker_container") in [
            container.name for container in cli.docker_client.containers.list()
        ]:
            stop(down=True)
        build()
        start()


# @app.command()
# @utils.handle_exceptions(cli.console)
# def checkout(name: str):
#     """
#     Checkout a specific branch of the OpenCrate environment.

#     Args:
#         name (str): The name of the branch to checkout.
#     """

#     cli.console.print(f"\n░▒▓█ [bold]Checking out[/bold] > {cli.config.get('title')}\n")

#     with utils.spinner(cli.console, ">>"):
#         utils.run_command(f"git checkout {name}")

#         new_docker_image = f"{cli.config.get('docker_image').split(':')[0]}:{name}"
#         new_docker_container = f"{new_docker_image.replace(':', '-')}-container"
#         dockercompose_filepath = "docker-compose.yml"
#         replacements = (
#             (cli.config.get("docker_image"), new_docker_image),
#             (cli.config.get("docker_container"), new_docker_container),
#         )
#         with open(dockercompose_filepath, "r") as file:
#             file_contents = file.read()
#         for old_string, new_string in replacements:
#             file_contents = file_contents.replace(old_string, new_string)
#         with open(dockercompose_filepath, "w") as file:
#             file.write(file_contents)

#         cli.config.get("version") = name
#         cli.config.get("docker_image") = new_docker_image
#         cli.config.get("docker_container") = new_docker_container
#         utils.create_file(".opencrate/cli.config.json", CONFIG)

#         cli.docker_client.images.prune()

#     # check if the container is running
#     if cli.config.get("docker_container") in [
#         container.name for container in cli.docker_client.containers.list()
#     ]:
#         stop(down=True)
#     build()
#     start()


# @app.command()
# @utils.handle_exceptions(cli.console)
# def release(
#     message: str,
# ):
#     """
#     Commit the latest OpenCrate changes to a new image version.
#     """

#     new_version = f"v{int(cli.config.get('version')[1:]) + 1}"
#     new_docker_image = f"{cli.config.get('docker_image').split(':')[0]}:{new_version}"
#     cli.console.print(f"\n░▒▓█ [bold]Releasing[/bold] > {new_docker_image}")
#     git_new_path = os.path.join(os.path.dirname(__file__), "bash", "git_new.sh")
#     current_git_branch = utils.run_command("git rev-parse --abbrev-ref HEAD").strip()

#     build()
#     # try:
#     #     container = cli.docker_client.containers.get(cli.config.get("docker_container"))
#     #     container.commit(
#     #         repository=new_docker_image,
#     #         author=os.environ["HOST_GIT_NAME"],
#     #         message=message,
#     #     )
#     #     cli.console.print("✔ Successfully committed changes!")
#     # except docker.errors.NotFound:
#     #     cli.console.print("[ERROR]: Container not found, skipping...", style="bold red")
#     #     cli.get_help("start_container")()
#     #     return

#     # create new git branches
#     with utils.spinner(cli.console, ">>"):
#         utils.run_command(
#             f"bash {git_new_path} {new_version[1:]} '{message}' {current_git_branch}"
#         )
#         # clone docker image to new version
#         utils.run_command(f"docker tag {cli.config.get('docker_image')} {new_docker_image}")

#         new_docker_container = f"{new_docker_image.replace(':', '-')}-container"
#         dockercompose_filepath = "docker-compose.yml"
#         replacements = (
#             (cli.config.get("docker_image"), new_docker_image),
#             (cli.config.get("docker_container"), new_docker_container),
#         )
#         with open(dockercompose_filepath, "r") as file:
#             file_contents = file.read()
#         for old_string, new_string in replacements:
#             file_contents = file_contents.replace(old_string, new_string)
#         with open(dockercompose_filepath, "w") as file:
#             file.write(file_contents)

#         cli.config.get("version") = new_version
#         cli.config.get("docker_image") = new_docker_image
#         cli.config.get("docker_container") = new_docker_container
#         utils.create_file(".opencrate/cli.config.json", CONFIG)

#         utils.run_command("git add .", ignore_error=True)
#         utils.run_command(
#             f"git commit -m 'opencrate updated devcontainer to {new_version}'",
#             ignore_error=True,
#         )

#         cli.docker_client.images.prune()

#         # Start outside of spinner to avoid LiveError
#     build()
#     start()


@app.command()
@utils.handle_exceptions(cli.console)
def checkout(
    name: str,
):
    """
    Checkout a specific version of the OpenCrate environment.
    """

    cli.console.print(f"\n░▒▓█ [bold]Checking out[/bold] > {name}\n")

    stop()
    with utils.spinner(cli.console, ">>"):
        utils.run_command(f"git checkout {name}")
    cli.config.read(reload=True)
    start()


@app.command()
@utils.handle_exceptions(cli.console)
def clone(git_url: str):
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
        cli.console.print(
            f"✔ Successfully cloned into [bold cyan]{repo_name}[/bold cyan]!"
        )

        # Change into the new project directory
        os.chdir(repo_name)
        cli.console.print(f"✔ Changed directory to [bold cyan]{repo_name}[/bold cyan]")

        if os.path.exists(".opencrate/cli.config.json"):
            cli.console.print("✔ Loaded project configuration")
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
def status():
    """
    Display the status of the OpenCrate environment.
    """

    cli.console.print(f"\n░▒▓█ [bold]Status[/bold] > {cli.config.get('title')}\n")
    cli.console.print(f"- Task:\t{cli.config.get('task')}")
    cli.console.print(f"- Framework:\t{cli.config.get('framework')}")
    cli.console.print(f"- Python:\t{cli.config.get('python_version')}")
    cli.console.print(f"- Version:\t{cli.config.get('version')}")
    print()

    try:
        image = cli.docker_client.images.get(cli.config.get("docker_image"))
        cli.console.print(f"- Image name:\t{', '.join(image.tags)}")
        cli.console.print(f"- Image Size:\t{image.attrs['Size'] / (1024**2):.2f} MB")
        cli.console.print(f"- Image ID:\t{image.id}")
        print()
    except errors.ImageNotFound:
        cli.console.print(
            f"- Image {cli.config.get('docker_image')} [bold red]not found[/bold red]"
        )
        cli.get_help("build_image")()
        print()
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting image info: {e}", style="bold red")
        print()

    try:
        container = cli.docker_client.containers.get(cli.config.get("docker_container"))
        cli.console.print(f"- Container Name:\t{container.name}")
        cli.console.print(f"- Container Status:\t{container.status}")
        cli.console.print(f"- Container ID:\t{container.id}")
        print()
    except errors.NotFound:
        cli.console.print(
            f"- Container {cli.config.get('docker_container')} [bold red]not found[/bold red]"
        )
        cli.get_help("start_container")()
        print()
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting container info: {e}", style="bold red")
        print()

    try:
        git_remote_url = utils.run_command(
            "git ls-remote --get-url origin", ignore_error=True
        )
        git_last_commit_date = utils.run_command(
            "git log -1 --format=%cd", ignore_error=True
        )
        git_pull_requests_count = utils.run_command(
            "git log --merges --oneline | wc -l", ignore_error=True
        )
        cli.console.print(
            f"- Git Remote URL:\t{None if git_remote_url == 'origin' else git_remote_url}"
        )
        cli.console.print(f"- Last Commit Date:\t{git_last_commit_date}")
        cli.console.print(f"- Pull Requests Count:\t{git_pull_requests_count}")
    except Exception as e:
        cli.console.print(f"[ERROR] > Extracting git info: {e}", style="bold red")
        print()


@app.command()
@utils.handle_exceptions(cli.console)
def launch(
    workflow: str,
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

    # if use_version != "new":
    #     assert (
    #         use_config == "default"
    #     ), f"\n\nCannot set --use-config to custom when --use-version is set to {use_version}, they are mutually exclusive. If you want to use custom config, then you must set --use-config=custom, and not set --use-version which will consider --use-version=new and create a new version. And if you want to use the config from version {use_version}, then you must not set the --use-cli.config.\n"
    # is_exited = False
    # try:
    #     container = cli.docker_client.containers.get(cli.config.get("docker_container"))
    #     if container.status == "exited":
    #         is_exited = True
    #         container.start()
    # except docker.errors.NotFound:  # type: ignore
    #     start()
    #     container = cli.docker_client.containers.get(cli.config.get("docker_container"))

    # Check if the script exists
    import opencrate as oc

    if isinstance(workflow, str) and "." in workflow:
        script, class_name = workflow.split(".")
        local_script_path = f"{script}.py"
        if not os.path.isfile(local_script_path):
            cli.console.print(
                f"\n[ERROR]: Script {script}.py not found.\n", style="bold red"
            )
            exit(1)

    cli.console.print(
        f"\n░▒▓█ [bold]Launching[/bold] > {workflow if isinstance(workflow, str) else workflow.__name__}"
    )

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
        crate_classes = []
        if isinstance(workflow, str):
            # First, make sure the script's directory is in the Python path
            script_dir = os.path.dirname(os.path.abspath(local_script_path))
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)

            # Import the module
            module_name = os.path.basename(script).replace(".py", "")
            spec = importlib.util.spec_from_file_location(
                module_name, local_script_path
            )
            if spec is None:
                raise ImportError(f"Cannot import module {module_name}")
            module = importlib.util.module_from_spec(spec)
            if spec.loader is not None:
                spec.loader.exec_module(module)
            else:
                raise ImportError(f"Cannot load module {module_name}")

            # Find classes in the module that inherit from OpenCrate
            for name, inherited_class in inspect.getmembers(module):
                if (
                    inspect.isclass(inherited_class)
                    and issubclass(inherited_class, OpenCrate)
                    and inherited_class != OpenCrate
                ):
                    crate_classes.append(inherited_class)
        else:
            crate_classes.append(workflow)

        if len(crate_classes) == 0:
            if isinstance(workflow, str):
                cli.console.print(
                    f"\n[ERROR]: No OpenCrate workflow found in {script}.py.\n",
                    style="bold red",
                )
                exit(1)

        if isinstance(workflow, str):
            available_classes = [cls.__name__ for cls in crate_classes]
            assert class_name in available_classes, (
                f"\n\nNo '{class_name}' workflow found in '{script}.py'. Available workflows: {available_classes}."
            )
            crate_class = list(
                filter(lambda x: x.__name__ == class_name, crate_classes)
            )[0]
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
            assert hasattr(crate_instance, job), (
                f"\n\n{crate_class.__name__} has no job named '{job}'. Available jobs are: {crate_instance.available_jobs}\n"
            )
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
def snapshot(name: str, reset: bool = False, show: bool = False):
    """
    Create a snapshot of the OpenCrate environment.
    """

    import opencrate as oc

    cli.console.print(f"\n░▒▓█ [bold]Snapshot[/bold] > {cli.config.get('title')}\n")
    if reset:
        cli.console.print(f"✔ Resetting {name} snapshot")
        oc.snapshot.snapshot_name = name
        oc.snapshot.reset(confirm=True)

    if show:
        cli.console.print(f"✔ Showing {name} snapshot")

        # TODO: Implement `oc snapshot train --tag`

    # TODO: Implement `oc snapshot train --tag`
