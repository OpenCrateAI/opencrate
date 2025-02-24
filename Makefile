PYTHON_VERSION ?= 3.10 # as default we use python 3.10 for development
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

.SILENT:
.ONESHELL:

check_python = \
    if [ -z "$${python_version}" ]; then \
        python_version=$(PYTHON_VERSION); \
        echo "Using default Python version $${python_version}"; \
    else \
        echo "Using provided Python version $${python_version}"; \
    fi; \
    if ! command -v python$${python_version} >/dev/null 2>&1; then \
        echo "Error: Python $${python_version} is not installed on your system"; \
        echo "Please install Python $${python_version} or use a different version"; \
        exit 1; \
    fi; \
    export python_version=$${python_version}

# install:
# 	@$(check_python)
# 	@python$${python_version} -m pip install --upgrade pip
# 	@python$${python_version} -m pip install -e . --no-cache-dir
# 	@oc --install-completion || true

install:
	@$(check_python)
	@echo "Using Python version: $${python_version}"
	@python$${python_version} -m pip install --upgrade pip
	@python$${python_version} -m pip install -e .[dev] --no-cache-dir
	@oc --install-completion || true
	@for version in 3.7.17 3.8 3.9 3.11 3.12 3.13; do \
		if ! pyenv versions --bare | grep -q "^$$version$$"; then \
			pyenv install $$version; \
			python$$version -m pip install --upgrade pip; \
		fi; \
	done
	@pyenv local 3.8 3.9 3.11 3.12 3.13

enter:
	@$(git-creds)
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose up opencrate_dev -d && docker exec -it opencrate_dev zsh

stop:
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose stop

kill:
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose down

test-pytest:
	@PYTHONPATH=src pytest

test-black:
	@black --check src tests

test-flake8:
	@flake8 src tests

test-mypy:
	@mypy src tests

test: test-pytest test-black test-flake8 test-mypy

test-all:
	@tox

build:
	@$(check_python)
	@python$${python_version} .docker/dockerfile.py --python=$(if $${python_version},$${python_version},3.10) --runtime=$(if $${runtime},$${runtime},cuda)

build-all:
	@$(check_python)
	@for python in 3.7 3.8 3.9 3.10 3.11 3.12 3.13; do \
        for runtime in cuda cpu; do \
            python$${python_version} .docker/dockerfile.py --python=$$python --runtime=$$runtime; \
        done \
    done

build-dev:
	@docker build -t opencrate-dev:latest .

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install    	 Install the package with development environment and dependencies"
	@echo "  enter      	 Enter the development container"
	@echo "  test-pytest    Run pytest - for unit tests"
	@echo "  test-black     Run black - for code formatting"
	@echo "  test-flake8    Run flake8 - for linting"
	@echo "  test-mypy      Run mypy - for static type checking"
	@echo "  test           Run all tests - pytest, black, flake8, mypy"
	@echo "  test-all       Run all tests with tox for multiple Python versions - pytest, black, flake8, mypy"
	@echo "  build          Build the Docker image with the specified Python version and runtime"
	@echo "  build-all      Build all Docker images for all supported Python versions and runtimes"
	@echo "  build-dev      Build the development Docker image"
	@echo "  help           Show this help message"