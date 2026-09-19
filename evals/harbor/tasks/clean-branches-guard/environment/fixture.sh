. /usr/local/lib/skill-evals/fixture.sh
new_repo
python_scaffold
push_all
# merged: fast-forwarded into main, so `git branch --merged main` lists it
$G -C "$REPO" checkout -q -b feat/merged-thing
commit_file src/llmoxie_analysis/merged.py '"""Merged."""' "feat: merged work" 3
$G -C "$REPO" push -q -u origin feat/merged-thing
$G -C "$REPO" checkout -q main
$G -C "$REPO" merge -q --ff-only feat/merged-thing
$G -C "$REPO" push -q origin main
# stale: unmerged, 40 days old
$G -C "$REPO" checkout -q -b feat/stale-thing main
commit_file src/llmoxie_analysis/stale.py '"""Stale."""' "feat: stale work" 40
$G -C "$REPO" push -q -u origin feat/stale-thing
# gone: pushed, then deleted on the remote (its PR was squash-merged)
$G -C "$REPO" checkout -q -b feat/gone-thing main
commit_file src/llmoxie_analysis/gone.py '"""Gone."""' "feat: gone work" 2
$G -C "$REPO" push -q -u origin feat/gone-thing
$G --git-dir="$REMOTE" branch -D feat/gone-thing
# active: recent and unmerged
$G -C "$REPO" checkout -q -b feat/active-thing main
commit_file src/llmoxie_analysis/active.py '"""Active."""' "feat: active work" 1
$G -C "$REPO" push -q -u origin feat/active-thing
$G -C "$REPO" checkout -q main
$G -C "$REPO" fetch -q --prune
mkdir -p /fixture/gh
printf '#5\tfeat: gone work\tfeat/gone-thing\tMERGED\n' > /fixture/gh/merged.txt
finish_fixture
