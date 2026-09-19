#!/bin/bash
set -euo pipefail
cd /app
git branch
git branch -r
git branch --merged main
git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:relative) %(upstream:track)' refs/heads/
gh pr list --state merged
git diff main..feat/gone-thing --stat
git branch -d feat/merged-thing
git push origin --delete feat/merged-thing
git branch -D feat/gone-thing
git fetch --prune
git branch
