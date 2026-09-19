#!/bin/bash
set -euo pipefail
cd /app
gh issue create --title "fix(io): skip empty ADLS JSON files instead of crashing" --body "$(cat <<'EOF'
## Summary

The ADLS reader raises on zero-byte JSON files instead of skipping them.

## Requirements

- [ ] Skip empty files
- [ ] Log a warning that names the file path
EOF
)"
