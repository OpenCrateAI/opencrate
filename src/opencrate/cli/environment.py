import importlib.util
import inspect
import json
import os
import re
import sys
import traceback
from typing import Optional

import docker
from rich.console import Console

from ..core.opencrate import OpenCrate
from . import utils
from .app import app

console = Console()
CONFIG = {}

CONFIG_PATH = ".opencrate/config.json"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as config_file:
        CONFIG = json.load(config_file)

HELPERS = {
    "build_image": lambda: console.print(
        "● Use [bold yellow]$ oc build[/bold yellow] to build the image"
    ),
    "start_container": lambda: console.print(
        "● Use [bold yellow]$ oc start[/bold yellow] to start the container"
    ),
    "enter_container": lambda: console.print(
        "● Use [bold yellow]$ oc enter[/bold yellow] to enter the container"
    ),
}
DOCKER_CLIENT = docker.from_env()
COMMANDS = {
    "get_git_name": "git config --get user.name",
    "get_git_email": "git config --get user.email",
}
os.environ["HOST_GIT_NAME"] = utils.run_command(command=COMMANDS["get_git_name"])  # type: ignore
os.environ["HOST_GIT_EMAIL"] = utils.run_command(command=COMMANDS["get_git_email"])  # type: ignore


def stream_docker_logs(command, is_build=False):
    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

    try:
        for line in command:
            if is_build:
                if "stream" in line:
                    clean_line = ansi_escape.sub("", line["stream"].rstrip())
                    console.print(f"[#919191]{clean_line}[/]")
                elif "status" in line:
                    clean_line = ansi_escape.sub("", line["status"])
                    console.print(f"[#919191]{clean_line}[/]")
                elif "error" in line:
                    raise Exception(f"{line['error']}")
            else:
                stdout, stderr = line
                if stdout:
                    clean_stdout = ansi_escape.sub("", stdout.decode("utf-8").strip())
                    console.print(f"[#919191]{clean_stdout}[/]")
                if stderr:
                    clean_stderr = ansi_escape.sub("", stderr.decode("utf-8").strip())
                    console.print(clean_stderr, style="bold red")
    except Exception as e:
        console.print(f"\n⛌ [ERROR]: Build failed > {e}", style="bold red")


@app.command()
@utils.handle_exceptions(console)
def build():
    """
    Build the OpenCrate baseline image.
    """

    console.print(f"\n░▒▓█ [[bold]Building[/bold]] > {CONFIG['title']}\n")
    with utils.spinner(console, ">>"):
        stream_docker_logs(
            command=DOCKER_CLIENT.api.build(
                path=".", tag=CONFIG["docker_image"], rm=True, decode=True
            ),
            is_build=True,
        )


@app.command()
@utils.handle_exceptions(console)
def start():
    """
    Start the OpenCrate container.
    """

    console.print(f"\n░▒▓█ [[bold]Starting[/bold]] > {CONFIG['title']}\n")
    with utils.spinner(console, ">>"):
        try:
            DOCKER_CLIENT.images.get(CONFIG["docker_image"])
        except docker.errors.ImageNotFound:
            console.print("⛌ [ERROR]: Docker image not found")
            HELPERS["build_image"]()
            return

        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            if container.status == "running":
                console.print("✔ Container is already running!")
                HELPERS["enter_container"]()
                return
            elif container.status == "exited":
                container.start()
                console.print("✔ Successfully restarted container!")
                HELPERS["enter_container"]()
                return
        except docker.errors.NotFound:
            pass

        utils.run_command(
            f"docker compose --project-name={CONFIG['name']} up {CONFIG['name']}_development -d"
        )
        console.print("✔ Created and started new container")
        HELPERS["enter_container"]()


@app.command()
@utils.handle_exceptions(console)
def stop(down: bool = False):
    """
    Stop the OpenCrate container.
    """

    if not down:
        console.print(f"\n░▒▓█ [[bold]Stopping[/bold]] > {CONFIG['title']}\n")

    with utils.spinner(console, ">>"):
        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            if container.status == "exited":
                if not down:
                    console.print("✔ Container is already stopped")
                    HELPERS["start_container"]()
                else:
                    container.remove()
                return
            elif container.status == "running":
                utils.run_command(
                    f"docker compose --project-name={CONFIG['name']} {'stop' if not down else 'down'}"
                )
                console.print("✔ Stopped container")
                HELPERS["start_container"]()
        except docker.errors.NotFound:
            console.print(
                f"⛌ [ERROR]: Container {CONFIG['docker_container']} not found",
                style="bold red",
            )
            if not down:
                HELPERS["start_container"]()


