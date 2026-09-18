---
type: Fact
title: "Caveat: The Responses API Output Gap"
description: "Requests made through the OpenAI Responses API return output under a different key, which the reader does not parse — so those replies are silently missing from sessions."
tags: [caveat, responses-api, copilot, missing-data, agent-type]
governance: constraint
code_refs:
  - reference/llmoxie/src/llmaven/data/group_sessions.py
  - reference/llmoxie/src/llmaven/data/reader.py
sources:
  - resource: reference/llmoxie/src/llmaven/data/group_sessions.py, _adls_record_to_spend_log_shape() docstring
  - resource: reference/llmoxie/src/llmaven/data/reader.py, _rows_from_record()
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

## The mismatch

[[upstream/reader-flattening]] reads a request's reply from exactly one place:

```python
response["choices"][0]["message"]
```

That is the Chat Completions shape. The OpenAI **Responses API** returns
`{"output": [...]}` instead — no `choices` key at all. The lookup raises
`KeyError`, is caught by the surrounding
`try/except (KeyError, IndexError, TypeError)`, logs
`"request_id=%s: could not read response.choices[0].message: %s"`, and
continues.

The request's input messages are still captured. Only the **assistant's reply is
missing**, and the session is otherwise complete and plausible.

## How it was found

The docstring of `_adls_record_to_spend_log_shape` in
[[upstream/session-reconstruction]] records the discovery: the adapter was
verified against a real sample from the `litellm-logs` container — a GitHub
Copilot / `gpt-5.3-codex` request made through the Responses API — and the
author noted that for `call_type == "responses"` the reply shape differs, so
_"reader.py logs a warning and the session's messages simply won't include that
request's final reply."_

This is a known, documented gap, not a suspicion.

## Why it is more than an edge case

!!! warning "The gap is correlated with client, not randomly distributed"
Responses-API traffic comes from particular clients. GitHub Copilot is the
confirmed example. That means missing assistant replies cluster in one
`agent_type` rather than scattering evenly.

[[pipeline/analytics-schema]] tags every session with `agent_type` —
`claude_code`, `copilot`, `opencode`, or `unknown`. Any comparison across those
values touches this directly:

- **Response-length comparisons across clients are invalid** while the gap
  exists — one client's replies are systematically absent.
- **Message counts per session** are undercounted for affected clients.
- **Conversation-shape analysis** (turn-taking, ratio of user to assistant
  content) is distorted in the same direction.

Token and cost figures are unaffected: those come from the standard logging
object's own counters, not from parsing message bodies.

## Detection

The gap is observable rather than silent, if you look for it. Two signals:

1. The warning in the logs, counted per run and per `agent_type`.
2. Sessions whose messages contain user turns with no intervening assistant turn
   — structurally impossible in a real conversation.

A reasonable practice is to surface the count of failed response reads in the
run statistics alongside `skipped_session_count` (see
[[caveats/end-user-parsing]]), so both coverage problems are reported together.

## The fix

Extend the reply parser to recognize the Responses shape and normalize
`{"output": [...]}` into the same block rows produced from `choices[0].message`.
The natural home is the response-reading path in `reader.py`, or the adapter
layer described in [[pipeline/source-adapters]] if the normalization should
happen before the reader sees the record.

Until that lands, treat any cross-`agent_type` analysis of message content as
provisional.

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](../upstream/reader-flattening.md):
  The parser that reads only the Chat Completions response shape is the one with
  this gap.
- [group_sessions.py — Reconstructing Conversations](../upstream/session-reconstruction.md):
  The gap was first documented as an upstream comment in the grouping prototype.
- [Analytics Schema — Four Tables](../pipeline/analytics-schema.md):
  `agent_type` is the column the gap correlates with, which is why it is not
  safely analyzable on its own.
