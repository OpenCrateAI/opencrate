# Docker Build, Test, and Push Workflow Documentation

## Overview

This GitHub Actions workflow automates the process of building, testing, and publishing OpenCrate Docker images for multiple Python versions (3.7-3.13) and runtime configurations (CPU and CUDA). The workflow ensures that all images are thoroughly tested before being pushed to Docker Hub.

## Workflow Triggers

The workflow runs automatically under three different scenarios:

### 1. Version Tag Push (Release)
```yaml
push:
  tags:
    - 'v*.*.*'
```
- **When**: A new version tag matching the pattern `v*.*.*` is pushed (e.g., `v0.1.0-rc`, `v1.2.3`)
- **Purpose**: Build, test, and publish official release images
- **Outcome**: Images are pushed to Docker Hub and tagged as "latest"

### 2. Scheduled Weekly Build
```yaml
schedule:
  - cron: '0 3 * * 0'
```
- **When**: Every Sunday at 3:00 AM UTC
- **Purpose**: Keep images fresh with latest base layers and security updates
- **Outcome**: Images are rebuilt and pushed, but NOT tagged as "latest"

### 3. Manual Trigger
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
3. Set up Python 3.10
4. Generate Dockerfiles for all Python versions and runtimes
5. Upload generated Dockerfiles as artifacts

**Outputs**:
- `version`: The version string from the VERSION file
- `rebuild_flag`: Whether to force rebuild base layers (`true` for scheduled/tag pushes)

### Job 2: `build-and-test`
**Purpose**: Build and test images for all configurations in parallel

**Matrix Strategy**: Runs 14 parallel jobs (2 runtimes × 7 Python versions)
- Runtimes: `cpu`, `cuda`
- Python versions: `3.7`, `3.8`, `3.9`, `3.10`, `3.11`, `3.12`, `3.13`

**Steps**:
1. **Setup**:
   - Checkout repository
   - Download generated Dockerfiles
   - Set up QEMU (for ARM64 support)
   - Set up Docker Buildx
   - Login to Docker Hub

2. **Build Local Test Image**:
   - Platform: `linux/amd64` only (faster for testing)
   - Uses layer caching from registry
   - Image tag: `braindotai/opencrate-{runtime}-py{version}:{VERSION}`
   - Example: `braindotai/opencrate-cpu-py3.10:v0.1.0-rc`

3. **Clean Up Storage**:
   - Prune Docker buildx cache
   - Clean apt cache

4. **Test Local Image**:
   - Run tests inside the freshly built Docker container
   - Tests include: ruff linting, mypy type checking, pytest
   - Logs are saved to `./tests/logs/test-py{version}-{runtime}.log`

5. **Upload Test Logs**:
   - Upload logs as artifacts (runs even if tests fail)
   - Artifact name: `test-logs-{runtime}-py{version}`
   - Example: `test-logs-cuda-py3.11`

6. **Build and Push Multi-Platform Image** (only if tests pass):
   - Platforms: `linux/amd64`, `linux/arm64`
   - Pushed to Docker Hub with version tag
   - Updates build cache in registry

### Job 3: `release-latest`
**Purpose**: Tag successful builds as "latest"

**Condition**: Only runs if:
- All build-and-test jobs succeeded AND
- Triggered by a version tag push (NOT scheduled or manual)

**Steps**:
1. Login to Docker Hub
2. Tag all images with "latest" tag
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

#### Scenario 4: Testing Without Publishing
If you want to test the workflow without publishing:

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

The workflow uses Docker BuildKit caching to speed up builds with **per-Python-version cache images** to avoid parallel write conflicts.

### Cache Images
Each Python version and runtime combination has its own dedicated cache image:
- `braindotai/opencrate-build-cache:cpu-py3.7`
- `braindotai/opencrate-build-cache:cpu-py3.8`
- `braindotai/opencrate-build-cache:cpu-py3.9`
- ... (and so on for all Python versions)
- `braindotai/opencrate-build-cache:cuda-py3.7`
- `braindotai/opencrate-build-cache:cuda-py3.8`
- ... (etc.)

**Why per-version caches?**
- ✓ Prevents parallel write conflicts in matrix builds
- ✓ Better cache hit rates (each Python version gets its optimal cache)
- ✓ No race conditions during concurrent builds
- ✓ Each build can safely update its own cache

### Cache Behavior
- **Normal builds**: Use existing cache layers from the specific Python version's cache
- **Force rebuild** (`REBUILD_BASE=true`): Pull fresh base images and update the version-specific cache
- **Scheduled builds**: Automatically force rebuild to get security updates

### When to Force Rebuild
- Base images have critical security updates
- Want to test with latest dependencies
- Cache corruption suspected
- Weekly refresh (automatic)

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

### ❌ DON'T
- Don't create tags without updating VERSION file
- Don't push tags for untested code
- Don't manually edit Dockerfiles in `docker/dockerfiles/` (they're auto-generated)
- Don't tag experimental features as "latest" (use pre-release suffixes)
- Don't force rebuild unless necessary (wastes CI time)

## Monitoring and Notifications

### Success Indicators
- ✓ All 14 matrix jobs complete successfully
- ✓ Images pushed to Docker Hub
- ✓ "latest" tags updated (for tag pushes only)

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

## Questions or Issues?

If you encounter problems with the workflow:
1. Check this documentation
2. Review test logs in Artifacts
3. Test locally using Makefile targets
4. Open an issue with workflow run link and error logs
