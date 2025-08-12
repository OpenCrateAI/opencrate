PYTHON_VERSION ?= 3.10
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)
VERSION ?= $(shell cat VERSION | tr -d '\n')
DOCKER_BUILD_ARGS ?=

.SILENT:
.ONESHELL:


build-generate:
	@echo "======== ● Generating all Dockerfiles ========"
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"
	@mkdir -p ./docker/dockerfiles
	@for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			python3.10 docker/dockerfile.py --generate --python=$$python_version --runtime=$$runtime; \
		done; \
	done
	@echo "\n======== ✔ All Dockerfiles generated successfully ========\n"


build-opencrate:
	@python3.10 docker/dockerfile.py --generate --build --python=$${python:-3.10} --runtime=$${runtime:-cpu} --build-args="$(DOCKER_BUILD_ARGS)" --log-level=DEBUG


build-opencrate-all: build-generate
	@echo "======== ● Building all OpenCrate images locally for all supported versions ========"
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			python3.10 docker/dockerfile.py --build --python=$$python_version --runtime=$$runtime --build-args="$(DOCKER_BUILD_ARGS)" --log-level=DEBUG; \
		done; \
	done; \
	echo "\n======== ✔ All local images built successfully! ========\n";


build-clean-all:
	echo "Cleaning container cache"; \
	docker container prune -f;
	echo "Cleaning buildx cache"; \
	docker buildx prune -f;
	echo "Cleaning image cache"; \
	docker image prune -f;


gh-build-opencrate-all: generate-dockerfiles
	@echo "======== ● Building all OpenCrate images for Docker Registry for version $(VERSION) ========..."
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"
	@for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			echo "-------- ● Building & Pushing: Python $$python_version, Runtime $$runtime --------"; \
			python3.10 docker/dockerfile.py --build --python=$$python_version --runtime=$$runtime --build-args="$(DOCKER_BUILD_ARGS)" \
			|| (echo "-------- ✗ Error: Failed to build and push in CI --------" && exit 1); \
		done; \
	done;
	@echo "\n======== ● All images have been built for Docker Registry for version $(VERSION) ========\n";

gh-tag-latest:
	@echo "Tagging 'latest' for all images with version $(VERSION)..."
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			IMAGE_TAG="braindotai/opencrate-$$runtime-py$$python_version:$(VERSION)"; \
			LATEST_TAG="braindotai/opencrate-$$runtime-py$$python_version:latest"; \
			echo "Tagging ${IMAGE_TAG} as ${LATEST_TAG}"; \
			docker buildx imagetools create -t ${LATEST_TAG} ${IMAGE_TAG}; \
		done; \
	done;


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


test-ruff:
	@ruff check src


test-mypy:
	@mypy src


test: test-pytest test-ruff test-mypy


test-all:
	@tox


help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets for CI/CD:"
	@echo "  build-opencrate-all   			Build all production images with buildx"
	@echo "  push-opencrate-all    			Push all versioned images to the registry"
	@echo ""
	@echo "Targets for Local Development:"
	@echo "  build-opencrate 			Build a single image locally (e.g., make build-opencrate python=3.12 runtime=cuda)"
	@echo "  build-opencrate-all   	Build all images locally for all supported Python versions"
	@echo "  start           				Start the development container"
	@echo "  enter           				Enter the development container"
	@echo "  stop            				Stop the development container"
	@echo "  kill            				Remove the development container"
	@echo "  test-pytest     				Run pytest - for unit tests"
	@echo "  test-ruff       				Run ruff - for code formatting"
	@echo "  test-mypy       				Run mypy - for static type checking"
	@echo "  test            				Run all tests - pytest, ruff, mypy"
	@echo "  test-all        				Run all tests with tox for multiple Python versions"
	@echo "  help            				Show this help message"