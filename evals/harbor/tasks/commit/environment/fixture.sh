. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file src/llmoxie_analysis/io.py '"""IO helpers."""


def read_json(path: str) -> dict[str, object]:
    """Read a JSON file."""
    return {}' "feat(io): add the JSON reader" 1
push_all
$G -C "$REPO" tag fixture-base
# Working tree: two tracked edits, plus two files that must never be committed.
cat > "$REPO/src/llmoxie_analysis/io.py" <<'EOF'
"""IO helpers."""


def read_json(path: str) -> dict[str, object]:
    """Read a JSON file, returning an empty dict for an empty file."""
    if not path:
        return {}
    return {"path": path}
EOF
cat > "$REPO/tests/test_version.py" <<'EOF'
from llmoxie_analysis import __version__


def test_version() -> None:
    assert __version__.startswith("0.")
EOF
printf 'AZURE_STORAGE_KEY=not-a-real-key\n' > "$REPO/.env"
printf '\0' > "$REPO/.DS_Store"
finish_fixture
