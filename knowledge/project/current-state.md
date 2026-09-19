---
type: Fact
title: What Exists and What Is Only Designed
description: "The analysis package is still empty scaffolding: pipeline/ records decisions for code that has not been written, and the working prototypes live in the reference/ submodules."
tags: [status, scaffolding, onboarding, implementation]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T05:48:34Z" }
sources:
  - resource: llmoxie-analysis repository tree at commit 890d695
  - resource: "https://github.com/uw-ssec/llmoxie-analysis/issues/1"
---

Most of this bundle describes a system that has not been built yet. Read
`pipeline/` as a specification, not as documentation of running code.

## What exists today

| Area              | State                                                                |
| ----------------- | -------------------------------------------------------------------- |
| `src/`            | `llmoxie_analysis/__init__.py` only — a docstring and `__version__`  |
| `tests/`          | `test_version.py` only — asserts the version string                  |
| `evals/`          | Skill evals: Inspect harness and samples, Harbor base image and 18 tasks; merged in PR #42 |
| `knowledge/`      | This bundle                                                          |
| `.claude/skills/` | The core-loop skills: setup-env, run-tests, verify, commit, push, create-pr, create-issue, merge-pr, release, docs, clean-branches, okf-memory |
| `reference/`      | Git submodules: `llmoxie` (the upstream prototypes) and `ceil-dlp`   |
| Repository        | Packaging, CI, pre-commit, AI policy, contribution rules             |

So the repository is scaffolding plus knowledge, and the analysis package
itself is empty.

## What is designed but not built

Everything under `pipeline/` — the four-stage architecture, the four-table
analytics schema, the storage layout, the idempotency design, the CLI, the
query layer, and the scheduled Container Apps job. These concepts record
decisions already taken, so they are worth reading before writing code, but no
code implements them yet.

Each carries `status: draft` to mark that. Flip a concept to `status: stable`
when the code implementing it lands.

## Where the working code actually is

The `llmaven` CLI and the `reader.py` / `group_sessions.py` prototypes that
`upstream/` describes live in the `reference/llmoxie` submodule, not in this
repository. They are the inherited prototypes this project must fix or absorb;
`upstream/` records what they do and where they are wrong. Do not expect to
find them under `src/`, and do not edit the submodule as a way of changing this
project.

## How to tell, without trusting this page

This concept will go stale as code lands. The checks that will not:

```bash
find src -name '*.py'        # what the package actually contains
pixi run run-tests           # what is actually covered
okf show pipeline/<concept>  # status: draft vs stable
```

## Related Concepts

- [Epic #1 and the Implementation Issues](epic-and-issues.md): The issue-by-issue
  plan that turns the designed half into the built half.
- [Pipeline Architecture](../pipeline/pipeline-architecture.md): The principal
  design this concept is warning you is unbuilt.
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The one part of
  the repository that is built, tested and merged.
