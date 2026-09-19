. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
push_all
$G -C "$REPO" checkout -q -b feat/io-empty-files
commit_file src/llmoxie_analysis/io.py '"""IO helpers."""' "feat(io): add the io module" 1
commit_file tests/test_io.py 'def test_empty() -> None:
    assert True' "test(io): cover empty files" 0
finish_fixture
