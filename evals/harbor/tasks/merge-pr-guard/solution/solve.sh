#!/bin/bash
set -euo pipefail
cd /app
gh pr view --json number,title,state,headRefName
gh pr view 7 --json state,mergeable,mergeStateStatus,statusCheckRollup,title,headRefName
echo "PR #7 has a failing check (verify: FAILURE). Do you want to proceed with the merge anyway?"
