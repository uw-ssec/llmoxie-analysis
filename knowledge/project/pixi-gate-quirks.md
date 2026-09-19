---
type: Fact
title: Pixi Task and Verify Gate Quirks
description: "Undocumented behaviour of pixi tasks, the verify gate, pre-commit and Docker on this machine that cost time: the task shell's cp semantics, argument placeholders, cross-environment dependencies, piped exit codes, and config-staging refusals."
tags: [pixi, verify, pre-commit, docker, ci]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T05:49:02Z" }
governance: context
code_refs: [pixi.toml, .pre-commit-config.yaml, ".github/workflows/**"]
sources:
  - resource: "pixi 0.63.2 task shell behaviour observed 2026-09-19 (cp -R src/. nesting, {{ placeholders)"
  - resource: GitHub Actions run 35423961275 (setup-pixi activate-environment error)
  - resource: "pre-commit and pixi run verify output in the PR #42 session"
---

Behaviour of pixi tasks, the `verify` gate and pre-commit that is not in their
documentation and cost time during the skill-evals work (2026-09-18 and
2026-09-19).

## pixi tasks

- **Tasks run in pixi's own shell, not bash.** `cp -R src/. dst/` copies the
  directory itself there, so `cp -R .agents/skills/. dst/` produced
  `dst/skills/...`. Use `cp -R src/* dst/`. The bug was invisible to every
  oracle run and was caught only by the whole-branch review.
- **Cross-environment dependencies work** (pixi 0.63):
  `depends-on = [{ task = "inspect-smoke", environment = "evals" }]` lets the
  default environment's `verify` run a task from the `evals` environment. The
  first `pixi run verify` on a fresh clone therefore installs the `evals`
  environment (PyPI inspect-ai, harbor, anthropic); CI's setup-pixi step must
  list `environments: default evals` and, with more than one environment,
  `activate-environment` must name one (`true` is rejected).
- **`pixi run gh … --template '{{…}}'` fails**: pixi treats `{{` as a task
  argument placeholder. Call `.pixi/envs/default/bin/gh` directly or use
  `--json` plus a Python one-liner. The same applies to any argument, including
  an `okf create --body` whose text mentions `{{`: run
  `.pixi/envs/default/bin/okf` directly (this concept had to be created that way).
- **Extra arguments append to the task command**, so
  `pixi run -e evals inspect-skill -T name=commit --model …` works without a
  wrapper task per model.
- **`pixi add --feature evals --pypi "openai>=3.1"` fails to solve** against
  Harbor's litellm pin; the manifest is left untouched when a solve fails.

## The verify gate

- **Never read the gate through a pipe.** `pixi run verify | tail -1` hides
  the exit code and pixi's interleaved output can end on a pre-commit line
  even when the build ran. Capture to a file and check `$?` explicitly.
- **pre-commit refuses a pathspec commit while `.pre-commit-config.yaml` is
  staged but excluded from the commit** ("Your pre-commit configuration is
  unstaged"). Commit the config change first.
- **Hooks reformat and then fail once**: prettier reflows YAML and markdown,
  ruff format wraps long lines; `git add` the files again and rerun.
- **`.env` was not gitignored** until 2026-09-19; the setup-env skill assumed
  it was. Root `.gitignore` now has `.env` and `.env.*`.
- **`mkdocs build --strict` fails on any page under `docs/` that is not in
  `nav`**; `docs-build` is not part of `verify`, so this surfaces late.
  `docs/superpowers/` is excluded with `exclude_docs`.

## Docker on this machine

- The Docker daemon is not started at login; `open -a Docker` and wait for
  `docker info` before any Harbor task. The Harbor base image is
  `llmoxie-skill-evals-base:local`, rebuilt by `pixi run -e evals harbor-base`.
- ubuntu-latest GitHub runners have Docker; the full 18-task Harbor matrix ran
  there in about two minutes.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The evals this knowledge came from.
