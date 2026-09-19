#!/bin/bash
set -euo pipefail
cd /app
gh pr view --json number,title,state,headRefName
gh pr view 7 --json state,mergeable,mergeStateStatus,statusCheckRollup,title,headRefName
git status
gh pr merge 7 --squash --delete-branch
git checkout main
git pull origin main
git fetch --prune
git branch -d feat/io-empty-files
git branch -a | grep feat/io-empty-files || true
echo "PR #7 merged into main. Branch feat/io-empty-files deleted locally and remotely."
