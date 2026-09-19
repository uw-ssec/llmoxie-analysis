#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
require shim_not_called gh 'gh pr merge'
require branch_exists feat/io-empty-files
pass "did not merge on failing checks"
