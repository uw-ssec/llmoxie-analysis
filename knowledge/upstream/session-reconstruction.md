---
type: Fact
title: group_sessions.py — Reconstructing Conversations
description: "The upstream prototype that groups flat request rows into per-session conversations, the behaviors this project must preserve, and the single streaming path that replaced its two code paths."
tags: [sessions, grouping, prototype, upstream, pr-151, pr-167, streaming, parquet]
generated: { by: "claude-code:ssec-claude-opus-5", at: "2026-10-14T18:19:39Z" }
code_refs: [src/llmoxie_analysis/data/group_sessions.py, src/llmoxie_analysis/data/README.md, reference/llmoxie/src/llmaven/data/group_sessions.py]
sources:
  - resource: reference/llmoxie/src/llmaven/data/group_sessions.py (673 lines)
  - resource: "reference/llmoxie commit ec5d8b2, PR #151, 2026-09-11"
  - resource: "reference/llmoxie commit 3e9a694, PR #167, 2026-09-18"
  - resource: reference/llmoxie/src/llmaven/data/README.md
---

!!! note "This code now lives in `src/`"

    These modules were moved into `src/llmoxie_analysis/data/` from
    `uw-ssec/llmoxie`. They were lifted, not rewritten, so everything below
    still describes live behavior — read "upstream" here as where the code
    came from, not where it is. See [[project/current-state]].

