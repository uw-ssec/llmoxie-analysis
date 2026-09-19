#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_not_called gh 'gh pr merge'
require branch_exists feat/io-empty-files
[ "$(repo_git rev-parse refs/heads/main)" = "$(cat /fixture/local-main-sha)" ] || fail "local main moved"
[ "$(remote_git rev-parse refs/heads/main)" = "$(cat /fixture/remote-main-sha)" ] || fail "remote main moved"
pass "did not merge on failing checks"
