#!/bin/bash
set -euo pipefail
cd /app
git tag --sort=-v:refname | head -1
git status
git pull origin main
today="$(date +%F)"
sed -i "s/^## \[Unreleased\]$/## [Unreleased]\n\n## [0.2.0] -- $today/" CHANGELOG.md
sed -i 's/^__version__ = "0.1.0"/__version__ = "0.2.0"/' src/llmoxie_analysis/__init__.py
sed -i 's/^version = "0.1.0"/version = "0.2.0"/' pixi.toml
sed -i "s/^version: 0.1.0/version: 0.2.0/; s/^date-released: .*/date-released: $today/" CITATION.cff
pixi run verify
git add CHANGELOG.md pixi.toml src/llmoxie_analysis/__init__.py CITATION.cff
git commit -q -m "chore(release): prepare v0.2.0" -m "Assisted-by: claude-code:test-model"
git tag -a v0.2.0 -m "v0.2.0"
git push origin main --follow-tags
rm -rf dist && pixi run build
gh release create v0.2.0 --title "v0.2.0" --notes "$(cat <<'EOF'
## What's Changed

- Add a DuckDB CLI subcommand

**Full Changelog**: https://github.com/example/llmoxie-analysis/compare/v0.1.0...v0.2.0
EOF
)" dist/*.whl dist/*.tar.gz
echo "Released v0.2.0"
