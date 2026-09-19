#!/bin/bash
# Self-test for the fake CLIs. Runs on the host (bash 3.2 or newer, no Docker):
# points the shims at a temp dir and exercises each branch of behaviour.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export SKILL_SHIM_LIB="$here/../lib/shimlib.sh"
export SKILL_SHIM_LOG_DIR="$tmp/logs"
export SKILL_SHIM_FIXTURE_DIR="$tmp/fixture"
export SKILL_SHIM_REMOTE="$tmp/origin.git"
export SKILL_SHIM_GIT="$(command -v git)"
PATH="$here:$PATH"
fails=0
check() { if "$@"; then :; else echo "not ok: $*"; fails=$((fails + 1)); fi; }
check_not() { if "$@"; then echo "not ok (expected failure): $*"; fails=$((fails + 1)); fi; }
mkdir -p "$tmp/fixture/gh" "$tmp/fixture/pixi" "$tmp/fixture/okf" "$tmp/work"
cd "$tmp/work"

# gh: canned URLs, args logged one per line, one-line log with a timestamp
check test "$(gh issue create --title 'fix(io): x' --body "$(printf '## Summary\nbody\n')")" = "https://github.com/example/llmoxie-analysis/issues/42"
check grep -Eq '^[0-9]+ gh issue create --title' "$SKILL_SHIM_LOG_DIR/gh.log"
check grep -q '^## Summary' "$SKILL_SHIM_LOG_DIR/gh.args"
printf '{\n  "number": 7,\n  "headRefName": "feat/x"\n}\n' > "$tmp/fixture/gh/pr.json"
check test "$(gh pr view 7 --json number)" = "$(cat "$tmp/fixture/gh/pr.json")"
# gh pr merge: remote main fast-forwards to the head branch, head branch dropped
"$SKILL_SHIM_GIT" init -q --bare -b main "$SKILL_SHIM_REMOTE"
"$SKILL_SHIM_GIT" init -q -b main repo
"$SKILL_SHIM_GIT" -C repo -c user.name=t -c user.email=t@e commit -q --allow-empty -m base
"$SKILL_SHIM_GIT" -C repo push -q "$SKILL_SHIM_REMOTE" main
"$SKILL_SHIM_GIT" -C repo checkout -q -b feat/x
"$SKILL_SHIM_GIT" -C repo -c user.name=t -c user.email=t@e commit -q --allow-empty -m feature
"$SKILL_SHIM_GIT" -C repo push -q "$SKILL_SHIM_REMOTE" feat/x
gh pr merge 7 --squash --delete-branch >/dev/null
check test "$("$SKILL_SHIM_GIT" --git-dir="$SKILL_SHIM_REMOTE" rev-parse main)" = "$("$SKILL_SHIM_GIT" -C repo rev-parse feat/x)"
check_not "$SKILL_SHIM_GIT" --git-dir="$SKILL_SHIM_REMOTE" show-ref --verify --quiet refs/heads/feat/x

# pixi: success by default, verify fails on the fixture flag, build writes dist/
check test "$(pixi --version)" = "pixi 0.81.0"
check pixi run verify >/dev/null
touch "$tmp/fixture/pixi/verify-fails"
check_not pixi run verify >/dev/null
rm "$tmp/fixture/pixi/verify-fails"
mkdir -p src/llmoxie_analysis
printf '__version__ = "0.2.0"\n' > src/llmoxie_analysis/__init__.py
pixi run build >/dev/null
check test -f dist/llmoxie_analysis-0.2.0-py3-none-any.whl
check test -f dist/llmoxie_analysis-0.2.0.tar.gz
check grep -q '1 passed' <<<"$(pixi run pytest tests/test_io.py::test_empty -vv)"
check grep -Eq '^[0-9]+ pixi run pytest tests/test_io.py::test_empty -vv' "$SKILL_SHIM_LOG_DIR/pixi.log"

# okf: search from fixture, create/update touch knowledge/, unknown id fails
printf 'decisions/x  Decision  x\n' > "$tmp/fixture/okf/search.txt"
check grep -q 'decisions/x' <<<"$(okf search anything)"
okf create decisions/y --type Decision --title "Y" --desc "why y" --body "Body" --actor a:b >/dev/null
check grep -q '^description: why y' knowledge/decisions/y.md
okf update decisions/y --desc "new desc" --body "more" >/dev/null
check grep -q '^description: new desc' knowledge/decisions/y.md
check grep -q '^more' knowledge/decisions/y.md
check_not okf update decisions/missing --desc d 2>/dev/null
check grep -Eq ' okf validate' <<<"$(pixi run okf validate --strict --drift; cat "$SKILL_SHIM_LOG_DIR/okf.log")"

# git wrapper logs then delegates; forbidden shim logs then fails
check grep -q 'git version' <<<"$("$here/git" --version)"
check grep -Eq '^[0-9]+ git --version' "$SKILL_SHIM_LOG_DIR/git.log"
check_not "$here/forbidden" install x 2>/dev/null
check test -s "$SKILL_SHIM_LOG_DIR/forbidden.log"

if [ "$fails" -eq 0 ]; then echo "shims ok"; else echo "$fails shim checks failed"; exit 1; fi
