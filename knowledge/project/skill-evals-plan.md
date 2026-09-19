---
type: Process
title: Skill Evals Implementation Plan
description: "The eleven-task order that builds the skill evals, the decisions made while planning them, the constraints an executor must keep, and where execution stands."
tags: [evals, plan, inspect, harbor, skills, sdd]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T03:42:37Z" }
sources:
  - resource: docs/superpowers/plans/2026-09-18-skill-evals.md on branch worktree-inspect-harbor-pixi
  - resource: docs/superpowers/specs/2026-09-18-skill-evals-design.md on branch worktree-inspect-harbor-pixi
---

The plan that turns the skill-evals design in [[project/skill-evals]] into
code. Full text with every file's contents:
`docs/superpowers/plans/2026-09-18-skill-evals.md`. It is executed with
subagent-driven development: a fresh implementer per task, a task review after
each, one whole-branch review at the end.

## Tasks

| #   | Deliverable                                                                                     | Proof                                              |
| --- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| 1   | Rebase the branch onto current `main`; regenerate `pixi.lock`                                   | `verify` and `inspect-smoke` green                 |
| 2   | `evals/inspect/skill_eval.py`: task `skill(name, smoke)`, rule scorer, `samples/` loader        | greeting-file smoke, a deliberately broken rule fails |
| 3–5 | Twelve `samples/<skill>.yaml` files, three per batch (local git; GitHub; toolchain)             | smoke accuracy 1.0 after each batch                |
| 6   | `tests/test_skill_evals.py`: every skill has a samples file                                     | pytest, and a removed file makes it fail           |
| 7   | Harbor base image: shims (`gh`, `pixi`, `okf`, `git` wrapper, forbidden), `lib/`, `test_shims.sh` | shim self-test on the host; greeting-file oracle 1.0 |
| 8   | Harbor tasks commit, push, clean-branches and their guards                                      | oracle 1.0; `nop` agent 0.0 on happy paths         |
| 9   | Harbor tasks create-issue, create-pr, merge-pr, release and two guards                          | same                                               |
| 10  | Harbor tasks verify, run-tests, setup-env, docs, okf-memory                                     | same                                               |
| 11  | `inspect-smoke` on the `verify` gate, Harbor coverage test, README, Docker CI job               | full matrix 18/18 at reward 1.0                    |

Each task is one conventional commit with an `Assisted-by:` trailer, made by
the orchestrator through the `commit` skill after the task review passes.

## Decisions made while planning

### 2026-09-18: Rule regexes are case-sensitive (Accepted, amends the spec)

- **Decision:** `regex:` rules use `re.MULTILINE` only.
- **Why:** The spec said case-insensitive; that would make a forbidden
  `git branch -D` match the required `git branch -d`.
- **Result:** Spec and plan both updated on 2026-09-18.

### 2026-09-18: Helper libraries live in the base image directory (Accepted, amends the spec)

- **Decision:** `evals/harbor/base/lib/{shimlib,fixture,verify}.sh` rather
  than `evals/harbor/lib/`.
- **Why:** A Docker build context cannot reach a sibling directory; the base
  image copies `lib/` to `/usr/local/lib/skill-evals/`.

### 2026-09-18: Guard fixtures are verbatim copies (Accepted)

- **Decision:** A guard task's `environment/fixture.sh` copies its happy-path
  sibling in full and adds the one line that removes the precondition.
- **Why:** Each Harbor task builds from its own `environment/` directory;
  fixtures are data, and the duplication is the price of isolation.
- **Cost if wrong:** the two fixtures drift and a guard tests a different repo
  state than its happy path.

## Constraints the executor must keep

- Pixi only; every command is `pixi run …` or `pixi run -e evals …`.
- Shell under `evals/harbor/base/shims/` runs on bash 3.2, because the shim
  self-test runs on the macOS host inside `pixi run verify`.
- Python under `evals/` passes ruff with numpy docstrings; `tests/` passes
  mypy strict.
- Tasks 7 through 11 need a running Docker daemon.

## Status

Task 1 complete on 2026-09-18. Remaining tasks are dispatched in order; the
session ledger is `.superpowers/sdd/2026-09-18-skill-evals/progress.md` in
the worktree (gitignored, so it does not survive the branch).

## Related Concepts

- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The design this
  plan implements and its decision log.
- [What Exists and What Is Only Designed](current-state.md): The status page
  to flip once `evals/` lands on `main`.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The design and decision log this plan implements.
