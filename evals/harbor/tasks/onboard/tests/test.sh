#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh

# Stage 1: the environment gate, pixi only and in the documented order.
require shim_called pixi '^[0-9]+ pixi install'
require shim_called pixi '^[0-9]+ pixi run verify'
require before "$(shim_first_ts pixi 'pixi install')" "$(shim_first_ts pixi 'pixi run verify')"
for tool in pip pip3 conda uv; do
  [ -s "$SHIM_LOG_DIR/$tool.log" ] && fail "$tool was invoked"
done

# Stage 2: orientation came out of project memory, not guesswork.
require shim_called okf '^[0-9]+ okf show project/current-state'
require shim_called okf '^[0-9]+ okf (search|show).*caveat'

# The caveats index is a reserved bundle document; search is the way in.
require shim_not_called okf 'okf show caveats/index'

# The gate precedes orientation: later stages assume a working environment.
require before "$(shim_first_ts pixi 'pixi run verify')" "$(shim_first_ts okf 'okf show project/current-state')"

pass "environment gated first, then oriented from project memory"
