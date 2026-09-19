#!/bin/bash
. /usr/local/lib/skill-evals/verify.sh
cd "$REPO"
new_docs="$(repo_git ls-files --others --exclude-standard docs; repo_git diff --name-only --diff-filter=A HEAD -- docs)"
[ -n "$new_docs" ] || fail "no new documentation file under docs/"
for f in $new_docs; do
  rel="${f#docs/}"
  grep -q "$rel" mkdocs.yml || fail "mkdocs.yml nav does not reference $rel"
done
[ -f docs/index.md ] || fail "docs/index.md was removed"
[ -f docs/guides/getting-started.md ] || fail "an existing doc was removed"
require shim_called pixi '^[0-9]+ pixi run docs-build'
pass "new doc written, nav updated, site built"
