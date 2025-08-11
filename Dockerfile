# Stage 1: Base image with essential tools
FROM nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

RUN apt update -y && \
    apt install -y --no-install-recommends software-properties-common ca-certificates build-essential pkg-config libgoogle-perftools-dev cmake tzdata gcc wget curl vim git speedtest-cli iputils-ping && \
    echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata && \
    git config --global init.defaultBranch main && \
    apt install -y --no-install-recommends fontconfig btop unrar make tree htop bat tldr zoxide cpufetch jq nvtop && \
    mkdir -p /etc/apt/keyrings && \
    wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | gpg --dearmor -o /etc/apt/keyrings/gierens.gpg && \
    echo 'deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main' | tee /etc/apt/sources.list.d/gierens.list && \
    chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list && \
    add-apt-repository ppa:zhangsongcui3371/fastfetch -y && \
    apt update -y && \
    apt install -y --no-install-recommends eza fastfetch && \
    apt install -y zlib1g zlib1g-dev libssl-dev libbz2-dev libsqlite3-dev libedit-dev libffi-dev libreadline-dev && \
    apt install -y --no-install-recommends zsh && \
    chsh -s $(which zsh) && \
    wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O - | zsh || true && \
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone https://github.com/marlonrichert/zsh-autocomplete.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autocomplete && \
    curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh && \
    mkdir -p ~/.config/btop/ ~/.config/atuin/ ~/.config/fastfetch/ ~/.local/share/fonts && \
    fc-cache -f -v && \
    # install docker
    curl -fsSL https://get.docker.com | sh && \
    usermod -aG docker root

# Stage 2: Copy configuration files
FROM base AS config
COPY docker/cli/ /root/
COPY docker/fonts/ /root/
COPY docker/hooks/ /root/.hooks/

RUN mv /root/zsh/.zshrc /root/.zshrc && \
    mv /root/zsh/.p10k.zsh /root/.p10k.zsh && \
    mv /root/zsh/.aliases.sh /root/ && \
    mv /root/zsh/.exports.sh /root/ && \
    cp -r /root/btop/ ~/.config/ && \
    cp -r /root/atuin/ ~/.config/ && \
    cp -r /root/fastfetch/ ~/.config/ && \
    cp /root/*ttf ~/.local/share/fonts/ && \
    rm -rf /root/zsh/ /root/*ttf && \
    echo '\n# PyEnv Configuration\nexport PYENV_ROOT="$HOME/.pyenv"\n[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init - zsh)"\n' >> /root/.zshrc

# Stage 3: Install Python and PyEnv
FROM base AS python

RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt update -y && \
    apt install -y --no-install-recommends python3.10-distutils python3.10-dev && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    python3.10 -m pip install --upgrade pip docker rich --root-user-action=ignore && \
    curl -fsSL https://pyenv.run | bash

# Final stage: Combine everything
FROM base

COPY --from=config /root/.hooks/ /root/.hooks/
COPY --from=config /root/.zshrc /root/.zshrc
COPY --from=config /root/.p10k.zsh /root/.p10k.zsh
COPY --from=config /root/.aliases.sh /root/.aliases.sh
COPY --from=config /root/.exports.sh /root/.exports.sh
COPY --from=config /root/.config/ /root/.config/
COPY --from=config /root/.local/ /root/.local/
COPY --from=python /usr/local/ /usr/local/
COPY --from=python /root/.pyenv/ /root/.pyenv/

RUN mkdir /home/opencrate/
WORKDIR /home/opencrate/

CMD ["zsh"]