import argparse

import docker
from rich.console import Console
from utils import CLInstall, spinner, stream_docker_logs, write_python_version

parser = argparse.ArgumentParser(
    description="Build Dockerfile with specified configurations."
)
parser.add_argument(
    "--python", type=float, default=3.10, help="Specify the Python version to use."
)
parser.add_argument("--runtime", type=str, default="cuda", help="Specify the runtime")

args = parser.parse_args()
if args.python == 3.1:
    args.python = "3.10"
python_version = int(f"{args.python}"[2:])
assert python_version >= 7, "Python version must be 3.7 or higher."

# Optimized Ubuntu installation with aggressive cleanup
UBUNTU_POST_INSTALLATION = [
    CLInstall(
        install_cmd="apt install -y --no-install-recommends",
        packages=[
            "software-properties-common",
            "ca-certificates",
            "build-essential",
            "pkg-config",
            "libgoogle-perftools-dev",
            "cmake",
            "tzdata",
            "gnupg",
            "gcc",
            "wget",
            "curl",
            "vim",
            "git",
            "speedtest-cli",
            "iputils-ping",
            "libcairo2-dev",
        ],
        pre_installation_steps=[
            "apt update -y",
            "apt upgrade -y",
        ],
        post_installation_steps=[
            "echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata",
            # Aggressive cleanup
            "apt-get autoremove -y",
            "apt-get clean",
            "rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc /usr/share/man /usr/share/locale",
        ],
    )
]

# Combined CLI packages installation with cleanup
CLI_PACKAGES = [
    CLInstall(
        install_cmd="apt install -y --no-install-recommends",
        pre_installation_steps=[
            "apt update -y",
        ],
        packages=[
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
            "zsh",  # Move zsh here with other standard packages
            "nvtop" if args.runtime == "cuda" else "",
        ],
        post_installation_steps=[
            # Clean up after CLI tools installation
            "apt-get clean",
            "rm -rf /var/lib/apt/lists/*",
        ],
    ),
    CLInstall(
        install_cmd="apt install -y --no-install-recommends",
        packages=["eza", "fastfetch"],
        pre_installation_steps=[
            "mkdir -p /etc/apt/keyrings",
            "wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | gpg --dearmor -o /etc/apt/keyrings/gierens.gpg",
            "echo 'deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main' | tee /etc/apt/sources.list.d/gierens.list",
            "chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list",
            "add-apt-repository ppa:zhangsongcui3371/fastfetch -y",
            "apt update -y",
        ],
        post_installation_steps=[
            # Clean up package lists and temp files
            "apt-get clean",
            "rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*",
        ],
    ),
    CLInstall(
        install_cmd="",  # No install command needed, just setup
        packages=[],
        pre_installation_steps=[
            "COPY .docker/cli/ /home/",
        ],
        post_installation_steps=[
            "chsh -s $(which zsh)",
            "wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O - | zsh || true",
            "git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k",
            "git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions",
            "git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting",
            "curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh",
            "mv /home/zsh/.zshrc ~/.zshrc && mv /home/zsh/.p10k.zsh ~/.p10k.zsh && mv /home/zsh/.aliases.sh ~/ && mv /home/zsh/.exports.sh ~/",
            "mkdir -p ~/.config/btop/ && mkdir -p ~/.config/atuin/ && mkdir -p ~/.config/fastfetch/",
            "cp -r /home/btop/ ~/.config/",
            "cp -r /home/atuin/ ~/.config/",
            "cp -r /home/fastfetch/ ~/.config/",
            "rm -rf /home/zsh/",
            # Clean up after shell setup
            "rm -rf /tmp/* /var/tmp/* /root/.cache",
        ],
    ),
]

# Optimized Python installation with Rust (for Python 3.7)
additional_pre_installation_steps = []
rust_env_vars = ""
if python_version == 7:
    additional_pre_installation_steps = [
        # Set Rust environment variables before installation
        "export CARGO_HOME=/usr/local/cargo",
        "export RUSTUP_HOME=/usr/local/rustup",
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal --no-modify-path",
    ]
    rust_env_vars = "ENV PATH='/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/root/.cargo/bin:${PATH}' CARGO_HOME=/usr/local/cargo RUSTUP_HOME=/usr/local/rustup"

# Optimized Python installation with Rust (for Python 3.7)
additional_pre_installation_steps = []
additional_post_installation_steps = []

if python_version == 7:
    additional_pre_installation_steps = [
        # Install Rust properly in Docker environment
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal",
    ]
    additional_post_installation_steps = [
        # Set up Rust environment without using 'source'
        'export PATH="$HOME/.cargo/bin:$PATH"',
        # Move Rust to standard locations for easier copying
        "mkdir -p /usr/local/cargo /usr/local/rustup",
        "cp -r $HOME/.cargo/* /usr/local/cargo/ 2>/dev/null || true",
        "cp -r $HOME/.rustup/* /usr/local/rustup/ 2>/dev/null || true",
        "ln -sf /usr/local/cargo/bin/* /usr/local/bin/ 2>/dev/null || true",
    ]

