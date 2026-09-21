#!/usr/bin/env bash
# Claude Code PreToolUse hook for Edit and Write.
#
# AGENTS.md asks agents to run `okf search --for-path <file>` before the first
# edit to a file. Measured across past sessions, that step was never taken by
# hand, so this hook performs it mechanically: it looks up the OKF concepts
# whose code_refs govern the file about to change and injects any hit into the
# model's context. It never blocks the edit and stays silent when nothing
# governs the file.
#
# Input: the hook payload JSON on stdin. Output: additionalContext JSON on a hit.
set -u

root="${CLAUDE_PROJECT_DIR:-$PWD}"
file="$(jq -r '.tool_input.file_path // empty')"
[ -n "$file" ] || exit 0

# Only files inside the repository can carry code_refs, and the bundle itself
# is edited through okf, not governed by it.
case "$file" in
  "$root"/*) rel="${file#"$root"/}" ;;
  *) exit 0 ;;
esac
case "$rel" in
  knowledge/*) exit 0 ;;
esac

hits="$(cd "$root" && pixi run okf search --for-path "$rel" --json 2>/dev/null)" || exit 0
count="$(printf '%s' "$hits" | jq 'if type == "array" then length else 0 end' 2>/dev/null)" || exit 0
[ "${count:-0}" -gt 0 ] || exit 0

summary="$(printf '%s' "$hits" | jq -r '.[] | "- [\(.governance // "context")] \(.concept_id): \(.description)"')"
jq -n --arg rel "$rel" --arg summary "$summary" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    additionalContext: (
      "Project memory governing \($rel) (hold = stop and confirm with the user; constraint = invariants the change must keep; run `pixi run okf show <id>` for detail):\n" + $summary
    )
  }
}'
