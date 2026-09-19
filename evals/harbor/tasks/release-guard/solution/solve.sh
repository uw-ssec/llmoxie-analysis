#!/bin/bash
set -euo pipefail
cd /app
git status
echo "Not on main (on feat/next-thing). Releases are cut from main only; stopping."
