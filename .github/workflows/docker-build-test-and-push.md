# Docker Build, Test, and Push Workflow

This document provides a detailed technical reference for the OpenCrate CI/CD pipeline. For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Table of Contents

- [Overview](#overview)
- [Workflow Triggers](#workflow-triggers)
- [Workflow Architecture](#workflow-architecture)
- [Atomic Release Consistency](#atomic-release-consistency)
- [Build Caching Strategy](#build-caching-strategy)
- [Version Management](#version-management)
- [Release Process](#release-process)
- [Image Naming Convention](#image-naming-convention)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

This GitHub Actions workflow automates building, testing, and publishing OpenCrate Docker images for:
- **7 Python versions**: 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **2 Runtimes**: CPU and CUDA

The workflow uses a **tiered testing strategy**:
- **Pull Requests**: Fast feedback with minimal matrix (2 Python versions × 1 runtime = 2 jobs)
- **Main/Release**: Full validation with complete matrix (7 Python versions × 2 runtimes = 14 jobs)

The workflow ensures **Atomic Release Consistency** - the exact image that passes tests is the one published to Docker Hub.

---

## Workflow Triggers

### 1. Version Tag Push (Release)
```yaml
push:
  tags:
    - 'v*.*.*'
```
- **When**: A tag matching `v*.*.*` is pushed (e.g., `v0.1.0`, `v1.2.3-rc`)
- **Outcome**: Images are built, tested, pushed, and tagged as `latest`

### 2. Pull Request to Main
```yaml
pull_request:
  branches: ["main"]
  paths:
    - "src/**"
    - "tests/**"
    - "docker/**"
    - "pyproject.toml"
    - "setup.cfg"
    - "setup.py"
    - "Makefile"
    - "Makefile.ci"
    - "VERSION"
    - "PYTHON_VERSIONS"
    - ".github/workflows/docker-build-test-and-push.yml"
```
- **When**: PR opened/updated targeting `main` with relevant file changes
- **Outcome**: Images are built and tested, but **NOT pushed**
- **Optimization**: Skipped for documentation-only changes

### 3. Scheduled Weekly Build
```yaml
schedule:
  - cron: '0 3 * * 0'
```
- **When**: Every Sunday at 3:00 AM UTC
- **Outcome**: Fresh builds with updated base layers, pushed but **NOT tagged as `latest`**

### 4. Manual Trigger
```yaml
workflow_dispatch:
  inputs:
    REBUILD_BASE:
      description: 'Force a pull of new base layers and refresh the cache?'
      type: boolean
      default: false
```
- **When**: Manually triggered from GitHub Actions UI
- **Outcome**: Rebuilt and pushed, but **NOT tagged as `latest`**

---

## Workflow Architecture

The pipeline consists of **5 jobs** with parallel execution:

```
┌──────────────────┐     ┌────────────────────────┐
│  static-checks   │     │  generate-dockerfiles  │
│   (parallel)     │     │      (parallel)        │
└────────┬─────────┘     └───────────┬────────────┘
         │                           │
         └─────────────┬─────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│            build-and-test-images (Matrix)              │
│                                                        │
│  For PRs:        cpu-py3.7, cpu-py3.13 (2 jobs)        │
│  For Main/Tag:   [cpu,cuda] × [3.7-3.13] (14 jobs)     │
└────────┬───────────────────────────────────────────────┘
         │
         ▼  (Only if NOT a PR)
┌────────────────────────────────────────────────────────┐
│            build-and-push-images (14 jobs)             │
│  Job 4: Verify digest → Push to Docker Hub             │
└────────┬───────────────────────────────────────────────┘
         │
         ▼  (Only for tag pushes)
┌──────────────────┐
│  release-latest  │  Job 5: Tag images as "latest"
└──────────────────┘
```

### Job 1: `static-checks`

**Purpose**: Fail fast on simple errors before expensive Docker builds.

**Runs in parallel with**: `generate-dockerfiles`

**Timeout**: 5 minutes

**Steps**:
1. Checkout repository
2. Set up Python 3.10
3. Install development packages (`pip install ".[ci]"`)
4. Run `make test` (ruff, mypy, pytest)

### Job 2: `generate-dockerfiles`

**Purpose**: Generate Dockerfiles and set up the build matrix.

**Runs in parallel with**: `static-checks`

**Outputs**:
- `version`: From `VERSION` file
- `rebuild_flag`: `true` for scheduled/manual rebuilds
- `python_versions_json`: Matrix of Python versions (varies by trigger)

**Matrix Selection Logic**:
| Trigger | Python Versions | Rationale |
|---------|-----------------|------------|
| **Pull Request** | First + Last from `PYTHON_VERSIONS` (e.g., 3.7, 3.13) | Fast feedback, edge-version coverage |
| **Main/Tag/Schedule** | All versions from `PYTHON_VERSIONS` | Full compatibility validation |

### Job 3: `build-and-test-images`

**Purpose**: Build, scan, and test images.

**Depends on**: Both `static-checks` AND `generate-dockerfiles` must pass.

**Matrix Strategy by Trigger**:

| Trigger | Runtimes | Python Versions | Total Jobs |
|---------|----------|-----------------|------------|
| **Pull Request** | CPU only | 3.7 + 3.13 | **2 jobs** |
| **Main/Tag/Schedule** | CPU + CUDA | All 7 versions | **14 jobs** |

**Why this strategy?**
- **PRs**: 86% fewer jobs = faster feedback
- **Oldest + Newest Python**: Catches "too new" and "deprecated" issues
- **CPU only for PRs**: Logic bugs are runtime-agnostic; CUDA just adds GPU libraries
- **Full matrix on merge**: Comprehensive validation before any release

**Steps**:
1. Setup (checkout, download Dockerfiles, Buildx, Docker Hub login)
2. Determine build strategy (cache behavior based on trigger type)
3. Build image with `make ci-build MODE=test`
4. Scan with Trivy for vulnerabilities
5. Run tests with `make docker-test`
6. Upload test logs as artifacts
7. **Export image digest** (SHA256 of layer hashes)
8. Upload digest as artifact

### Job 4: `build-and-push-images`

**Purpose**: Verify integrity and push to Docker Hub.

**Condition**: Only runs if all test jobs pass AND not a PR.

**Steps**:
1. Download digest artifacts from Job 3
2. Rebuild image from cache (`REBUILD_FLAG=false`, `CACHE_UPDATE=false`)
3. **Verify Integrity**: Compare digests
   - `Digest_Test == Digest_Push` → Proceed
   - `Digest_Test != Digest_Push` → **FAIL** (prevents untested images)
4. Push verified image to Docker Hub

### Job 5: `release-latest`

**Purpose**: Tag images as `latest`.

**Condition**: Only for tag pushes (not scheduled or manual).

---

## Atomic Release Consistency

The workflow implements a **Digest Gate** to ensure the exact image tested is the one released.

### The Problem: Ephemeral Runners

GitHub Actions runners are ephemeral. The test job and push job run on **different machines**. Without verification, you might:
1. **Push an old image** (if cache upload failed silently)
2. **Push a drifted image** (if cache pull failed and Docker rebuilt from scratch)

### The Solution: Layer Digest Verification

```
Test Job                              Push Job
────────                              ────────
Build image                           Pull cache from registry
    │                                     │
    ▼                                     ▼
Compute Digest A ─────────────────▶  Compute Digest B
(sha256 of layers)                   (sha256 of layers)
    │                                     │
    ▼                                     ▼
Upload as artifact ───────────────▶  Download artifact
                                          │
                                          ▼
                                    Compare A == B?
                                     ├─ YES → Push ✅
                                     └─ NO  → FAIL ❌
```

### Failure Scenarios Prevented

| Scenario | Cause | Without Digest Gate | With Digest Gate |
|----------|-------|---------------------|------------------|
| **Stale Cache** | Test job fails to upload cache | Old image pushed as new | ❌ Blocked |
| **Silent Drift** | Push job fails to pull cache, rebuilds | Untested environment released | ❌ Blocked |

---

## Build Caching Strategy

Each Python/runtime combination has its own dedicated cache:
```
braindotai/opencrate-build-cache:cpu-py3.7
braindotai/opencrate-build-cache:cpu-py3.8
...
braindotai/opencrate-build-cache:cuda-py3.13
```

### Cache Behavior by Trigger

There are **two registries** involved in this workflow:

1. **Build Cache Registry** (`braindotai/opencrate-build-cache:*`) - Stores intermediate Docker layers to speed up future builds
2. **Docker Hub** (`braindotai/opencrate-cpu-py*:*`, `braindotai/opencrate-cuda-py*:*`) - The public registry where final images are published

| Trigger | Test Job → Build Cache | Push Job → Build Cache | Push Job → Docker Hub |
|---------|------------------------|------------------------|----------------------|
| **Pull Request** | No read, No write | Does not run | Does not run |
| **Tag Push** | Read + Write (if deps changed) | Read only | ✅ Pushes image |
| **Scheduled** | Fresh build + Write | Read only | ✅ Pushes image |
| **Manual (REBUILD=false)** | Read + Write (if deps changed) | Read only | ✅ Pushes image |
| **Manual (REBUILD=true)** | Fresh build + Write | Read only | ✅ Pushes image |

**Key Principle**: The Push job **never writes to the build cache** - it only reads cached layers from the Test job, then pushes the final image to Docker Hub.

### PR Isolation

Pull Request builds are **completely isolated**:
- Fresh builds with `--pull --no-cache`
- No access to shared cache (read or write)
- Prevents cache poisoning from untrusted code

---

## Version Management

### Single Source of Truth: `VERSION` File

```
v0.1.0-rc
```

The workflow reads version from this file, ensuring consistency across:
- Scheduled runs (no tag context)
- Manual triggers (branch context only)
- Tag pushes (verified against tag)

---

## Release Process

### Step 1: Update VERSION
```bash
echo "v1.0.0" > VERSION
```

### Step 2: Commit
```bash
git add VERSION
git commit -m "Release v1.0.0"
```

### Step 3: Tag
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
```

### Step 4: Push
```bash
git push origin main
git push origin v1.0.0  # Triggers the workflow
```

### Step 5: Monitor
1. Go to GitHub → Actions
2. Watch the "Docker Build, Test and Push" workflow
3. Verify images appear on Docker Hub

---

## Image Naming Convention

```
braindotai/opencrate-{runtime}-py{version}:{tag}
```

**Examples**:
- `braindotai/opencrate-cpu-py3.10:v1.0.0`
- `braindotai/opencrate-cuda-py3.11:latest`

---

## Troubleshooting

### Static Checks Failed

```bash
# Fix linting
make test-ruff

# Check types
make test-mypy

# Run tests
make test-pytest
```

### Docker Build/Test Failed

Ideally you should locally run `make docker-test` followed by `make docker-test-all` before you make a push to ensure your changes pass CI. But in any case if the CI fails:

1. Download `test-logs-{runtime}-py{version}` from workflow artifacts
2. Reproduce locally and fix:
   ```bash
   make docker-test RUNTIME=<runtime> PYTHON_VERSION=<version>
   ```

### Digest Verification Failed

This will happen because the build-test and build-push jobs produced different image digests, which indicates a cache inconsistency.

- **Log**: "Integrity check failed, aborting push to protect registry"
- **Cause**: Cache inconsistency between test and push jobs
- **Solution**: Re-run the workflow. If persistent, trigger manual rebuild with `REBUILD_BASE=true`.

## Best Practices

### ✓ DO

- Update `VERSION` file before creating tags
- Use semantic versioning (`major.minor.patch`)
- Test locally with `make test` before pushing

### ✗ DON'T

- Create tags without updating `VERSION` file
- Push tags for untested code
- Manually edit files in `docker/dockerfiles/` (auto-generated)
- Force rebuild unless necessary (wastes CI time)
