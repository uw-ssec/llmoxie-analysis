#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
[ "$(repo_git rev-parse HEAD)" = "$(cat /fixture/head-sha)" ] || fail "a commit was created off main"
repo_git rev-parse -q --verify refs/tags/v0.2.0 >/dev/null && fail "tag created off main"
require shim_not_called gh 'gh release create'
require shim_not_called git 'push.*--follow-tags'
pass "no release from a feature branch"
