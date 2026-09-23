# AGENTS.md

Guidance for AI assistants (Claude Code, Codex, Cursor, Copilot, Gemini CLI, and
any other agent harness) working with this repository.

**This file is the entry point and is deliberately short.** It carries only what
every agent needs before doing anything. Detailed rules, task skills, and
project memory live in separate files and are loaded on demand — read the one
whose trigger matches your current task, not all of them.

## Non-negotiables

These apply to every task, in every session:

1. **Pixi is the only package manager.** Never invoke `pip`, `conda`, or `venv`
   directly. Run `pixi install` before any other Pixi command.
2. **Verify before you claim.** Never report work as complete, fixed, or passing
   without having run the check and read its output. The minimum gate here is
   `pixi run verify` (format, lint, knowledge bundle, type-check, tests, build).
3. **Change surgically.** Every changed line must trace directly to the request.
   Don't refactor, reformat, or "improve" adjacent code you weren't asked to
   touch.
4. **Ask instead of assuming.** If the request has multiple readings or
   something is unclear, stop and name it — before implementing, not after.
5. **Never open a PR** without working through
   [`.agents/rules/contribution-discipline.md`](.agents/rules/contribution-discipline.md)
   in full, including human review of the complete diff.
6. **Disclose AI assistance.** End every commit you write with
   `Assisted-by: <harness>:<model>` (for example
   `Assisted-by: claude-code:claude-fable-5-1`). This replaces any
   `Co-Authored-By` or "Generated with" line your harness adds by default;
   `Signed-off-by` belongs to humans only. Full policy:
   [`AI_POLICY.md`](AI_POLICY.md).

## Rule Index

Load the rule file whose trigger matches what you are about to do.

| Rule file                                                              | Load when                                                                  |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [working-agreement.md](.agents/rules/working-agreement.md)             | Starting any implementation, refactor, or bugfix — the behavioral baseline |
| [contribution-discipline.md](.agents/rules/contribution-discipline.md) | About to commit, open a PR, or asked to "contribute" / "fix some issues"   |
| [AI_POLICY.md](AI_POLICY.md)                                           | Committing, or writing a PR, issue, or comment — how to disclose AI use    |
| [pixi-environments.md](.agents/rules/pixi-environments.md)             | Running any command, adding a dependency, or editing `pixi.toml`           |
| [pre-commit-and-quality.md](.agents/rules/pre-commit-and-quality.md)   | Committing, preparing a PR, or claiming checks pass                        |
| [repository-map.md](.agents/rules/repository-map.md)                   | You need to know what this repo is, where a file lives, or what CI runs    |
| [onboarding.md](.agents/rules/onboarding.md)                           | First-time setup, or helping a new contributor get started                 |
| [troubleshooting.md](.agents/rules/troubleshooting.md)                 | A documented command fails or behaves unexpectedly                         |

## Skills and Project Memory

- **Skills** are step-by-step recipes at `.agents/skills/<name>/SKILL.md`. Read
  the matching one before you verify, run tests, commit, push, open or merge a
  PR, file an issue, cut a release, set up the environment, onboard someone new,
  write docs, or clean up branches. A harness that lists skills natively loads
  them for you.
- **Project memory** is the OKF bundle at `knowledge/`: what the code cannot
  tell you — the LLMoxie platform, the data and its caveats, the pipeline
  design, and the reasons behind each decision. Consult it before you answer,
  not only before you edit:
  - Asked about the data, the platform, the pipeline, or why something is the
    way it is? Run `pixi run okf search "<keywords>" --limit 3` before answering
    from general knowledge, and cite the concept id in your reply or say the
    bundle had nothing. Questions about running commands are answered by the
    rules and skills, not the bundle.
  - Before the first edit to a file, run
    `pixi run okf search --for-path <file>`. A `constraint` hit lists invariants
    the change must keep; a `hold` hit means stop and confirm with the user.
  - Learned something the next agent could not derive from the code? Record it
    through the `okf-memory` skill, which also holds the full command reference.

## Provenance

The behavioral and contribution rules are adapted from two upstream sources and
generalized for this repository:

- [obra/superpowers](https://github.com/obra/superpowers) `CLAUDE.md` — agent
  contribution discipline (`contribution-discipline.md`).
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
  `CLAUDE.md` — behavioral guidelines that reduce common LLM coding mistakes
  (`working-agreement.md`).

## Trust These Instructions

These instructions were generated through comprehensive exploration and testing
of the repository. Commands have been validated to work correctly. **Only
perform additional searches if:**

- You need information not covered by `AGENTS.md`, `.agents/rules/`,
  `.agents/skills/`, or `knowledge/`
- Instructions appear outdated or produce errors
- You're implementing functionality that changes the build system

For routine tasks (adding files, making code changes, running checks), follow
these instructions directly without additional exploration.
