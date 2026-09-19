#!/bin/bash
set -euo pipefail
cd /app
git status
git log --oneline main..HEAD
git push -u origin feat/io-empty-files
