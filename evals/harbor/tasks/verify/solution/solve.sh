#!/bin/bash
set -euo pipefail
cd /app
git status
pixi run verify