PYTHON_INSTALL = CLInstall(
    install_cmd="apt install -y --no-install-recommends",
    packages=[
        f"python{args.python}-distutils"
        if python_version <= 11
        else f"python{args.python}",
        f"python{args.python}-dev",
    ],
    pre_installation_steps=[
        "add-apt-repository ppa:deadsnakes/ppa -y",
        "apt update -y",
    ]
    + additional_pre_installation_steps,
    post_installation_steps=[
        (
            f"curl -sS https://bootstrap.pypa.io/get-pip.py | python{args.python}"
            if python_version >= 9
            else f"curl -sS https://bootstrap.pypa.io/pip/{args.python}/get-pip.py | python{args.python}"
        ),
        f"python{args.python} -m pip install --upgrade pip --root-user-action=ignore --no-cache-dir",
    ]
    + additional_post_installation_steps
    + [
        # Clean up build dependencies
        "apt-get autoremove -y",
        "apt-get clean",
        "rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache ~/.cargo ~/.rustup",
        # Set environment variables for Rust (only for Python 3.7)
        "ENV PATH='/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/cargo/bin:${PATH}'"
        if python_version == 7
        else "",
    ],
)

# Optimized Python packages with cleanup
PYTHON_PACKAGES = [
    CLInstall(
        install_cmd=f"python{args.python} -m pip install --no-cache-dir --upgrade --root-user-action=ignore",
        packages=[
            "ipython",
            "jupyter",
        ],
        post_installation_steps=[
            f"python{args.python} -m pip cache purge",
        ],
    ),
]

# if python_version >= 9 and python_version != 13 and args.runtime == "cuda":
#     PYTHON_PACKAGES.append(
#         CLInstall(
#             install_cmd=f"python{args.python} -m pip install --no-cache-dir --upgrade --root-user-action=ignore --extra-index-url=https://pypi.nvidia.com",
#             packages=["cudf-cu12"],
#             post_installation_steps=[
#                 f"python{args.python} -m pip cache purge",
#             ],
#         ),
#     )

CUDA_IMAGES = [
    "nvcr.io/nvidia/cuda:12.9.1-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.9.0-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.6.2-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.6.1-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.6.0-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.5.1-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.0.1-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.0.0-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04",
    "nvcr.io/nvidia/cuda:11.7.0-cudnn8-runtime-ubuntu22.04",
]

# Multi-stage build base templates
FROM_IMAGE_BUILDER = (
    "FROM nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04 AS builder"
    if args.runtime == "cuda"
    else "FROM ubuntu:22.04 AS builder"
)

FROM_IMAGE_RUNTIME = (
    "FROM nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04"
    if args.runtime == "cuda"
    else "FROM ubuntu:22.04"
)

ENV_VARIABLES = """
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata
"""
if args.runtime == "cuda":
    ENV_VARIABLES += "ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH\n"

INIT_SCRIPTS = """
RUN mkdir /root/.hooks/
COPY .docker/hooks/ /root/.hooks/
"""

# Multi-stage optimized OpenCrate installation
OPENCRATE_BUILDER = f"""
# Builder stage - install application
WORKDIR /home/opencrate/
COPY pyproject.toml setup.cfg setup.py ./
COPY src/ ./src/
RUN python{args.python} -m pip install -e . --no-cache-dir --root-user-action=ignore && \\
    python{args.python} -m pip cache purge
"""

OPENCRATE_RUNTIME = f"""
# Copy application and Python environment from builder
COPY --from=builder /home/opencrate /home/opencrate
COPY --from=builder /usr/local/lib/python{args.python} /usr/local/lib/python{args.python}
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy Python binary and libraries
COPY --from=builder /usr/bin/python{args.python} /usr/bin/python{args.python}
COPY --from=builder /usr/lib/python{args.python} /usr/lib/python{args.python}
"""

# Add Rust runtime copy only for Python 3.7 and only if directories exist
if python_version == 7:
    OPENCRATE_RUNTIME += """
# Copy Rust components (only for Python 3.7)
COPY --from=builder /usr/local/cargo /usr/local/cargo
COPY --from=builder /usr/local/rustup /usr/local/rustup
COPY --from=builder /root/.cargo /root/.cargo
"""

WORKSPACE = """
WORKDIR /home/workspace/
RUN git config --global --add safe.directory '*' && git config --global init.defaultBranch main
"""


