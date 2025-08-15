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
	echo "\nDone installing the package with development environment and dependencies"


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
	@echo "======== ● Generating all Dockerfiles ========"
	@PYTHON_VERSIONS_TO_USE="$${PYTHON_VERSIONS:-3.7 3.8 3.9 3.10 3.11 3.12 3.13}"; \
	RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	mkdir -p ./docker/dockerfiles; \
	for python_version in $$PYTHON_VERSIONS_TO_USE; do \
		for runtime in $$RUNTIMES_TO_USE; do \
			python3.10 docker/dockerfile.py --generate --python=$$python_version --runtime=$$runtime; \
		done; \
	done
	@echo "\n======== ✔ All Dockerfiles generated successfully ========\n"


# This target builds all supported OpenCrate images locally for all Python versions and runtimes.
docker-build: docker-generate
	@echo "======== ● Building all OpenCrate images locally for all supported versions ========"
	@PYTHON_VERSIONS_TO_USE="$${PYTHON_VERSIONS:-3.7 3.8 3.9 3.10 3.11 3.12 3.13}"; \
	RUNTIMES_TO_USE="$${RUNTIMES:-cpu cuda}"; \
	for python_version in $$PYTHON_VERSIONS_TO_USE; do \
		for runtime in $$RUNTIMES_TO_USE; do \
			python3.10 docker/dockerfile.py --build --python=$$python_version --runtime=$$runtime --log-level=DEBUG; \
		done; \
	done; \
	echo "\n======== ✔ All local images built successfully! ========\n";


# This target cleans up all Docker-related caches and unused images.
docker-clean:
	@echo "Cleaning container cache"; \
	docker container prune -f; \
	echo "Cleaning buildx cache"; \
	docker buildx prune -f; \
	echo "Cleaning image cache"; \
	docker image prune -f;


# This target is used in github actions to build a single image for CI/CD. Used in the matrix parallel builds.
ci-build:
	@set -e
	@echo "--- Building: Runtime=$(RUNTIME), Python=$(PYTHON_VERSION), Version=$(VERSION) ---"

	FINAL_IMAGE_TAG="braindotai/opencrate-$(RUNTIME)-py$(PYTHON_VERSION):$(VERSION)"
	DOCKERFILE_PATH="./docker/dockerfiles/Dockerfile.$(RUNTIME)-py$(PYTHON_VERSION)"

	echo "Image Tag: $$FINAL_IMAGE_TAG"
	echo "Dockerfile: $$DOCKERFILE_PATH"
	echo "Remote Cache: $$CACHE_IMAGE_VAR"

	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-f "$$DOCKERFILE_PATH" \
		-t "$$FINAL_IMAGE_TAG" \
		--push \
		--progress=plain \
		.

	@echo "--- ✔ Successfully built and pushed $$FINAL_IMAGE_TAG ---"


# This target pushes the images as the latest tag to the registry. Used in the CI/CD workflow if new git tag is created.
ci-release:
	@echo "Tagging 'latest' for all images with version $(VERSION)..."
	@set -e; \
	PYTHON_VERSIONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$PYTHON_VERSIONS; do \
		for runtime in cpu cuda; do \
			IMAGE_TAG="braindotai/opencrate-$$runtime-py$$python_version:$(VERSION)"; \
			LATEST_TAG="braindotai/opencrate-$$runtime-py$$python_version:latest"; \
			echo "Tagging $$IMAGE_TAG as $$LATEST_TAG"; \
			docker buildx imagetools create -t "$$LATEST_TAG" "$$IMAGE_TAG"; \
		done; \
	done; \
	echo "✔ All images tagged as latest"


docker-test:
	@echo "======== ● Testing OpenCrate in Docker for Python $(PYTHON_VERSION) and runtime $(RUNTIME) ========"
	@set -e
	IMAGE_TAG="braindotai/opencrate-$(RUNTIME)-py$(PYTHON_VERSION):v$(VERSION)"
	LOG_FILE="tests/logs/test-py$(PYTHON_VERSION)-$(RUNTIME).log"
	mkdir -p tests/logs

	@echo "--- Running tests in Docker container from image: $$IMAGE_TAG ---"
	@echo "--- Log file: $$LOG_FILE ---"
	docker run --rm \
		-v $(shell pwd)/tests:/home/opencrate/tests \
		-v $(shell pwd)/Makefile:/home/opencrate/Makefile:ro \
		-w /home/opencrate \
		$$IMAGE_TAG \
		sh -c 'pip install pytest pytest-cov && make test-pytest' > $$LOG_FILE 2>&1 || (cat $$LOG_FILE && exit 1)
	
	@echo "======== ✔ Test finished successfully. ========"


help:
	@echo "OpenCrate Project Makefile"
	@echo ""
	@echo "Usage: make [target] [ARG=value]"
	@echo ""
	@echo "-----------------------------------------"
	@echo "Local Development Environment"
	@echo "-----------------------------------------"
	@echo "  start             Start the development Docker container in detached mode."
	@echo "  enter             Get a shell inside the running development container."
	@echo "  stop              Stop the development container."
	@echo "  kill              Stop and remove the development container and its resources."
	@echo ""
	@echo "-----------------------------------------"
	@echo "Docker Image Management"
	@echo "-----------------------------------------"
	@echo "  docker-generate   Generate all Dockerfiles for supported Python versions and runtimes."
	@echo "                    Example: make docker-generate PYTHON_VERSIONS=\"3.10 3.11\""
	@echo "  docker-build      Build all Docker images locally based on the generated files."
	@echo "                    Example: make docker-build RUNTIMES=cpu"
	@echo "  docker-clean      Clean up Docker build cache, dangling images, and containers."
	@echo "  docker-test       Run tox tests inside a Docker container for a specific Python version and runtime."
	@echo "                    Example: make docker-test PYTHON_VERSION=3.9 RUNTIME=cpu"
	@echo ""
	@echo "-----------------------------------------"
	@echo "Testing and Linting"
	@echo "-----------------------------------------"
	@echo "  test              Run all primary tests (ruff, mypy, pytest) for the current environment."
	@echo "  test-ruff         Run ruff linter."
	@echo "  test-mypy         Run mypy for static type checking."
	@echo "  test-pytest       Run unit tests with pytest."
	@echo "  test-tox          Run tests against all supported Python versions using tox."
	@echo "  test-clean        Remove cache files generated by testing tools."
	@echo ""
	@echo "-----------------------------------------"
	@echo "Installation & Setup"
	@echo "-----------------------------------------"
	@echo "  install           Install the project in editable mode and required Python versions."
	@echo "  install-dev-package Install the project package in editable mode with dev dependencies."
	@echo "  install-dev-versions Install multiple Python versions using pyenv."
	@echo ""
	@echo "-----------------------------------------"
	@echo "CI/CD (For GitHub Actions)"
	@echo "-----------------------------------------"
	@echo "  ci-build          Build and push a single Docker image. (Internal use for CI)"
	@echo "                    Requires RUNTIME, PYTHON_VERSION, and VERSION variables."
	@echo "  ci-release        Tag versioned images as 'latest'. (Internal use for CI)"
	@echo ""
	@echo "-----------------------------------------"
	@echo "Documentation"
	@echo "-----------------------------------------"
	@echo "  mkdocs            Serve the project documentation locally on http://0.0.0.0:8000."
	@echo ""
	@echo "-----------------------------------------"
	@echo "Miscellaneous"
	@echo "-----------------------------------------"
	@echo "  help              Show this help message."
	@echo ""