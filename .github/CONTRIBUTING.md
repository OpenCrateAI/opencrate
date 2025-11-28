# Contributing to OpenCrate

First off, thanks for taking the time to contribute! 🎉

This guide will help you understand our workflow, set up your environment, and submit high-quality contributions.

## Table of Contents

- [Branching Strategy](#branching-strategy)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing Your Changes](#testing-your-changes)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [What to Expect from CI](#what-to-expect-from-ci)
- [Code Style](#code-style)
- [Getting Help](#getting-help)

---

## Branching Strategy

We follow **GitHub Flow** — a simple, branch-based workflow.

| Branch | Purpose |
|--------|---------|
| `main` | The single source of truth. Always deployable. |
| `feature/*`, `fix/*` | Temporary branches for your work. |
| `v*.*.*` (Tags) | Release triggers. Not branches. |

> **Important**: We do **not** use a `dev` or `develop` branch.  
> All Pull Requests must target `main` - single source of truth.

---

## Development Setup

### Prerequisites

All you need is Docker! We have a nice dev container waiting for you to be spun up that contains all dependencies baked in.

### 1. Fork & Clone

**For Community Contributors:**
```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/opencrate.git
cd opencrate
git remote add upstream https://github.com/OpenCrateAI/opencrate.git
```

**For Core Maintainers:**
```bash
git clone https://github.com/OpenCrateAI/opencrate.git
cd opencrate
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in development mode with all extras
pip install -e ".[dev]"
```

Or use the Makefile:
```bash
make install DEPS=dev
```

---

## Making Changes

### 1. Create a Branch

```bash
# Sync with upstream first
git checkout main
git pull origin main  # or: git pull upstream main

# Create your feature branch
git checkout -b feature/my-awesome-feature
```

**Branch Naming Conventions:**
- `feature/short-description` — New features
- `fix/issue-description` — Bug fixes
- `docs/what-changed` — Documentation updates
- `refactor/what-changed` — Code refactoring

### 2. Make Your Changes

- Write clear, concise code
- Add tests for new functionality
- Update documentation if needed

### 3. Commit Your Changes

```bash
git add .
git commit -m "feat: add support for custom optimizers"
```

**Commit Message Format:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Adding or updating tests
- `chore:` — Maintenance tasks

---

## Testing Your Changes

Before submitting a PR, ensure your changes pass all tests.

### Quick Local Tests

```bash
# Run all tests (ruff, mypy, pytest)
make test

# Run individual test suites
make test-ruff    # Linting
make test-mypy    # Type checking
make test-pytest  # Unit tests
```

### Docker-Based Tests (Recommended)

This matches exactly what CI runs:

```bash
# Test with default settings (Python 3.10, CUDA runtime)
make docker-test

# Test specific configuration
make docker-test PYTHON_VERSION=3.10 RUNTIME=cpu
```

---

## Submitting a Pull Request

### 1. Push Your Branch

**Community Contributors:**
```bash
git push origin feature/my-awesome-feature
```

**Core Maintainers:**
```bash
git push origin feature/my-awesome-feature
```

### 2. Open a Pull Request

1. Go to the [OpenCrate repository](https://github.com/OpenCrateAI/opencrate)
2. Click "Compare & pull request"
3. **Target Branch**: Select `main` (not `dev` — we don't have one!)
4. Fill out the PR template
5. Submit

### 3. PR Checklist

Before submitting, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally (`make test`)
- [ ] New functionality includes tests
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive

---

## What to Expect from CI

When you open a PR, our CI pipeline runs automatically. Here's what happens:

### Pipeline Overview

```
┌─────────────────┐
│  static-checks  │  ← Fast linting & type checks (5 min)
└────────┬────────┘
         │ (if passes)
         ▼
┌─────────────────────────┐
│  generate-dockerfiles   │  ← Prepare build matrix
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│           build-and-test-images (Matrix)             │
│  ┌─────────────┐ ┌─────────────┐     ┌────────────┐  │
│  │ cpu-py3.7   │ │ cpu-py3.8   │ ... │ cuda-py3.13│  │
│  └─────────────┘ └─────────────┘     └────────────┘  │
│        (14 parallel jobs: 7 Python × 2 Runtimes)     │
└──────────────────────────────────────────────────────┘
         │
         ▼
    (For PRs: STOP here. Images are NOT pushed.)
```

### CI Stages Explained

| Stage | What It Does | Time | Your Action on Failure |
|-------|--------------|------|------------------------|
| **Static Checks** | Runs `ruff`, `mypy`, `pytest` | ~2-5 min | Fix linting/type errors locally |
| **Generate Dockerfiles** | Creates Dockerfiles for all Python versions | ~1 min | Rarely fails |
| **Build & Test Images** | Builds Docker images and runs tests inside them | ~5-10 min each | Check test logs in Artifacts |

### Understanding CI Results

**✅ All Checks Passed**: Your PR is ready for review!

**❌ Static Checks Failed**: 
- Linting issues → Run `make test-ruff` locally
- Type errors → Run `make test-mypy` locally
- Test failures → Run `make test-pytest` locally

**❌ Docker Build/Test Failed**:
1. Go to the failed workflow run
2. Download artifacts: `test-logs-{runtime}-py{version}`
3. Review the logs to identify the issue
4. Reproduce locally:
   ```bash
   make docker-test PYTHON_VERSION=3.10 RUNTIME=cpu
   ```

### PR Build Isolation

For security and reproducibility, PR builds are **completely isolated**:
- Fresh builds with `--pull --no-cache`
- No access to shared build cache
- No images are pushed to Docker Hub

This ensures your code is tested in a clean environment and cannot affect production caches.

---

## Code Style

We use automated tools to enforce consistent code style:

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Ruff** | Linting & formatting | `pyproject.toml` |
| **MyPy** | Static type checking | `pyproject.toml` |
| **Pytest** | Unit testing | `pyproject.toml` |

### Quick Fixes

```bash
# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

---

## Getting Help

- **Questions?** Open a [Discussion](https://github.com/OpenCrateAI/opencrate/discussions)
- **Found a bug?** Open an [Issue](https://github.com/OpenCrateAI/opencrate/issues)
- **CI Problems?** Check the [Workflow Documentation](.github/workflows/docker-build-test-and-push.md)

---

## Thank You! 🙏

Every contribution, no matter how small, helps make OpenCrate better.  
We appreciate your time and effort!