def clean_dockerfile(dockerfile_content: str) -> str:
    dockerfile_content = dockerfile_content.replace("RUN COPY", "COPY")
    dockerfile_content = dockerfile_content.replace(" && COPY", "\nCOPY")
    dockerfile_content = dockerfile_content.replace("RUN  &&\\\n    ", "\nRUN ")

    # Remove empty lines and clean up formatting
    lines = [line for line in dockerfile_content.split("\n") if line.strip()]
    return "\n".join(lines)


def generate_multi_stage_dockerfile(image_name: str, version: str) -> str:
    """Generate optimized single-stage Dockerfile with aggressive cleanup"""

    dockerfile_content = f"""
# Optimized single-stage build with aggressive cleanup
FROM opencrate-base-{args.runtime}:v{version}

{ENV_VARIABLES}

# Install Python and dependencies in one optimized layer
RUN {PYTHON_INSTALL()}

# Install Python packages
"""

    for package in PYTHON_PACKAGES:
        dockerfile_content += f"RUN {package()}\n"

    # Install application
    dockerfile_content += f"""
# Install application
RUN mkdir -p /home/opencrate/
WORKDIR /home/opencrate/
COPY src/ /home/opencrate/src
COPY pyproject.toml /home/opencrate/
COPY setup.cfg /home/opencrate/
COPY setup.py /home/opencrate/
RUN python{args.python} -m pip install -e . --no-cache-dir --root-user-action=ignore && \\
    python{args.python} -m pip cache purge && \\
    # Final aggressive cleanup
    apt-get autoremove -y && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

{INIT_SCRIPTS}
{WORKSPACE}
"""

    return clean_dockerfile(dockerfile_content)


def generate_base_dockerfile_with_cli() -> str:
    """Generate base dockerfile with CLI tools (non-multi-stage for CLI tools)"""
    dockerfile_content = (
        FROM_IMAGE_RUNTIME.replace(" AS builder", "") + "\n"
        if "AS builder" in FROM_IMAGE_RUNTIME
        else FROM_IMAGE_RUNTIME + "\n"
    )
    dockerfile_content += ENV_VARIABLES + "\n"

    # Install Ubuntu packages with cleanup
    for package in UBUNTU_POST_INSTALLATION:
        dockerfile_content += f"RUN {package()}\n"

    # Install CLI packages with cleanup
    for package in CLI_PACKAGES:
        dockerfile_content += f"RUN {package()}\n"

    return clean_dockerfile(dockerfile_content)


def main():
    console = Console()
    docker_client = docker.from_env()
    image_name = f"opencrate-{args.runtime}-py{args.python}"

    with open("VERSION", "r") as version_file:
        version = version_file.read().strip()

    console.print(
        f"\n [blue]●[/blue] [[blue]Building[/blue]] > {image_name}:v{version}"
    )

    with spinner(console, ">>"):
        write_python_version(args.python)

        # Generate optimized base dockerfile with CLI tools
        dockerfile_base_content = generate_base_dockerfile_with_cli()
        dockerfile_base_path = f"./.docker/dockerfiles/Dockerfile:base-{args.runtime}"

        with open(dockerfile_base_path, "w") as f:
            f.write(dockerfile_base_content)

        # Build base image
        while (
            stream_docker_logs(
                console,
                command=docker_client.api.build(  # type: ignore
                    path=".",
                    dockerfile=dockerfile_base_path,
                    tag=f"opencrate-base-{args.runtime}:v{version}",
                    rm=True,
                    decode=True,
                ),
            )
            == "Failed"
        ):
            pass

        # Generate optimized multi-stage application dockerfile
        dockerfile_content = generate_multi_stage_dockerfile(image_name, version)

        # Replace the FROM line to use our base image for builder stage
        dockerfile_content = dockerfile_content.replace(
            FROM_IMAGE_BUILDER,
            f"FROM opencrate-base-{args.runtime}:v{version} AS builder",
        ).replace(FROM_IMAGE_RUNTIME, f"FROM opencrate-base-{args.runtime}:v{version}")

        # Fix potential duplicate environment variables
        lines = dockerfile_content.split("\n")
        seen_envs = set()
        filtered_lines = []
        for line in lines:
            if line.startswith("ENV "):
                env_key = line.split()[1].split("=")[0]
                if env_key not in seen_envs:
                    seen_envs.add(env_key)
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        dockerfile_content = "\n".join(filtered_lines)

        dockerfile_path = (
            f"./.docker/dockerfiles/Dockerfile:{image_name.replace('opencrate-', '')}"
        )

        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Build final optimized image
        while (
            stream_docker_logs(
                console,
                command=docker_client.api.build(  # type: ignore
                    path=".",
                    dockerfile=dockerfile_path,
                    tag=f"braindotai/{image_name}:v{version}",
                    rm=True,
                    decode=True,
                ),
            )
            == "Failed"
        ):
            pass


if __name__ == "__main__":
    main()
