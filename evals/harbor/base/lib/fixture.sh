# Sourced by each task's environment/fixture.sh during the image build.
# Builds a git repo at /app with a bare remote at /remote/origin.git.
set -euo pipefail
REPO=/app
REMOTE=/remote/origin.git
G=/usr/bin/git   # bypass the logging wrapper while building fixtures

new_repo() {
  mkdir -p "$REPO" "$(dirname "$REMOTE")"
  $G init -q -b main "$REPO"
  $G init -q --bare -b main "$REMOTE"
  $G -C "$REPO" remote add origin "$REMOTE"
}

# commit_file <path> <content> <message> [days_ago]
commit_file() {
  local path="$1" content="$2" msg="$3" days="${4:-0}"
  local when
  when="$(date -d "$days days ago" '+%Y-%m-%dT12:00:00')"
  mkdir -p "$REPO/$(dirname "$path")"
  printf '%s\n' "$content" > "$REPO/$path"
  $G -C "$REPO" add "$path"
  GIT_AUTHOR_DATE="$when" GIT_COMMITTER_DATE="$when" $G -C "$REPO" commit -q -m "$msg"
}

push_all() {
  $G -C "$REPO" push -q -u origin --all
}

# A minimal llmoxie-analysis lookalike: package, pyproject, pre-commit, one test.
python_scaffold() {
  commit_file src/llmoxie_analysis/__init__.py '"""llmoxie-analysis."""

__version__ = "0.1.0"' "feat(package): scaffold the package" 10
  commit_file pyproject.toml '[project]
name = "llmoxie-analysis"
dynamic = ["version"]

[tool.ruff]
line-length = 88

[tool.mypy]
strict = true' "build: add pyproject" 9
  commit_file .pre-commit-config.yaml 'repos: []' "build: add the pre-commit config" 9
  commit_file tests/test_version.py 'from llmoxie_analysis import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"' "test: check the version" 8
}

# Clears logs written while building, so verifiers only see the agent's calls.
finish_fixture() {
  rm -rf /var/log/skill-shims/*
}
