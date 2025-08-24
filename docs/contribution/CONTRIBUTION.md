# Contributing to OpenCrate

> First off, **thank you** for considering contributing to OpenCrate! We're thrilled you're interested in making it better. 

This document provides a complete guide for contributing, from setting up your branches to understanding how your code becomes part of an official release.

Following these guidelines helps us manage the project efficiently and respectfully. In return, we will reciprocate that respect by addressing your issue, assessing changes, and helping you finalize your pull requests.

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Core Philosophy](#-core-philosophy)
- [Development and Release Workflow](#-the-development-and-release-workflow)
- [Branching Strategy](#-branching-strategy--merge-rules)
- [Your Contribution Lifecycle](#-your-contribution-lifecycle-step-by-step)
- [The Release Cycle](#-the-release-cycle--cicd-triggers)
- [Reporting Issues](#-reporting-issues)

## 📖 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## 🎯 Core Philosophy

Our development follows these key principles:

- **`main` is always stable** - It represents the latest official release
- **Development happens in isolation** - New work is done on feature branches  
- **Pull Requests are our quality gate** - All changes are reviewed before integration
- **Automation ensures reliability** - Our CI/CD pipeline validates every step

## 🔄 The Development and Release Workflow

We use a branching model based on **GitFlow**. Understanding this model is key to contributing effectively.

## 🌳 Branching Strategy & Merge Rules

Our repository has two permanent, protected branches with strict rules:

| Branch | Purpose | Source Branch | Target Branch | Merged via |
|--------|---------|---------------|---------------|------------|
| `main` | Latest stable release code. Tagged for every official release. | `release/*` or `hotfix/*` | Never merges into other branches. | Pull Request |
| `develop` | Integration branch for the next release. Can be unstable. | `feature/*`, `fix/*`, `release/*`, `hotfix/*` | `release/*` | Pull Request or Direct Merge |

And several types of **temporary branches**:

| Branch Prefix | Purpose | Source Branch | Target Branch | Merged via |
|---------------|---------|---------------|---------------|------------|
| `feature/*` | Develop a new feature. | `develop` | `develop` | Pull Request |
| `fix/*` | Fix a non-urgent bug for the next release. | `develop` | `develop` | Pull Request |
| `release/*` | Prepare a new release (version bump, changelog). | `develop` | `main` and `develop` | Pull Request |
| `hotfix/*` | Fix a critical bug in a released version. | `main` | `main` and `develop` | Pull Request |
## ✨ Your Contribution Lifecycle: Step-by-Step

Here's how to get your code from an idea to part of the project.

### Step 1: Create Your Branch

Always start your work from the latest `develop` branch.

```bash
# Get the latest code
git checkout develop
git pull origin develop

# Create a new branch for your work
git checkout -b feature/new-authentication-flow
```

### Step 2: Code, Commit, and Push

Write your code and tests. Make small, logical commits using the [Conventional Commits](https://www.conventionalcommits.org/) standard. Push your branch to the remote frequently to back up your work.

```bash
git add .
git commit -m "feat: Add password hashing for user accounts"
git push -u origin feature/new-authentication-flow
```

### Step 3: Open a Pull Request (PR)

When your feature is complete, open a Pull Request on GitHub.

- **Target Branch**: `develop`
- **From Branch**: Your `feature/new-authentication-flow` branch

> 🔄 Opening the PR will trigger our CI pipeline. It will run `pytest` and other checks on your code.

A project maintainer will review your code. **All checks must pass** and the PR must be **approved** before it can be merged.

### Step 4: Merging

Once approved, a maintainer will **squash and merge** your PR into `develop`. This keeps the history of our main development branch clean and readable. 

🎉 **Your work is now officially part of the "next release"!**

## 🚀 The Release Cycle & CI/CD Triggers

This section explains how your merged feature becomes an official release. This process is typically handled by project maintainers.

### Phase 1: Preparing a Release

When we have enough features in `develop` for a new version, we create a release branch.

```bash
# Create release branch from develop
git checkout -b release/v1.2.0 develop
```

On this branch, we do final preparations:

- ✏️ Update the `VERSION` file
- 📝 Finalize the `CHANGELOG.md`
- 🐛 Fix any minor bugs found during testing

### Phase 2: Testing with Release Candidates (RCs)

To ensure the release is stable, we create pre-release tags on the release branch.

**Action**: A maintainer creates and pushes a tag like `v1.2.0-rc.1`.

```bash
git tag v1.2.0-rc.1
git push origin v1.2.0-rc.1
```

**🤖 CI/CD Trigger**: Pushing this tag automatically runs the full pipeline. It builds, tests, and publishes Docker images tagged with `:v1.2.0-rc.1`. This allows for broad testing by the community. 

> If bugs are found, we fix them on the release branch and push a new `rc.2` tag.

### Phase 3: The Official Release

Once an RC is approved, we perform the final release steps:

1. **📥 Merge to main**: The `release/v1.2.0` branch is merged into `main` via a Pull Request
2. **🏷️ Tag the release**: The `main` branch is tagged with the official version

**Action**: A maintainer pushes the final tag.

```bash
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

**🤖 CI/CD Trigger**: This is the **most important trigger**. Pushing the official version tag runs the final pipeline. This publishes the official `:v1.2.0` Docker images and updates the `:latest` tag.

3. **🔄 Merge back to develop**: The `release/v1.2.0` branch is merged back into `develop` to ensure any last-minute fixes are included in future development.

### Phase 4: Scheduled Maintenance

**🤖 CI/CD Trigger**: Every Sunday, our pipeline automatically runs a scheduled build. This build forces a refresh of our base images and updates our build cache, ensuring we stay on top of the latest security patches.

## 🐛 Reporting Issues

If you find a bug or have a feature idea, please check if an issue already exists. If not, open a new issue and provide as much detail as possible.

### Bug Reports 🐞

When reporting bugs, please include:

- **Environment details**: OS, Python version, OpenCrate version
- **Steps to reproduce**: Clear, numbered steps
- **Expected vs actual behavior**: What should happen vs what actually happens  
- **Error messages**: Full error output if available
- **Code samples**: Minimal reproducible example

### Feature Requests 💡

For feature requests, please describe:

- **Use case**: What problem does this solve?
- **Proposed solution**: How would you like it to work?
- **Alternatives considered**: Other ways you've thought about solving this
- **Additional context**: Screenshots, mockups, or examples

---

## 🎉 Thank You!

**Thank you again for your contribution! It's the community that makes open source great.**

> 💡 **Need help?** Don't hesitate to ask questions in our issues or discussions. We're here to help make your contribution experience smooth and enjoyable!