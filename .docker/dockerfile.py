import argparse

import docker
from rich.console import Console
from utils import CLInstall, spinner, stream_docker_logs, write_python_version

parser = argparse.ArgumentParser(description="Build Dockerfile with specified configurations.")
parser.add_argument("--python", type=float, default=3.9, help="Specify the Python version to use.")
parser.add_argument("--runtime", type=str, default="cuda", help="Specify the runtime")

args = parser.parse_args()
if args.python == 3.1:
    args.python = f"{3.10:.2f}"

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
            "gcc",
            "wget",
            "curl",
            "vim",
            "git",
            "speedtest-cli",
            "iputils-ping",
        ],
        pre_installation_steps=[
            "apt update -y",
            "apt upgrade -y",
        ],
        post_installation_steps=[
            "echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata",
        ],
    )
]

CLI_PACKAGES = [
    CLInstall(
        install_cmd="apt install -y --no-install-recommends",
        pre_installation_steps=[
            "apt update -y",
        ],
        packages=[
            "fontconfig",
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
            "nvtop" if args.runtime == "cuda" else "",
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
    ),
    CLInstall(
        install_cmd="apt install -y --no-install-recommends",
        packages="zsh",
        pre_installation_steps=[
            "COPY .docker/cli/ /home/",
            "COPY .docker/fonts/ /home/",
        ],
        post_installation_steps=[
            "chsh -s $(which zsh)",
            "wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O - | zsh || true",
            "git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k",
            "git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions",
            "git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting",
            "git clone https://github.com/marlonrichert/zsh-autocomplete.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autocomplete",
            "curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh",
            "mv /home/zsh/.zshrc ~/.zshrc && mv /home/zsh/.p10k.zsh ~/.p10k.zsh && mv /home/zsh/.aliases.sh ~/ && mv /home/zsh/.exports.sh ~/",
            "mkdir -p ~/.config/btop/ && mkdir -p ~/.config/atuin/ && mkdir -p ~/.config/fastfetch/",
            "cp -r /home/btop/ ~/.config/",
            "cp -r /home/atuin/ ~/.config/",
            "cp -r /home/fastfetch/ ~/.config/",
            "rm -rf /home/zsh/",
            "mkdir -p ~/.local/share/fonts",
            "cp /home/*ttf ~/.local/share/fonts/",
            "fc-cache -f -v",
            "rm /home/*ttf",
        ],
    ),
]

python_version = int(f"{args.python}"[2:])
additional_pre_installation_steps = []
if python_version <= 7:
    additional_pre_installation_steps = [
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    ]
PYTHON_INSTALL = CLInstall(
    install_cmd="apt install -y --no-install-recommends",
    packages=[
        f"python{args.python}-distutils" if python_version <= 11 else f"python{args.python}",
        f"python{args.python}-dev",
        # f"python{args.python}-venv",
    ],
    pre_installation_steps=[
        "add-apt-repository ppa:deadsnakes/ppa -y",
        "apt update -y",
    ]
    + additional_pre_installation_steps,
    post_installation_steps=[
        (
            f"curl -sS https://bootstrap.pypa.io/get-pip.py | python{args.python}"
            if python_version >= 8
            else f"curl -sS https://bootstrap.pypa.io/pip/{args.python}/get-pip.py | python{args.python}"
        ),
        f"python{args.python} -m pip install --upgrade pip --root-user-action=ignore",
        (
            "ENV PATH='/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/root/.cargo/bin:${PATH}'"
            if python_version <= 7
            else ""
        ),
    ],
)

PYTHON_PACKAGES = [
    CLInstall(
        install_cmd=f"python{args.python} -m pip install --no-cache-dir --upgrade --root-user-action=ignore",
        packages=[
            "matplotlib",
            "seaborn",
            "scikit-learn",
            "pandas",
            "ipython",
            "scipy",
            "opencv-python",
            "pillow",
            "jupyter",
            "rich",
            "requests",
            "loguru",
            "onnxruntime-gpu" if args.runtime == "cuda" else "onnxruntime",
        ],
        post_installation_steps=[
            f"python{args.python} -m pip cache purge",
        ],
    ),
]
if python_version >= 9 and python_version != 13 and args.runtime == "cuda":
    PYTHON_PACKAGES.append(
        CLInstall(
            install_cmd=f"python{args.python} -m pip install --no-cache-dir --upgrade --root-user-action=ignore --extra-index-url=https://pypi.nvidia.com",
            packages=["cudf-cu12"],
            post_installation_steps=[
                f"python{args.python} -m pip cache purge",
            ],
        ),
    )

FROM_IMAGE = (
    """FROM nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04
"""
    if args.runtime == "cuda"
    else """
FROM ubuntu:22.04
"""
)

ENV_VARIABLES = """
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata
"""
if args.runtime == "cuda":
    ENV_VARIABLES += "ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH\n"  # type: ignore

INIT_SCRIPTS = """
RUN mkdir /root/.hooks/
COPY .docker/hooks/ /root/.hooks/
"""

requirements = f"requirements-pytorch-{args.runtime}.txt"

OPENCRATE = f"""
RUN mkdir /home/opencrate/
WORKDIR /home/opencrate/
COPY src/ /home/opencrate/src
COPY pyproject.toml /home/opencrate/
COPY setup.cfg /home/opencrate/
COPY setup.py /home/opencrate/
COPY .docker/requirements/{requirements} /home/opencrate/
RUN python{args.python} -m pip install -r {requirements} --no-cache-dir --root-user-action=ignore
RUN python{args.python} -m pip install -e . --no-cache-dir --root-user-action=ignore
"""

WORKSPACE = """
WORKDIR /home/workspace/
RUN git config --global --add safe.directory '*' && git config --global init.defaultBranch main
"""


def clean_dockerfile(dockerfile_content: str) -> str:
    dockerfile_content = dockerfile_content.replace("RUN COPY", "COPY")
    dockerfile_content = dockerfile_content.replace(" && COPY", "\nCOPY")

    return dockerfile_content


def main():
    console = Console()
    docker_client = docker.from_env()
    image_name = f"opencrate-pytorch-{args.runtime}-py{args.python}"

    console.print(f"\n [blue]●[/blue] [[blue]Building[/blue]] > {image_name}")

    with spinner(console, ">>"):
        write_python_version(args.python)

        # Combine blocks based on configuration
        dockerfile_base_content = FROM_IMAGE
        dockerfile_base_content += f"{ENV_VARIABLES}"

        for package in UBUNTU_POST_INSTALLATION:
            dockerfile_base_content += f"\nRUN {package()}"

        for package in CLI_PACKAGES:
            dockerfile_base_content += f"\n\nRUN {package()}"

        dockerfile_base_content = clean_dockerfile(dockerfile_base_content)

        dockerfile_base_path = f"./.docker/dockerfiles/Dockerfile:base"
        with open(dockerfile_base_path, "w") as f:
            f.write(dockerfile_base_content)
        stream_docker_logs(
            console,
            command=docker_client.api.build(  # type: ignore
                path=".",
                dockerfile=dockerfile_base_path,
                tag=f"opencrate-base:latest",
                rm=True,
                decode=True,
            ),
        )

        dockerfile_content = "FROM opencrate-base:latest"
        dockerfile_content += f"\n{INIT_SCRIPTS}"
        dockerfile_content += f"\nRUN {PYTHON_INSTALL()}"

        for package in PYTHON_PACKAGES:
            dockerfile_content += f"\nRUN {package()}"

        dockerfile_content += f"\n{OPENCRATE}"
        dockerfile_content += f"{WORKSPACE}"

        dockerfile_content = clean_dockerfile(dockerfile_content)

        dockerfile_path = f"./.docker/dockerfiles/Dockerfile:{image_name.replace('opencrate-', '')}"

        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        stream_docker_logs(
            console,
            command=docker_client.api.build(  # type: ignore
                path=".",
                dockerfile=dockerfile_path,
                tag=f"{image_name}:latest",
                rm=True,
                decode=True,
            ),
        )


if __name__ == "__main__":
    main()
