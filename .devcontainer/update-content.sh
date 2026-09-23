#!/usr/bin/env bash
# Fetch repository content that the image cannot carry: the git submodules and
# the pixi environments.
#
# This runs as the devcontainer "updateContentCommand", which means it executes
# both while a Codespaces prebuild is being built (so the result is baked into
# the prebuild image) and again when a codespace is created from that image (so
# a pixi.lock change landed after the last prebuild is still picked up, as an
# incremental install rather than a full one).
set -euo pipefail

GREEN="\033[0;32m"
BOLD="\033[1m"
RESET="\033[0m"

STAGE="update-content"

say()  { printf "%b\n==> [%s] %s%b\n" "${BOLD}${GREEN}" "${STAGE}" "$*" "${RESET}"; }
info() { printf "      %s\n" "$*"; }

say "$(pixi --version)"

# Codespaces does not initialise submodules on clone, so reference/ would
# otherwise be a set of empty directories.
if [ -f .gitmodules ]; then
  say "Initialising git submodules"
  git submodule update --init --recursive
else
  info "No .gitmodules found; skipping submodule init"
fi

if [ -f pixi.toml ] || [ -f pyproject.toml ]; then
  say "Installing all pixi environments"
  # --all: default, onboard, and evals are all baked into the prebuild.
  # --locked: fail loudly if pixi.lock has drifted from pixi.toml rather than
  # silently re-solving during a prebuild.
  pixi install --all --locked
else
  info "No pixi.toml or pyproject.toml found; skipping pixi install"
fi

say "complete"
