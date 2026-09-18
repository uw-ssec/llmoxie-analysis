---
name: okf-memory
description:
  Use when a decision, constraint, or non-obvious discovery from this session
  should outlive it, before changing code in an area that may carry recorded
  constraints, when asked what the project decided about something, or when `okf
  validate` fails.
---

# OKF Memory

Project memory is the OKF v0.2 bundle at `knowledge/` in the repository root.
Read it and write it only through the `okf` CLI, run as `pixi run okf` (the
binary from the pixi environment; there is no pixi task). The bundle path
defaults to `knowledge`, so it can be omitted.

## Quick reference

| Task                      | Command                                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------------------------------- |
| Find what is recorded     | `pixi run okf search "<keywords>" --limit 3`                                                              |
| Concepts governing a file | `pixi run okf search --for-path src/llmoxie_analysis/<file>.py`                                           |
| Read one concept          | `pixi run okf show <id>`                                                                                  |
| Record                    | `pixi run okf create <area>/<slug> --type <Type> --title "<t>" --desc "<d>" --tags "<a,b>" --body "<md>"` |
| Revise                    | `pixi run okf update <id> --desc "<d>"` (also `--title`, `--body`)                                        |
| Link two concepts         | `pixi run okf relate <src-id> <tgt-id> --desc "<why they relate>"`                                        |
| Check the bundle          | `pixi run okf validate --strict --drift`                                                                  |

Add `--json` for machine-readable output. `pixi run okf help <command>` lists
the rest. Pass `--actor <harness>:<model>` to `create`, `update`, and `relate`,
using the same token as the `Assisted-by` trailer in `AI_POLICY.md`.

## Read before write

1. Search first. On a fresh bundle an empty result is normal; go on to create.
   Do not browse `knowledge/` with `find`, `grep`, or `cat` to learn what is
   there; `search` and `show` are the readers. Read a hit's one-line description
   and `show` it only if needed.
2. Before the first edit in a subsystem, run `search --for-path` on the file. A
   hit with `governance: hold` means stop and confirm with the user. A hit with
   `governance: constraint` lists invariants the change must keep.
3. If a concept already covers the topic, `update` it. Do not create a `-v2`.
   Keep superseded reasoning in a "Superseded" section of the same concept.

## What to record

| Persist                                                     | Discard                                         |
| ----------------------------------------------------------- | ----------------------------------------------- |
| Decisions, rejected alternatives, and their trade-offs      | Naming deliberations, momentary thoughts        |
| Requirements, constraints, platform or performance targets  | One-off prompt instructions ("make it shorter") |
| Non-obvious quirks, workarounds, undocumented tool behavior | Anything the official docs already say          |
| Root causes of subtle bugs                                  | Syntax errors fixed in one step                 |
| Explicit, durable directives from the project owner         | Transcripts, scratch notes, chain of thought    |

The test: would an agent starting from a blank context benefit from knowing
this? Concept IDs are `<area>/<slug>`, where area is one of `decisions`,
`architecture`, `facts`, `requirements`, `bugs`. Types are free-form; use
`Decision`, `Architecture`, `Fact`, `Requirement`, or `Bug` unless the concept
is clearly something else. Mark inferences as inferred and name what would
confirm them; do not write a guess as a fact.

## Frontmatter fields with no CLI flag

`show --json` prints them. Opening the one concept file you are changing and
editing these fields by hand is allowed; validate afterwards.

| Field         | Meaning and rules                                                                     |
| ------------- | ------------------------------------------------------------------------------------- |
| `code_refs`   | Paths or globs the concept governs, relative to the repo root. No `..`, no `/` start. |
| `governance`  | `hold`, `constraint`, or `context`; surfaced by `search --for-path`.                  |
| `status`      | `draft`, `stable`, or `deprecated`. `update --status` is in the help but not built.   |
| `stale_after` | `YYYY-MM-DD`; `validate --stale` fails the gate once it passes.                       |
| `sources`     | Documents, commits, or URLs the knowledge came from.                                  |
| `verified`    | Human-only. Never write it; `generated` is the agent's provenance and okf sets it.    |

## Repo-specific traps

- `knowledge/` is excluded from the prettier hook because prettier folds long
  `description:` lines into multi-line YAML that okf reads as empty. Do not run
  prettier over the bundle by hand, and keep the exclusion in
  `.pre-commit-config.yaml`.
- Keep `description:` on one line. Detail goes in the body.
- `end-of-file-fixer` still runs on the bundle and may trim a trailing blank
  line okf leaves. If verify says a file was modified, `git add knowledge` and
  rerun.
- `pre-commit-all` skips untracked files, so `git add knowledge` before
  `pixi run verify`.
- okf stamps `log.md` and `generated.at` in UTC.

## Done

- `pixi run okf validate --strict --drift` reports 0 errors, 0 warnings, and no
  "producer gate failed".
- `pixi run okf show <id>` prints a non-empty Description for each concept
  touched.
- `git add knowledge && pixi run verify` passes; paste the final lines.

## Rules

- No hand-written concept files. Create and change them through `okf`; the
  hand-edited fields above are the only exception.
- Never forge `verified:`; never persist scratch, transcripts, or speculation.
- A human correction wins. Never restore or re-infer an assumption a human has
  rejected.
- Never "fix" a validation failure by deleting the concept it points at without
  saying so.
