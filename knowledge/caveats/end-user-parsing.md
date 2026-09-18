---
type: Fact
title: "Caveat: end_user Parsing Fragility"
description: "Session identity is recovered by parsing a free-form client-supplied string, and roughly a quarter of early-2026 requests cannot be parsed at all."
tags: [caveat, data-quality, sessions, end-user, coverage]
governance: constraint
code_refs:
  - reference/llmoxie/src/llmaven/data/reader.py
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: reference/llmoxie/src/llmaven/data/reader.py, _parse_end_user()
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

This is the most consequential data-quality problem in the project. Every
session-level number produced by [[project/llmoxie-analysis]] is conditional on
it.

## The mechanism

LiteLLM has no notion of a "session". The gateway learns about device, account,
and session only because the client packs all three into the free-form
`end_user` field. `_parse_end_user` in [[upstream/reader-flattening]] tries to
unpack it:

1. `json.loads` — the well-behaved case.
2. Failing that, a regex:
   ```python
   r"user_(?P<device_id>[0-9a-f]*)_account_(?P<account_uuid>.*?)_session_(?P<session_id>[0-9a-f-]+)"
   ```
3. Failing both, log and return
   `{"device_id": "", "account_uuid": "", "session_id": ""}`.

There is no negotiated contract here. The format is whatever the client happened
to send, and different clients — and different versions of the same client —
send different things.

## The magnitude

!!! danger "About 25% of Jan–Mar 2026 requests have no usable session_id"

    Those requests are not merely mislabeled. They are **dropped** from session
    grouping entirely: `build_sessions` filters on `session_id == ""` and
    counts them out.

Two consequences follow immediately.

**Session counts are a lower bound, and a biased one.** If parse failure
correlates with a particular client or client version — which is likely, since
the format is client-determined — then the surviving sessions over-represent
whichever clients happened to format `end_user` correctly. A statement like
"most sessions use model X" may be a statement about one client's users.

**Request-level and session-level totals will not reconcile.** Summing spend
across sessions gives a smaller number than summing spend across requests. That
gap is the dropped quarter, not an arithmetic error.

## What the pipeline must do about it

Issue #1 makes this a hard requirement: **every pipeline run must log
`skipped_session_count`**. The prototype already computes it as the second
element of `build_sessions`'s return tuple (see
[[upstream/session-reconstruction]]); the production run statistics must surface
it rather than discard it.

The figure belongs in `PipelineRunStats` and in any report built on the output.
A session count published without its companion skip count is incomplete.

## An era-specific measurement

The "~25%" figure was measured on the January–March 2026 dump. Per
[[platform/llmoxie-timeline]], that dump necessarily came from the LiteLLM
spend-log path, because [[platform/adls-logger]] did not exist until 2026-05-08.
So the figure characterizes **LiteLLM-sourced data from early 2026** — not the
ADLS path, and not the present day.

Do not assume it generalizes in either direction. Client behavior changes over
time, and the rate should be recomputed per source and per period rather than
carried forward as a constant. Because every row carries `data_source` (see
[[pipeline/analytics-schema]]), that recomputation is a group-by away.

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](../upstream/reader-flattening.md):
  `_parse_end_user` lives there, and its failure mode is what this caveat
  describes.
- [group_sessions.py — Reconstructing Conversations](../upstream/session-reconstruction.md):
  Requests whose `end_user` cannot be parsed are dropped and counted during
  grouping.
- [LLMoxie Development Timeline](../platform/llmoxie-timeline.md): The roughly
  25% unparsed share is era-specific, and the timeline explains which eras it
  applies to.
