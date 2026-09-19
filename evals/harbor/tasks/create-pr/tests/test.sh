#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_called pixi '^[0-9]+ pixi run verify'
require shim_called gh '^[0-9]+ gh pr create'
require before "$(shim_first_ts pixi 'pixi run verify')" "$(shim_first_ts gh 'gh pr create')"
title="$(shim_arg gh --title)"
[ -n "$title" ] || fail "gh pr create had no --title"
echo "$title" | grep -Eq '^(feat|fix|refactor|docs|chore|perf|ci|build|test)\([a-z0-9-]+\): [a-z]' || fail "title is not conventional: $title"
[ "${#title}" -lt 70 ] || fail "title is ${#title} chars"
require shim_args_have gh '^## Test plan'
require shim_args_have gh '^- \[ \]'
shim_args_have gh 'Generated with' && fail "marketing line in the PR body"
require remote_branch_exists feat/io-empty-files
pass "PR opened after a green gate"
