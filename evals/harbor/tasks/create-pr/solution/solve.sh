#!/bin/bash
set -euo pipefail
cd /app
git status
git diff --stat
git branch --show-current
git log --oneline main..HEAD
git diff main...HEAD --stat
pixi run verify
gh pr create --title "feat(io): read ADLS JSON files, skipping empty ones" --body "$(cat <<'EOF'
## Summary
- Add the JSON reader for ADLS extracts and make it tolerate empty files

## Changes
- io: add `read_json`
- tests: cover the empty-file case with a fixture

## Test plan
- [ ] `pixi run verify` exits 0 (Successfully built llmoxie_analysis-0.1.0-py3-none-any.whl)
- [ ] `tests/test_io.py::test_empty` passes

## AI assistance disclosure
claude-code:test-model
EOF
)"
