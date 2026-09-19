---
type: Fact
title: Lessons for Writing Verifiers and Sample Rules
description: "Each rule for a Harbor verifier or an Inspect sample that was learned from a concrete failure: positive guard checks, state anchors, command shapes, and the formatter traps that corrupt eval files."
tags: [evals, verifiers, samples, guards, prettier, codespell]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T05:49:37Z" }
governance: constraint
code_refs: ["evals/harbor/tasks/**", "evals/inspect/samples/**"]
sources:
  - resource: "PR #42 task reviews and the whole-branch review, 2026-09-18 to 2026-09-19"
  - resource: Harbor nop-agent runs and Inspect real-model runs on 2026-09-19
---

Rules for writing a Harbor task or an Inspect sample file that hold up under
review and under a real model. Each one was learned from a concrete failure
during the skill-evals work (PR #42, 2026-09-18 to 2026-09-19).

## Verifiers (`evals/harbor/tasks/*/tests/test.sh`)

- **A guard needs one positive check.** A verifier made only of "X did not
  happen" scores 1.0 for an agent that crashed or did nothing. Every guard now
  also requires evidence the agent inspected state (`gh pr view`, `git status`,
  `git branch`).
- **Anchor guards on state, not on the absence of a command.** The merge-pr
  guard once passed an agent that merged by hand with `git merge` because it
  only checked that `gh pr merge` was never called; it now compares the local
  and remote `main` SHAs captured by the fixture.
- **Check what the instruction asked for.** The create-pr verifier accepted a
  PR that dropped the AI disclosure the instruction supplied; it now requires
  the token or an `ai-assisted` label.
- **Accept every valid command shape.** `pixi run pytest -x <test>` is
  documented by the run-tests skill and failed a regex that expected the test
  id first; allow flags anywhere with `( [^ ]+)*`.
- **Diffing against `HEAD` punishes an agent that commits.** The docs,
  run-tests and verify verifiers still do this; a fixture tag is the safer
  baseline.
- **Do not compute "today" at verification time** if the oracle wrote it at
  solve time; a run across UTC midnight fails.
- **`shim_arg` reads single-line values only.** Multi-line arguments span
  lines in the `.args` log; match bodies with line-anchored `shim_args_have`.
- **Prove the negative.** Run each task under Harbor's `nop` agent: happy-path
  tasks must score 0.

## Sample rules (`evals/inspect/samples/*.yaml`)

- A `must` that already appears in the input proves nothing (an "ImportError"
  input satisfied `must: ["import"]`); require the action the skill prescribes.
- A bare-word `must_not` ("Co-Authored-By", "pip install") trips a correct
  refusal that names the thing; anchor it as a command or trailer shape.
- The smoke gate replays author-written answers against author-written rules,
  so it can only catch broken YAML or regexes, never a skill regression.
- Three to five samples per skill, each aimed at one rule of the skill, at
  least one that tempts a forbidden action.

## Repository tooling that bites eval files

- Prettier (`--prose-wrap=always`) reflows YAML lists and markdown; a code
  block containing a nested triple-backtick fence gets corrupted. Fence such
  blocks with four backticks or exclude the path (`docs/superpowers/` is).
- codespell reads regex fragments as words: a bracket class such as `[Nn]`
  leaves the two letters after it as a misspelling, and a truncated stem of
  "delete" is flagged too; spell alternations out (`(not|Not)`,
  `(delete|deleting)`).
- The plan for a task must not rely on `cp -R src/. dst/` in a pixi task
  (see [[project/pixi-gate-quirks]]).
