# Skill evals

Evaluate skills (directories with a `SKILL.md`) at two levels, using two
frameworks, from one Pixi environment.

| Level | Question                                                      | Framework                                   | Needs              |
| ----- | ------------------------------------------------------------- | ------------------------------------------- | ------------------ |
| Model | Given the skill in context, does the model answer correctly?  | [Inspect](https://inspect.aisi.org.uk/)     | a model (or mock)  |
| Agent | Dropped into a sandbox with the skill, does the agent use it? | [Harbor](https://docs.harborframework.com/) | Docker (+ a model) |

## Layout

```
evals/
├── skills/                 # canonical skills under test (one dir per skill)
│   └── greeting-file/SKILL.md
├── inspect/                # Inspect tasks; import skills from ../skills
│   └── greeting_file.py
├── harbor/tasks/           # Harbor tasks; skills are copied into the build context
│   └── greeting-file/
│       ├── task.toml       # environment.skills_dir = "/skills"
│       ├── instruction.md
│       ├── environment/Dockerfile   # COPY skills/ /skills/
│       ├── solution/solve.sh        # what the oracle agent runs
│       └── tests/test.sh            # writes /logs/verifier/reward.txt
└── logs/                   # gitignored run output
```

## Setup

```bash
pixi install -e evals
```

The `evals` environment is in its own solve group because Harbor needs Python
3.12+. Both packages are PyPI dependencies on purpose; see the comment in
`pixi.toml`.

## Run

```bash
pixi run -e evals inspect-smoke    # mock model, deterministic, no API key
pixi run -e evals harbor-oracle    # builds the task image, runs solution/solve.sh, verifies
pixi run -e evals evals-smoke      # both

pixi run -e evals inspect-view     # browse Inspect logs
pixi run -e evals harbor-view      # browse Harbor trajectories
```

Against a real model:

```bash
export ANTHROPIC_API_KEY=...
pixi run -e evals inspect eval evals/inspect/greeting_file.py --model anthropic/claude-haiku-4-5
pixi run -e evals harbor run -p evals/harbor/tasks/greeting-file -a claude-code -m anthropic/claude-haiku-4-5 -o evals/logs/harbor
```

## Adding a skill

1. Put the skill under `evals/skills/<name>/SKILL.md`.
2. Inspect: add samples (prompt + expected answer) to a task in `evals/inspect/`
   and load the skill with `load_skill("<name>")`.
3. Harbor: `pixi run -e evals harbor tasks init <name> -p evals/harbor/tasks`,
   set `environment.skills_dir = "/skills"` in `task.toml`, add
   `COPY skills/ /skills/` to the Dockerfile, and extend `harbor-sync-skills` in
   `pixi.toml` to copy the new skill in. Write `solution/solve.sh` so the oracle
   agent passes, then write `tests/test.sh`.

## Notes

- Harbor also accepts skills at job time with `--skill <path|org/repo>`, which
  are uploaded into the same `skills_dir` and override bundled skills by name.
  Useful for A/B testing a skill revision without rebuilding the image.
- Harbor records a content digest of every skill in the job lock file, so
  results trace back to the exact SKILL.md that was used.
