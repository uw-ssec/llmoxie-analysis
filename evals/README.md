# Skill evals

Every skill under `.agents/skills/` is evaluated at two levels from the `evals`
Pixi environment. Design:
`docs/superpowers/specs/2026-09-18-skill-evals-design.md`.

| Level | Question                                                             | Framework | Runs in                        |
| ----- | -------------------------------------------------------------------- | --------- | ------------------------------ |
| Model | With `SKILL.md` in context, does the model answer as the skill says? | Inspect   | `pixi run verify` (mock model) |
| Agent | Dropped into a sandbox with the skill, does the agent act on it?     | Harbor    | `harbor-oracle` (needs Docker) |

## Layout

```
evals/
├── skills/greeting-file/SKILL.md   # toy smoke fixture; real skills stay in .agents/skills
├── inspect/
│   ├── skill_eval.py               # one task for every skill: inject SKILL.md, score by rules
│   └── samples/<skill>.yaml        # user turns + must / must_not rules + canned smoke answer
├── harbor/
│   ├── base/                       # shared image: git, fake gh/pixi/okf, all skills
│   │   ├── Dockerfile
│   │   ├── lib/                    # shimlib.sh, fixture.sh, verify.sh
│   │   ├── shims/                  # gh, pixi, okf, git wrapper, forbidden, test_shims.sh
│   │   └── skills/                 # gitignored, filled by harbor-sync
│   └── tasks/<task>/               # 12 happy-path tasks + 5 guard tasks + greeting-file
│       ├── task.toml               # environment.skills_dir = "/skills"
│       ├── instruction.md          # pre-answers the confirmations the skill would ask
│       ├── environment/            # Dockerfile FROM the base + fixture.sh
│       ├── solution/solve.sh       # what the oracle agent runs
│       └── tests/test.sh           # reads shim logs and repo state, writes the reward
└── logs/                           # gitignored
```

## Run

```bash
pixi run -e evals inspect-smoke                                  # all skills, canned answers, no key
pixi run -e evals inspect-skill -T name=commit --model anthropic/claude-haiku-4-5
pixi run -e evals harbor-oracle                                  # build base, run every task with the oracle
pixi run -e evals harbor run -p evals/harbor/tasks/commit -a nop -o evals/logs/harbor   # a do-nothing agent: happy-path tasks must score 0
pixi run -e evals harbor-agent -m anthropic/claude-haiku-4-5     # every task with claude-code
pixi run -e evals inspect-view                                   # browse Inspect logs
pixi run -e evals harbor-view                                    # browse Harbor trajectories
```

## Running against the LLMoxie gateway

The gateway is a LiteLLM proxy. Put its URL and token in a gitignored `.env` at
the repository root as `LLMOXIE_ENDPOINT` and `LLMOXIE_API_TOKEN`, then map them
to the client each framework uses:

```bash
set -a; . ./.env; set +a
# Inspect: the anthropic provider works for every gateway model, because the
# proxy speaks the Anthropic messages API and routes on the model name.
export ANTHROPIC_API_KEY="$LLMOXIE_API_TOKEN" ANTHROPIC_BASE_URL="${LLMOXIE_ENDPOINT%/}"
pixi run -e evals inspect-skill -T name=all --model anthropic/gpt-oss-120b --max-connections 4
# Harbor with a GPT-family model: the codex agent reads skills from ~/.agents/skills.
export OPENAI_API_KEY="$LLMOXIE_API_TOKEN" OPENAI_BASE_URL="${LLMOXIE_ENDPOINT%/}/v1"
pixi run -e evals harbor run -p evals/harbor/tasks/commit -a codex -m gpt-5.4-mini -o evals/logs/harbor --force-build
# Harbor with a Claude-family model: the claude-code agent, through the same ANTHROPIC_* variables.
pixi run -e evals harbor run -p evals/harbor/tasks/commit -a claude-code -m ssec-claude-haiku-4-5 -o evals/logs/harbor --force-build
```

Known limits, all observed on 2026-09-19:

- Inspect's `openai` and `openai-api` providers need `openai>=3.1`, which
  Harbor's litellm pin (`openai<3`) forbids in the same environment. Use the
  anthropic provider for gateway models instead.
- The Azure-hosted GPT deployments reject the parameters the proxy produces when
  translating Anthropic-format requests (`gpt-5.4-mini` fails on both Inspect
  and claude-code that way). Non-Azure models such as `gpt-oss-120b` and
  `gemma-4-31b` work; GPT models work through the OpenAI route (codex).
- The claude-code agent sends Anthropic-only parameters (`context_management`)
  that the proxy cannot translate for non-Claude models, so pair it with a
  Claude-family model.
- Real-model Inspect scores are noisy between runs (temperature); compare a rule
  change on two runs before trusting a moved sample.

## How scoring works

Inspect: a sample's reply is CORRECT only if every `must` matches and no
`must_not` matches. Plain strings are case-insensitive substrings; a `regex:`
prefix is a case-sensitive multiline regex. Write forbidden rules as command
shapes (`regex:git push[^\n]*--force`) so a reply that merely mentions the flag
while refusing it still passes.

Harbor: the fake `gh`, `pixi` and `okf` (and a `git` wrapper) append every call
to `/var/log/skill-shims/<tool>.log` with a timestamp, and `<tool>.args` with
one argument per line. `tests/test.sh` sources `verify.sh` and asserts with
`shim_called`, `shim_arg`, `before`, `branch_exists` and friends. Fixture repos
live at `/app` with a real bare remote at `/remote/origin.git`. Guard tasks
leave out the confirmation and reward the agent for stopping.

## Adding a skill

1. Write `.agents/skills/<name>/SKILL.md`.
2. Add `evals/inspect/samples/<name>.yaml`: three to five samples, each aimed at
   one rule of the skill, at least one that tempts a forbidden action.
3. Add `evals/harbor/tasks/<name>/` from any existing task: `fixture.sh` builds
   the repo state, `instruction.md` pre-answers confirmations, `solve.sh` is the
   oracle, `test.sh` checks logs and state. Add a `<name>-guard` task if the
   skill has a NEVER rule.
4. `pixi run verify` (Inspect smoke and the coverage test) and
   `pixi run -e evals harbor-oracle`.

Both packages come from PyPI on purpose: conda-forge's inspect-ai pins
websockets 17 while harbor needs <16; one PyPI resolve settles both.
