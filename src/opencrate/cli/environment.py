import json
import os
import re

import docker
import docker.errors
from rich.console import Console

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
        f"    [yellow]●[/yellow] Use `[bold blue]oc build[/bold blue]` to build the image"
    ),
    "start_container": lambda: console.print(
        f"    [yellow]●[/yellow] Use `[bold blue]oc start[/bold blue]` to start the container"
    ),
    "enter_container": lambda: console.print(
        f"    [yellow]●[/yellow] Use `[bold blue]oc enter[/bold blue]` to enter the container"
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
                    console.print(f"{clean_line}")
                elif "status" in line:
                    clean_line = ansi_escape.sub("", line["status"])
                    console.print(f"{clean_line}")
                elif "error" in line:
                    raise Exception(f"{line['error']}")
            else:
                stdout, stderr = line
                if stdout:
                    clean_stdout = ansi_escape.sub("", stdout.decode("utf-8").strip())
                    console.print(clean_stdout)
                if stderr:
                    clean_stderr = ansi_escape.sub("", stderr.decode("utf-8").strip())
                    console.print(clean_stderr, style="bold red")
    except Exception as e:
        console.print(f"\n    >> [red]●[red] Operation failed: {e}", style="bold red")


@app.command()
@utils.handle_exceptions(console)
def build():
    """
    Build the OpenCrate baseline image.
    """

    console.print(f"\n [blue]●[/blue] [[blue]Building[/blue]] > {CONFIG['title']}")
    with utils.spinner(console, ">>"):
        stream_docker_logs(
            command=DOCKER_CLIENT.api.build(path=".", tag=CONFIG["docker_image"], rm=True, decode=True),
            is_build=True,
        )


@app.command()
@utils.handle_exceptions(console)
def start():
    """
    Start the OpenCrate container.
    """

    console.print(f"\n [blue]●[/blue] [[blue]Starting[/blue]] > {CONFIG['title']}")
    with utils.spinner(console, ">>"):
        try:
            DOCKER_CLIENT.images.get(CONFIG["docker_image"])
        except docker.errors.ImageNotFound:
            console.print(f" [red]○[/red] Docker image not found")
            HELPERS["build_image"]()
            return

        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            if container.status == "running":
                console.print(f"    >> ● Container is already running!")
                HELPERS["enter_container"]()
                return
            elif container.status == "exited":
                container.start()
                console.print(f"    >> ● Successfully restarted container!")
                HELPERS["enter_container"]()
                return
        except docker.errors.NotFound:
            pass

        utils.run_command(f"docker compose --project-name={CONFIG['name']} up {CONFIG['name']}_development -d")
        console.print(f"    >> ● Created and started new container")
        HELPERS["enter_container"]()


@app.command()
@utils.handle_exceptions(console)
def stop(down: bool = False):
    """
    Stop the OpenCrate container.
    """

    if not down:
        console.print(f"\n [blue]●[/blue] [[blue]Stopping[/blue]] > {CONFIG['title']}")

    with utils.spinner(console, ">>"):
        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            if container.status == "exited":
                if not down:
                    console.print(f" ● Container is already stopped")
                    HELPERS["start_container"]()
                else:
                    container.remove()
                return
            elif container.status == "running":
                utils.run_command(
                    f"docker compose --project-name={CONFIG['name']} {'stop' if not down else 'down'}"
                )
                console.print(f"    >> ● Stopped container")
        except docker.errors.NotFound:
            console.print(f" [red]○[/red] Container {CONFIG['docker_container']} not found, skipping removal")
            if not down:
                HELPERS["start_container"]()


@app.command()
@utils.handle_exceptions(console)
def enter():
    """
    Enter the OpenCrate container.
    """

    console.print(f"\n [blue]●[/blue] [[blue]Entering[/blue]] > {CONFIG['title']}")
    try:
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
        if container.status == "running":
            os.execvp(
                "docker", ["docker", "exec", "-it", container.id, CONFIG["entry_command"]]  # type: ignore
            )
        else:
            console.print(f" [red]○[/red] Container is not running")
            HELPERS["start_container"]()
    except docker.errors.NotFound:
        console.print(f" [red]○[/red] Container not found")
        HELPERS["start_container"]()


@app.command()
@utils.handle_exceptions(console)
def commit(message: str):
    """
    Commit changes to the OpenCrate container.
    """

    console.print(f"\n [blue]●[/blue] [[blue]Committing[/blue]] > {CONFIG['title']}")
    with utils.spinner(console, ">>"):
        try:
            container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
            container.commit(repository=CONFIG["docker_image"], author=CONFIG["git_name"], message=message)
            console.print(f"    >> ● Successfully updated changes!")
        except docker.errors.NotFound:
            console.print(f" [red]○[/red] Container not found")
            HELPERS["start_container"]()

        DOCKER_CLIENT.images.prune()


@app.command()
@utils.handle_exceptions(console)
def reset():
    """
    Reset the OpenCrate environment.
    """

    console.print(f"\n [blue]●[/blue] [[blue]Resetting[/blue]] > {CONFIG['title']}")
    try:
        stop(down=True)
        start()
    except Exception as e:
        console.print(f" ⊝ [ERROR]: {e}")


@app.command()
@utils.handle_exceptions(console)
def kill():
    """
    Kill the OpenCrate environment.
    """
    console.print(f"\n [blue]●[/blue] [[blue]Killing[/blue]] > {CONFIG['title']}")

    stop(down=True)
    try:
        DOCKER_CLIENT.images.remove(CONFIG["docker_image"], force=True)
        console.print(f"    >> ● Removed image {CONFIG['docker_image']}")
    except docker.errors.ImageNotFound:
        console.print(f" [red]○[/red] Image {CONFIG['docker_image']} not found, skipping removal")
    except Exception as e:
        console.print(f" ⊝ [ERROR]: {e}")


@app.command()
@utils.handle_exceptions(console)
def new():
    """
    Commit the latest OpenCrate changes to a new image version.
    """

    new_version = f"v{int(CONFIG['version'][1:]) + 1}"
    new_docker_image = f"{CONFIG['docker_image'].split(':')[0]}:{new_version}"
    console.print(f"\n [blue]●[/blue] [[blue]Committing[/blue]] > {new_docker_image}")
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
                repository=new_docker_image, author=CONFIG["git_name"], message=f"Release {CONFIG['version']}"
            )
            console.print(f"    >> ● Successfully committed changes!")
        except docker.errors.NotFound:
            console.print(f" [red]○[/red] Container not found")
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

    console.print(f"\n [blue]●[/blue] [[blue]Status[/blue]] > {CONFIG['title']}\n")
    console.print(f" ● Task:\t{CONFIG['task']}")
    console.print(f" ● Framework:\t{CONFIG['framework']}")
    console.print(f" ● Python:\t{CONFIG['python_version']}")
    console.print(f" ● Version:\t{CONFIG['version']}")
    print()

    try:
        image = DOCKER_CLIENT.images.get(CONFIG["docker_image"])
        console.print(f" ● Image name:\t{', '.join(image.tags)}")
        console.print(f" ● Image Size:\t{image.attrs['Size'] / (1024 ** 2):.2f} MB")
        console.print(f" ● Image ID:\t{image.id}")
        print()
    except docker.errors.ImageNotFound:
        console.print(f" ● Image {CONFIG['docker_image']} [bold red]not found[/bold red]")
        HELPERS["build_image"]()
        print()
    except Exception as e:
        console.print(f" ● [ERROR] with docker image: {e}")
        print()

    try:
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
        console.print(f" ● Container Name:\t{container.name}")
        console.print(f" ● Container Status:\t{container.status}")
        console.print(f" ● Container ID:\t{container.id}")
        print()
    except docker.errors.NotFound:
        console.print(f" ● Container {CONFIG['docker_container']} [bold red]not found[/bold red]")
        HELPERS["start_container"]()
        print()
    except Exception as e:
        console.print(f" ● [ERROR] with docker container: {e}")
        print()

    try:
        git_remote_url = utils.run_command("git ls-remote --get-url origin", ignore_error=True)
        git_last_commit_date = utils.run_command("git log -1 --format=%cd", ignore_error=True)
        git_pull_requests_count = utils.run_command("git log --merges --oneline | wc -l", ignore_error=True)
        console.print(f" ● Git Remote URL:\t{None if git_remote_url == 'origin' else git_remote_url}")
        console.print(f" ● Last Commit Date:\t{git_last_commit_date}")
        console.print(f" ● Pull Requests Count:\t{git_pull_requests_count}")
    except Exception as e:
        console.print(f" ● [ERROR] with git: {e}")
        print()


@app.command()
@utils.handle_exceptions(console)
def launch(script: str):
    """
    Launch a specific command script from the ./src folder.
    """

    if not CONFIG:
        console.print("[red]Configuration not loaded. Exiting.[/red]")
        return

    is_exited = False
    try:
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])
        if container.status == "exited":
            is_exited = True
            container.start()
    except docker.errors.NotFound:  # type: ignore
        start()
        container = DOCKER_CLIENT.containers.get(CONFIG["docker_container"])

    assert os.path.isfile(f"./{script}.py"), f"Script {script}.py not found in ./src"
    script_path = os.path.join("/home/workspace", f"{script}.py")
    command = f"python{CONFIG['python_version']} {script_path}"
    console.print(f"\n [blue]●[/blue] [[blue]Launching[/blue]] > {script}.py")
    result = container.exec_run(command, stream=True, demux=True)
    stream_docker_logs(result.output)

    if is_exited:
        container.stop()
