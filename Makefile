SHELL := /bin/bash
PYTHON_VERSION ?= 3.10
RUNTIME ?= cuda
DEPS ?= dev

# 1. Read supported versions from file (replace newlines with spaces)
PYTHON_VERSIONS_LIST := $(shell cat PYTHON_VERSIONS | tr '\n' ' ')

# 2. Detect dependency changes (Robust check for working tree AND last commit)
# This variable is used for local make commands
DETECTED_CHANGE := $(shell (git diff --name-only -- 2>/dev/null || true; git diff --name-only HEAD~1 HEAD -- 2>/dev/null || true) | grep -E 'pyproject.toml|setup.cfg')

HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

VERSION ?= $(shell cat VERSION | tr -d '\n')

MAKEFLAGS += --no-print-directory

.SILENT:
.ONESHELL:

# Color and format codes
BOLD := \033[1m
RESET := \033[0m
GREEN := \033[32m
YELLOW := \033[33m
BOLD_RED := \033[1;31m
BOLD_GREEN := \033[1;32m
BOLD_YELLOW := \033[1;33m
BOLD_BLUE := \033[1;34m
BOLD_ORANGE := \033[1;38;5;214m


start:
	@echo -e "$(BOLD_YELLOW)● Starting development container...$(RESET)"
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose up opencrate_dev -d
	@echo -e "$(BOLD_GREEN)✓ Container started successfully$(RESET)"


enter:
	@echo -e "$(BOLD_YELLOW)● Entering development container...$(RESET)"
	@docker exec -it opencrate_dev zsh


stop:
	@echo -e "$(BOLD_YELLOW)● Stopping development container...$(RESET)"
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose stop
	@echo -e "$(BOLD_GREEN)✓ Container stopped$(RESET)"


kill:
	@echo -e "$(BOLD_RED)● Killing and removing development container...$(RESET)"
	@export HOST_GIT_EMAIL=$(HOST_GIT_EMAIL)
	@export HOST_GIT_NAME=$(HOST_GIT_NAME)
	@docker compose down
	@echo -e "$(BOLD_GREEN)✓ Container removed$(RESET)"


install-dev-package:
	@echo -e "$(BOLD_YELLOW)● Installing development package...$(RESET)"
	@echo -e "  $(BOLD_BLUE)▶ Upgrading pip...$(RESET)"
	@python3.10 -m pip install --upgrade pip --root-user-action=ignore
	@echo -e "  $(BOLD_BLUE)▶ Installing package in editable mode with dev dependencies...$(RESET)"
	@python3.10 -m pip install -e ".[dev]" --root-user-action=ignore
	@echo -e "$(BOLD_GREEN)✓ Development package installed$(RESET)"


install-dev-versions:
	@echo -e "$(BOLD_YELLOW)● Installing Python versions for testing...$(RESET)"
	@echo -e "  $(BOLD_BLUE)▶ Target versions: $(PYTHON_VERSIONS_LIST)$(RESET)"; \
	for version in $(PYTHON_VERSIONS_LIST); do \
		if ! pyenv versions --bare | grep -q "^$$version\\."; then \
			echo -e "  $(BOLD_YELLOW)  ▶ Installing Python $$version...$(RESET)"; \
			pyenv install $$version; \
		else \
			echo -e "  $(GREEN)  ✓ Python $$version already installed$(RESET)"; \
		fi; \
	done; \
	pyenv local $(PYTHON_VERSIONS_LIST)
	@echo -e "  $(BOLD_BLUE)▶ Installing pre-commit hooks...$(RESET)"
	@pre-commit install
	@echo -e "$(BOLD_GREEN)✓ All Python versions and tools installed$(RESET)"


install: install-dev-package install-dev-versions


mkdocs:
	@echo -e "$(BOLD_YELLOW)● Starting MkDocs server...$(RESET)"
	@echo -e "  $(BOLD_BLUE)▶ Server will be available at: $(BOLD)http://0.0.0.0:8789$(RESET)"
	@python$(PYTHON_VERSION) -m mkdocs serve -a 0.0.0.0:8789


test-ruff:
	@echo -e "\n$(BOLD_YELLOW)▶ Running ruff linter...$(RESET)"
	@ruff check . --fix
	@echo -e "$(BOLD_GREEN)✓ Ruff checks completed$(RESET)"


test-mypy:
	@echo -e "\n$(BOLD_YELLOW)▶ Running mypy type checks...$(RESET)"
	@mypy --pretty
	@echo -e "$(BOLD_GREEN)✓ Mypy checks completed$(RESET)"


test-pytest:
	@echo -e "\n$(BOLD_YELLOW)▶ Running pytest unit tests...$(RESET)"
	@pytest
	@echo -e "$(BOLD_GREEN)✓ Pytest completed$(RESET)"

test-all: test-ruff test-mypy test-pytest

test-tox:
	@echo -e "\n$(BOLD_YELLOW)● Running tox for multi-version testing...$(RESET)"
	@tox
	@echo -e "$(BOLD_GREEN)✓ Tox tests completed$(RESET)"


test-clean:
	@echo -e "\n$(BOLD_YELLOW)● Cleaning test artifacts...$(RESET)"
	@rm -rf .mypy_cache .pytest_cache .ruff_cache .tox .coverage
	@echo -e "$(BOLD_GREEN)✓ Test artifacts cleaned$(RESET)"

# This target generates Dockerfiles for all supported Python versions and runtimes.
docker-generate:
	@set -e; \
	echo -e "$(BOLD_YELLOW)\n======== ● Generating all Dockerfiles ========$(RESET)\n"
	@RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	echo -e "  $(BOLD_BLUE)▶ Python versions: $(PYTHON_VERSIONS_LIST)$(RESET)"; \
	echo -e "  $(BOLD_BLUE)▶ Runtimes: $$RUNTIMES_TO_USE$(RESET)\n"; \
	mkdir -p ./docker/dockerfiles; \
	for python_version in $(PYTHON_VERSIONS_LIST); do \
		for runtime in $$RUNTIMES_TO_USE; do \
			python3.10 docker/dockerfile.py --generate --python=$$python_version --runtime=$$runtime; \
		done; \
	done; \
	echo -e "\n$(BOLD_GREEN)======== ✓ All Dockerfiles generated successfully ========$(RESET)\n"


# This target builds all supported OpenCrate images locally.
docker-build:
	@set -e; \
	echo -e "$(BOLD_YELLOW)\n======== ● Building all OpenCrate images locally ========$(RESET)\n"; \
	CACHE_UPDATE="false"; \
	if [ "$(REBUILD_FLAG)" = "true" ]; then \
		echo -e "  $(BOLD_ORANGE)! Manual Rebuild Flag Detected !"; \
		echo -e "  $(BOLD_ORANGE)! Cache update forced !$(RESET)"; \
		CACHE_UPDATE="true"; \
	elif [ -n "$(DETECTED_CHANGE)" ]; then \
		echo -e "  $(BOLD_ORANGE)! Dependency Changes Detected in !"; \
		echo -e "  > $(DETECTED_CHANGE)$(RESET)"; \
		echo -e "  $(BOLD_ORANGE)! Cache update forced !$(RESET)"; \
		CACHE_UPDATE="true"; \
	else \
		echo -e "  $(GREEN)✓ No dependency changes. Using read-only cache with fast build$(RESET)"; \
	fi; \
	\
	RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	\
	for python_version in $(PYTHON_VERSIONS_LIST); do \
		for runtime in $$RUNTIMES_TO_USE; do \
			make -f Makefile.ci build \
				MODE=test \
				RUNTIME=$$runtime \
				PYTHON_VERSION=$$python_version \
				VERSION=$(VERSION) \
				REBUILD_FLAG=$(REBUILD_FLAG) \
				CACHE_UPDATE=$$CACHE_UPDATE; \
		done; \
	done; \
	echo -e "\n$(BOLD_GREEN)======== ✓ All local images built successfully! ========$(RESET)\n";


# Helper target for CI to strictly check changes against previous commit
check-dependency-changes:
	@if (git diff --name-only HEAD~1 HEAD -- 2>/dev/null || true) | grep -E 'pyproject.toml|setup.cfg' > /dev/null; then \
		echo "true"; \
	else \
		echo "false"; \
	fi

# This target cleans up all Docker-related caches and unused images.
docker-clean:
	@echo -e "$(BOLD_YELLOW)● Cleaning Docker resources...$(RESET)"
	@echo -e "  $(BOLD_BLUE)▶ Cleaning container cache...$(RESET)"; \
	docker container prune -f; \
	@echo -e "  $(BOLD_BLUE)▶ Cleaning buildx cache...$(RESET)"; \
	docker buildx prune -f; \
	@echo -e "  $(BOLD_BLUE)▶ Cleaning image cache...$(RESET)"; \
	docker image prune -f;
	@echo -e "$(BOLD_GREEN)✓ Docker cleanup completed$(RESET)"


# This target runs tests inside a Docker container for a specific Python version and runtime.
docker-test:
	@set -e;
	@echo -e "$(BOLD_YELLOW)\n======== ● Testing OpenCrate in Docker ========$(RESET)"
	@echo -e "$(BOLD_ORANGE)- Python: $(BOLD)$(PYTHON_VERSION)$(RESET)"
	@echo -e "$(BOLD_ORANGE)- Runtime: $(BOLD)$(RUNTIME)$(RESET)"
	@echo -e "$(BOLD_ORANGE)- Dependencies: $(BOLD)$(DEPS)$(RESET)\n"
	IMAGE_TAG="braindotai/opencrate-$(RUNTIME)-py$(PYTHON_VERSION):$(VERSION)"; \
	LOG_FILE="tests/logs/test-py$(PYTHON_VERSION)-$(RUNTIME).log"; \
	mkdir -p tests/logs; \
	echo -e "$(BOLD_ORANGE)- Image: $(BOLD)$$IMAGE_TAG$(RESET)"; \
	echo -e "$(BOLD_ORANGE)- Log file: $(BOLD)$$LOG_FILE$(RESET)\n"; \
	if [ -t 0 ]; then \
		TTY_FLAG="-it"; \
	else \
		TTY_FLAG=""; \
	fi; \
	echo -e "$(BOLD_YELLOW)▶ Starting Docker container...$(RESET)"; \
	docker run --rm $$TTY_FLAG \
		-v $(shell pwd)/tests:/home/opencrate/tests \
		-v $(shell pwd)/src:/home/opencrate/src \
		-v $(shell pwd)/Makefile:/home/opencrate/Makefile:ro \
		-v $(shell pwd)/pyproject.toml:/home/opencrate/pyproject.toml:ro \
		-v $(shell pwd)/Makefile.ci:/home/opencrate/Makefile.ci:ro \
		-w /home/opencrate \
		$$IMAGE_TAG \
		sh -c 'set -e && \
			echo "$(BOLD_BLUE)▶ Installing dependencies...$(RESET)" && \
			pip install pip --quiet --upgrade --root-user-action=ignore && \
			pip install .[$(DEPS)] --quiet --extra-index-url https://download.pytorch.org/whl/cpu --root-user-action=ignore && \
			echo "\n$(BOLD_BLUE)▶ Running tests...$(RESET)" && \
			if [ "$(DEPS)" = "ci" ]; then \
				make test-ruff test-pytest; \
			else \
				make test-all; \
			fi' | tee $$LOG_FILE; \
	if [ $${PIPESTATUS[0]} -ne 0 ]; then \
		echo -e "\n$(BOLD_RED)======== ✗ Tests failed ========$(RESET)"; \
		echo -e "$(BOLD_RED)Check log file: $$LOG_FILE$(RESET)\n"; \
		exit 1; \
	fi; \
	echo -e "\n$(GREEN)Log saved to: $$LOG_FILE$(RESET)"
	echo -e "$(BOLD_GREEN)======== ✓ Tests completed successfully ========$(RESET)"; \

docker-test-all:
	@echo -e "$(BOLD_YELLOW)\n======== ● Testing OpenCrate in Docker Versions ========$(RESET)"
	@RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	echo -e "$(BOLD_BLUE)- Python versions: $(PYTHON_VERSIONS_LIST)$(RESET)"; \
	echo -e "$(BOLD_BLUE)- Runtimes: $$RUNTIMES_TO_USE$(RESET)"; \
	for python_version in $(PYTHON_VERSIONS_LIST); do \
		for runtime in $$RUNTIMES_TO_USE; do \
			make docker-test PYTHON_VERSION=$$python_version RUNTIME=$$runtime; \
		done; \
	done; \
	echo -e "$(BOLD_GREEN)======== ✓ All Docker tests completed successfully! ========$(RESET)\n";


help:
	@BOLD=$$(printf "\033[1m"); RESET=$$(printf "\033[0m"); BOLD_BLUE=$$(printf "\033[36m"); YELLOW=$$(printf "\033[33m"); GREEN=$$(printf "\033[32m"); \
	printf "\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "                  $${BOLD_BLUE}$${BOLD} OpenCrate Development Makefile $${RESET}\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "\n"; \
	printf "$${BOLD} Usage:$${RESET} make [target] [VARIABLE=value]\n"; \
	printf "\n"; \
	printf "$${BOLD} Available Variables:$${RESET}\n"; \
	printf "  $${BOLD_BLUE} PYTHON_VERSION $${RESET}   Python version to use (default: $${YELLOW}$(PYTHON_VERSION)$${RESET})\n"; \
	printf "  $${BOLD_BLUE} RUNTIME        $${RESET}   Runtime type: cpu or cuda\n"; \
	printf "  $${BOLD_BLUE} VERSION        $${RESET}   Project version (default: $${YELLOW}$(VERSION)$${RESET})\n"; \
	printf "  $${BOLD_BLUE} REBUILD_FLAG   $${RESET}   Force rebuild of base layers: true/false\n"; \
	printf "\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "                    $${GREEN} Development Environment $${RESET}\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "\n"; \
	printf "  $${YELLOW} start $${RESET}         Start the development Docker container in detached mode\n"; \
	printf "                  Uses docker-compose to launch the opencrate_dev service\n"; \
	printf "                  Example: make start\n"; \
	printf "\n"; \
	printf "  $${YELLOW} enter $${RESET}           Open an interactive shell inside the running container\n"; \
	printf "                  Provides zsh shell access to the development environment\n"; \
	printf "                  Example: make enter\n"; \
	printf "\n"; \
	printf "  $${YELLOW} stop $${RESET}            Stop the running development container gracefully\n"; \
	printf "                  Preserves container state for later restart\n"; \
    printf "                  Example: make stop\n"; \
    printf "\n"; \
    printf "  $${YELLOW} kill $${RESET}            Stop and completely remove the development container\n"; \
    printf "                  Destroys all container state and volumes\n"; \
    printf "                  Example: make kill\n"; \
    printf "\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "                    $${GREEN} Package Installation & Setup $${RESET}\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "\n"; \
    printf "  $${YELLOW} install $${RESET}         Complete development setup: install package + Python versions\n"; \
    printf "                  Combines install-dev-package and install-dev-versions\n"; \
    printf "                  Example: make install\n"; \
    printf "\n"; \
    printf "  $${YELLOW} install-dev-package $${RESET}\n"; \
    printf "                  Install the OpenCrate package in editable mode with dev dependencies\n"; \
    printf "                  Uses pip to install the current project in development mode\n"; \
    printf "                  Example: make install-dev-package\n"; \
    printf "\n"; \
    printf "  $${YELLOW} install-dev-versions $${RESET}\n"; \
    printf "                  Install multiple Python versions (3.7-3.13) using pyenv\n"; \
    printf "                  Sets up multi-version testing environment\n"; \
    printf "                  Example: make install-dev-versions\n"; \
    printf "\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "                    $${GREEN} Testing & Code Quality $${RESET}\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test $${RESET}            Run complete test suite: ruff + mypy + pytest\n"; \
    printf "                  Comprehensive testing for the current environment\n"; \
    printf "                  Example: make test\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test-ruff $${RESET}       Run ruff linter for code style and quality checks\n"; \
    printf "                  Excludes tests/pipelines directory\n"; \
    printf "                  Example: make test-ruff\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test-mypy $${RESET}       Run mypy for static type checking\n"; \
    printf "                  Validates type annotations and catches type errors\n"; \
    printf "                  Example: make test-mypy\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test-pytest $${RESET}     Run unit tests with pytest\n"; \
    printf "                  Sets PYTHONPATH=src for proper imports\n"; \
    printf "                  Example: make test-pytest\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test-tox $${RESET}        Run tests across all supported Python versions using tox\n"; \
    printf "                  Multi-environment testing for compatibility\n"; \
    printf "                  Example: make test-tox\n"; \
    printf "\n"; \
    printf "  $${YELLOW} test-clean $${RESET}      Remove all testing cache files and artifacts\n"; \
    printf "                  Cleans .mypy_cache, .pytest_cache, .ruff_cache, .tox, .coverage\n"; \
    printf "                  Example: make test-clean\n"; \
    printf "\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "                    $${GREEN} Docker Image Management $${RESET}\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "\n"; \
    printf "  $${YELLOW} docker-generate $${RESET} Generate Dockerfiles for all supported Python versions and runtimes\n"; \
    printf "                  Creates dockerfiles in ./docker/dockerfiles/ directory\n"; \
    printf "                  Example: make docker-generate\n"; \
    printf "                  Example: make docker-generate PYTHON_VERSIONS=\"3.10 3.11\" RUNTIMES=\"cpu\"\n"; \
    printf "\n"; \
    printf "  $${YELLOW} docker-build $${RESET}    Build all Docker images locally for all supported configurations\n"; \
    printf "                  Builds images for all Python versions (3.7-3.13) and runtimes (cpu/cuda)\n"; \
    printf "                  Example: make docker-build\n"; \
    printf "                  Example: make docker-build PYTHON_VERSIONS=\"3.11\" RUNTIMES=\"cpu\"\n"; \
    printf "\n"; \
    printf "  $${YELLOW} docker-test $${RESET}     Run tests inside a Docker container for specific configuration\n"; \
    printf "                  Tests a specific Python version and runtime combination\n"; \
    printf "                  Example: make docker-test PYTHON_VERSION=3.11 RUNTIME=cpu\n"; \
    printf "                  Example: make docker-test PYTHON_VERSION=3.9 RUNTIME=cuda\n"; \
    printf "\n"; \
    printf "  $${YELLOW} docker-clean $${RESET}    Clean up Docker build cache, containers, and unused images\n"; \
    printf "                  Removes dangling containers, build cache, and unused images\n"; \
    printf "                  Example: make docker-clean\n"; \
    printf "\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "                    $${GREEN} Documentation & Utilities $${RESET}\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "\n"; \
    printf "  $${YELLOW} mkdocs $${RESET}          Serve project documentation locally using MkDocs\n"; \
    printf "                  Accessible at http://0.0.0.0:8000\n"; \
    printf "                  Example: make mkdocs\n"; \
    printf "\n"; \
    printf "  $${YELLOW} help $${RESET}            Display this comprehensive help message\n"; \
    printf "                  Shows all available targets with descriptions and examples\n"; \
    printf "                  Example: make help\n"; \
    printf "\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "                    $${GREEN} Common Usage Patterns $${RESET}\n"; \
    printf "$${BOLD}====================================================================$${RESET}\n"; \
    printf "\n"; \
    printf "  $${BOLD} Development Setup: $${RESET}\n"; \
    printf "    make start                       # Start development container\n"; \
    printf "    make enter                       # Enter container for development\n"; \
    printf "    make install                     # Install entire project requirements for development\n"; \
    printf "\n"; \
    printf "  $${BOLD} Local Testing: $${RESET}\n"; \
    printf "    make test                        # Run all tests locally\n"; \
    printf "    make test-tox                    # Test across Python versions\n"; \
    printf "    make docker-test PYTHON_VERSION=3.11 RUNTIME=cpu  # Test in container\n"; \
    printf "\n"; \
    printf "  $${BOLD} Docker Operations: $${RESET}\n"; \
    printf "    make docker-build                # Build all images\n"; \
    printf "    make docker-clean                # Clean up Docker resources\n"; \
    printf "\n"; \
    printf "  $${BOLD} CI/CD (GitHub Actions): $${RESET}\n"; \
    printf "    make ci-build-test RUNTIME=cpu PYTHON_VERSION=3.11 VERSION=main\n"; \
    printf "    make ci-push RUNTIME=cpu PYTHON_VERSION=3.11 VERSION=main REBUILD_FLAG=true\n"; \
    printf "    make ci-release VERSION=1.0.0\n"; \
    printf "\n"; \
    printf "\n"


# importing targets from external source
ci-%:
	@make -f Makefile.ci $*