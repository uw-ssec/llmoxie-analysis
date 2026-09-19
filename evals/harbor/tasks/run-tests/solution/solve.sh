#!/bin/bash
set -euo pipefail
cd /app
pixi run pytest tests/test_io.py::test_empty -vv
