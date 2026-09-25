---
type: Reference
title: Inspect Conventions for Skill Samples
description: "How the Inspect harness is invoked, which providers reach the LLMoxie gateway, and the rule semantics and sample-writing rules that real-model runs forced."
tags: [inspect, evals, gateway, litellm, samples]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-09-25T15:05:52Z" }
governance: context
code_refs: ["evals/inspect/**"]
sources:
  - resource: evals/inspect/skill_eval.py at commit a164c9d
  - resource: "Inspect eval logs under evals/logs/inspect on 2026-09-19 (gemma-4-31b, gpt-oss-120b)"
  - resource: "https://inspect.aisi.org.uk/"
---

How Inspect (the UK AI Safety Institute's `inspect-ai`, 0.3.265 from PyPI)
behaves in this repository's harness, `evals/inspect/skill_eval.py`, as learned
on 2026-09-18 and 2026-09-19.

## Invocation

- `inspect eval evals/inspect/skill_eval.py -T name=<skill> --model <provider/model>`;
  `-T name=all` loads every `samples/*.yaml`. The pixi tasks `inspect-smoke`
  and `inspect-skill` wrap this.
- A model must always be named, even when nothing is generated: the smoke run
  passes `--model mockllm/model` and a solver that replays each sample's
  `smoke_answer` instead of calling `generate()`. That replaced `mockllm`'s
  `custom_outputs`, whose replay order does not survive concurrent samples.
- Logs land in `evals/logs/inspect/*.eval`; read them with
  `inspect_ai.log.read_eval_log` (`sample.id`, `sample.output.completion`,
  `sample.scores`), or `inspect view`.

## Providers and the gateway

- The `anthropic` provider needs the `anthropic` package (added to the `evals`
  feature) and reaches any model on the LLMoxie LiteLLM gateway through
  `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY`, because the proxy serves the
  Anthropic messages API for every model name. Use `anthropic/<gateway model>`.
- The `openai` and `openai-api` providers require `openai>=3.1`, which the same
  environment cannot have (Harbor's litellm pins `openai<3`).
- Azure-hosted deployments behind the gateway reject the parameters LiteLLM
  produces when translating Anthropic-format requests; `gpt-5.4-mini` failed,
  `gpt-oss-120b` and `gemma-4-31b` worked.
- Real-model scores are noisy between runs at default temperature; judge a
  rule change on two runs of the same model.

## Rule semantics in `skill_eval.py`

- Plain `must` / `must_not` strings are case-insensitive substrings; `regex:`
  entries are `re.search` with `re.MULTILINE` only, so use the inline `(?i)`
  flag when case must not matter. Case-sensitive by default keeps
  `git branch -d` and `git branch -D` distinct.
- Forbidden rules are written as command shapes anchored to a line start
  (`regex:^\s*pip install`, `regex:^Co-Authored-By:`) so a reply that refuses
  by naming the thing still passes.
- The injected system message ends with a note that the review is text-only
  and the model cannot run tools; without it, small models answer with pseudo
  tool calls instead of the commands they would run.
- Sample inputs must pre-answer any confirmation the skill would ask for (the
  release sample once failed a model that correctly stopped to ask before
  tagging).
- Match punctuation loosely: models write `can’t` with a curly apostrophe, so
  `can.t` beats `can't`.

# Related Concepts
- [Skill Evaluation with Inspect and Harbor](skill-evals.md): The evals this knowledge came from.
