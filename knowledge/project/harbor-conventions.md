---
type: Reference
title: Harbor Conventions for Skill Tasks
description: "How Harbor runs a task directory, delivers skills per agent, which agents prove what, the flags that matter, and the litellm/openai pin that shapes the evals environment."
tags: [harbor, evals, docker, agents, skills]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T05:48:35Z" }
governance: context
code_refs: ["evals/harbor/**"]
sources:
  - resource: evals/harbor/base/lib/verify.sh and evals/harbor/tasks/ at commit a164c9d
  - resource: "harbor 0.23.0 source, agents/installed/claude_code.py and codex.py (skills delivery)"
  - resource: "https://docs.harborframework.com/"
---

What Harbor (Laude's agent-task framework, `harbor` 0.23.0 from PyPI) actually
does with a task directory, learned while building `evals/harbor/` on
2026-09-18 and 2026-09-19. The official docs cover the schema; this records the
behaviour that shaped the verifiers.

## Task anatomy at run time

| Task file                | Where it lands in the container                                       |
| ------------------------ | --------------------------------------------------------------------- |
| `environment/Dockerfile` | Built with `pull_policy: build`; the context is `environment/` only   |
| `solution/solve.sh`      | `/solution/solve.sh`, run by the `oracle` agent                        |
| `tests/test.sh`          | `/tests/test.sh`, run after the agent; must write `/logs/verifier/reward.txt` |
| `instruction.md`         | The agent's prompt; pre-answer every confirmation a skill would ask    |

`environment.skills_dir = "/skills"` in `task.toml` is copied into the agent's
own skills location by each installed agent: `claude-code` copies it to
`$CLAUDE_CONFIG_DIR/skills/`, `codex` to `~/.agents/skills/`. The `oracle` and
`nop` agents never read it, so a matrix that is green under the oracle proves
nothing about skill delivery; only a real agent run does. The Dockerfile now
asserts `/skills/commit/SKILL.md` exists because a silent nesting bug once put
every skill under `/skills/skills/`.

## Agents worth knowing

- `oracle` runs the solution script: proves the task is solvable and the
  verifier accepts a correct trajectory.
- `nop` does nothing: every happy-path verifier must score 0 under it, and a
  guard verifier must not score 1 under it either, which forces at least one
  positive check per guard.
- `claude-code` and `codex` are the skill-aware installed agents used here;
  `terminus-2` is Harbor's own LiteLLM agent and does not receive skills.

## Flags that matter

- `--force-build` on every real run: fixture branch ages are relative to image
  build time (`date -d "40 days ago"`), so a cached image drifts.
- `-p <dir>` accepts one task or a directory of tasks; `-o evals/logs/harbor`
  keeps trajectories, `verifier/test-stdout.txt`, and the copied shim logs.
- `-m <model>` is passed to `claude-code` unchanged when `ANTHROPIC_BASE_URL`
  is set, so a gateway alias like `ssec-claude-haiku-4-5` works as-is.
- `--ae KEY=VALUE` sets agent environment variables; the API key and base URL
  are read from the host environment.

## Dependency pins

Harbor's `litellm` (1.101) pins `openai<3`; Inspect's OpenAI providers need
`openai>=3.1`. Both live in the one `evals` pixi environment, so Inspect must
reach OpenAI-compatible gateways through its `anthropic` provider instead. No
stable litellm lifts the pin as of 2026-09-19 (only a pre-release).

## Verifier helpers

`evals/harbor/base/lib/verify.sh` (installed at
`/usr/local/lib/skill-evals/verify.sh`) gives every `tests/test.sh` the same
vocabulary: `pass`, `fail`, `require`, `shim_called`, `shim_not_called`,
`shim_first_ts`, `shim_arg` (single-line values only), `shim_args_have`
(line-anchored greps over the one-argument-per-line log), `before`,
`repo_git`, `remote_git`, `commit_has_trailer`, `branch_exists`,
`remote_branch_exists`. `pass` and `fail` always exit 0 so Harbor records a
reward instead of an exception.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The evals this knowledge came from.
