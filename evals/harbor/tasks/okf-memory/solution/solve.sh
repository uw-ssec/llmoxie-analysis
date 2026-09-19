#!/bin/bash
set -euo pipefail
cd /app
pixi run okf search "parquet partition date" --limit 3
pixi run okf search --for-path src/llmoxie_analysis/sessions.py
pixi run okf show decisions/parquet-partitioning
pixi run okf update decisions/parquet-partitioning \
  --body "Why: ADLS listings are per-day, so a date partition maps one listing to one write." \
  --actor claude-code:test-model
pixi run okf validate --strict --drift
