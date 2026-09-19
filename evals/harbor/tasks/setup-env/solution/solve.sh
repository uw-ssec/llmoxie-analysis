#!/bin/bash
set -euo pipefail
cd /app
pixi --version
pixi install
pixi run setup
pixi run verify
