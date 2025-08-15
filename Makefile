PYTHON_VERSION ?= 3.10
HOST_GIT_EMAIL = $(shell git config user.email)
HOST_GIT_NAME = $(shell git config user.name)

VERSION ?= $(shell cat VERSION | tr -d '\n')

# Default cache image names, can be overridden by CI

.SILENT:
.ONESHELL:

# This target generates all necessary Dockerfiles.
# It's called once by a setup job in the CI workflow.
build-generate:
	@echo "======== ● Generating all Dockerfiles ========"
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12 3.13"; \
	mkdir -p ./docker/dockerfiles; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			python3.10 docker/dockerfile.py --generate --python=$$python_version --runtime=$$runtime; \
		done; \
	done
	@echo "\n======== ✔ All Dockerfiles generated successfully ========\n"


build-local:
	@python3.10 docker/dockerfile.py --generate --build --python=$${python:-3.10} --runtime=$${runtime:-cpu} --log-level=DEBUG


build-local-all:
	@echo "======== ● Building all OpenCrate images locally for all supported versions ========"
	@SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			python3.10 docker/dockerfile.py --generate --build --python=$$python_version --runtime=$$runtime --log-level=DEBUG; \
		done; \
	done; \
	echo "\n======== ✔ All local images built successfully! ========\n";


build-local-clean:
	@echo "Cleaning container cache"; \
	docker container prune -f; \
	echo "Cleaning buildx cache"; \
	docker buildx prune -f; \
	echo "Cleaning image cache"; \
	docker image prune -f;


# This target builds and pushes a SINGLE image.
# All parameters are passed from the CI matrix job.
ci-build-one:
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


# This target remains the same for tagging 'latest' after all builds succeed.
gh-release-latest:
	@echo "Tagging 'latest' for all images with version $(VERSION)..."
	@set -e; \
	SUPPORTED_PYTHONS="3.7 3.8 3.9 3.10 3.11 3.12"; \
	for python_version in $$SUPPORTED_PYTHONS; do \
		for runtime in cpu cuda; do \
			IMAGE_TAG="braindotai/opencrate-$$runtime-py$$python_version:$(VERSION)"; \
			LATEST_TAG="braindotai/opencrate-$$runtime-py$$python_version:latest"; \
			echo "Tagging $$IMAGE_TAG as $$LATEST_TAG"; \
			docker buildx imagetools create -t "$$LATEST_TAG" "$$IMAGE_TAG"; \
		done; \
	done; \
	echo "✔ All images tagged as latest"


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
	@python3.10 -m pip install --upgrade pip --root-user-action=ignore --no-cache-dir
	@python3.10 -m pip install -e .[dev] --root-user-action=ignore --no-cache-dir
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