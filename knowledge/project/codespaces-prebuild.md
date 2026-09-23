---
type: Architecture
title: Codespaces prebuilds and the devcontainer lifecycle
description: "Prebuilds bake onCreateCommand and updateContentCommand but re-run postCreateCommand on every codespace, so the expensive pixi and submodule setup must live in updateContentCommand to be cached at all."
tags: [devcontainer, codespaces, prebuild, pixi, onboarding]
generated: { by: "claude-code:claude-opus-5", at: "2026-09-23T18:45:38Z" }
status: draft
governance: constraint
code_refs: [".devcontainer/**"]
sources:
  - resource: "commit f7c00bf, branch build/codespaces-prebuild, 2026-09-23"
  - resource: "PR #15 build(devcontainer): add Codespaces setup with pixi and coding agent CLIs, 2026-09-17"
  - resource: "https://docs.github.com/en/codespaces/prebuilding-your-codespaces"
---

## The lifecycle rule

A Codespaces prebuild snapshots the container after running `onCreateCommand`
and `updateContentCommand`. It does **not** snapshot `postCreateCommand` — that
re-runs in full every time a codespace is created from the prebuild.

This is the whole game. Setup work parked in `postCreateCommand` is invisible to
a prebuild no matter how the prebuild is configured.

## How this repo is arranged

`.devcontainer/update-content.sh` (`updateContentCommand`) holds the expensive,
content-dependent work:

- `git submodule update --init --recursive` — Codespaces does not initialise
  submodules on clone, so `reference/llmoxie` and `reference/ceil-dlp` otherwise
  arrive as empty directories.
- `pixi install --all --locked` — all three environments (`default`, `onboard`,
  `evals`; roughly 1.7 GB installed). `--all` was a deliberate choice over
  baking only `default`: it costs prebuild storage and build time, in exchange
  for `pixi run -e evals` being instant. `--locked` makes a `pixi.lock` that has
  drifted from `pixi.toml` fail the prebuild loudly instead of silently
  re-solving.

`.devcontainer/post-create.sh` (`postCreateCommand`) keeps only the `~/.bashrc`
pixi shell-hook, which is idempotent and costs milliseconds.

`updateContentCommand` was chosen over `onCreateCommand` on purpose: it runs
during the prebuild *and* again at codespace creation, so a `pixi.lock` change
that landed after the last prebuild is picked up as an incremental install
rather than shipping a stale environment.

## State as of 2026-09-23

A prebuild configuration exists on `uw-ssec/llmoxie-analysis` and one prebuild
build has completed successfully (observed by the project owner).

**That build predates the script split.** It ran against a `main` carrying only
`postCreateCommand` — confirmed on 2026-09-23 by reading
`.devcontainer/devcontainer.json` on remote `main` through the contents API — so
it cached the Docker image layer (the pinned pixi binary and the four agent CLIs
from `install-agents.sh`) and nothing else. The pixi install and submodule init
still ran on every codespace start.

The split landed on `main` in the same change that added this concept. The first
prebuild to run after that is the first one that can bake the pixi environments
and submodules. If the prebuild trigger is *on configuration change*, the merge
itself should schedule it; otherwise it needs a manual run from
Settings → Codespaces.

## Not verified

No codespace has been created from a prebuild and timed. That a prebuild
actually bakes `updateContentCommand` output here is taken from GitHub's
documented lifecycle, not from an observed run in this repo. Creating a
codespace after the next prebuild completes and checking that `.pixi/` and
`reference/*` are already populated on attach would confirm it.

## Prebuild configuration is UI-only

There is no public REST endpoint for prebuild configurations —
`GET /repos/{owner}/{repo}/codespaces/prebuilds` returns 404. It is managed at
**Settings → Codespaces → Prebuild configuration**. Recommended triggers: *on
configuration change* (catches `.devcontainer/**` and `pixi.lock` edits) plus a
weekly schedule, since `install-agents.sh` pulls the agent CLIs from unpinned
upstream installers that only move on a rebuild.

# Related Concepts
- [Pixi Task and Verify Gate Quirks](pixi-gate-quirks.md): The prebuild bakes all three pixi environments, so the pixi gate quirks apply to what a prebuilt codespace ships with
