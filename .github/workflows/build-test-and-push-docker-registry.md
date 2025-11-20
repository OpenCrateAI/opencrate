# Docker Build, Test, and Push Workflow Documentation

## Overview

This GitHub Actions workflow automates the process of building, testing, and publishing OpenCrate Docker images for multiple Python versions (3.7-3.14) and runtime configurations (CPU and CUDA). The workflow ensures that all images are thoroughly tested before being pushed to Docker Hub.

## Workflow Triggers

The workflow runs automatically under four different scenarios:

### 1. Version Tag Push (Release)
```yaml
push:
  tags:
    - 'v*.*.*'
```
- **When**: A new version tag matching the pattern `v*.*.*` is pushed (e.g., `v0.1.0-rc`, `v1.2.3`)
- **Purpose**: Build, test, and publish official release images
- **Outcome**: Images are pushed to Docker Hub and tagged as "latest"

### 2. Pull Request to Main Branch
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
    - ".github/workflows/build-test-and-push-docker-registry.yml"
```
- **When**: A pull request is opened or updated targeting the main branch, AND changes are detected in relevant files (source code, tests, docker config, dependencies).
- **Purpose**: Validate changes before merging (CI validation)
- **Outcome**: Images are built and tested, but NOT pushed to Docker Hub.
- **Optimization**: Does not run for documentation-only changes (e.g., README.md updates).

### 3. Scheduled Weekly Build
```yaml
schedule:
  - cron: '0 3 * * 0'
```
- **When**: Every Sunday at 3:00 AM UTC
- **Purpose**: Keep images fresh with latest base layers and security updates
- **Outcome**: Images are rebuilt and pushed, but NOT tagged as "latest"

### 4. Manual Trigger
```yaml
workflow_dispatch:
  inputs:
    REBUILD_BASE:
      description: 'Force a pull of new base layers and refresh the cache?'
      required: true
      type: boolean
      default: false
