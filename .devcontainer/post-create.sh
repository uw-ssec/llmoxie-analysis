#!/usr/bin/env bash
# Auto-activate the pixi environment in interactive shells.
#
# This runs as the devcontainer "postCreateCommand", which is *not* baked into a
# Codespaces prebuild -- it re-runs on every codespace. Keep it cheap: the
# expensive, cacheable work (submodules and pixi environments) lives in
# update-content.sh so the prebuild can carry it.
set -euo pipefail

GREEN="\033[0;32m"
BOLD="\033[1m"
RESET="\033[0m"

STAGE="post-create"

say()  { printf "%b\n==> [%s] %s%b\n" "${BOLD}${GREEN}" "${STAGE}" "$*" "${RESET}"; }
info() { printf "      %s\n" "$*"; }

if [ ! -f pixi.toml ] && [ ! -f pyproject.toml ]; then
  info "No pixi.toml or pyproject.toml found; skipping shell auto-activation"
  exit 0
fi

say "Configuring shell auto-activation of the pixi env"
BASHRC="${HOME}/.bashrc"
HOOK_MARKER='# >>> pixi shell-hook (llmoxie-analysis) >>>'
if ! grep -qF "${HOOK_MARKER}" "${BASHRC}" 2>/dev/null; then
  {
    echo ""
    echo "${HOOK_MARKER}"
    echo 'if [ -z "${PIXI_ENVIRONMENT_NAME:-}" ]; then'
    pixi shell-hook
    echo 'fi'
    echo "# <<< pixi shell-hook (llmoxie-analysis) <<<"
  } >> "${BASHRC}"
  info "Added pixi shell-hook to ~/.bashrc"
else
  info "~/.bashrc already has the pixi shell-hook"
fi

say "complete"
