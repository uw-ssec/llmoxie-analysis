---
type: Reference
title: "Harness wiring: where agent definitions live and which harness reads them"
description: "Harness-neutral agent material lives under .agents/ and .claude/ holds only symlinks into it, so Claude Code discovers skills and subagents without making .claude/ the source of truth."
tags: [agents, claude-code, skills, conventions, harness]
generated: { by: "claude-code:claude-opus-5", at: "2026-09-23T14:10:13Z" }
status: draft
governance: constraint
code_refs: [AGENTS.md, ".agents/rules/**", ".agents/skills/**", .claude/settings.json, ".claude/agents/**"]
sources:
  - resource: llmoxie-analysis .claude/skills symlink and .claude/settings.json as of 2026-09-23
  - resource: Claude Code subagent discovery at .claude/agents (official documented behaviour)
---

## The layout

Agent-facing material is harness-neutral by default. Sources live under
`.agents/`; `.claude/` holds only the symlinks Claude Code needs to discover
them. The established instance is skills:

```
.claude/skills -> ../.agents/skills
```

`AGENTS.md` is the entry point every harness reads, and it delegates to
`.agents/rules/` and `.agents/skills/`. Nothing that every harness must obey
belongs only inside a `.claude/`-specific file.

## Subagents

Claude Code discovers project subagents at `.claude/agents/*.md`. The
directory name has no leading dot inside `.claude/` — a `.claude/.agents`
directory is never scanned. To follow the skills precedent:

```
mkdir -p .agents/agents
ln -s ../.agents/agents .claude/agents
```

Each definition is one markdown file with YAML frontmatter:

- `name` — kebab-case, matching the filename stem.
- `description` — the field the dispatcher matches against when deciding to
  delegate. Write it as a trigger ("Use when ..."), not as a summary.
- `tools` — optional; omitted means the subagent inherits every tool.
- `model` — optional; `sonnet`, `opus`, `haiku`, or `inherit`.

A project agent at `.claude/agents/` overrides a personal one at
`~/.claude/agents/` with the same `name`.

## Consequences worth knowing

- Only Claude Code reads `.claude/agents/`. Codex, Cursor, Copilot, and Gemini
  CLI do not. A subagent is therefore additive convenience on top of the rules
  and skills, never the only home for a behavioral rule — otherwise the rule
  silently disappears for every other harness.
- The `PreToolUse` hook registered in `.claude/settings.json` matches
  `Edit|Write|MultiEdit` for the whole session, subagents included. Any
  subagent granted write tools still passes through
  `.claude/hooks/okf-for-path.sh` and gets the project-memory check on the
  file it is about to touch.
- Skills under `.agents/skills` are covered by the two-level eval suite (see
  `project/skill-evals`). Subagent definitions are not, so a subagent that
  encodes a workflow bypasses the evidence those evals provide. Prefer a
  skill when the behavior needs to be proven.

## Status

As of 2026-09-23 the skills symlink exists and `.claude/agents/` does not.
The subagent half of this concept records the intended wiring and the reasons
for it, not the present state of the tree.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): Skills under .agents/skills carry eval coverage that subagent definitions under .claude/agents do not.
