PYTHON_VERSION ?= 3.10 # as default we use python 3.10 for development
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)
VERSION_FILE := VERSION
VERSION := $(shell cat $(VERSION_FILE) | tr -d '\n')

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


build-opencrate:
	@$(check_python)
	@python$${python_version} .docker/dockerfile.py --python=$${python:-3.10} --runtime=$${runtime:-cpu}

build-opencrate-all:
	@$(check_python)
	@for python in 3.7 3.8 3.9 3.10 3.11 3.12 3.13; do \
        for runtime in cpu cuda; do \
            python$${python_version} .docker/dockerfile.py --python=$$python --runtime=$$runtime; \
        done; \
    done; \
	docker container prune -f; \
	docker image prune -f;

push-opencrate:
	docker push braindotai/opencrate-$${runtime:-cpu}-py$${python:-3.10}:latest

push-opencrate-all:
	@for python in 3.7 3.8 3.9 3.10 3.11 3.12 3.13; do \
        for runtime in cpu cuda; do \
			docker push braindotai/opencrate-$${runtime}-py$${python}:v$(VERSION); \
            \
            if [ "$(latest)" = "True" ]; then \
				docker tag braindotai/opencrate-$${runtime}-py$${python}:v$(VERSION) braindotai/opencrate-$${runtime}-py$${python}:latest; \
				docker push braindotai/opencrate-$${runtime}-py$${python}:latest; \
            fi; \
        done; \
    done;

build:
	@docker build -t opencrate-dev:latest .

start:
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose up opencrate_dev -d

enter:
	@docker exec -it opencrate_dev zsh

stop:
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose stop

kill:
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose down

install:
	@$(check_python)
	@echo "Using Python version: $${python_version}"
	@python$${python_version} -m pip install --upgrade pip --root-user-action=ignore --no-cache-dir
	@python$${python_version} -m pip install -e .[dev] --root-user-action=ignore --no-cache-dir
	@PYTHON_VERSIONS="3.7 3.8 3.9 3.11 3.12 3.13"; \
	echo "Installing Python versions: $$PYTHON_VERSIONS"; \
	for version in $$PYTHON_VERSIONS; do \
		if ! pyenv versions --bare | grep -q "^$$version\\."; then \
			pyenv install $$version; \
		fi; \
	done; \
	echo "\nDone installing the package with development environment and dependencies"

mkdocs:
	mkdocs serve -a 0.0.0.0:8000
	
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

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install         Install the package with development environment and dependencies"
	@echo "  build           Build the Docker image (opencrate-dev:latest)"
	@echo "  build-opencrate Build OpenCrate Docker image with specified Python and runtime"
	@echo "  build-opencrate-all Build all OpenCrate Docker images for all supported Python versions and runtimes"
	@echo "  start           Start the development container"
	@echo "  enter           Enter the development container"
	@echo "  stop            Stop the development container"
	@echo "  kill            Remove the development container"
	@echo "  test-pytest     Run pytest - for unit tests"
	@echo "  test-black      Run black - for code formatting"
	@echo "  test-flake8     Run flake8 - for linting"
	@echo "  test-mypy       Run mypy - for static type checking"
	@echo "  test            Run all tests - pytest, black, flake8, mypy"
	@echo "  test-all        Run all tests with tox for multiple Python versions"
	@echo "  help            Show this help message"