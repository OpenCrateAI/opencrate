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
- [Complete Contributor Workflows](#complete-contributor-workflows)
- [Getting Help](#getting-help)

---

## Branching Strategy

We follow **GitHub Flow** - a simple, branch-based workflow.

| Branch | Purpose |
|--------|---------|
| `main` | The single source of truth. Always deployable. |
| `feature/*`, `fix/*` | Temporary branches for your work. |
| `v*.*.*` (Tags) | Release triggers. Not branches. |

> **Important**: We do **not** use a `dev` or `develop` branch.  
> All Pull Requests must target `main` - single source of truth.

Use only the following prefixes for your branches:

| Prefix | Use For |
|--------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `ci/` | CI/CD changes |
| `refactor/` | Code cleanup |
| `test/` | Test changes |

**Examples:**
- `feature/async-loader`
- `fix/123-memory-leak` (with issue number)
- `docs/api-reference`

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

### 2. Setup Dev Container

```bash
make start
```
This will build and start the development container. Once the dev container starts, you can get inside its shell with:

```bash
make enter
```

### 3. Install Dependencies

Once you're inside the dev container, you can install all the dependencies required for development:
```bash
make install
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
- `feature/short-description` - New features
- `fix/issue-description` - Bug fixes
- `docs/what-changed` - Documentation updates
- `refactor/what-changed` - Code refactoring

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
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

---

## Testing Your Changes

Before submitting a PR, ensure your changes pass all tests.

### Quick Local Tests

This doesn't require running any docker build and is faster for quick checks:

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
make docker-test PYTHON_VERSION=3.8 RUNTIME=cpu

# Once defaults are tested, you should run tests for all possible runtimes and python versions before submitting your PR.
make docker-test-all
```

---

## Submitting a Pull Request

### 1. Push Your Branch

```bash
git push origin feature/my-awesome-feature
```

### 2. Open a Pull Request

1. Go to the [OpenCrate repository](https://github.com/OpenCrateAI/opencrate)
2. Click "Compare & pull request"
3. **Target Branch**: Select `main` (not `dev` - we don't have one!)
4. Fill out the PR template
5. Submit

### 3. PR Checklist

Before submitting, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally (`make test`)
- [ ] New functionality includes tests
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive

#### 4. Code Style

We use automated tools to enforce consistent code style:

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Ruff** | Linting & formatting | `pyproject.toml` |
| **MyPy** | Static type checking | `pyproject.toml` |
| **Pytest** | Unit testing | `pyproject.toml` |

#### 5. Quick Fixes

```bash
# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

---

## What to Expect from CI

When you open a PR, our CI pipeline runs automatically. We use a **tiered testing strategy** to give you fast feedback while ensuring full validation before release.

### PR vs. Main: Testing Strategy

| Aspect | Pull Request | After Merge to Main |
|--------|--------------|---------------------|
| **Python Versions** | 3.7 + 3.13 (oldest + newest) | All 7 versions (3.7–3.13) |
| **Runtimes** | CPU only | CPU + CUDA |
| **Total Jobs** | 2 | 14 |
| **Feedback Time** | ~4–5 minutes | ~10–15 minutes |
| **Purpose** | Fast feedback, edge-version bugs | Full compatibility validation |

**Why this approach?**
- ✓ **Fast feedback**: 86% fewer jobs on PRs = faster iteration
- ✓ **Edge coverage**: Testing oldest (3.7) catches "feature too new" bugs; newest (3.13) catches deprecations
- ✓ **Runtime-agnostic logic**: If tests pass on CPU, they'll pass on CUDA (same Python code)
- ✓ **Full validation on merge**: All 14 configurations tested before any release

### Pipeline Overview

```
┌──────────────────┐     ┌─────────────────────────┐
│  static-checks   │     │  generate-dockerfiles   │
│   (~2 min)       │     │       (~20 secs)        │
└────────┬─────────┘     └───────────┬─────────────┘
         │         (parallel)        │
         └─────────────┬─────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│           build-and-test-images (Matrix)           │
│                                                    │
│  For PRs:    cpu-py3.7, cpu-py3.13 (2 jobs)        │
│  For Main:   [cpu,cuda] × [3.7-3.13] (14 jobs)     │
└────────────────────────────────────────────────────┘
                       │
                       ▼
            (For PRs: STOP here. Images NOT pushed.)
```

### CI Stages Explained

| Stage | What It Does | Time (PR) | Your Action on Failure |
|-------|--------------|-----------|------------------------|
| **Static Checks** | Runs `ruff`, `mypy`, `pytest` | ~2 min | Fix linting/type errors locally |
| **Generate Dockerfiles** | Creates Dockerfiles, selects Python versions | ~20 secs | Rarely fails |
| **Build & Test Images** | Builds Docker images and runs tests inside them | ~3 min (2 jobs) | Check test logs in Artifacts |

### Understanding CI Results

**✓ All Checks Passed**: Your PR is ready for review!

**✗ Static Checks Failed**: 
- Linting issues → Run `make test-ruff` locally
- Type errors → Run `make test-mypy` locally
- Test failures → Run `make test-pytest` locally

**✗ Docker Build/Test Failed**:
1. Go to the failed workflow run
2. Download artifacts: `test-logs-{runtime}-py{version}`
3. Review the logs to identify the issue
4. Reproduce locally:
   ```bash
   make docker-test RUNTIME=<runtime> PYTHON_VERSION=<version>
   ```

### PR Build Isolation

For security and reproducibility, PR builds are **completely isolated**:
- Fresh builds with `--pull --no-cache`
- No access to shared build cache
- No images are pushed to Docker Hub

This ensures your code is tested in a clean environment and cannot affect production caches.

---

## Complete Contributor Workflows

### Workflow for Community Contributors (External)

```
1. FORK & CLONE
   └── Fork on GitHub → Clone your fork → Add upstream remote

2. CREATE BRANCH
   └── git checkout -b fix/my-bugfix

3. MAKE CHANGES
   └── Code → Write tests → Update docs (if needed)

4. TEST LOCALLY
   └── make test  (fast: ruff, mypy and pytest)
   └── make test-all  (slow: run ruff, mypy and pytest for all python versions)
   └── make docker-test (fast: builds docker image and runs `make test` inside)
   └── make docker-test-all (slow: builds all possible docker images and runs `make test` inside)

5. PUSH & OPEN PR
   └── git push origin fix/my-bugfix
   └── Open PR targeting `main` (NOT `dev` - we don't have one)

6. CI RUNS (Lightweight)
   └── static-checks + generate-dockerfiles (parallel)
   └── build-and-test: cpu-py3.7 + cpu-py3.13 (2 jobs only)
   └── Total time: ~2-5 minutes

7. CODE REVIEW
   └── Maintainer reviews → Request changes or Approve

8. MERGE (by Maintainer)
   └── Squash & Merge to `main`
   └── Full CI runs: ALL 14 images tested (7 Python × 2 runtimes)
   └── Your contribution is now in `main`! 🎉
```

### Workflow for Core Maintainers (Internal)

```
1. CREATE BRANCH (directly in main repo)
   └── git checkout main && git pull
   └── git checkout -b feature/new-feature

2. MAKE CHANGES
   └── Code → Write tests → Update docs

3. TEST LOCALLY
   └── make test  (fast: ruff, mypy and pytest)
   └── make test-all  (slow: run ruff, mypy and pytest for all python versions)
   └── make docker-test (fast: builds docker image and runs `make test` inside)
   └── make docker-test-all (slow: builds all possible docker images and runs `make test` inside)

4. PUSH & OPEN PR
   └── git push origin feature/new-feature
   └── Open PR targeting `main`

5. CI RUNS (Lightweight) → Same as external contributors

6. SELF-REVIEW or PEER REVIEW
   └── At least one approval recommended

7. MERGE
   └── Squash & Merge to `main`
   └── Full CI runs automatically on `main`

8. RELEASE (when ready)
   └── Update VERSION file
   └── git tag -a v1.0.0 -m "Release v1.0.0"
   └── git push origin v1.0.0
   └── Full 14-image build → Test → Push to Docker Hub → Tag as latest
```

### What Happens After Merge?

When your PR is merged to `main`, the **full validation pipeline** runs:

| Step | What Happens |
|------|-------------|
| 1. Static Checks | Same linting/typing/tests |
| 2. Generate Dockerfiles | Same as PR |
| 3. Build & Test | **All 14 images** (7 Python × 2 runtimes) |
| 4. Build & Push | Push all 14 images to Docker Hub (version-tagged) |
| 5. Release Latest | (Only on tag push) Tag images as `latest` |

This ensures that even if a rare version-specific bug slipped through the PR (which tested only 3.7 + 3.13), it's caught **before any release**.

---

## Getting Help

- **Questions?** Open a [Discussion](https://github.com/OpenCrateAI/opencrate/discussions)
- **Found a bug?** Open an [Issue](https://github.com/OpenCrateAI/opencrate/issues)

---

## Thank You!

Every contribution, no matter how small, helps us build the next generation of the AI stack. We truly appreciate your time, effort, and passion for open source!