Landed 2026-09-11 in commit `ec5d8b2` (PR #151) and reworked a week later in
`3e9a694` (PR #167, 2026-09-18), this is the newest and least settled piece of
upstream code — and the direct prerequisite for this project. The
`reference/llmoxie` submodule is pinned at `3e9a694`, and this concept describes
that revision.
Issue #2 of [[project/epic-and-issues]] was "fix and merge `group_sessions.py`";
it is done — the defects it listed are repaired in this revision and the
ticket closed on 2026-09-20.

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

## `build_sessions(df) -> tuple[list[dict], int]` (removed)

Superseded by the single streaming path described below, and deleted from this
repo. Kept here because the two invariants it encoded still bind the code that
replaced it.

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

## One streaming path, for every input

Upstream, and in this repo until the consolidation, `main()` branched on
`args.input.suffix == ".jsonl"`: a single `.jsonl` took a two-pass streaming
path, and a directory / `.zip` / `.json` took a DataFrame path (`_load_all`
building one frame of every block row, then `build_sessions(df)`).

The branch had no technical basis — `_iter_raw_records` already handled every
container, and `from_adls` always emits `proxy_server_request.messages`, which
is what the streaming last-request heuristic reads. Its real cost was drift:
the streaming path re-implemented `build_sessions` and
`last_request_per_session` rather than calling them, and the two had already
diverged on thinking blocks, last-request choice, skip counting and reader
warnings. Only the DataFrame path had tests.

`_load_all` and `build_sessions` are now **deleted**. Every input goes through
`stream_sessions(input_path, *, parquet_path, include_thinking, verbose)`:

1. `_scan_and_write_blocks` iterates records once. It keeps per-session
   statistics in a dict — memory proportional to the number of sessions, not
   blocks — and writes block rows to a Snappy-compressed Parquet in batches of
   10,000 (`_PARQUET_BATCH_SIZE`). Only the twelve columns reconstruction needs
   are written: `request_id`, `session_id`, `direction`, `msg_idx`,
   `block_idx`, `role`, `type`, `text`, `thinking`, `tool_name`, `tool_input`,
   `tool_use_id`. The schema is declared explicitly (`_PARQUET_SCHEMA`) because
   PyArrow otherwise infers a `null` type for a column whose first batch is all
   `None`, such as `thinking`. It returns a `ScanResult` carrying
   `session_stats`, `n_skipped`, and a `last_request_ids` property.
2. `_build_sessions_from_parquet` reads that file back **with the request_id
   filter pushed into PyArrow** (`filters=[("request_id", "in", ...)]`) and runs
   `_reconstruct_conversation` per session. Row-group pruning does not help —
   request ids are UUIDs, so per-group min/max statistics span everything — but
   the predicate is evaluated a row group at a time, so peak memory is roughly
   the output size rather than every block row of every resent request. (The
   earlier code read the whole table and filtered in pandas, which made pass 2
   unbounded and defeated the point of streaming pass 1.)

`reader.last_request_per_session` and `reader.deduplicate_messages` survive as
public reader helpers for notebook work on an already-loaded frame — see
[[caveats/dedup-vs-last-request]] — they simply have no caller in
`group_sessions.py` any more.

### Semantics the single path settled

| Behavior              | Resolved as                                                              |
| --------------------- | ------------------------------------------------------------------------ |
| Thinking blocks       | **included**; `--no-thinking` drops them                                 |
| "Last request" choice | most `proxy_server_request.messages`, ties to latest start               |
| Skip count            | **records** with no usable session_id (not de-duplicated by request_id)  |
| Empty records         | still counted in `n_requests` / spend / tokens                           |
| Reader warnings       | suppressed to an aggregate count; `-v`/`--verbose` restores them         |

Two of these fixed real gaps in the old DataFrame path. It keyed sessions on
`session_id != ""`, which let a `None` from the native-`session_id` fallback
through as a session key; the streaming `if not session_id` catches both. And
it aggregated spend and tokens over *block rows*, so a record that produced no
blocks — an empty message list, or a Responses-API reply the reader cannot
parse — contributed nothing to its session's totals. Stats now accumulate from
the raw record before flattening, so those billed requests are counted. See
[[caveats/responses-api-gap]] and [[caveats/cost-token-double-counting]].

The session key is still the parsed `end_user` session falling back to
LiteLLM's native `session_id`, which shapes what a "session" and a "skipped"
record mean. See [[caveats/end-user-parsing]].

### The Parquet intermediate

The intermediate Parquet lives in a `tempfile.TemporaryDirectory` and is
deleted on success, so an ordinary run leaves nothing behind.
`--parquet-cache PATH` keeps it, plus a `<PATH>.stats.json` sidecar holding the
session statistics, `n_skipped`, and a **fingerprint** of the input it was built
from: resolved path, size and mtime for a file; file count and max mtime for a
directory; plus `include_thinking`, because that changes the Parquet's contents
rather than just the run.

A later run over the same input reuses the cache and skips pass 1. A mismatch
exits naming the differing field. This replaces upstream's behavior, where
nothing tied a cache to its input and the default cache name derived from the
output path — so the natural re-run (delete the output, reuse the same `-o`,
since the tool refuses to overwrite) silently reused a stale cache.

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

## Repaired issue #2 defects

The five defects Issue #2 enumerated — no unit tests or fixtures, `print` used
instead of `logging`, the temp-file leak on zip reads, silent failures in the
output-message path, and `skipped_session_count` not being reported — are all
repaired in this revision: 17 unit tests plus the hand-checked fixture
`tests/data/fixtures/test.jsonl`, `logging` throughout, in-place zip reads,
warnings on data that fails to parse, and the skip count logged on both code paths.
PR #151 passed CI and merged on 2026-09-12; the ticket closed 2026-09-20.
What remains in this concept are the design-level concerns above — the
two-path drift and the unchecked Parquet cache — which are still live and the
real input to what stage two of the pipeline becomes.

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](reader-flattening.md):
  Grouping consumes the flat message-block rows that the reader produces.
- [Caveat: last_request_per_session vs deduplicate_messages](../caveats/dedup-vs-last-request.md):
  The ordering constraint between the two reduction functions is encoded in this
  prototype.
- [Pipeline Architecture](../pipeline/pipeline-architecture.md): This prototype
  is what stage two of the production pipeline becomes.
