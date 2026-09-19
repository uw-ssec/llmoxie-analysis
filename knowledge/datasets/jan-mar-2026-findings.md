---
type: Fact
title: What Profiling the Jan–Mar 2026 Extract Proved
description: "Structure-only profiling confirmed four documented caveats with real numbers, and surfaced three new ones — an unreliable cache flag, a useless native session_id, and an 11% failure rate that must be filtered before any metric."
tags: [findings, data-quality, caveats, validation, early-2026]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T00:10:18Z" }
sources:
  - resource: structure-only profile of the Jan-Mar 2026 extract
  - resource: "https://github.com/uw-ssec/llmoxie-analysis/issues/1"
---

Until now every caveat in this bundle was derived from reading upstream code and
the epic. [[datasets/jan-mar-2026-extract]] is the first chance to check those
claims against real records. This concept holds what the profile settled.

Every figure below came from counting keys, types, and values — never from
reading a value that could carry user content. See [[datasets/pii-handling]].

## Confirmed: the fidelity ceiling is real, and it is the floor

[[platform/logging-paths]] warns that the LiteLLM path may carry truncated
messages because prompts appear only when `store_prompts_in_spend_logs` is
enabled. In this extract the top-level `messages` column is an **empty object on
all 13,291 records**. The setting was off.

The prompts are not gone, though. They survive in the request echo:

| Location                        | Records carrying it |
| ------------------------------- | ------------------- |
| `proxy_server_request.messages` | 11,992              |
| `proxy_server_request.system`   | 9,904               |
| `response.choices`              | 11,804              |

So conversation content **is** recoverable for this era — just not from the
column an adapter would naturally reach for. Any reader targeting this extract
must read `proxy_server_request`, and [[pipeline/source-adapters]] needs a
LiteLLM adapter variant that knows this.

## Confirmed: end_user coverage is about 74%

[[caveats/end-user-parsing]] asserts that roughly a quarter of early-2026
requests cannot be parsed into a session identity. Measured directly: `end_user`
is **empty on 3,512 of 13,291 records — 26.4%**.

The shape of the non-empty values is also consistent with `_parse_end_user`'s
regex branch rather than its JSON branch. Across all 9,779 present values there
is not a single `.`, `@`, `/`, or `#`; 9,777 contain both `-` and `_`, and 851
additionally contain `:`. That is the `user_…_account_…_session_…` form, not a
JSON object.

## Confirmed: the Responses API gap exists, and is tiny here

[[caveats/responses-api-gap]] describes replies that go unparsed because the
Responses API returns `output` instead of `choices`. This extract contains **13
such records** — `call_type: aresponses`, carrying `input_tokens` and
`output_tokens` rather than `prompt_tokens` and `completion_tokens`.

The caveat holds, and the magnitude in this window is 0.1%. That is small enough
to ignore for aggregate spend and large enough to invalidate a per-client
response-length comparison, exactly as the caveat predicts.

## Confirmed: context resend dominates the token counts

[[caveats/cost-token-double-counting]] argues that raw token sums mostly measure
conversation length. The extract makes the scale of that concrete:

- Prompt tokens **486,320,257** against completion tokens **4,837,330** — a
  ratio near **100:1**.
- Of those prompt tokens, **419,111,970 were cache reads** (86%), with a further
  49,030,638 spent creating cache entries.

A 100:1 ratio is not what conversation looks like. It is what resending the same
context on every turn looks like, and it is the clearest possible argument for
carrying `net_` variants alongside the raw sums.

## New: the cache_hit column cannot be trusted

The top-level `cache_hit` column is `False` on 11,950 records and `None` on
1,341. **It is never `True`** — in a dataset where 86% of prompt tokens were
served from cache.

!!! warning "Read cache behavior from response.usage, not from cache_hit"

    LiteLLM's `cache_hit` column tracks its *own* proxy-level response cache,
    not the provider's prompt cache. Anthropic prompt caching is reported inside
    `response.usage` as `cache_creation_input_tokens` and
    `cache_read_input_tokens`, present on 11,514 records. Any cache analysis
    built on the `cache_hit` column will report zero cache usage and be wrong by
    two orders of magnitude.

## New: the native session_id is not a conversation key

The extract carries a `session_id` column, populated on every record — which
makes it look like the session grouping problem is already solved. It is not:
there are **13,221 distinct values across 13,291 records**.

That is effectively one session per request. The column identifies a request's
own trace, not a conversation. [[upstream/session-reconstruction]] must still
derive sessions from the parsed `end_user` string, and the 26.4% coverage gap
above cannot be closed by falling back to this column.

Upstream commit `3e9a694` (2026-09-18) nevertheless added exactly that fallback.
The counts here are why it inflates the session count rather than repairing it;
see [[caveats/end-user-parsing]].

## New: 11% of requests failed, and they poison every average

**1,474 of 13,291 records (11.1%) have `status: "failure"`.** They are not inert
rows — they carry a distinctive and misleading shape:

- `response` is an empty object; `total_tokens`, `prompt_tokens`, and
  `completion_tokens` are all zero.
- `call_type` and `custom_llm_provider` are empty strings, so they fall outside
  every provider breakdown.
- `model_group` is populated — 1,474 of them read `claude-opus-4-6`, which is
  **exactly the full failure count**. Any "requests by model" chart will
  attribute a large block of failures to one model family.

Error classes, from `metadata.error_information.error_class`:

| Class                     | Code | Count |
| ------------------------- | ---- | ----- |
| `ProxyException`          | —    | 1,229 |
| `APIConnectionError`      | 500  | 73    |
| `BaseLLMException`        | 400  | 37    |
| `ProxyModelNotFoundError` | 400  | 34    |
| `Exception`               | —    | 29    |
| `BadRequestError`         | 400  | 22    |
| `MidStreamFallbackError`  | 503  | 19    |
| `RateLimitError`          | 429  | 12    |
| Remaining classes         | —    | 19    |

!!! important "Filter on status before computing anything"

    Zero-token failures drag every per-request average downward, and their
    `model_group` value inflates one model's request count by 1,474. Every
    usage, cost, and model-mix metric should filter `status = 'success'` and
    report the failure count separately as its own signal.

The dominance of bare `ProxyException` with no error code (83% of failures) is
itself worth noting: the most common failure mode in this window is also the
least self-describing one.

## Minor observations

- `agent_id` and `mcp_namespaced_tool_name` are null on every record. They are
  forward-looking columns; nothing in this era populates them.
- `requester_ip_address` has a single distinct value across 11,949 records — the
  gateway's own egress address, not a client address. It carries no per-user
  signal here.
- `organization_id` has one distinct value and 6,284 nulls, so it cannot
  partition this dataset.

## Related Concepts

- [Jan–Mar 2026 Spend-Log Extract](jan-mar-2026-extract.md): The artifact these
  findings were measured from.
- [Handling This Data Without Touching PII](pii-handling.md): The constraint
  under which every figure here was produced.
- [Caveat: end_user Parsing Fragility](../caveats/end-user-parsing.md): The
  26.4% empty rate measured here is the direct confirmation of its estimate.
- [Caveat: Cost and Token Double-Counting](../caveats/cost-token-double-counting.md):
  The 100:1 prompt-to-completion ratio is what its mechanism produces.
- [The Two Logging Paths](../platform/logging-paths.md): The empty `messages`
  column is the worst case of the fidelity difference it describes.
