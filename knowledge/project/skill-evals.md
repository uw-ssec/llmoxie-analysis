---
type: Process
title: Skill Evaluation with Inspect and Harbor
description: "Every skill under .agents/skills is evaluated at two levels: Inspect with deterministic must/must-not rules on the verify gate, and Harbor in a Docker sandbox with fake gh/pixi/okf that log every call; the decision log records why."
tags: [evals, inspect, harbor, skills, pixi, testing]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T05:49:02Z" }
sources:
  - resource: docs/superpowers/specs/2026-09-18-skill-evals-design.md on branch worktree-inspect-harbor-pixi
  - resource: llmoxie-analysis evals/README.md on branch worktree-inspect-harbor-pixi
  - resource: "https://inspect.aisi.org.uk/"
  - resource: "https://docs.harborframework.com/"
---

Skills in this repository are directories with a `SKILL.md` under
`.agents/skills/` (`.claude/skills` is a symlink to it). They are evaluated at
two levels, because a skill can be perfectly written and still never get used.

| Level | Question                                                             | Framework | Runs in                        |
| ----- | -------------------------------------------------------------------- | --------- | ------------------------------ |
| Model | With `SKILL.md` in context, does the model answer as the skill says? | Inspect   | `pixi run verify` (mock model) |
| Agent | Dropped into a sandbox with the skill, does the agent act on it?     | Harbor    | `harbor-oracle` (needs Docker) |

Inspect is the UK AI Safety Institute's evaluation framework; Harbor is Laude's
agent-task framework, which bundles a skill into a container via
`environment.skills_dir`. Model-level and agent-level results answer different
questions and neither substitutes for the other.

## Decision log

The design was brainstormed and approved on 2026-09-18. Full text:
`docs/superpowers/specs/2026-09-18-skill-evals-design.md`. The implementation
order is in [[project/skill-evals-plan]].

### 2026-09-18: Both levels for every skill (Accepted)

- **Decision:** All twelve skills get an Inspect task and a Harbor task.
- **Why:** Inspect alone cannot tell whether an agent uses a skill; Harbor
  alone needs Docker and a model, so it cannot sit on the local gate.
- **Result:** `pixi run verify` runs the Inspect smoke; a Docker-backed CI job
  runs the Harbor matrix.

### 2026-09-18: Deterministic rule scoring, no judge model (Accepted)

- **Decision:** Each Inspect sample carries `must` / `must_not` rules. Plain
  strings are case-insensitive substrings; `regex:` entries are case-sensitive
  multiline regular expressions.
- **Why:** Keyless, deterministic, no judge drift between runs. Case-sensitive
  regexes keep `git branch -d` and `git branch -D` distinct, which a judge or a
  case-insensitive match would blur.
- **Result:** One task factory, `evals/inspect/skill_eval.py`, plus one
  `evals/inspect/samples/<skill>.yaml` per skill. Forbidden rules are written
  as command shapes (`regex:git push[^\n]*--force`) so a reply that refuses a
  flag while naming it still passes.
- **Rejected:** A model-graded rubric (needs an API key on every run, scores
  drift); rules plus rubric (double the authoring for little gate value).

### 2026-09-18: Fake toolchain inside the sandbox (Accepted)

- **Decision:** Harbor images carry fake `gh`, `pixi` and `okf` CLIs that
  append every call to `/var/log/skill-shims/<tool>.log` with a timestamp and
  answer from `/fixture`, plus a `git` wrapper that logs flags before
  delegating to the real binary. `pip`, `pip3`, `conda` and `uv` are shims
  that log and fail.
- **Why:** Real pixi means a multi-minute network build per task and an okf
  binary that must resolve inside the image. The evals test skill-following,
  not the toolchain; the log is what a verifier needs.
- **Result:** One base image, `llmoxie-skill-evals-base:local`, built by
  `pixi run -e evals harbor-base`; every task Dockerfile is `FROM` it.

### 2026-09-18: Pre-answered confirmations plus guard tasks (Accepted)

- **Decision:** Happy-path tasks state every confirmation the skill would ask
  for in `instruction.md` (harness token `claude-code:test-model`, which
  branches to delete, the bump type). Five guard tasks (commit, push,
  clean-branches, merge-pr, release) omit the confirmation and reward the
  agent for stopping.
- **Why:** An unattended run has no user to answer; the NEVER rules are the
  part most worth testing.
- **Result:** Twelve happy-path tasks and five guard tasks. Harbor's `nop`
  agent is the built-in negative test: happy-path tasks must score 0 under it,
  guard tasks 1.

### 2026-09-18: Shared harness and base image over per-skill files (Accepted)

- **Decision:** One Inspect task factory driven by sample files, one Harbor
  base image holding shims and every skill, thin per-task Dockerfiles that
  only build a fixture repo.
