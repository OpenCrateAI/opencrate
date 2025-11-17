SHELL := /bin/bash
PYTHON_VERSION ?= 3.10
RUNTIME ?= cuda
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

VERSION ?= $(shell cat VERSION | tr -d '\n')

MAKEFLAGS += --no-print-directory

.SILENT:
.ONESHELL:


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


install-dev-package:
	@python3.10 -m pip install --upgrade pip --root-user-action=ignore
	@python3.10 -m pip install -e ".[dev]" --root-user-action=ignore


install-dev-versions:
	@PYTHON_VERSIONS="3.7 3.8 3.9 3.11 3.12 3.13"; \
	echo "Installing Python versions: $$PYTHON_VERSIONS"; \
	for version in $$PYTHON_VERSIONS; do \
		if ! pyenv versions --bare | grep -q "^$$version\\."; then \
			pyenv install $$version; \
		fi; \
	done; \
	pyenv local $$PYTHON_VERSIONS
	pre-commit install
	echo -e "\nDone installing the package with development environment and dependencies"


install: install-dev-package install-dev-versions


mkdocs:
	python$(PYTHON_VERSION) -m mkdocs serve -a 0.0.0.0:8789


test-ruff:
	@echo -e "\nRunning ruff linter..."
	@ruff check . --fix


test-mypy:
	@echo -e "\nRunning mypy type checks..."
	@mypy --pretty


test-pytest:
	@echo -e "\nRunning pytest unit tests..."
	@pytest

test-tox:
	@tox

test: test-ruff test-mypy test-pytest

test-clean:
	@rm -rf .mypy_cache .pytest_cache .ruff_cache .tox .coverage

# This target generates Dockerfiles for all supported Python versions and runtimes.
docker-generate:
	@set -e; \
	echo -e "\n======== ● Generating all Dockerfiles ========\n"
	@PYTHON_VERSIONS_TO_USE="$${PYTHON_VERSIONS:-3.7 3.8 3.9 3.10 3.11 3.12 3.13}"; \
	RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	mkdir -p ./docker/dockerfiles; \
	for python_version in $$PYTHON_VERSIONS_TO_USE; do \
		for runtime in $$RUNTIMES_TO_USE; do \
			python3.10 docker/dockerfile.py --generate --python=$$python_version --runtime=$$runtime; \
		done; \
	done; \
	echo -e "\n======== ✓ All Dockerfiles generated successfully ========\n"


# This target builds all supported OpenCrate images locally for all Python versions and runtimes.
docker-build: docker-generate
	@set -e; \
	echo -e "\n======== ● Building all OpenCrate images locally for all supported versions ========\n"
	@PYTHON_VERSIONS_TO_USE="$${PYTHON_VERSIONS:-3.7 3.8 3.9 3.10 3.11 3.12 3.13}"; \
	RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	for python_version in $$PYTHON_VERSIONS_TO_USE; do \
		for runtime in $$RUNTIMES_TO_USE; do \
			python3.10 docker/dockerfile.py --build --python=$$python_version --runtime=$$runtime --log-level=DEBUG; \
		done; \
	done; \
	echo -e "\n======== ✓ All local images built successfully! ========\n";


# This target cleans up all Docker-related caches and unused images.
docker-clean:
	@echo "Cleaning container cache"; \
	docker container prune -f; \
	echo "Cleaning buildx cache"; \
	docker buildx prune -f; \
	echo "Cleaning image cache"; \
	docker image prune -f;


# This target runs tests inside a Docker container for a specific Python version and runtime.
# must be run outside of opencrate's development environment
docker-test:
	@set -e; \
	echo -e "\n======== ● Testing OpenCrate in Docker for Python $(PYTHON_VERSION) and runtime $(RUNTIME) ========\n"
	IMAGE_TAG="braindotai/opencrate-$(RUNTIME)-py$(PYTHON_VERSION):$(VERSION)"; \
	LOG_FILE="tests/logs/test-py$(PYTHON_VERSION)-$(RUNTIME).log"; \
	mkdir -p tests/logs; \
	echo "--- Running tests in Docker container from image: $$IMAGE_TAG ---"; \
	echo "--- Log file: $$LOG_FILE ---"; \
	docker run --rm \
		-v $(shell pwd)/tests:/home/opencrate/tests \
		-v $(shell pwd)/src:/home/opencrate/src \
		-v $(shell pwd)/Makefile:/home/opencrate/Makefile:ro \
		-v $(shell pwd)/Makefile.ci:/home/opencrate/Makefile.ci:ro \
		-w /home/opencrate \
		$$IMAGE_TAG \
		sh -c 'set -e && \
			echo "--- Installing test dependencies ---" && \
			pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu --root-user-action=ignore && \
			pip install --quiet pytest pytest-cov --root-user-action=ignore && \
			echo "\nRunning tests..." && \
			make test-pytest' | tee $$LOG_FILE; \
	if [ $${PIPESTATUS[0]} -ne 0 ]; then \
		echo "!!!!!!!!!! ❌ Tests failed. Check log file: $$LOG_FILE" !!!!!!!!!!; \
		exit 1; \
	fi; \
	echo -e "\n======== ✓ Tests completed successfully. Log saved to: $$LOG_FILE ========\n"

# must be run outside of opencrate's development environment
docker-test-all:
	@set -e;
	@PYTHON_VERSIONS_TO_USE="3.7 3.8 3.9 3.10 3.11 3.12 3.13"; \
	RUNTIMES_TO_USE="cpu cuda"; \
	for python_version in $$PYTHON_VERSIONS_TO_USE; do \
		for runtime in $$RUNTIMES_TO_USE; do \
			make docker-test PYTHON_VERSION=$$python_version RUNTIME=$$runtime; \
		done; \
	done; \
	echo -e "\n======== ✓ All Docker tests completed successfully! ========\n";


help:
	@BOLD=$$(printf "\033[1m"); RESET=$$(printf "\033[0m"); CYAN=$$(printf "\033[36m"); YELLOW=$$(printf "\033[33m"); GREEN=$$(printf "\033[32m"); \
	printf "\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "                  $${CYAN}$${BOLD} OpenCrate Development Makefile $${RESET}\n"; \
	printf "$${BOLD}====================================================================$${RESET}\n"; \
	printf "\n"; \
	printf "$${BOLD} Usage:$${RESET} make [target] [VARIABLE=value]\n"; \
	printf "\n"; \
	printf "$${BOLD} Available Variables:$${RESET}\n"; \
	printf "  $${CYAN} PYTHON_VERSION $${RESET}   Python version to use (default: $${YELLOW}$(PYTHON_VERSION)$${RESET})\n"; \
	printf "  $${CYAN} RUNTIME        $${RESET}   Runtime type: cpu or cuda\n"; \
	printf "  $${CYAN} VERSION        $${RESET}   Project version (default: $${YELLOW}$(VERSION)$${RESET})\n"; \
	printf "  $${CYAN} REBUILD_FLAG   $${RESET}   Force rebuild of base layers: true/false\n"; \
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