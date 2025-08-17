SHELL := /bin/bash
PYTHON_VERSION ?= 3.10
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

VERSION ?= $(shell cat VERSION | tr -d '\n')

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
	echo -e "\nDone installing the package with development environment and dependencies"


install: install-dev-package install-dev-versions


mkdocs:
	mkdocs serve -a 0.0.0.0:8000


test-ruff:
	@ruff check src tests --exclude tests/pipelines


test-mypy:
	@mypy src tests --exclude tests/pipelines


test-pytest:
	@PYTHONPATH=src pytest


test: test-ruff test-mypy test-pytest


test-tox:
	@tox


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
	echo -e "\n======== ✔ All Dockerfiles generated successfully ========\n"


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
	echo -e "\n======== ✔ All local images built successfully! ========\n";


# This target cleans up all Docker-related caches and unused images.
docker-clean:
	@echo "Cleaning container cache"; \
	docker container prune -f; \
	echo "Cleaning buildx cache"; \
	docker buildx prune -f; \
	echo "Cleaning image cache"; \
	docker image prune -f;


# This target runs tests inside a Docker container for a specific Python version and runtime.
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
	echo -e "\n======== ✔ Tests completed successfully. Log saved to: $$LOG_FILE ========\n"


help:
	@echo ""
	@echo "===================================================================="
	@echo "                  OpenCrate Development Makefile" 
	@echo "===================================================================="
	@echo ""
	@echo "Usage: make [target] [VARIABLE=value]"
	@echo ""
	@echo "Available Variables:"
	@echo "  PYTHON_VERSION    Python version to use (default: $(PYTHON_VERSION))"
	@echo "  RUNTIME           Runtime type: cpu or cuda"
	@echo "  VERSION           Project version (default: $(VERSION))"
	@echo "  REBUILD_FLAG      Force rebuild of base layers: true/false"
	@echo ""
	@echo "===================================================================="
	@echo "                    Development Environment"
	@echo "===================================================================="
	@echo ""
	@echo "  start           Start the development Docker container in detached mode"
	@echo "                  Uses docker-compose to launch the opencrate_dev service"
	@echo "                  Example: make start"
	@echo ""
	@echo "  enter           Open an interactive shell inside the running container"
	@echo "                  Provides zsh shell access to the development environment"
	@echo "                  Example: make enter"
	@echo ""
	@echo "  stop            Stop the running development container gracefully"
	@echo "                  Preserves container state for later restart"
	@echo "                  Example: make stop"
	@echo ""
	@echo "  kill            Stop and completely remove the development container"
	@echo "                  Destroys all container state and volumes"
	@echo "                  Example: make kill"
	@echo ""
	@echo "===================================================================="
	@echo "                    Package Installation & Setup"
	@echo "===================================================================="
	@echo ""
	@echo "  install         Complete development setup: install package + Python versions"
	@echo "                  Combines install-dev-package and install-dev-versions"
	@echo "                  Example: make install"
	@echo ""
	@echo "  install-dev-package"
	@echo "                  Install the OpenCrate package in editable mode with dev dependencies"
	@echo "                  Uses pip to install the current project in development mode"
	@echo "                  Example: make install-dev-package"
	@echo ""
	@echo "  install-dev-versions"
	@echo "                  Install multiple Python versions (3.7-3.13) using pyenv"
	@echo "                  Sets up multi-version testing environment"
	@echo "                  Example: make install-dev-versions"
	@echo ""
	@echo "===================================================================="
	@echo "                    Testing & Code Quality"
	@echo "===================================================================="
	@echo ""
	@echo "  test            Run complete test suite: ruff + mypy + pytest"
	@echo "                  Comprehensive testing for the current environment"
	@echo "                  Example: make test"
	@echo ""
	@echo "  test-ruff       Run ruff linter for code style and quality checks"
	@echo "                  Excludes tests/pipelines directory"
	@echo "                  Example: make test-ruff"
	@echo ""
	@echo "  test-mypy       Run mypy for static type checking"
	@echo "                  Validates type annotations and catches type errors"
	@echo "                  Example: make test-mypy"
	@echo ""
	@echo "  test-pytest     Run unit tests with pytest"
	@echo "                  Sets PYTHONPATH=src for proper imports"
	@echo "                  Example: make test-pytest"
	@echo ""
	@echo "  test-tox        Run tests across all supported Python versions using tox"
	@echo "                  Multi-environment testing for compatibility"
	@echo "                  Example: make test-tox"
	@echo ""
	@echo "  test-clean      Remove all testing cache files and artifacts"
	@echo "                  Cleans .mypy_cache, .pytest_cache, .ruff_cache, .tox, .coverage"
	@echo "                  Example: make test-clean"
	@echo ""
	@echo "===================================================================="
	@echo "                    Docker Image Management"
	@echo "===================================================================="
	@echo ""
	@echo "  docker-generate Generate Dockerfiles for all supported Python versions and runtimes"
	@echo "                  Creates dockerfiles in ./docker/dockerfiles/ directory"
	@echo "                  Example: make docker-generate"
	@echo "                  Example: make docker-generate PYTHON_VERSIONS=\"3.10 3.11\" RUNTIMES=\"cpu\""
	@echo ""
	@echo "  docker-build    Build all Docker images locally for all supported configurations"
	@echo "                  Builds images for all Python versions (3.7-3.13) and runtimes (cpu/cuda)"
	@echo "                  Example: make docker-build"
	@echo "                  Example: make docker-build PYTHON_VERSIONS=\"3.11\" RUNTIMES=\"cpu\""
	@echo ""
	@echo "  docker-test     Run tests inside a Docker container for specific configuration"
	@echo "                  Tests a specific Python version and runtime combination"
	@echo "                  Example: make docker-test PYTHON_VERSION=3.11 RUNTIME=cpu"
	@echo "                  Example: make docker-test PYTHON_VERSION=3.9 RUNTIME=cuda"
	@echo ""
	@echo "  docker-clean    Clean up Docker build cache, containers, and unused images"
	@echo "                  Removes dangling containers, build cache, and unused images"
	@echo "                  Example: make docker-clean"
	@echo ""
	@echo "===================================================================="
	@echo "                    Documentation & Utilities"
	@echo "===================================================================="
	@echo ""
	@echo "  mkdocs          Serve project documentation locally using MkDocs"
	@echo "                  Accessible at http://0.0.0.0:8000"
	@echo "                  Example: make mkdocs"
	@echo ""
	@echo "  help            Display this comprehensive help message"
	@echo "                  Shows all available targets with descriptions and examples"
	@echo "                  Example: make help"
	@echo ""
	@echo "===================================================================="
	@echo "                    Common Usage Patterns"
	@echo "===================================================================="
	@echo ""
	@echo "  Development Setup:"
	@echo "    make start                       # Start development container"
	@echo "    make enter                       # Enter container for development"
	@echo "    make install                     # Install entire project requirements for development"
	@echo ""
	@echo "  Local Testing:"
	@echo "    make test                        # Run all tests locally"
	@echo "    make test-tox                    # Test across Python versions"
	@echo "    make docker-test PYTHON_VERSION=3.11 RUNTIME=cpu  # Test in container"
	@echo ""
	@echo "  Docker Operations:"
	@echo "    make docker-build                # Build all images"
	@echo "    make docker-clean               # Clean up Docker resources"
	@echo ""
	@echo "  CI/CD (GitHub Actions):"
	@echo "    make ci-build-test RUNTIME=cpu PYTHON_VERSION=3.11 VERSION=main"
	@echo "    make ci-push RUNTIME=cpu PYTHON_VERSION=3.11 VERSION=main REBUILD_FLAG=true"
	@echo "    make ci-release VERSION=1.0.0"
	@echo ""
	@echo ""



# importing targets from external source
ci-%:
	@make -f Makefile.ci $*