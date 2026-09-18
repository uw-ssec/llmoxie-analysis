---
okf_version: "0.2"
---

# Knowledge Base

Project memory for **llmoxie-analysis** — the package that turns raw
[LLMoxie](https://github.com/uw-ssec/llmoxie) gateway request logs into a
queryable Parquet warehouse of sessions, messages, tool calls, and tool
definitions.

This bundle records what the code cannot tell you on its own: why the pipeline
is shaped the way it is, what the upstream prototypes actually do, and the
properties of this data that will quietly mislead anyone who queries it without
knowing them. Setup, commands, and contribution rules are not repeated here —
they live in `AGENTS.md`, `CONTRIBUTING.md`, and `.agents/rules/`.

Read and write this bundle through the `okf` CLI, run as `pixi run okf`. Start
with `okf search "<keywords>"` rather than browsing these files.

## Start here

* [What this project is](project/llmoxie-analysis.md) — the problem, the
  deliverable, and where it sits relative to LLMoxie.
* [What exists and what is only designed](project/current-state.md) — read this
  before going looking for code. Most of `pipeline/` is a specification.
* [Read the caveats before trusting a number](caveats/index.md) — four
  properties of this data that produce confidently wrong answers.
* [How this bundle is maintained](project/okf-conventions.md) — layout,
  frontmatter contract, and the gates a change must pass.
* [Why the repository looks like this](project/cross-viss-demo.md) — the two
  purposes it serves, and which one explains the current priorities.

## Areas

* [Project](project/index.md) - What this project is, how it is planned, and how
  its knowledge is kept.
* [Platform](platform/index.md) - LLMoxie itself, the system whose request logs
  this project consumes.
* [Upstream](upstream/index.md) - Prototype code inherited from LLMoxie that
  this project must fix or absorb.
* [Caveats](caveats/index.md) - Properties of the data that will mislead anyone
  who does not know them.
* [Pipeline](pipeline/index.md) - The design of the thing being built.
* [Datasets](datasets/index.md) - Specific extracts and the rules for handling
  them.
