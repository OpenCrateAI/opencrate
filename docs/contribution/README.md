# Contributing to OpenCrate

This guide provides step-by-step instructions on how to set up a local development environment for OpenCrate using development containers.

## Prerequisites

Before you begin, ensure you have the following installed:
- Git
- Docker and Docker Compose
- Visual Studio Code with the "Remote - Containers" extension

## Setting Up Your Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/opencrateai/opencrate.git
cd opencrate
```

### 2. Build the Development Container

Build the OpenCrate development container:

```bash
make build
```

This will create a Docker image named `opencrate-dev:latest` that contains all necessary development tools and dependencies.

### 3. Start the Development Container

Launch the container:

```bash
make start
```

This starts the development container in the background.

### 4. Open in VS Code's Dev Container

Open the project in VS Code:

```bash
code .
```

When VS Code opens, you'll see a notification asking if you want to "Reopen in Container." Click this option to reopen the project within the dev container.

Alternatively, you can:
1. Open the VS Code command palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Select "Remote-Containers: Reopen in Container"

### 5. Enter the Container via CLI

If you need direct command-line access to the container:

```bash
make enter
```

This command provides you with an interactive shell (zsh) inside the running development container.

### 6. Install Development Dependencies

Once inside the container, install the OpenCrate package in development mode:

```bash
make install
```

This installs the OpenCrate package with all development dependencies, allowing your changes to be reflected immediately.

## Development Workflow

### Building OpenCrate Images

To build an OpenCrate image with specific Python version and runtime:

```bash
make build-opencrate python=3.10 runtime=cuda
```

To build all supported combinations of OpenCrate images:

```bash
make build-opencrate-all
```

### Running Tests

Run unit tests with pytest:

```bash
make test-pytest
```

Check code formatting with black:

```bash
make test-black
```

Run linting with flake8:

```bash
make test-flake8
```

Perform static type checking with mypy:

```bash
make test-mypy
```

Run all tests:

```bash
make test
```

Run tests across all supported Python versions:

```bash
make test-all
```

### Getting Help

To see a list of all available make commands:

```bash
make help
```

## Stopping Your Development Environment

To stop the container:

```bash
make stop
```

To completely remove the container:

```bash
make kill
```

## Contribution Guidelines

1. Create a feature branch for your work
2. Ensure all tests pass before submitting a pull request
3. Follow the project's coding style and conventions
4. Include appropriate tests for new functionality
5. Update documentation as needed

Happy contributing!