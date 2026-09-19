---
name: verify
description:
  Use before committing, opening a pull request, or claiming a change is
  complete, fixed, or passing — the single quality gate for this repository.
---

# Verify

One command, exit 0:

```bash
git add <new files>   # pre-commit sees tracked and staged files only
pixi run verify
```

It runs, in order, and stops at the first failure:

| Step             | What it checks                                                   |
| ---------------- | ---------------------------------------------------------------- |
| `pre-commit-all` | ruff format and lint, whitespace, YAML/JSON, prettier, codespell |
| `okf-validate`   | okf check of `knowledge/`; warnings print but do not fail        |
| `typecheck`      | mypy, strict, over `src/` and `tests/`                           |
| `test`           | pytest over `tests/`                                             |
| `inspect-smoke`  | every skill's Inspect eval against canned answers (`evals/`)     |
| `build`          | wheel and sdist build into `dist/` (packaging metadata is valid) |

Each step is also a pixi task you can run alone; `pixi run lint` runs ruff
without modifying files.

## When a step fails

| Symptom                                      | Do                                                                |
| -------------------------------------------- | ----------------------------------------------------------------- |
| Hook says "files were modified by this hook" | The hook fixed formatting. `git add` the files and rerun.         |
| ruff error                                   | Fix the code. A `# noqa: <code>` needs a reason in the same line. |
| okf `gate` or `error` line                   | Fix the concept it names, through the `okf-memory` skill.         |
| mypy error                                   | Fix the type. `# type: ignore[<code>]` only with a reason.        |
| pytest failure                               | Use the `run-tests` skill to isolate and fix.                     |
| build error                                  | Check `pyproject.toml` and the version in `__init__.py`.          |

## Done

Every step ran and the final lines of the run are pasted into the commit body or
the PR's "How to test" section. A step you skipped is a step that failed; say
which and why.

## Rules

- Never bypass the gate: no `--no-verify`, no editing ruff, mypy, or pre-commit
  configuration to make a failure disappear.
- "Should pass" is not a result. Run it.