```
- **When**: Manually triggered from the GitHub Actions UI
- **Purpose**: On-demand builds for testing or emergency updates
- **Options**: Can force rebuild of base layers by setting `REBUILD_BASE` to `true`
- **Outcome**: Images are rebuilt and pushed, but NOT tagged as "latest"

## Workflow Architecture

The workflow consists of three sequential jobs:

### Job 1: `generate-files`
**Purpose**: Generate Dockerfiles and set up workflow variables

**Steps**:
1. Checkout repository
2. Read VERSION from the `VERSION` file (e.g., `v0.1.0-rc`)
3. Set up Python 3.10 and install dependencies (`rich`, `loguru`)
4. **Set Python Matrix**: Read `PYTHON_VERSIONS` file to generate the list of target versions dynamically
5. Generate Dockerfiles for all Python versions and runtimes
6. Upload generated Dockerfiles as artifacts

**Outputs**:
- `version`: The version string from the VERSION file
- `rebuild_flag`: Whether to force rebuild base layers (`true` for scheduled/tag pushes)
- `python_versions_json`: JSON array of Python versions to be used in the matrix

### Job 2: `build-and-test`
**Purpose**: Build and test images for all configurations in parallel

**Matrix Strategy**: Runs parallel jobs for each combination of:
- Runtimes: `cpu`, `cuda`
- Python versions: Dynamically sourced from `PYTHON_VERSIONS` file (e.g., 3.7 through 3.14)

**Steps**:
1. **Setup**:
   - Checkout repository (fetch depth 2 for diff checks)
   - Download generated Dockerfiles
   - Set up QEMU (for ARM64 support)
   - Set up Docker Buildx
   - Login to Docker Hub

2. **Check for Dependency Changes**:
   - Runs `make check-dependency-changes` to detect modifications in `pyproject.toml` or `setup.cfg`
   - Determines if `CACHE_UPDATE` should be true (if dependencies changed or `REBUILD_BASE` is requested)

3. **Build Local Test Image** (MODE=test):
   - Uses `make ci-build MODE=test` with hybrid caching strategy
   - Platform: `linux/amd64` only (faster for testing)
   - Caching layers:
     - Reads from registry cache (per-Python-version)
     - Writes to local cache for reuse in push step
   - Image tag: `braindotai/opencrate-{runtime}-py{version}:{VERSION}`
   - Example: `braindotai/opencrate-cpu-py3.10:v0.1.0-rc`
   - Image is loaded locally (not pushed)

4. **Light Cleanup**:
   - Cleans apt cache and user cache (`~/.cache/*`)
   - **Crucial**: Does NOT prune Docker Buildx cache to ensure layers are available for the push step

5. **Test Local Image**:
   - Run tests inside the freshly built Docker container
   - Uses `make docker-test` with `DEPS=ci`
   - Tests include: ruff linting, mypy type checking, pytest
   - Logs are saved to `./tests/logs/test-py{version}-{runtime}.log`

5. **Upload Test Logs**:
   - Upload logs as artifacts (runs even if tests fail)
   - Artifact name: `test-logs-{runtime}-py{version}`
   - Example: `test-logs-cuda-py3.11`

6. **Build and Push Multi-Platform Image** (MODE=push, only if tests pass):
   - Uses `make ci-build MODE=push` with hybrid caching strategy
   - Platforms: `linux/amd64`, `linux/arm64`
   - Caching layers:
     - Reads from registry cache (per-Python-version)
     - Reads from local cache (populated by test step)
     - Conditionally writes to registry cache (if REBUILD_FLAG or CACHE_UPDATE)
   - Pushed to Docker Hub with version tag
   - Updates build cache in registry (when applicable)

### Job 3: `release-latest`
**Purpose**: Tag successful builds as "latest"

**Condition**: Only runs if:
- All build-and-test jobs succeeded AND
- Triggered by a version tag push (NOT scheduled, manual, or PR)

**Steps**:
1. Login to Docker Hub
2. Tag images with "latest" tag for all Python versions listed in `PYTHON_VERSIONS`
3. Example: `braindotai/opencrate-cpu-py3.10:v0.1.0-rc` → `braindotai/opencrate-cpu-py3.10:latest`

## Version Management

### Single Source of Truth: VERSION File

The workflow reads the version from the `VERSION` file in the repository root. This ensures:
- ✓ Consistent versioning across all trigger types
- ✓ No mismatch between build and test steps
- ✓ Single location to update for version bumps

**Example VERSION file**:
```
v0.1.0-rc
```

**Why not use Git tags directly?**
- Scheduled runs don't have tag context
- Manual triggers use branch names, not tags
- VERSION file works consistently for all scenarios

## Developer Workflow

### Releasing a New Version

Follow these steps to release a new version of OpenCrate:

#### Step 1: Update the VERSION File
```bash
# Edit the VERSION file
echo "v0.2.0" > VERSION

# Or use your preferred editor
vim VERSION
```

**Format**: `v{major}.{minor}.{patch}[-{suffix}]`
- Examples: `v1.0.0`, `v0.1.0-rc`, `v2.3.1-beta`

#### Step 2: Commit Your Changes
```bash
# Stage all changes including VERSION file
git add .

# Commit with a meaningful message
git commit -m "Release v0.2.0: Add new feature XYZ"
```

#### Step 3: Create a Git Tag
```bash
# Create an annotated tag (recommended)
git tag -a v0.2.0 -m "Release v0.2.0"

# Or create a lightweight tag
git tag v0.2.0
```

**Important**: The tag name MUST match the pattern `v*.*.*` to trigger the workflow.

#### Step 4: Push to GitHub
```bash
# Push commits first
git push origin main

# Push the tag (this triggers the workflow)
git push origin v0.2.0

# Or push all tags at once
git push origin --tags
```

#### Step 5: Monitor the Workflow

1. Go to GitHub → Actions tab
2. Find the "Build, Test, and Push Docker Registry" workflow run
3. Monitor the progress
4. Download test logs if needed:
   - Click on the workflow run
   - Scroll to "Artifacts" section
   - Download logs for failed configurations

### Common Scenarios

#### Scenario 1: Regular Release
```bash
# Update version
echo "v1.0.0" > VERSION

# Commit and tag
git add VERSION
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"

# Push
git push origin main
git push origin v1.0.0
```

**Result**: Images built, tested, pushed, and tagged as "latest"

#### Scenario 2: Pre-release (RC, Beta, Alpha)
```bash
# Update version with suffix
echo "v1.1.0-rc1" > VERSION

# Commit and tag
git add VERSION
git commit -m "Release v1.1.0-rc1"
git tag -a v1.1.0-rc1 -m "Release candidate 1 for v1.1.0"

# Push
git push origin main
git push origin v1.1.0-rc1
```

**Result**: Images built, tested, pushed, and tagged as "latest" (use caution with pre-releases)

#### Scenario 3: Force Rebuild (Manual Trigger)
```bash
# No code changes needed
# Go to GitHub → Actions → Build, Test, and Push Docker Registry
# Click "Run workflow"
# Select branch: main
# Set REBUILD_BASE: true (to pull fresh base images)
# Click "Run workflow"
```

**Result**: Images built with fresh base layers, tested, and pushed (NOT tagged as "latest")

#### Scenario 4: Testing Changes via Pull Request
```bash
# Make your changes
git checkout -b feature/my-awesome-feature

# Update code and tests
# ...

# Commit and push
git add .
git commit -m "Add awesome feature"
git push origin feature/my-awesome-feature

# Open a PR targeting main branch on GitHub
```

**Result**: Images built and tested in CI, but NOT pushed to Docker Hub. Perfect for validating changes before merging.

#### Scenario 5: Testing Without Publishing (Manual)
If you want to test the workflow without opening a PR:

1. Create a feature branch
2. Update VERSION file
3. Push the branch (without tags)
4. Manually trigger workflow from that branch
5. Review test results
6. Merge to main and create tag when ready

## Image Naming Convention

All images follow this pattern:
```
braindotai/opencrate-{runtime}-py{python_version}:{version}
```

**Examples**:
- `braindotai/opencrate-cpu-py3.10:v0.1.0-rc`
- `braindotai/opencrate-cuda-py3.11:v1.0.0`
- `braindotai/opencrate-cpu-py3.12:latest`

## Build Caching Strategy

The workflow uses a **hybrid caching strategy** combining local filesystem cache and remote registry cache to optimize build performance and reliability.

### Two-Stage Build Process

Each matrix job builds the image twice:

1. **Test Stage** (`MODE=test`):
   - Builds for `linux/amd64` only
   - Loads image locally for testing

2. **Push Stage** (`MODE=push`):
   - Builds for `linux/amd64,linux/arm64`
   - Reuses local cache from test stage
   - Pushes to Docker Hub
   - Updates registry cache (conditionally)

### Cache Layers

#### 1. Registry Cache (Remote)
Each Python version and runtime combination has its own dedicated cache image:
- `braindotai/opencrate-build-cache:cpu-py3.7`
- `braindotai/opencrate-build-cache:cpu-py3.8`
- ...
- `braindotai/opencrate-build-cache:cpu-py3.14`
- `braindotai/opencrate-build-cache:cuda-py3.7`
- `braindotai/opencrate-build-cache:cuda-py3.8`
- ...
- `braindotai/opencrate-build-cache:cuda-py3.14`

**Why per-version caches?**
- ✓ Prevents parallel write conflicts in matrix builds
- ✓ Better cache hit rates (each Python version gets its optimal cache)
- ✓ No race conditions during concurrent builds
- ✓ Each build can safely update its own cache

**Registry Cache Behavior:**
- **Always reads** from registry cache (with `ignore-error=true`)
- **Only writes** when `MODE=push` AND (`REBUILD_FLAG=true` OR `CACHE_UPDATE=true`)
- Uses `mode=max` to cache all layers including intermediate steps

**Benefits:**
- ✓ Dramatically speeds up the push stage (reuses test build layers)
- ✓ Reduces build time for multi-platform images
- ✓ No network overhead between test and push stages
- ✓ Guaranteed cache hit for the second build

### Cache Behavior by Trigger Type

- **Pull Requests**: Read-only from registry cache, local cache used between stages, no cache writes to registry
- **Tag Pushes**: Full caching enabled (read + write to registry cache)
- **Scheduled Builds**: Force rebuild with `--pull` flag, updates registry cache
- **Manual Triggers**: Optionally force rebuild with `REBUILD_BASE=true`

### When to Force Rebuild
- Base images have critical security updates
- Want to test with latest dependencies
- Cache corruption suspected
- Weekly refresh (automatic on Sundays)

## Troubleshooting

### Tests Failing in CI

1. **Download test logs**:
   - Go to failed workflow run
   - Artifacts → Download `test-logs-{runtime}-py{version}`

2. **Reproduce locally**:
   ```bash
   # Test specific configuration
   make docker-test PYTHON_VERSION=3.10 RUNTIME=cpu VERSION=v0.1.0-rc
   ```

3. **Common issues**:
   - Dependency conflicts: Check `pyproject.toml`
   - Type errors: Run `make test-mypy` locally
   - Linting issues: Run `make test-ruff` locally

### Image Not Found Error

**Symptom**: "Unable to find image locally" during test step

**Cause**: Mismatch between build tag and test tag

**Solution**: Ensure VERSION file is committed before creating tag

### Build Cache Issues

**Symptom**: Builds taking very long or failing

**Solution**: Trigger manual workflow with `REBUILD_BASE=true`

### Push Permission Denied

**Cause**: Docker Hub credentials not configured

**Solution**: Verify repository secrets:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Best Practices

### ✓ DO
- Always update VERSION file before creating tags
- Use semantic versioning (major.minor.patch)
- Create annotated tags with meaningful messages
- Test locally before pushing tags
- Monitor workflow runs after pushing tags
- Download and review test logs for failures

### ✗ DON'T
- Don't create tags without updating VERSION file
- Don't push tags for untested code
- Don't manually edit Dockerfiles in `docker/dockerfiles/` (they're auto-generated)
- Don't tag experimental features as "latest" (use pre-release suffixes)
- Don't force rebuild unless necessary (wastes CI time)

## Monitoring and Notifications

### Success Indicators
- ✓ All 16 matrix jobs complete successfully (8 Python versions × 2 runtimes)
- ✓ Images pushed to Docker Hub (except for PR builds)
- ✓ "latest" tags updated (for tag pushes only, Python 3.7-3.12)

### Failure Handling
- Individual matrix job failures don't stop other jobs (`fail-fast: false`)
- Test logs uploaded even if tests fail (`if: always()`)
- Multi-platform push only happens if tests pass

### Viewing Results
1. **GitHub Actions UI**: Real-time progress and logs
2. **Docker Hub**: Verify images are pushed
3. **Artifacts**: Download test logs for debugging

## Additional Resources

- **Makefile**: Local development and testing commands
- **Makefile.ci**: CI-specific build targets
- **docker/dockerfile.py**: Dockerfile generator script
- **tests/**: Test suite for all Python versions
