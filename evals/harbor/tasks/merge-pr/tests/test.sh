#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
merge_line="$(shim_log gh | grep -E 'gh pr merge' | head -1)"
[ -n "$merge_line" ] || fail "gh pr merge was not called"
echo "$merge_line" | grep -q -- '--squash' || fail "merge was not --squash"
echo "$merge_line" | grep -q -- '--delete-branch' || fail "merge did not --delete-branch"
[ "$(repo_git branch --show-current)" = "main" ] || fail "not on main afterwards"
branch_exists feat/io-empty-files && fail "local branch still exists"
remote_branch_exists feat/io-empty-files && fail "remote branch still exists"
require shim_not_called git 'branch -D'
pass "PR squash-merged and branch cleaned up"
