. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file pixi.toml '[workspace]
name = "llmoxie-analysis"
version = "0.1.0"' "build: add the pixi manifest" 7
commit_file CITATION.cff 'cff-version: 1.2.0
title: llmoxie-analysis
version: 0.1.0
date-released: 2026-01-15' "docs: add citation metadata" 7
commit_file CHANGELOG.md '# Changelog

## [Unreleased]

## [0.1.0] -- 2026-01-15

- Initial release' "docs: start the changelog" 7
$G -C "$REPO" tag -a v0.1.0 -m "v0.1.0"
commit_file src/llmoxie_analysis/cli.py '"""CLI."""


def main() -> None:
    """Run the DuckDB subcommand."""' "feat(cli): add a DuckDB subcommand" 2
commit_file CHANGELOG.md '# Changelog

## [Unreleased]

- Add a DuckDB CLI subcommand

## [0.1.0] -- 2026-01-15

- Initial release' "docs(changelog): note the DuckDB subcommand" 1
push_all
$G -C "$REPO" push -q origin --tags
$G -C "$REPO" checkout -q -b feat/next-thing
$G -C "$REPO" rev-parse HEAD > /fixture/head-sha
finish_fixture
