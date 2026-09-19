---
type: Fact
title: group_sessions.py — Reconstructing Conversations
description: "The upstream prototype that groups flat request rows into per-session conversations, its DataFrame and streaming code paths, and the specific behaviors this project must preserve or repair."
tags: [sessions, grouping, prototype, upstream, pr-151, pr-167, streaming, parquet]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T00:11:42Z" }
code_refs: [reference/llmoxie/src/llmaven/data/group_sessions.py, reference/llmoxie/src/llmaven/data/README.md]
sources:
  - resource: reference/llmoxie/src/llmaven/data/group_sessions.py (673 lines)
  - resource: "reference/llmoxie commit ec5d8b2, PR #151, 2026-09-11"
  - resource: "reference/llmoxie commit 3e9a694, PR #167, 2026-09-18"
  - resource: reference/llmoxie/src/llmaven/data/README.md
---

Landed 2026-09-11 in commit `ec5d8b2` (PR #151) and reworked a week later in
`3e9a694` (PR #167, 2026-09-18), this is the newest and least settled piece of
upstream code — and the direct prerequisite for this project. The
`reference/llmoxie` submodule is pinned at `3e9a694`, and this concept describes
that revision.
Issue #2 of [[project/epic-and-issues]] is "fix and merge `group_sessions.py`";
nothing else in the pipeline can proceed until it does.

It sits one layer above [[upstream/reader-flattening]]: where `reader.py`
produces block rows, `group_sessions.py` collapses them into one record per
conversation.

## Input handling

`_iter_raw_records(input_path)` accepts four shapes:

| Input     | Behavior                               |
| --------- | -------------------------------------- |
| Directory | `rglob` for `.jsonl` and `.json`       |
| `.zip`    | Read **in place** — no disk extraction |
| `.jsonl`  | Line-delimited records                 |
| `.json`   | Single document                        |

Unknown extensions produce a warning rather than an error. Reading zips in
memory is deliberate: the prototype originally extracted to a temp directory and
leaked it.

`_load_adls_json(fh, name)` carries an explicit `json.JSONDecodeError` guard
with the reason stated in a comment: _"Unlike an empty .jsonl file, json.load()
raises on an empty/corrupt file."_ Given [[platform/adls-logger]]'s silent write
failures, partially-written blobs are a real possibility, and a single corrupt
file must not abort a day's read.

## ADLS → common format

`_adls_record_to_spend_log_shape(record, fallback_request_id)` reads from
`record["kwargs"]["standard_logging_object"]` and emits the LiteLLM spend-log
shape, converting epoch floats to ISO strings via `_epoch_to_iso`:

```python
{
    "request_id": slo.get("id") or fallback_request_id,
    "startTime": _epoch_to_iso(slo.get("startTime")),
    "endTime": _epoch_to_iso(slo.get("endTime")),
    "end_user": slo.get("end_user"),
    "model": slo.get("model"),
    "spend": slo.get("response_cost"),
    "total_tokens": slo.get("total_tokens"),
    "api_key": metadata.get("user_api_key_hash"),
    "metadata": {"user_api_key_alias": metadata.get("user_api_key_alias")},
    "proxy_server_request": {"messages": slo.get("messages") or []},
    "response": slo.get("response") or {},
}
```

The docstring records that this was verified against a real sample from the
`litellm-logs` container — a GitHub Copilot / `gpt-5.3-codex` request through
the Responses API — and names the gap that sample exposed: see
[[caveats/responses-api-gap]]. This function is the ancestor of `from_adls` in
[[pipeline/source-adapters]].

## `build_sessions(df) -> tuple[list[dict], int]`

Two things deserve attention.

**It keeps the raw, non-deduplicated frame.** The comment is explicit:

> Keep the raw (non-deduped) data: `last_request_per_session` needs each
> request's own full resent history intact. `deduplicate_messages` would strip
> most of that history away.

This ordering constraint is the subject of [[caveats/dedup-vs-last-request]].

**It counts what it drops.**

```python
n_requests_skipped = raw_input_df.loc[
    raw_input_df["session_id"] == "", "request_id"
].nunique()
```

That second return value is the `skipped_session_count` the epic requires every
pipeline run to surface — see [[caveats/end-user-parsing]].

Since `3e9a694` a row's `session_id` is only empty when both `end_user` and
LiteLLM's native `session_id` are, so this count no longer measures `end_user`
parse failures. That caveat explains what it measures instead.

Per-session statistics are computed by first collapsing to one row per
`(session_id, request_id)` via `drop_duplicates`, then aggregating: `device_id`,
`account_uuid`, and `user_api_key_alias` take the first value; `n_requests` is a
`nunique`; `total_spend` and `total_tokens` are sums; `start_time` is the min
and `end_time` the max. `models` is a sorted unique set. Sessions come out
ordered by `start_time`.

!!! warning "The sums are raw, not net"

    `total_spend` and `total_tokens` sum across every request in the session —
    and every request resends the conversation so far. See
    [[caveats/cost-token-double-counting]].

## Two code paths, chosen by file extension

Since `3e9a694`, `main()` branches on `args.input.suffix == ".jsonl"`.

**Any other input** — a directory, a `.zip`, a `.json` — takes the original path
described above: `_load_all` builds one DataFrame of every block row, then
`build_sessions(df)`.

**A single `.jsonl` file** takes a new two-pass streaming path, written so a
large export does not have to fit in memory as a block-level DataFrame:

1. `_stream_to_parquet(input_path, parquet_path)` iterates records once. It
   keeps per-session statistics in a dict — memory proportional to the number
   of sessions, not blocks — and writes block rows to a Snappy-compressed
   Parquet file in batches of 10,000 (`_PARQUET_BATCH_SIZE`). Only the twelve
   columns reconstruction needs are written: `request_id`, `session_id`,
   `direction`, `msg_idx`, `block_idx`, `role`, `type`, `text`, `thinking`,
   `tool_name`, `tool_input`, `tool_use_id`. The schema is declared explicitly
   (`_PARQUET_SCHEMA`) because PyArrow otherwise infers a `null` type for a
   column whose first batch is all `None`, such as `thinking`.
2. `_build_sessions_from_parquet` reads that file back, keeps only rows whose
   `request_id` is a session's chosen request, and runs the same
   `_reconstruct_conversation` per session.

The streaming path re-implements what `build_sessions` and
`last_request_per_session` do rather than calling them, so the two paths can
drift. They already differ in four ways:

| Behavior               | DataFrame path                                   | Streaming path (`.jsonl`)                                        |
| ---------------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| Thinking blocks        | excluded (`load_messages_from_records` defaults) | included (`include_thinking=True`)                               |
| "Last request" choice  | highest input `msg_idx`, ties to latest start    | most `proxy_server_request.messages`, ties to latest start       |
| Skip count             | distinct `request_id`s with empty `session_id`   | records with empty `session_id`, not de-duplicated               |
| Reader warnings        | emitted per record                               | reader logger raised to `ERROR`; only a no-content total logged  |

The streaming path also logs how many records yielded no content blocks, naming
_"empty messages or Responses-API format"_ as the causes — an upstream
acknowledgement of [[caveats/responses-api-gap]].

In both paths the session key is the parsed `end_user` session falling back to
LiteLLM's native `session_id`, which changes what a "session" and a "skipped"
request mean. See [[caveats/end-user-parsing]].

### The Parquet cache

Pass 1 leaves two files behind: the block Parquet, at `--parquet-cache PATH` or
by default `<output>.blocks.parquet`, and a `<PATH>.stats.json` sidecar holding
the session statistics and `n_skipped`. If the Parquet already exists, pass 1 is
**skipped and the cache reused**; if the Parquet exists without its sidecar the
run exits with an error.

Nothing checks that a reused cache was built from the same input. The default
cache name derives from the output path, and a finished run leaves its cache
behind. Because the tool refuses to overwrite its output, the natural way to
re-run is to delete the old output and use the same `-o` — which silently reuses
the previous run's cache, even if the input file has changed.

The change adds `pyarrow >=19.0.0,<20` to upstream's `llmaven` Pixi feature, and
the streaming path imports `tqdm` for its two progress bars.

## CLI

```bash
pixi run -e llmaven python -m llmaven.data.group_sessions \
  path/to/jan-feb-march-2026.zip -o sessions.jsonl
```

`argparse` takes `input`, `-o/--output`, `--format {jsonl,parquet}` (default
`jsonl`), and `--parquet-cache PATH` (streaming path only). It **refuses to
overwrite** an existing output
(`SystemExit(f"{output} already exists…")`) — safe for a prototype, wrong for a
scheduled job, which is why the production pipeline inverts this into
always-overwrite; see [[pipeline/idempotency-design]].

Output record keys: `session_id`, `device_id`, `account_uuid`,
`user_api_key_alias`, `models[]`, `n_requests`, `total_spend`, `total_tokens`,
`start_time`, `end_time`, `messages[]`.

Benchmark from the README: **11,992 requests → 279 sessions in about ten
seconds** on the January–March 2026 dump. That was measured before `3e9a694`,
when requests with an unparsable `end_user` were dropped. With the native
`session_id` fallback the same input should produce far more sessions; the
README figure has not been re-measured.

## Known defects to repair

Issue #2 enumerates them: no unit tests or fixtures, `print` used instead of
`logging`, the temp-file leak, silent failures in the output-message path, and
`skipped_session_count` not being reported.

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](reader-flattening.md):
  Grouping consumes the flat message-block rows that the reader produces.
- [Caveat: last_request_per_session vs deduplicate_messages](../caveats/dedup-vs-last-request.md):
  The ordering constraint between the two reduction functions is encoded in this
  prototype.
- [Pipeline Architecture](../pipeline/pipeline-architecture.md): This prototype
  is what stage two of the production pipeline becomes.
