---
type: Decision
title: "Caveat: last_request_per_session vs deduplicate_messages"
description: "Two reduction functions that look interchangeable are not, and applying them in the wrong order silently destroys most of a conversation."
tags: [caveat, deduplication, ordering, correctness]
governance: constraint
code_refs:
  - reference/llmoxie/src/llmaven/data/reader.py
  - reference/llmoxie/src/llmaven/data/group_sessions.py
  - src/llmoxie_analysis/**
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: reference/llmoxie/src/llmaven/data/reader.py
  - resource: reference/llmoxie/src/llmaven/data/group_sessions.py
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

Both functions in [[upstream/reader-flattening]] reduce a flattened frame. Both
remove redundancy created by conversation resending. They answer different
questions, and the mistake is cheap to make and hard to notice.

## What each one does

### `last_request_per_session` — reconstructing the transcript

Because every request carries the full history so far, the **longest** request
in a session contains the complete conversation. Keep that one request; discard
the rest. Ties break on `start_time`, latest wins.

This is the correct reduction for **"what was this conversation?"** The result
is one coherent transcript per session, in order.

### `deduplicate_messages` — timing each message

Keep the earliest occurrence of each `(session_id, msg_idx, block_idx)`. Every
message survives exactly once, stamped with the time it was _first_ introduced
rather than the last time it was resent.

This is the correct reduction for **"when did each message enter the
conversation?"** and for the `net_` metrics in
[[caveats/cost-token-double-counting]].

## The ordering trap

!!! danger "Deduplicating first destroys the transcript"

    `last_request_per_session` works by finding the request with the most
    messages. `deduplicate_messages` strips repeated messages _out of the
    requests that resent them_ — so after deduplication, the longest request is
    no longer the one holding the full history. The "longest request"
    comparison is then being made against mutilated inputs, and the function
    happily returns a truncated conversation with no error.

The upstream prototype encodes this constraint in a comment inside
`build_sessions` (see [[upstream/session-reconstruction]]):

> Keep the raw (non-deduped) data: `last_request_per_session` needs each
> request's own full resent history intact. `deduplicate_messages` would strip
> most of that history away.

## The rule

| Goal                                                               | Function                                  | Input                            |
| ------------------------------------------------------------------ | ----------------------------------------- | -------------------------------- |
| Reconstruct the conversation                                       | `last_request_per_session`                | **Raw**, non-deduplicated frame  |
| Per-message cross-request analysis, message timing, `net_` metrics | `deduplicate_messages`                    | Raw frame, applied independently |
| Both                                                               | Derive each from the raw frame separately | —                                |

They are two independent projections of the same raw data, not two stages of one
pipeline. Never chain them.

Issue #1 states the decision plainly: `last_request_per_session` is the correct
choice for session reconstruction, and `deduplicate_messages` is **only** for
per-message cross-request analysis. [[pipeline/pipeline-architecture]] keeps the
raw frame available to both consumers rather than reducing once and sharing the
result.

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](../upstream/reader-flattening.md):
  Both `deduplicate_messages` and `last_request_per_session` are defined in that
  module.
- [group_sessions.py — Reconstructing Conversations](../upstream/session-reconstruction.md):
  The grouping prototype is where the ordering constraint between the two
  functions is enforced in practice.
- [Caveat: Cost and Token Double-Counting](cost-token-double-counting.md):
  Deduplication exists to answer the cost question that double-counting
  otherwise makes unanswerable.
