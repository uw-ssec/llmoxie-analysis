#!/bin/bash
set -euo pipefail
cd /app
pixi install
pixi run setup
pixi run verify
pixi run okf show project/llmoxie-analysis
pixi run okf show project/current-state
pixi run okf search "caveat" --limit 5
pixi run okf show caveats/cost-token-double-counting
