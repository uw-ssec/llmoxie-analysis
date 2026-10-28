---
type: Fact
title: What Exists and What Is Only Designed
description: "Stage one of the pipeline now exists in src/ — sources, reader and session grouping — while everything downstream of it under pipeline/ is still specification, not code."
tags: [status, scaffolding, onboarding, implementation]
generated: { by: "claude-code:ssec-claude-opus-5", at: "2026-10-13T21:33:03Z" }
sources:
  - resource: llmoxie-analysis repository tree at commit 890d695
  - resource: "https://github.com/uw-ssec/llmoxie-analysis/issues/1"
---

Much of this bundle still describes a system that has not been built. Read
`pipeline/` as a specification except where noted below.

## What exists today

| Area              | State                                                                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/`            | `llmoxie_analysis/data/`: `sources.py`, `reader.py`, `group_sessions.py` — stage one, moved in from upstream                                   |
| `tests/`          | `test_version.py` plus `tests/data/`: 42 tests over the three data modules                                                                     |
| `evals/`          | Skill evals: Inspect harness and samples, Harbor base image and 18 tasks; merged in PR #42                                                     |
| `knowledge/`      | This bundle                                                                                                                                    |
| `.claude/skills/` | The core-loop skills: setup-env, run-tests, verify, commit, push, create-pr, create-issue, merge-pr, release, docs, clean-branches, okf-memory |
| `reference/`      | Git submodules: `llmoxie` (the upstream repo) and `ceil-dlp`                                                                                   |
| Repository        | Packaging, CI, pre-commit, AI policy, contribution rules                                                                                       |

## What is designed but not built

Everything under `pipeline/` except the adapters: the four-table analytics
schema, the storage layout, the idempotency design, the CLI, the query layer,
and the scheduled Container Apps job. These concepts record decisions already
taken, so they are worth reading before writing code, but no code implements
them yet.

[[pipeline/source-adapters]] is the partial exception — `from_adls` and
`from_litellm` exist; `iter_source` and its per-day auto detection do not.

## Where the working code actually is

The `reader.py` and `group_sessions.py` prototypes that `upstream/` describes
now live in this repository, under `src/llmoxie_analysis/data/`. They were moved
out of `uw-ssec/llmoxie` rather than rewritten, so `upstream/` still describes
their behavior accurately — read it as documentation of the code in `src/`, and
treat its "upstream" framing as history.

`reference/llmoxie` remains the home of the gateway, the infrastructure code and
the `llmaven infra extract` export tool. Do not edit the submodule as a way of
changing this project.

Still true of the moved code: it was lifted, not fixed. The caveats under
`caveats/` describe live behavior, not past behavior.

## How to tell, without trusting this page

This concept will go stale as code lands. The checks that will not:

```bash
find src -name "*.py"        # what the package actually contains
pixi run run-tests           # what is actually covered
okf show pipeline/<concept>  # status: draft vs stable
```
