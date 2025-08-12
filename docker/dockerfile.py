import argparse
import os
import sys

from loguru import logger
from rich.console import Console
from utils import stream_docker_logs, write_python_version

parser = argparse.ArgumentParser(
    description="Build Dockerfile with specified configurations."
)
parser.add_argument(
    "--python", type=str, default="3.10", help="Specify the Python version to use."
)
parser.add_argument(
    "--runtime",
    type=str,
    default="cuda",
    choices=["cuda", "cpu"],
    help="Specify the runtime",
)
parser.add_argument(
    "--generate-only",
    action="store_true",
    help="Only generate the Dockerfiles, do not build them.",
)
parser.add_argument(
    "--build-command",
    type=str,
    default=None,
    help="Actual docker build command to execute.",
)
parser.add_argument(
    "--log-level",
    type=str,
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Only generate the Dockerfiles, do not build them.",
)
parser.add_argument(
    "--log-workflow",
    action="store_true",
    help="If true then it will show full log of docker builts in the github action build workflow.",
)
args = parser.parse_args()

assert args.generate_only or args.build_command, (
    "Either --generate-only or --build-command must be specified."
)

log_file = os.path.join(f"docker/logs/build-{args.runtime}-py{args.python}.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Remove default handler and add file handler
logger.remove()
logger.add(
    log_file,
    level=args.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} {message}",
    colorize=False,
    backtrace=False,
    diagnose=True,
    mode="w",
)
if args.log_workflow:  # this means its a github action workflow
    logger.add(
        lambda msg: print(msg, end=""),  # Use print instead of sys.stderr.write
        format="{message}",
        level=args.log_level,
        colorize=True,
        backtrace=False,  # Show full stack traces for exceptions
        diagnose=True,  # Show detailed information about variables in stack traces
    )

UBUNTU_PACKAGES = [
    "software-properties-common",
    "ca-certificates",
    "build-essential",
    "pkg-config",
    "libgoogle-perftools-dev",
    "cmake",
    "tzdata",
    "gnupg",
    "wget",
    "curl",
    "vim",
    "git",
    "speedtest-cli",
    "iputils-ping",
]

CLI_PACKAGES = [
    "btop",
    "unrar",
    "make",
    "tree",
    "htop",
    "bat",
    "tldr",
    "zoxide",
    "cpufetch",
    "jq",
    "zsh",
    "ripgrep",
    "fzf",
]
# if args.runtime == "cuda":
#     CLI_PACKAGES.append("nvtop")

PYTHON_PIP_PACKAGES = ["ipython", "jupyter"]


