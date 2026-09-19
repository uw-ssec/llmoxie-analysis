# Shared by every fake CLI. Sourced, not executed. bash 3.2 compatible.
SHIM_LOG_DIR="${SKILL_SHIM_LOG_DIR:-/var/log/skill-shims}"
SHIM_FIXTURE_DIR="${SKILL_SHIM_FIXTURE_DIR:-/fixture}"
SHIM_REMOTE="${SKILL_SHIM_REMOTE:-/remote/origin.git}"
SHIM_GIT="${SKILL_SHIM_GIT:-/usr/bin/git}"

# shim_record <tool> "$@" -- append the call to <tool>.log (one line, embedded
# newlines flattened) and <tool>.args (one argument per line, for exact lookups).
shim_record() {
  local tool="$1"
  shift
  local ts
  ts="$(date +%s)"
  mkdir -p "$SHIM_LOG_DIR"
  printf '%s %s %s\n' "$ts" "$tool" "$(printf '%s ' "$@" | tr '\n' ' ')" >> "$SHIM_LOG_DIR/$tool.log"
  {
    printf -- '--- %s %s\n' "$ts" "$tool"
    printf '%s\n' "$@"
    printf -- '---\n'
  } >> "$SHIM_LOG_DIR/$tool.args"
}
