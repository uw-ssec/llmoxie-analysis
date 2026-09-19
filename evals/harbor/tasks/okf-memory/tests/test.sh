#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_called okf '^[0-9]+ okf search'
first_write="$(shim_log okf | grep -E ' okf (create|update|relate)' | head -1 | cut -d' ' -f1)"
require before "$(shim_first_ts okf 'okf search')" "$first_write"
require shim_called okf '^[0-9]+ okf update decisions/parquet-partitioning'
require shim_not_called okf 'okf create decisions/parquet-partitioning'
require shim_called okf '^[0-9]+ okf validate'
grep -Eiq 'per-day|per day' "$REPO/knowledge/decisions/parquet-partitioning.md" || fail "concept was not updated with the reasoning"
pass "existing concept refined through okf"
