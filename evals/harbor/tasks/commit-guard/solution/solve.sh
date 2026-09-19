#!/bin/bash
set -uo pipefail
cd /app
git status
git add src/llmoxie_analysis/io.py tests/test_version.py
if ! pixi run verify; then
  echo "The verify gate failed; not committing. The ruff error above needs fixing first."
fi
