#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_called pixi '^[0-9]+ pixi install'
require shim_called pixi '^[0-9]+ pixi run setup'
require shim_called pixi '^[0-9]+ pixi run verify'
require before "$(shim_first_ts pixi 'pixi install')" "$(shim_first_ts pixi 'pixi run setup')"
require before "$(shim_first_ts pixi 'pixi run setup')" "$(shim_first_ts pixi 'pixi run verify')"
for tool in pip pip3 conda uv; do
  [ -s "$SHIM_LOG_DIR/$tool.log" ] && fail "$tool was invoked"
done
pass "pixi-only setup in the documented order"
