#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_called pixi '^[0-9]+ pixi run pytest( [^ ]+)* (tests/test_io\.py::test_empty|--lf)( |$)'
repo_git diff HEAD -- tests | grep -Eiq 'mark\.(skip|xfail)' && fail "a test was silenced"
pass "single test re-run through pixi"
