. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file mkdocs.yml 'site_name: llmoxie-analysis
nav:
  - Home: index.md
  - Guides:
      - Getting started: guides/getting-started.md' "docs: add the MkDocs site" 4
commit_file docs/index.md '# llmoxie-analysis

Analysis pipeline for LLMoxie usage data.

## Documentation

- [Getting started](guides/getting-started.md): install and run the gate.' "docs: add the index" 4
commit_file docs/guides/getting-started.md '# Getting started

Run `pixi install` then `pixi run verify`.' "docs: add the getting-started guide" 4
commit_file src/llmoxie_analysis/sessions.py '"""Sessions table.

Builds the sessions table from raw request logs: one row per conversation,
partitioned by date because ADLS listings are per-day.
"""


def build_sessions(day: str) -> int:
    """Write the sessions partition for ``day`` and return the row count."""
    return 0' "feat(pipeline): add the sessions table builder" 0
finish_fixture
