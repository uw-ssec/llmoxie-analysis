#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
cd "$REPO"
grep -q '^__version__ = "0.2.0"' src/llmoxie_analysis/__init__.py || fail "__init__.py not bumped"
grep -q '^version = "0.2.0"' pixi.toml || fail "pixi.toml not bumped"
grep -q '^version: 0.2.0' CITATION.cff || fail "CITATION.cff not bumped"
today="$(date +%F)"
grep -Eq "^## \[0\.2\.0\] -- $today" CHANGELOG.md || fail "changelog lacks [0.2.0] -- $today"
unreleased_line="$(grep -n '^## \[Unreleased\]' CHANGELOG.md | head -1 | cut -d: -f1)"
release_line="$(grep -n '^## \[0\.2\.0\]' CHANGELOG.md | head -1 | cut -d: -f1)"
[ -n "$unreleased_line" ] && [ "$unreleased_line" -lt "$release_line" ] || fail "no fresh [Unreleased] above [0.2.0]"
[ "$(repo_git rev-parse 'v0.2.0^{commit}' 2>/dev/null)" = "$(repo_git rev-parse HEAD)" ] || fail "tag v0.2.0 is not on HEAD"
[ "$(repo_git log -1 --format=%s)" = "chore(release): prepare v0.2.0" ] || fail "release commit subject wrong"
require commit_has_trailer HEAD '^Assisted-by: claude-code:test-model'
remote_git rev-parse -q --verify refs/tags/v0.2.0 >/dev/null || fail "tag not pushed"
[ "$(remote_git rev-parse refs/heads/main)" = "$(repo_git rev-parse HEAD)" ] || fail "main not pushed"
require shim_called pixi '^[0-9]+ pixi run verify'
require shim_called pixi '^[0-9]+ pixi run build'
require shim_called gh '^[0-9]+ gh release create v0.2.0 .*dist/llmoxie_analysis-0.2.0-py3-none-any.whl'
require shim_called gh '^[0-9]+ gh release create v0.2.0 .*dist/llmoxie_analysis-0.2.0.tar.gz'
shim_args_have gh 'Generated with' && fail "marketing line in the release notes"
repo_git ls-files dist | grep -q . && fail "dist/ was committed"
pass "v0.2.0 released end to end"
