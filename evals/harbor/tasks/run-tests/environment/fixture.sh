. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file src/llmoxie_analysis/io.py '"""IO helpers."""


def read_json(path: str) -> dict[str, object]:
    """Read a JSON file."""
    return {"path": path}' "feat(io): add the JSON reader" 1
commit_file tests/test_io.py 'from llmoxie_analysis.io import read_json


def test_empty() -> None:
    assert read_json("") == {}' "test(io): cover empty files" 0
finish_fixture
