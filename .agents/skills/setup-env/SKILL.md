---
name: setup-env
description:
  Use when setting up this repository on a new machine, container, or Codespace,
  when a documented command fails with "not found", or when the environment
  needs resetting to a clean state.
---

# Setup Env

Bring a fresh clone to the state where `pixi run verify` passes.

## Instructions

1. **Pixi is the only toolchain.** `pixi --version` must print 0.49 or newer (CI
   and the devcontainer pin v0.81.0). If it is missing, install it from
   https://pixi.sh/latest/#installation. Never use `pip`, `conda`, `uv`, or
   `venv` directly.

2. **Install the environment:**

   ```bash
   pixi install
   ```

   Solves the `default` environment from `pixi.lock` (Python, pytest, ruff,
   mypy, build, pre-commit, GitHub CLI) and installs `llmoxie_analysis` as an
   editable package. Idempotent; rerun after any `pixi.toml` change.

3. **One-time repository setup:**

   ```bash
   pixi run setup
   ```

   Installs the git pre-commit hook and pulls the read-only submodules under
   `reference/` (`llmoxie`, the source project the pipeline ports code from;
   `ceil-dlp`, a LiteLLM callback plugin kept for its LiteLLM internals).

4. **Smoke test:**

   ```bash
   pixi run verify
   ```

   Exit 0 means the environment is complete.

## Reset to clean

```bash
rm -rf .pixi dist .mypy_cache .ruff_cache .pytest_cache
pixi install && pixi run setup && pixi run verify
```

## Secrets and environment variables

None are needed today. Pipeline work against live LLMoxie deployments will take
LiteLLM and Azure Storage credentials through an `--env-file`; keep them in a
gitignored `.env*` file and never in `pixi.toml`, tests, or fixtures.

## New contributors

`pixi run -e onboard onboard` runs the SSEC onboarding flow (`ssec` CLI and
shell completion). Details in `.agents/rules/onboarding.md`.

## Done

`pixi run verify` exited 0 on this machine and its final lines are in your
report.
