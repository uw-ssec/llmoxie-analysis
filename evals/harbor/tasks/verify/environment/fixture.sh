. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
printf '"""llmoxie-analysis."""\n\n__version__ = "0.1.0"\n__all__ = ["__version__"]\n' > "$REPO/src/llmoxie_analysis/__init__.py"
$G -C "$REPO" add src/llmoxie_analysis/__init__.py
finish_fixture
