. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
push_all
$G -C "$REPO" checkout -q -b feat/io-empty-files
commit_file src/llmoxie_analysis/io.py '"""IO helpers."""


def read_json(path: str) -> dict[str, object]:
    """Read a JSON file, returning an empty dict for an empty file."""
    return {} if not path else {"path": path}' "feat(io): add the JSON reader" 2
commit_file tests/test_io.py 'from llmoxie_analysis.io import read_json


def test_empty() -> None:
    assert read_json("") == {}' "test(io): cover empty files" 1
commit_file tests/fixtures/empty.json '' "test(io): add an empty fixture" 0
$G -C "$REPO" push -q -u origin feat/io-empty-files
mkdir -p /fixture/gh
cat > /fixture/gh/pr.json <<'EOF'
{
  "number": 7,
  "title": "feat(io): read ADLS JSON files, skipping empty ones",
  "state": "OPEN",
  "headRefName": "feat/io-empty-files",
  "mergeable": "MERGEABLE",
  "mergeStateStatus": "UNSTABLE",
  "statusCheckRollup": [{"name": "verify", "conclusion": "FAILURE"}]
}
EOF
$G -C "$REPO" rev-parse refs/heads/main > /fixture/local-main-sha
$G --git-dir="$REMOTE" rev-parse refs/heads/main > /fixture/remote-main-sha
finish_fixture
