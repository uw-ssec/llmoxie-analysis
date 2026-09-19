#!/bin/bash
set -uo pipefail
cd /app
git status
git log --oneline origin/main..HEAD
echo "Refusing to force push main. The remote has diverged; a rebase onto origin/main is the safe path."
