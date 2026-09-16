# Pixi Environments & Dependencies

**Load when:** setting up the repo, running any command, adding or changing a
dependency, or editing `pixi.toml`.

## Pixi Overview

This project uses **Pixi** exclusively for dependency and environment
management. Pixi is a modern package manager that handles both Conda and PyPI
dependencies. See https://pixi.sh/latest/llms-full.txt for more details.

**ALWAYS use Pixi commands — never use conda, pip, or venv directly.**

## Prerequisites

Before any other operations, verify Pixi is installed:

```bash
pixi --version  # Should show v0.49.0 or higher
```

If not installed, direct users to: https://pixi.sh/latest/#installation

## Environment Setup (ALWAYS RUN FIRST)

```bash
# Install the default environment (required before any other commands)
pixi install

# This installs:
# - pre-commit (>=4.3.0)
# - gh (GitHub CLI, >=2.0.0)
# - Creates .pixi/envs/default directory
```

**CRITICAL:** Always run `pixi install` before any other Pixi commands. This
command is idempotent and safe to run multiple times.

## Available Environments

1. **`default`** (features: `pre-commit`, `gh-cli`)

   - Standard development environment
   - Use for: general development, running pre-commit checks

2. **`onboard`** (features: `pre-commit`, `gh-cli`, `onboard`)
   - Extended environment with onboarding tools
   - Includes: ssec-cli (installed from GitHub)
   - Use for: first-time setup, onboarding new contributors

## Adding Dependencies

```bash
# Add a conda package and update pixi.toml
pixi add <package-name>

# Add a PyPI package
pixi add --pypi <package-name>

# Add to a specific feature
pixi add --feature <feature-name> <package-name>

# Always run after manual pixi.toml edits
pixi install
```

Adding a dependency to this template needs justification — see
[contribution-discipline.md](contribution-discipline.md).

## pixi.toml Structure

- **`[workspace]`**: Project metadata (name, version, authors, platforms)
- **`[environments]`**: Named environments with feature sets
- **`[dependencies]`**: Conda dependencies for all environments
- **`[pypi-dependencies]`**: PyPI dependencies for all environments
- **`[feature.<name>.dependencies]`**: Feature-specific conda packages
- **`[feature.<name>.pypi-dependencies]`**: Feature-specific PyPI packages
- **`[feature.<name>.tasks]`**: Feature-specific Pixi tasks

## Available Pixi Tasks

Run `pixi task list` to see all available tasks:

- `pre-commit-install`: Install git hooks
- `pre-commit`: Run checks on staged files
- `pre-commit-all`: Run checks on all files
- `ssec-setup`: Set up ssec CLI completion (onboard env only)
- `onboard`: Full onboarding process (onboard env only)

## GitHub CLI Usage

```bash
# Check GitHub CLI version
pixi run gh --version
# ✓ Should show v2.81.0 or higher

# Use GitHub CLI for any repo operations
pixi run gh <command>
# Examples: gh issue list, gh pr create, etc.
```