def generate_combined_dockerfile() -> str:
    """Generates a single, combined, multi-stage Dockerfile."""
    # --- Part 1: Define Base Stage Content ---
    base_image = (
        "nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04"
        if args.runtime == "cuda"
        else "ubuntu:22.04"
    )

    # The 'AS base' is the key to multi-stage builds.
    base_stage = f"""
# STAGE 1: Base image with OS dependencies and CLI tools.
FROM {base_image} AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata
"""
    if args.runtime == "cuda":
        base_stage += "ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH\n"

    base_stage += f"""
# Install all Ubuntu & CLI packages in a single, optimized layer
RUN apt-get update && apt-get install -y --no-install-recommends {" ".join(UBUNTU_PACKAGES)} {" ".join(CLI_PACKAGES)} \\
    # Add external repos for eza and fastfetch
    && mkdir -p /etc/apt/keyrings \\
    && wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | gpg --dearmor -o /etc/apt/keyrings/gierens.gpg \\
    && echo 'deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main' | tee /etc/apt/sources.list.d/gierens.list \\
    && chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list \\
    && add-apt-repository ppa:zhangsongcui3371/fastfetch -y \\
    && apt-get update \\
    && apt-get install -y --no-install-recommends eza fastfetch \\
    # Install lazygit
    && LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po \'"tag_name": *"v\\K[^\"]*\') \\
    && curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/download/v${{LAZYGIT_VERSION}}/lazygit_${{LAZYGIT_VERSION}}_Linux_x86_64.tar.gz" \\
    && tar xf lazygit.tar.gz lazygit \\
    && install lazygit /usr/local/bin \\
    && rm lazygit.tar.gz \\
    # Aggressive cleanup
    && apt-get autoremove -y \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Setup user shell environment (zsh, atuin, etc.)
COPY docker/cli/ /home/
RUN chsh -s $(which zsh) || true \\
    && wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O - | zsh || true \\
    && git clone --depth=1 https://github.com/romkatv/powerlevel10k.git $HOME/.oh-my-zsh/custom/themes/powerlevel10k \\
    && git clone https://github.com/zsh-users/zsh-autosuggestions $HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions \\
    && git clone https://github.com/zsh-users/zsh-syntax-highlighting.git $HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting \\
    && curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh \\
    && mv /home/zsh/.zshrc ~/.zshrc \\
    && mv /home/zsh/.p10k.zsh ~/.p10k.zsh \\
    && mv /home/zsh/.aliases.sh ~/ \\
    && mv /home/zsh/.exports.sh ~/ \\
    && mkdir -p ~/.config/btop/ ~/.config/atuin/ ~/.config/fastfetch/ \\
    && cp -r /home/btop/ ~/.config/ \\
    && cp -r /home/atuin/ ~/.config/ \\
    && cp -r /home/fastfetch/ ~/.config/ \\
    # Cleanup copied files
    && rm -rf /home/zsh /home/btop /home/atuin /home/fastfetch
"""

    # --- Part 2: Define App Stage Content ---
    py_ver_int = int(str(args.python).split(".")[-1])
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    if py_ver_int < 9:
        get_pip_url = f"https://bootstrap.pypa.io/pip/{args.python}/get-pip.py"
    distutils_package = f" python{args.python}-distutils" if py_ver_int < 12 else ""

    # 'FROM base' directly and reliably refers to the result of the first stage.
    app_stage = f"""
# STAGE 2: Final application image
FROM base

# Install Python from deadsnakes PPA
RUN add-apt-repository ppa:deadsnakes/ppa -y \\
    && apt-get update \\
    && apt-get install -y --no-install-recommends python{args.python} python{args.python}-dev{distutils_package} \\
    && curl -sS {get_pip_url} | python{args.python} \\
    && python{args.python} -m pip install --no-cache-dir --upgrade pip \\
    # Cleanup
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Install Python packages
RUN python{args.python} -m pip install --no-cache-dir --upgrade {" ".join(PYTHON_PIP_PACKAGES)} \\
    && python{args.python} -m pip cache purge

# Copy and install the opencrate application
WORKDIR /home/opencrate/
COPY pyproject.toml setup.cfg setup.py ./
COPY src/ ./src/
RUN python{args.python} -m pip install --no-cache-dir -e . \\
    && python{args.python} -m pip cache purge

# Setup final workspace and hooks
WORKDIR /home/workspace/
RUN git config --global --add safe.directory '*' && git config --global init.defaultBranch main

COPY docker/hooks/ /root/.hooks/
"""

    # --- Part 3: Combine and Return ---
    return f"{base_stage.strip()}\n\n{app_stage.strip()}"


def main():
    console = Console()

    try:
        with open("VERSION", "r") as version_file:
            version = version_file.read().strip()
    except FileNotFoundError:
        console.print("[bold red]Error: VERSION file not found.[/bold red]")
        sys.exit(1)

    # --- Define image tags ---
    # base_image_tag = f"braindotai/opencrate-base-{args.runtime}:v{version}"
    final_image_tag = f"braindotai/opencrate-{args.runtime}-py{args.python}:v{version}"

    # Update .aliases.sh before building anything
    write_python_version(args.python)

    if args.generate_only:
        logger.info(
            f"======== ● Generating dockerfile for runtime {args.runtime} and python{args.python} ========"
        )
        if not args.log_workflow:
            console.print(
                f"\n[bold yellow]======== ● Generating dockerfile for runtime {args.runtime} and python{args.python} ========[/]"
            )
    else:
        logger.info(
            f"======== ● Building image for Python {args.python}, Runtime {args.runtime} ========"
        )
        if not args.log_workflow:
            console.print(
                f"\n[bold yellow]======== ● Building image for Python {args.python}, Runtime {args.runtime} ========[/]"
            )

    dockerfile_content = generate_combined_dockerfile()
    dockerfile_path = f"./docker/dockerfiles/Dockerfile.{args.runtime}-py{args.python}"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    if args.generate_only and not args.log_workflow:
        console.print(
            f"\n[bold green]======== ✔ Dockerfile generated at {dockerfile_path} ========[/bold green]"
        )
        return

    build_command = args.build_command or (
        f"docker buildx build --platform linux/amd64 -f {dockerfile_path} -t {final_image_tag} --load"
    )
    build_result = stream_docker_logs(
        logger,
        console,
        command=build_command,
    )
    if build_result == "Failed":
        console.print(
            "[bold red]======== 𐄂 Exiting due to application image build failure ========[/bold red]"
        )
        sys.exit(1)

    logger.info(f"======== ✔ Successfully built {final_image_tag} ========")
    if not args.log_workflow:
        console.print(
            f"[bold green]======== ✔ Successfully built {final_image_tag} ========[/bold green]"
        )


if __name__ == "__main__":
    main()
