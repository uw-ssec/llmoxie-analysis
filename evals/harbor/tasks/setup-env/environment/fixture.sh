. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
commit_file .gitmodules '[submodule "reference/llmoxie"]
	path = reference/llmoxie
	url = https://github.com/example/llmoxie.git' "chore(reference): add the llmoxie submodule" 5
finish_fixture
