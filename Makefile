PYTHON_VERSION ?= 3.10
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

# Allow VERSION to be overridden by the CI environment (from git tag)
# Otherwise, fall back to the VERSION file
VERSION ?= $(shell cat VERSION | tr -d '\n')

# Allow DOCKER_BUILD_ARGS to be passed in from the CI environment for caching
DOCKER_BUILD_ARGS ?=

.SILENT:
.ONESHELL:

build-opencrate-local:
	@python3.10 docker/dockerfile.py --python=${python:-3.10} --runtime=${runtime:-cpu}

build-opencrate-local-all:
	@echo "Building all OpenCrate images locally for all supported versions..."
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			python3.10 docker/dockerfile.py --python=$$python_version --runtime=$$runtime; \
		done; \
	done; \
	echo "\n--- All local images built successfully! ---"; \

build-clean-local-all:
	echo "Cleaning container cache"; \
	docker container prune -f;
	echo "Cleaning buildx cache"; \
	docker buildx prune -f;
	echo "Cleaning image cache"; \
	docker image prune -f;

build-opencrate-all:
	@echo "Building all OpenCrate images for version v$(VERSION)..."
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"

	# --- STAGE 1: Build and load ALL base images first ---
	# This ensures they are available locally before the app images try to use them.
	@echo "\n--- Building all required base images ---"
	@for runtime in cpu cuda; do \
		echo "\n--- Building base image for runtime: $$runtime ---"; \
		# Make sure this path is correct, e.g., docker/dockerfile.py
		python3 docker/dockerfile.py --python=3.10 --runtime=$$runtime --generate-only; \
		\
		# FIX: Use the full repository name here to match the FROM line in the next stage.
		BASE_IMAGE_TAG="braindotai/opencrate-base-$$runtime:v$(VERSION)"; \
		\
		# Make sure this path is correct, e.g., docker/dockerfiles/
		DOCKERFILE_BASE_PATH="./docker/dockerfiles/Dockerfile.base-$$runtime"; \
		\
		docker buildx build --platform linux/amd64 -f $$DOCKERFILE_BASE_PATH -t $$BASE_IMAGE_TAG --load $(DOCKER_BUILD_ARGS) .; \
		echo "\n-- Successfully built and loaded base image: $$BASE_IMAGE_TAG --"; \
	done

	# --- STAGE 2: Now that all base images are loaded, build all app images ---
	@echo "\n--- Building all application images ---"
	@for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			echo "\n--- Building for Python $$python_version, Runtime $$runtime ---"; \
			# Make sure this path is correct
			python3 docker/dockerfile.py --python=$$python_version --runtime=$$runtime --generate-only; \
			\
			FINAL_IMAGE_TAG="braindotai/opencrate-$$runtime-py$$python_version:v$(VERSION)"; \
			\
			# Make sure this path is correct
			DOCKERFILE_APP_PATH="./docker/dockerfiles/Dockerfile.$$runtime-py$$python_version"; \
			\
			docker buildx build --platform linux/amd64 -f $$DOCKERFILE_APP_PATH -t $$FINAL_IMAGE_TAG --load $(DOCKER_BUILD_ARGS) .; \
		done; \
	done

	@echo "\n--- Cleaning up Docker system ---"; \
	@docker image prune -f;

push-opencrate-all:
	@echo "Pushing all OpenCrate images for version v$(VERSION)..."
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			IMAGE_TAG="braindotai/opencrate-$$runtime-py$$python_version:v$(VERSION)"; \
			echo "Pushing $$IMAGE_TAG"; \
			docker push $$IMAGE_TAG; \
			\
			if [ "$(latest)" = "True" ]; then \
				LATEST_TAG="braindotai/opencrate-$$runtime-py$$python_version:latest"; \
				echo "Tagging $$IMAGE_TAG as $$LATEST_TAG and pushing"; \
				docker tag $$IMAGE_TAG $$LATEST_TAG; \
				docker push $$LATEST_TAG; \
			fi; \
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
	@echo "  build-opencrate-local 			Build a single image locally (e.g., make build-opencrate-local python=3.12 runtime=cuda)"
	@echo "  build-opencrate-local-all   	Build all images locally for all supported Python versions"
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