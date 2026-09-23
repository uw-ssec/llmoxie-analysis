---
name: onboard
description:
  Use when someone is new to this repository and needs to get up to speed — a
  new contributor's first session, "help me understand this project", or handing
  the repo to someone who has never worked in it. For installing or repairing
  the environment alone, use `setup-env` instead.
---

# Onboard

Take a newcomer from a fresh clone to oriented: the gate passes on their
machine, and they can say what this repository produces, what does not exist
yet, and what will quietly mislead them.

This is a guided session, not a document to paste. Work one stage at a time and
wait for the person to confirm before moving on. Everything here delegates —
`setup-env` installs, `okf` answers what the project is, the rules cover layout
and process. Do not restate what those already say; send the person to them.

## Stage 1 — Get the gate passing

Run the `setup-env` skill. Then, for a first-time contributor, the SSEC flow:

```bash
pixi run -e onboard onboard
```

It installs the pre-commit hook, sets up `ssec` shell completion (which needs a
new terminal), and runs SSEC onboarding. Details in
`.agents/rules/onboarding.md`.

**Gate:** `pixi run verify` exits 0. Do not move on until it does — every later
stage assumes a working environment.

## Stage 2 — What this project is

Project memory lives in the OKF bundle at `knowledge/`. Read it with `okf`, not
with `cat`, `grep`, or `find`:

```bash
pixi run okf show project/llmoxie-analysis   # the problem and the deliverable
pixi run okf show project/current-state      # read this before hunting for code
pixi run okf search "caveat" --limit 5       # then show the ones that matter
```

Three things the newcomer has to leave this stage knowing:

| Point                       | Why it matters                                                                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| What the pipeline produces  | Raw LLMoxie gateway logs in, a queryable Parquet warehouse of sessions, messages, and tool calls out.                                                 |
| Most of `pipeline/` is spec | The package is still scaffolding. Those concepts describe code nobody has written; the prototypes are in `reference/`.                                |
| The data has traps          | Four recorded caveats produce confidently wrong answers — cost double-counting, dedup ordering, `end_user` parsing, and the Responses API output gap. |

`caveats/index` is a reserved bundle document, so `okf show` refuses it. Reach
the caveats through `okf search` and show them individually.

If they ask why the repository is shaped the way it is, or what to work on:
`project/cross-viss-demo` and `project/epic-and-issues`.

## Stage 3 — Where things live

Point at `.agents/rules/repository-map.md` rather than narrating the tree. What
to draw out of it:

- `AGENTS.md` is the entry point for every agent harness, and it is deliberately
  short — the rule index tells you which file to load for the task at hand.
- `.agents/skills/` holds the step-by-step recipes; `.claude/skills` is a
  symlink so Claude Code finds them, and `.cursorrules` and
  `.github/copilot-instructions.md` point at `AGENTS.md`.
- `reference/` is read-only submodules of upstream prototype code. Read it, port
  from it, never edit it.
- `knowledge/` and `docs/` are separate. Nothing in `knowledge/` is rendered
  into the documentation site.

## Stage 4 — How work gets done here

The six non-negotiables at the top of `AGENTS.md` are the whole contract; walk
them rather than summarizing. The two that catch people out:

- **Pixi is the only package manager.** No `pip`, `conda`, or `venv`, ever.
- **Verify before you claim.** `pixi run verify` is the single gate. "Should
  pass" is not a result.

Then the chain a change travels: `verify` → `commit` → `push` → `create-pr`, one
skill each, plus `contribution-discipline.md` in full before any PR. AI
assistance is disclosed with an `Assisted-by:` trailer — see `AI_POLICY.md`.

Behavioral baseline for the work itself: `.agents/rules/working-agreement.md`.

## Orientation check

Close by asking, and correcting with the concept id or rule file rather than
from your own memory:

1. What does this package turn its input into?
2. If you went looking for the pipeline code, what would you find?
3. Name one caveat that would make a number wrong, and what it does.
4. Which command decides whether your change is done?
5. Where would you look to find out which rule covers a task?

A wrong answer is not a problem — send them to the source and move on.

## Done

- `pixi run verify` exited 0 on their machine.
- The orientation check is answered.
- They know the next file to open for the work they are picking up.

Onboarding stops here. Landing a first change is the `commit`, `push`, and
`create-pr` skills' job.

## Rules

- One stage at a time. Dumping all four at once is how people finish onboarding
  having retained nothing.
- Never browse `knowledge/` with `cat`, `grep`, or `find` to answer a question —
  `okf search` and `okf show` are the readers.
- If the session turns up something a future contributor could not derive from
  the code, record it with the `okf-memory` skill.
