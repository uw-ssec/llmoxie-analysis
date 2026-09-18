---
type: Reference
title: Analytics Schema — Four Tables
description: "The sessions, messages, tool_calls, and tool_definitions tables the pipeline emits, their key columns, and the conventions that make them joinable."
tags: [schema, tables, parquet, polars, arrow, reference]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/4
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/5
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

Defined by `data/schema.py` (issue #4) as dataclasses plus Polars/Arrow schema
dicts, and produced by `data/transform.py` (issue #5). See
[[project/epic-and-issues]].

## The tables

| Table              | Grain                       | Purpose                            |
| ------------------ | --------------------------- | ---------------------------------- |
| `sessions`         | one row per conversation    | aggregates, cost, duration, client |
| `messages`         | one row per message         | content, roles, ordering           |
| `tool_calls`       | one row per tool invocation | which tools agents actually use    |
| `tool_definitions` | one row per tool offered    | what the client made available     |

The last pair is the interesting one. `tool_definitions` records what a client
_offered_ the model; `tool_calls` records what the model _used_. The difference
between them — tools advertised but never invoked — is a real finding about
agent design, not a data artifact.

## Transform functions

```python
session_to_row(session)              -> dict   # → sessions
session_to_messages(session)         -> list   # → messages
session_to_tool_calls(session)       -> list   # → tool_calls
session_to_tool_definitions(session) -> list   # → tool_definitions
build_tables(sessions, ...)          -> dict[str, pl.DataFrame]
```

## Conventions

### `data_source`

Every row of every table carries `'adls'` or `'litellm'`. Given the fidelity
difference documented in [[platform/logging-paths]], any metric derived from
message _content_ should be grouped or filtered by this column rather than
pooled.

### `agent_type`

One of `claude_code`, `copilot`, `opencode`, `unknown`, detected in
`data/schema.py`. `unknown` is a real category and should not be dropped — an
unrecognized client is information about gateway usage.

!!! warning "agent_type interacts with a known gap"

    Missing assistant replies cluster by client. See
    [[caveats/responses-api-gap]] before comparing message content across
    `agent_type` values.

### `model`

Normalized through the upstream function rather than reimplemented — see
[[upstream/model-name-normalization]].

### Raw and net metrics

`total_spend` / `total_tokens` alongside `net_spend` / `net_tokens`. The reason
both exist is [[caveats/cost-token-double-counting]]; the derivation constraint
is [[caveats/dedup-vs-last-request]].

### `tool_set_hash`

A **stable** sha256 over the session's tool definitions — stable meaning the
same set of tools hashes identically regardless of the order they arrived in.
Sort before hashing. This makes "which agent configuration is this?" a cheap
group-by instead of a set comparison, and lets a configuration change be spotted
as a hash change over time.

### `msg_idx`

`None` for output and assistant messages. Input messages carry their position in
the resent history; an output has no position in that sequence. Treat a null
`msg_idx` as "this is a reply", not as missing data.

### Timestamps

`timestamp[us, UTC]` throughout — microsecond precision, explicitly UTC. Fixing
this in the schema rather than inferring it prevents the timezone drift that
appears when Parquet files written on different machines are unioned.

## Session identity

The join key across all four tables is `session_id`, recovered by parsing
`end_user`. Roughly a quarter of early-2026 requests have no usable value and
are absent from every table — see [[caveats/end-user-parsing]].

## Related Concepts

- [Pipeline Architecture](pipeline-architecture.md): The four stages described
  there are what produce these four tables.
- [Storage Layout and Parquet I/O](storage-layout.md): The storage layer decides
  how each of these tables is partitioned and written to disk.
- [Query Layer: DuckDB and Synapse Serverless](query-layer.md): The query layer
  is how these tables are read back for analysis.
