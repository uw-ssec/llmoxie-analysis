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

## Areas

* [Platform](platform/index.md) - LLMoxie itself, the system whose request logs
  this project consumes.
