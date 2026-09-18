---
type: Fact
title: "Caveat: Cost and Token Double-Counting"
description: "Agentic clients resend the whole conversation on every turn, so summing per-request spend across a session counts the same content many times over."
tags: [caveat, cost, tokens, double-counting, metrics]
governance: constraint
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: uw-ssec/llmoxie data/group_sessions.py, build_sessions()
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

## The mechanism

The LLM API is stateless. A coding agent holding a twenty-turn conversation does
not send turn twenty — it sends turns one through twenty, every time. Request
_n_ contains everything requests 1…*n*−1 contained, plus the new material.

Per-request accounting is therefore correct _as billing_ and misleading _as
measurement_. The provider genuinely charged for those input tokens on every
call (that is what prompt caching exists to mitigate), but the conversation did
not contain twenty copies of turn one.

## Where it bites

`build_sessions` in [[upstream/session-reconstruction]] aggregates with
`total_spend=sum` and `total_tokens=sum` over the session's requests. For a long
agentic session those sums grow roughly quadratically in turn count.

The failure modes are specific:

- **"Average cost per session"** is dominated by session length, not by what the
  session did.
- **"Tokens per session"** compares a 20-turn agentic session against a 2-turn
  chat on completely different scales.
- **Cross-client comparison is invalid.** A client that trims its context window
  and one that resends everything will show very different session costs for
  identical work.

## The resolution

!!! important "Store both, name them distinctly"

    Issue #1 requires the schema to carry **both** the raw sums and `net_`
    variants — for example `total_spend` alongside `net_spend`, `total_tokens`
    alongside `net_tokens` — so that neither number is silently substituted for
    the other.

The `net_` variants are computed against the deduplicated view of the
conversation: each unique message counted once, at the point it was introduced.
The raw sums remain the correct answer to "what did this cost us", and the
`net_` variants the correct answer to "how much conversation was there".

Getting the deduplicated view requires care about ordering — see
[[caveats/dedup-vs-last-request]].

## Choosing between them

| Question                                       | Use                           |
| ---------------------------------------------- | ----------------------------- |
| What did this session cost the center?         | `total_spend` (raw)           |
| How much did users actually write and read?    | `net_tokens`                  |
| Which model family is most expensive to serve? | `total_spend` (raw)           |
| How long are conversations getting over time?  | `net_tokens` or message count |
| Are clients managing context efficiently?      | ratio of raw to `net_`        |

That last row is worth noting: the raw-to-net ratio is not noise to be
eliminated. It is a direct measure of context-resend overhead, and a useful
signal in its own right for a center trying to understand gateway load.

## Related Concepts

- [group_sessions.py — Reconstructing Conversations](../upstream/session-reconstruction.md):
  The raw `total_spend` and `total_tokens` sums that this caveat warns about are
  computed there.
- [Analytics Schema — Four Tables](../pipeline/analytics-schema.md): The schema
  stores both the raw and the net variant precisely so this distinction survives
  into the warehouse.
- [Caveat: last_request_per_session vs deduplicate_messages](dedup-vs-last-request.md):
  Deduplication is the reduction that produces the net view; the ordering rule
  there must be respected to get it.