@app.command()
@utils.handle_exceptions(console)
def enter():
    """
    Enter the OpenCrate container.
    """

    console.print(f"\n░▒▓█ [[bold]Entering[/bold]] > {CONFIG['title']}\n")
    try:
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
        if container.status == "running":
            os.execvp(
                "docker",
                ["docker", "exec", "-it", container.id, CONFIG["entry_command"]],  # type: ignore
            )
        else:
            console.print(f"⛌ [ERROR]: Container is not running")
            HELPERS["start_container"]()
    except docker.errors.NotFound:
        console.print(f"⛌ [ERROR]: Container not found")
        HELPERS["start_container"]()


@app.command()
@utils.handle_exceptions(console)
def commit(message: str):
    """
    Commit changes to the OpenCrate container.
    """

    console.print(f"\n░▒▓█ [[bold]Committing[/bold]] > {CONFIG['title']}\n")
    with utils.spinner(console, ">>"):
        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            container.commit(
                repository=CONFIG["docker_image"],
                author=CONFIG["git_name"],
                message=message,
            )
            console.print(f"✔ Successfully updated changes!")
        except docker.errors.NotFound:
            console.print(f"⛌ [ERROR]: Container not found")
            HELPERS["start_container"]()

        DOCKER_CLIENT.images.prune()


