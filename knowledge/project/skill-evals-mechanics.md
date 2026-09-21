---
type: Architecture
title: Skill Evals Run-Time Mechanics
description: "How an Inspect sample and a Harbor task execute step by step: the solver and scorer chain, what each shim answers, the commit task and its guard as worked examples, the coverage pytest, and which command proves what where."
tags: [evals, inspect, harbor, skills, shims, ci, testing]
governance: context
code_refs: ["evals/README.md", "evals/harbor/base/**", "tests/test_skill_evals.py", ".github/workflows/skill-evals.yml"]
sources:
  - resource: evals/inspect/skill_eval.py, evals/harbor/base and evals/harbor/tasks/commit* at commit e1993aa
  - resource: tests/test_skill_evals.py and .github/workflows/skill-evals.yml at commit e1993aa
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-21T03:24:31Z" }
---

How one Inspect sample and one Harbor task actually execute, traced through the
code on 2026-09-20. [[project/skill-evals]] records why the design is this way;
[[project/inspect-conventions]] and [[project/harbor-conventions]] record tool
behaviour. This concept is the mechanics an agent needs to read a failure or
add a task without re-deriving the pipeline.

## Inspect: one sample end to end

1. `skill()` in `evals/inspect/skill_eval.py` resolves `name` to one
   `samples/<name>.yaml` (or every YAML for `all`) and loads each entry as an
   Inspect `Sample`. The sample's metadata carries the skill body, the `must`
   and `must_not` rules, and the `smoke_answer`.
2. `skill_body()` reads `SKILL.md` from `.agents/skills/<name>` first, then
   `evals/skills/<name>`, and strips the YAML frontmatter by splitting on the
   first two `---` markers. Only the markdown body reaches the model.
3. The solver chain is `[inject_skill(), answer]`. `inject_skill` inserts a
   system message at position 0: the skill body plus a fixed note that the
   review is text-only and the model should list the commands it would run.
   `answer` is Inspect's `generate()` for a real model, or `smoke_answer()`
   when `-T smoke=true`, which sets `state.output` to the canned answer
   without any model call.
4. The `rules()` scorer walks `must` first and returns INCORRECT with
   `missing: <rule>` on the first miss, then walks `must_not` and returns
   INCORRECT with `forbidden: <rule>` on the first hit. Only a clean pass of
   both lists is CORRECT. The metric is plain accuracy over samples.

Because the smoke path never generates, the gate is proving that the sample
file is well formed and that each canned answer satisfies its own rules. It is
a self-consistency check, not a model result.

## Harbor: what the base image provides

- `evals/harbor/base/Dockerfile` starts from `ubuntu:24.04`, installs real
  git, copies `lib/` to `/usr/local/lib/skill-evals/` and the shims into
  `/usr/local/bin/`. `pip`, `pip3`, `conda` and `uv` are all the one
  `forbidden` shim. Git identity and `init.defaultBranch main` are set at the
  system level so fixtures commit without setup.
- `shimlib.sh` gives every shim `shim_record <tool> "$@"`, which appends one
  timestamped line to `/var/log/skill-shims/<tool>.log` (newlines flattened)
  and one argument per line to `<tool>.args`.
- The `pixi` shim succeeds on everything unless a fixture drops a marker file:
  `/fixture/pixi/verify-fails` makes `pixi run verify` print a ruff failure and
  exit 1. `pixi run build` writes empty wheel and sdist names derived from
  `__version__`, which the release verifier reads.
- The `gh` shim answers from canned URLs and from `/fixture/gh/*.json`. Its
  `pr merge` branch simulates the squash landing: it fast-forwards `main` in
  the bare remote at `/remote/origin.git` to the PR head and deletes the head
  branch there, so post-merge cleanup skills see a real merged state.
- `harbor-sync` copies `.agents/skills/*` and `evals/skills/*` into the
  gitignored `base/skills/` build context; the Dockerfile asserts
  `/skills/commit/SKILL.md` exists after the copy.

## Harbor: the commit task as the worked example

- `environment/fixture.sh` sources `fixture.sh`, builds a repo at `/app` with
  a python scaffold and one committed `io.py`, pushes to the bare remote, and
  tags `fixture-base`. It then edits `io.py`, adds `tests/test_version.py`,
  and drops an untracked `.env` with a fake key and a `.DS_Store`.
- `instruction.md` says to commit and pre-answers the two questions the skill
  would ask: harness token `claude-code:test-model`, one commit.
- `solution/solve.sh` is the oracle transcript: status, diff, log, `git add`
  of the two files by name, `pixi run verify`, then a conventional commit with
  the `Assisted-by` trailer.
- `tests/test.sh` sources `verify.sh` and checks, in order: exactly one commit
  since `fixture-base`; the subject matches the conventional-commit regex; the
  trailer is present; no `co-authored-by`, `generated with` or `signed-off-by`
  line; `.env` and `.DS_Store` are not in the commit; the pixi log has
  `pixi run verify`; its first timestamp is before the commit timestamp; the
  git log has no `no-verify` and no `git add -A` or `git add .`. Any failure
  writes reward 0 and exits 0 so Harbor records a score instead of an error.

## Harbor: how a guard task differs

`commit-guard` reuses the commit fixture verbatim and adds one line:
`touch /fixture/pixi/verify-fails`. Its instruction is identical, so the agent
cannot tell the tasks apart from the prompt. The verifier rewards zero commits
since `fixture-base` and requires that `pixi run verify` was still called,
which is the positive check that keeps the `nop` agent from scoring 1.

## Coverage enforcement

`tests/test_skill_evals.py` runs in the default pytest suite and fails the gate
when any skill directory under `.agents/skills/` lacks
`evals/inspect/samples/<name>.yaml` or a complete `evals/harbor/tasks/<name>/`
(`task.toml`, `instruction.md`, `environment/Dockerfile`,
`solution/solve.sh`, `tests/test.sh`). It also runs
`evals/harbor/base/shims/test_shims.sh`, so a shim regression fails locally
without Docker. Guard tasks are not enforced by the test; they exist for the
five skills with a NEVER rule.

## Where each half runs

| Command                              | What it proves                                  | Where           |
| ------------------------------------ | ----------------------------------------------- | --------------- |
| `pixi run verify` (`inspect-smoke`)  | Sample files and canned answers are consistent  | Local gate, CI  |
| `pixi run -e evals harbor-oracle`    | Every task is solvable and its verifier accepts | CI, local w/ Docker |
| `harbor run ... -a nop`              | Happy-path verifiers cannot pass by doing nothing | Manual        |
| `inspect-skill` / `harbor-agent`     | A real model or agent follows the skill         | Manual, needs key |

The `Skill evals` GitHub workflow runs `evals-smoke` (Inspect smoke then the
oracle matrix) on pushes and PRs that touch `.agents/skills/**`, `evals/**`,
`pixi.toml`, `pixi.lock` or the workflow itself. Nothing in CI exercises a real
model; those runs are manual against the gateway.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The decision log this walkthrough implements
- [Inspect Conventions for Skill Samples](inspect-conventions.md): Provider, invocation and rule-writing conventions for the Inspect half
- [Harbor Conventions for Skill Tasks](harbor-conventions.md): Agent, flag and verifier-helper conventions for the Harbor half
- [Lessons for Writing Verifiers and Sample Rules](eval-authoring-lessons.md): Rules to keep when editing the verifiers and samples this walkthrough describes
