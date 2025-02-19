PYTHON_VERSION ?= 3.9
SHELL := /bin/bash

.SILENT:
.ONESHELL:

check_python = \
	if [ -z "$(python)" ]; then \
		echo "Using default Python version $(PYTHON_VERSION)"; \
		python=$(PYTHON_VERSION); \
	fi; \
	if ! command -v python$$python >/dev/null 2>&1; then \
		echo "Error: Python $$python is not installed on your system"; \
		echo "Please install Python $$python or use a different version"; \
		exit 1; \
	fi

install:
	@$(check_python)
	@python$(python) -m pip install --upgrade pip
	@python$(python) -m pip install -e . --no-cache-dir
	@oc --install-completion || true

dev-install:
	@$(check_python)
	@if [ ! -d ".venv" ]; then \
        python$(python) -m venv .venv; \
        source .venv/bin/activate; \
    fi
	@.venv/bin/python$(python) -m pip install --upgrade pip
	@.venv/bin/python$(python) -m pip install -e .[testing] --no-cache-dir
	@source .venv/bin/activate

build:
	@.venv/bin/python3.9 .docker/dockerfile.py --python=$(if $(python),$(python),3.10) --runtime=$(if $(runtime),$(runtime),cuda)

build-all:
	@for python in 3.7 3.8 3.9 3.10 3.11 3.12 3.13; do \
        for runtime in cuda cpu; do \
            .venv/bin/python3.9 .docker/dockerfile.py --python=$$python --runtime=$$runtime; \
        done \
    done

test:
	@PYTHONPATH=src .venv/bin/pytest