- **Why:** Adding a skill is one YAML file and one task directory; the shims
  and helper libraries live once.
- **Rejected:** Fully self-contained per-skill files (twelve copies of the
  shims that drift), and a hybrid with data-driven Inspect but self-contained
  Harbor tasks (buys nothing once the base image exists).

### 2026-09-18: Skills are read from `.agents/skills/`, never copied (Accepted)

- **Decision:** The harness resolves `.agents/skills/<name>` first, then
  `evals/skills/<name>`; only the greeting-file smoke toy lives in the latter.
  A gitignored sync step copies both into the base image build context.
- **Why:** One source of truth for a skill; an eval of a stale copy proves
  nothing.

## Layout once the plan lands

```
evals/
├── skills/greeting-file/SKILL.md   # toy smoke fixture only
├── inspect/
│   ├── skill_eval.py               # task factory + rule scorer
│   └── samples/<skill>.yaml        # 12 skills + greeting-file
├── harbor/
│   ├── base/                       # Dockerfile, lib/ (shimlib, fixture, verify), shims/, skills/ (synced)
│   └── tasks/<task>/               # task.toml, instruction.md, environment/{Dockerfile,fixture.sh},
│                                   # solution/solve.sh, tests/test.sh
└── logs/                           # gitignored
```

Fixture repos live at `/app` with a real bare remote at `/remote/origin.git`,
so push, prune and upstream tracking behave normally inside the sandbox.

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
pixi run -e evals inspect-smoke                               # every skill, canned answers, no key
pixi run -e evals inspect-skill -T name=commit --model <model>
pixi run -e evals harbor-oracle                               # base image + every task with the oracle
pixi run -e evals harbor-agent -m <model>                     # every task with claude-code
```

The Inspect smoke is deterministic and keyless, so it is part of
`pixi run verify`. Harbor needs a Docker daemon on the host, which is the main
reason an agent may be unable to run the agent-level half locally.

## Running against the LLMaven gateway (observed 2026-09-19)

The gateway is a LiteLLM proxy; credentials live in a gitignored `.env`
(`LLMOXIE_ENDPOINT`, `LLMOXIE_API_TOKEN`). What worked and what did not:

- Inspect reaches gateway models only through its `anthropic` provider
  (`ANTHROPIC_BASE_URL` + `ANTHROPIC_API_KEY`, model `anthropic/<name>`): the
  proxy speaks the Anthropic messages API for any model. The `openai` and
  `openai-api` providers need `openai>=3.1`, which Harbor's litellm pin
  (`openai<3`) forbids in the same environment; no stable litellm lifts it.
- Azure-hosted GPT deployments (`gpt-5.4-mini`) reject parameters the proxy
  produces when translating Anthropic-format requests; non-Azure models
  (`gpt-oss-120b`, `gemma-4-31b`) work on that route.
- Harbor's `claude-code` agent sends Anthropic-only parameters
  (`context_management`) the proxy cannot translate for non-Claude models, so it
  needs a Claude-family model. Harbor's `codex` agent works for GPT models
  through `OPENAI_BASE_URL` and reads skills from `~/.agents/skills`.
- First real-model results on the 39 Inspect samples: gemma-4-31b 0.795,
  gpt-oss-120b 0.667. The `commit` Harbor task scored 1.0 with codex on
  gpt-5.4-mini and with claude-code on ssec-claude-haiku-4-5, with the
  trajectory showing the agent reading `commit/SKILL.md` and `verify/SKILL.md`.
- The first real runs exposed rules that failed correct replies (case and
  curly-apostrophe variants of "can't delete main", a release input that never
  approved the tag, text-only models emitting pseudo tool calls). The injected
  skill now states the review is text-only, and those rules were loosened.
  Scores are noisy between runs; compare a rule change on two runs.

## Status

Merged to `main` in PR #42 (squash commit a164c9d, 2026-09-19) after CI ran the
Inspect smoke and the full 18-task Harbor matrix on a GitHub runner. What the
build taught about the tools is in [[project/harbor-conventions]],
[[project/inspect-conventions]], [[project/eval-authoring-lessons]] and
[[project/pixi-gate-quirks]].

# Related Concepts
- [Skill Evals Implementation Plan](skill-evals-plan.md): The plan that implements this design, with the decisions made while planning it.
- [Harbor Conventions for Skill Tasks](harbor-conventions.md): What building the skill evals taught about this tool or practice.
- [Inspect Conventions for Skill Samples](inspect-conventions.md): What building the skill evals taught about this tool or practice.
- [Lessons for Writing Verifiers and Sample Rules](eval-authoring-lessons.md): What building the skill evals taught about this tool or practice.
- [Pixi Task and Verify Gate Quirks](pixi-gate-quirks.md): What building the skill evals taught about this tool or practice.
