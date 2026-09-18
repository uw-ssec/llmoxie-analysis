---
type: Fact
title: reader.py — Flattening Requests to Message Blocks
description: "The upstream module that explodes each gateway request into one row per content block, including the end_user parsing that session identity depends on."
tags: [reader, flattening, pandas, upstream, dataframe]
code_refs:
  - reference/llmoxie/src/llmaven/data/reader.py
sources:
  - resource: reference/llmoxie/src/llmaven/data/reader.py (435 lines)
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

`src/llmaven/data/reader.py` in the upstream repo is the layer that turns a
LiteLLM spend-log record into a tabular DataFrame — one row per _content block_,
not per message and not per request. The pipeline in
[[project/llmoxie-analysis]] reuses these functions unchanged; issue #3 in
[[project/epic-and-issues]] makes that reuse an explicit acceptance criterion.

## Entry points

```python
load_messages_from_records(records, *, include_thinking=False, include_tool_use=True) -> pd.DataFrame
load_messages(path, *, include_thinking=False, include_tool_use=True) -> pd.DataFrame
```

`load_messages` reads a JSONL file via `jsonlines.open`; the `_from_records`
variant takes an in-memory iterable, which is what the pipeline uses so it can
feed adapted ADLS records through the same code.

Note the defaults: **thinking blocks are excluded and tool-use blocks are
included.** Any analysis of reasoning content must pass `include_thinking=True`
explicitly.

## Row construction

`_base_row(record)` extracts the per-request fields carried onto every block
row:

| Output column                             | Source field           |
| ----------------------------------------- | ---------------------- |
| `request_id`                              | `request_id`           |
| `start_time`                              | `startTime`            |
| `end_time`                                | `endTime`              |
| `device_id`, `account_uuid`, `session_id` | parsed from `end_user` |
| `model`                                   | `model`                |
| `spend`                                   | `spend`                |
| `total_tokens`                            | `total_tokens`         |
| `user_api_key`                            | `api_key`              |
| `user_api_key_alias`                      | `metadata`             |

`_rows_from_record` then reads inputs from
`record["proxy_server_request"]["messages"]` and the output from
`response["choices"][0]["message"]`, tagging rows with `direction` of `input` or
`output` and indices `msg_idx` / `block_idx`.

The output read is wrapped in `try/except (KeyError, IndexError, TypeError)`
which logs `"request_id=%s: could not read response.choices[0].message: %s"`.
That handler is where Responses-API traffic quietly disappears — see
[[caveats/responses-api-gap]].

## Block handling

`_rows_from_block` recognizes `text`, `thinking`, and `tool_use`. Unknown block
types are not dropped — they are serialized into the `text` column, under an
explicit comment: _"Fallback: serialise unknown block types so no data is
lost."_ Cache metadata is read as `block["cache_control"]["type"]`.

## `end_user` parsing

`_parse_end_user(raw)` first tries `json.loads`. If that fails it falls back to
a regex:

```python
r"user_(?P<device_id>[0-9a-f]*)_account_(?P<account_uuid>.*?)_session_(?P<session_id>[0-9a-f-]+)"
```

If both fail it logs
`"Could not parse end_user field into device/account/session ids: %r"` and
returns empty strings for all three. This single function is the mechanism
behind the project's most consequential data-quality problem — see
[[caveats/end-user-parsing]].

## The two reduction functions

These are **not interchangeable**, and choosing wrongly silently corrupts
results. Full treatment in [[caveats/dedup-vs-last-request]].

### `last_request_per_session(df)`

Keeps only the longest request per session — because each request in an agentic
conversation resends the full history, the longest one contains the whole
transcript. Ties break on `start_time`, latest wins.

```python
longest = (
    df[df["direction"] == "input"]
    .groupby(["session_id", "request_id", "start_time"])["msg_idx"]
    .max()
    .reset_index()
    .sort_values(["msg_idx", "start_time"], ascending=[False, False])
    .groupby("session_id", as_index=False)
    .first()
)[["request_id"]]
return df.merge(longest, on="request_id")
```

### `deduplicate_messages(df)`

Keeps the **earliest** occurrence of each `(session_id, msg_idx, block_idx)`, so
that `start_time` reflects when a message was first introduced rather than when
it was last resent.

## Utilities

`flatten_value(value)`, `get_value(record, keys)`, `inspect_keys(data, keys)`,
and `normalize_model_name(model)` — the last of which is significant enough to
have its own note, [[upstream/model-name-normalization]].

## Related Concepts

- [group_sessions.py — Reconstructing Conversations](session-reconstruction.md):
  Session grouping is the layer built directly on top of these flattened rows.
- [Caveat: end_user Parsing Fragility](../caveats/end-user-parsing.md):
  `_parse_end_user` is the fragile step in this module, and that caveat records
  its failure rate.
- [Model Name Normalization](model-name-normalization.md): Model-identifier
  cleanup is the other normalization this module performs.
- [Caveat: The Responses API Output Gap](../caveats/responses-api-gap.md): The
  response parser in this module reads only one of the two OpenAI response
  shapes.
