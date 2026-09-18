---
type: Process
title: Skill Evaluation with Inspect and Harbor
description: Skills are evaluated at two levels — Inspect for model-level correctness and Harbor for whether an agent actually uses the skill — from one Pixi environment whose dependencies must come from PyPI.
tags: [evals, inspect, harbor, skills, pixi, testing]
sources:
  - resource: llmoxie-analysis evals/README.md on branch worktree-inspect-harbor-pixi
  - resource: https://inspect.aisi.org.uk/
  - resource: https://docs.harborframework.com/
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:08:05Z" }
---

Skills in this repository are directories with a `SKILL.md`. They are evaluated
at two levels, because a skill can be perfectly written and still never get
used.

| Level | Question                                                     | Framework | Needs             |
| ----- | ------------------------------------------------------------ | --------- | ----------------- |
| Model | Given the skill in context, does the model answer correctly? | Inspect   | a model (or mock) |
| Agent | Dropped into a sandbox with the skill, does the agent use it? | Harbor   | Docker (+ model)  |

Inspect is the UK AI Safety Institute's evaluation framework; Harbor is Laude's
agent-task framework, which bundles a skill into a container via
`environment.skills_dir` and scores whether the agent's trajectory used it.
Model-level and agent-level results answer different questions and neither
substitutes for the other.

## Layout

```
evals/
├── skills/                 # canonical skills under test (one dir per skill)
├── inspect/                # Inspect tasks; import skills from ../skills
├── harbor/tasks/<name>/    # task.toml, instruction.md, environment/Dockerfile,
│                           # solution/solve.sh, tests/test.sh
└── logs/                   # gitignored run output
```

Adding a skill means putting it under `evals/skills/<name>/SKILL.md` and giving
it **both** an Inspect task and a Harbor task. `evals/README.md` carries the
step-by-step pattern.

## Why both dependencies come from PyPI

This is the trap worth recording. The `evals` environment takes Inspect and
Harbor as PyPI dependencies inside Pixi rather than from conda-forge, because
conda-forge's `inspect-ai` pins `websockets` 17 while Harbor requires
`websockets` <16. Taking either from conda-forge makes the environment
unsolvable. The environment is also in its own solve group, because Harbor
requires Python 3.12+.

This is a deliberate, documented exception to the repository's Pixi-first rule,
not an oversight — see the comment in `pixi.toml`.

## Running them

```bash
pixi install -e evals
pixi run -e evals inspect-smoke    # mock model, deterministic, no API key
pixi run -e evals harbor-oracle    # builds the image, runs the oracle, verifies
pixi run -e evals evals-smoke      # both
```

The smoke tasks use a mock model and require no API key, so they are safe in CI
and safe to run repeatedly. Harbor requires a Docker daemon on the host, which
is the main reason an agent may be unable to run the agent-level half.

## Status

Prototype, not yet merged. The working scaffold lives on the branch
`worktree-inspect-harbor-pixi`, in a locked worktree under
`.claude/worktrees/inspect-harbor-pixi`, and has been run end to end: the Harbor
oracle task verified at reward 1.0 and Inspect produced logs against the mock
model. It is not on `main`, and `evals/` on `main` is an empty directory.

## Related Concepts

- [What Exists and What Is Only Designed](current-state.md): Where this sits
  relative to the rest of the unbuilt work.
- [Epic #1 and the Implementation Issues](epic-and-issues.md): The issue-by-issue
  plan this prototype is not yet part of.