@app.command()
@utils.handle_exceptions(console)
def reset():
    """
    Reset the OpenCrate environment.
    """

    console.print(f"\n░▒▓█ [[bold]Resetting[/bold]] > {CONFIG['title']}\n")
    try:
        stop(down=True)
        start()
    except Exception as e:
        console.print(f" ⛌ [ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(console)
def kill():
    """
    Kill the OpenCrate environment.
    """
    console.print(f"\n░▒▓█ [[bold]Killing[/bold]] > {CONFIG['title']}\n")

    stop(down=True)
    try:
        DOCKER_CLIENT.images.remove(CONFIG["docker_image"], force=True)
        console.print(f"✔ Removed image {CONFIG['docker_image']}")
        HELPERS["build_image"]()
    except docker.errors.ImageNotFound:
        console.print(
            f"⛌ [ERROR]: Image {CONFIG['docker_image']} not found", style="bold red"
        )
    except Exception as e:
        console.print(f" ⛌ [ERROR]: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(console)
def new():
    """
    Commit the latest OpenCrate changes to a new image version.
    """

    new_version = f"v{int(CONFIG['version'][1:]) + 1}"
    new_docker_image = f"{CONFIG['docker_image'].split(':')[0]}:{new_version}"
    console.print(f"\n░▒▓█ [[bold]Committing[/bold]] > {new_docker_image}")
    git_new_path = os.path.join(os.path.dirname(__file__), "bash", "git_new.sh")

    with utils.spinner(console, ">>"):
        new_docker_container = f"{new_docker_image.replace(':', '-')}-container"

        file_path = "docker-compose.yml"
        replacements = (
            (CONFIG["docker_image"], new_docker_image),
            (CONFIG["docker_container"], new_docker_container),
        )
        with open(file_path, "r") as file:
            file_contents = file.read()
        for old_string, new_string in replacements:
            file_contents = file_contents.replace(old_string, new_string)
        with open(file_path, "w") as file:
            file.write(file_contents)

        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            container.commit(
                repository=new_docker_image,
                author=CONFIG["git_name"],
                message=f"Release {CONFIG['version']}",
            )
            console.print(f"✔ Successfully committed changes!")
        except docker.errors.NotFound:
            console.print(f"⛌ [ERROR]: Container not found", style="bold red")
            HELPERS["start_container"]()

        CONFIG["version"] = new_version
        CONFIG["docker_image"] = new_docker_image
        CONFIG["docker_container"] = new_docker_container
        utils.create_file(".opencrate/config.json", CONFIG)

        DOCKER_CLIENT.images.prune()

        # create new git branches
        utils.run_command(f"bash {git_new_path} {new_version}")

    with utils.spinner(console, ">>"):
        start()


@app.command()
@utils.handle_exceptions(console)
def status():
    """
    Display the status of the OpenCrate environment.
    """

    console.print(f"\n░▒▓█ [[bold]Status[/bold]] > {CONFIG['title']}\n")
    console.print(f"- Task:\t{CONFIG['task']}")
    console.print(f"- Framework:\t{CONFIG['framework']}")
    console.print(f"- Python:\t{CONFIG['python_version']}")
    console.print(f"- Version:\t{CONFIG['version']}")
    print()

    try:
        image = DOCKER_CLIENT.images.get(CONFIG["docker_image"])
        console.print(f"- Image name:\t{', '.join(image.tags)}")
        console.print(f"- Image Size:\t{image.attrs['Size'] / (1024**2):.2f} MB")
        console.print(f"- Image ID:\t{image.id}")
        print()
    except docker.errors.ImageNotFound:
        console.print(
            f"- Image {CONFIG['docker_image']} [bold red]not found[/bold red]"
        )
        HELPERS["build_image"]()
        print()
    except Exception as e:
        console.print(f"[ERROR] > Extracting image info: {e}", style="bold red")
        print()

    try:
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
        console.print(f"- Container Name:\t{container.name}")
        console.print(f"- Container Status:\t{container.status}")
        console.print(f"- Container ID:\t{container.id}")
        print()
    except docker.errors.NotFound:
        console.print(
            f"- Container {CONFIG['docker_container']} [bold red]not found[/bold red]"
        )
        HELPERS["start_container"]()
        print()
    except Exception as e:
        console.print(f"[ERROR] > Extracting container info: {e}", style="bold red")
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
        console.print(
            f"- Git Remote URL:\t{None if git_remote_url == 'origin' else git_remote_url}"
        )
        console.print(f"- Last Commit Date:\t{git_last_commit_date}")
        console.print(f"- Pull Requests Count:\t{git_pull_requests_count}")
    except Exception as e:
        console.print(f"[ERROR] > Extracting git info: {e}", style="bold red")
        print()


@app.command()
@utils.handle_exceptions(console)
def finetune(
    script: str,
    start: str = "new",
    tag: Optional[str] = None,
    custom_config: bool = False,
    default_config: bool = False,
    replace: bool = False,
    finetune: Optional[str] = None,
    finetune_tag: Optional[str] = None,
    log_level: str = "info",
):
    """
    Finetune the OpenCrate environment.
    """
    console.print(f"\n░▒▓█ [[bold]Finetuning[/bold]] > {CONFIG['title']}\n")


@app.command()
@utils.handle_exceptions(console)
def launch(
    workflow: str,
    job: Optional[str] = None,
    start: str = "new",
    tag: Optional[str] = None,
    config: str = "default",
    # custom_config: bool = False,
    # default_config: bool = False,
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
    if not CONFIG:
        console.print("[red]Configuration not loaded. Exiting.[/red]")
        return

    # if use_version != "new":
    #     assert (
    #         use_config == "default"
    #     ), f"\n\nCannot set --use-config to custom when --use-version is set to {use_version}, they are mutually exclusive. If you want to use custom config, then you must set --use-config=custom, and not set --use-version which will consider --use-version=new and create a new version. And if you want to use the config from version {use_version}, then you must not set the --use-config.\n"
    # is_exited = False
    # try:
    #     container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
    #     if container.status == "exited":
    #         is_exited = True
    #         container.start()
    # except docker.errors.NotFound:  # type: ignore
    #     start()
    #     container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])

    # Check if the script exists
    import opencrate as oc

    if isinstance(workflow, str) and "." in workflow:
        script, class_name = workflow.split(".")
        local_script_path = f"{script}.py"
        if not os.path.isfile(local_script_path):
            console.print(
                f"\n⛌ [ERROR]: Script {script}.py not found.\n", style="bold red"
            )
            exit(1)

    console.print(
        f"\n░▒▓█ [[bold]Launching[/bold]] > {workflow if isinstance(workflow, str) else workflow.__name__}"
    )

    # if custom_config and default_config:
    #     console.print(
    #         f"\n⛌ [ERROR]: Cannot set both --custom_config and --default_config flags.\n",
    #         style="bold red",
    #     )
    #     exit(1)

    # if (not custom_config) and (not default_config):
    #     use_config = "latest"
    # else:
    #     use_config = "custom" if custom_config else "default"
    use_config = config

    if finetune is not None:
        if not (start == "new"):
            console.print(
                f"\n⛌ [ERROR]: Cannot set --finetune with --start={start}. If you want to finetune, then you must set --start=new.\n",
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
                console.print(
                    f"\n⛌ [ERROR]: No OpenCrate workflow found in {script}.py.\n",
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
            console.print(f"⛌ [ERROR]: {traceback.format_exc()}", style="bold red")
        else:
            e = str(e).replace("\n", "")
            oc.snapshot.exception(f"{e}")

    # # If we're here, either the direct import failed or no OpenCrate classes were found
    # # Fall back to the original execution method in the Docker container
    # script_path = os.path.join("/home/workspace", f"{script}.py")
    # command = f"python{CONFIG['python_version']} {script_path}"
    # result = container.exec_run(command, stream=True, demux=True)
    # stream_docker_logs(result.output)

    # if is_exited:
    #     container.stop()


@app.command()
@utils.handle_exceptions(console)
def snapshot(name: str, reset: bool = False, show: bool = False):
    """
    Create a snapshot of the OpenCrate environment.
    """

    import opencrate as oc

    console.print(f"\n░▒▓█ [[bold]Snapshot[/bold]] > {CONFIG['title']}\n")
    if reset:
        console.print(f"✔ Resetting {name} snapshot")
        oc.snapshot.snapshot_name = name
        oc.snapshot.reset(confirm=True)

    if show:
        console.print(f"✔ Showing {name} snapshot")

        # TODO: Implement `oc snapshot train --tag`
        console.print(f"✔ Showing {name} snapshot")

    # TODO: Implement `oc snapshot train --tag`
