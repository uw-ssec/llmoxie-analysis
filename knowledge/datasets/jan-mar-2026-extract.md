---
type: Entity
title: Jan–Mar 2026 Spend-Log Extract
description: "A 1.0 GB local extract of 90 daily LiteLLM spend-log files covering 2026-01-02 through 2026-03-24, holding 13,291 requests in a rectangular 31-column shape."
tags: [dataset, litellm, extract, early-2026, schema]
sources:
  - resource: local extract, 90 litellm_spend_logs_*.jsonl files
  - resource: structure-only profile, no record values inspected
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

The first real corpus this project has to work with: a flat directory of daily
newline-delimited JSON files produced by the LiteLLM spend-log path. It is the
dataset against which every claim in [[caveats/index]] can finally be checked
rather than inferred.

!!! danger "This extract contains prompt and response bodies"

    Request bodies live under `proxy_server_request`, which carries `messages`
    on 11,992 records. Treat the whole directory as sensitive and follow
    [[datasets/pii-handling]] before running anything against it.

## Provenance

The files are named `litellm_spend_logs_YYYY-MM-DD.jsonl`, one per calendar day,
and the record shape is LiteLLM's `SpendLogs` row — so this is the spend-log
path of [[platform/logging-paths]], not the data-lake path.

That is forced rather than chosen. [[platform/adls-logger]] did not exist until
2026-05-08, so for any window in early 2026 the spend logs are the only record
that exists. Every row here would carry `data_source = 'litellm'` under
[[pipeline/analytics-schema]].

## Coverage

| Property         | Value                                     |
| ---------------- | ----------------------------------------- |
| Files            | 90 (one per day, 2026-01-01 → 2026-03-31) |
| Non-empty files  | 64                                        |
| Zero-byte files  | 26                                        |
| Total size       | 1.0 GB                                    |
| Records          | 13,291                                    |
| First record     | 2026-01-02T23:00:11Z                      |
| Last record      | 2026-03-24T21:27:45Z                      |
| Largest file     | `2026-01-30`, ~124 MB                     |
| Mean record size | ~79 KB                                    |

Two gaps are worth naming before anyone treats the file list as the date range.
The file series runs to 2026-03-31, but **the last record is 2026-03-24** — the
final week is present only as empty files. And the series begins 2026-01-01
while the first record lands on 2026-01-02.

Per month: January 3,346 requests, February 6,773, March 3,172.

The 26 empty days skew toward Sundays — 9 of the 13 Sundays in the window are
empty, against 1 of 13 Tuesdays — which is what a research center's gateway
traffic should look like. The remaining empty days are mostly the trailing run
after 2026-03-24.

## Record shape

The extract is perfectly rectangular: all 31 top-level keys are present on all
13,291 records, with no ragged rows.

```
agent_id                  endTime                   proxy_server_request
api_base                  end_user                  request_id
api_key                   mcp_namespaced_tool_name  request_tags
cache_hit                 messages                  requester_ip_address
cache_key                 metadata                  response
call_type                 model                     session_id
completionStartTime       model_group               spend
completion_tokens         model_id                  startTime
custom_llm_provider       organization_id           status
                          prompt_tokens             team_id
                                                    total_tokens
                                                    user
```

Present-but-empty is the dominant pattern, and it matters more than the column
list does:

- `agent_id` and `mcp_namespaced_tool_name` are **null on every record**. The
  columns exist for a later era of the gateway; they carry nothing here.
- `messages` is an **empty object on every record** — see
  [[datasets/jan-mar-2026-findings]] for why, and for where the prompts actually
  are.
- `organization_id` is null on 6,284 records; `requester_ip_address` on 1,342.
- `request_tags` is an array; `metadata`, `response`, and `proxy_server_request`
  are objects.

## Cardinality

Distinct-value counts only — no values were read.

| Column                 | Distinct | Note                                 |
| ---------------------- | -------- | ------------------------------------ |
| `request_id`           | 13,291   | Unique per record                    |
| `session_id`           | 13,221   | Near-unique — not a conversation key |
| `end_user`             | 281      | Empty on 3,512 records               |
| `model`                | 39       | Before normalization                 |
| `model_group`          | 17       | LiteLLM routing alias                |
| `model_id`             | 17       | Deployment identifier                |
| `api_key`              | 36       | Hashed key identifiers               |
| `team_id`              | 8        |                                      |
| `user`                 | 5        |                                      |
| `organization_id`      | 1        | Plus 6,284 nulls                     |
| `requester_ip_address` | 1        | Single gateway egress address        |

## Volume and spend

| Measure                | Value       |
| ---------------------- | ----------- |
| Total spend            | $413.43     |
| Largest single request | $0.98       |
| Prompt tokens          | 486,320,257 |
| Completion tokens      | 4,837,330   |
| Total tokens           | 491,157,587 |
| Cache creation tokens  | 49,030,638  |
| Cache read tokens      | 419,111,970 |

The prompt-to-completion ratio is roughly **100:1**, and 86% of prompt tokens
are cache reads. Both figures are consequences of agentic context resend rather
than of unusually long prompts — see [[caveats/cost-token-double-counting]].

## Traffic mix

Requests resolve to four call types: `anthropic_messages` (9,964), `acompletion`
(1,840), an empty string on the 1,474 failed requests, and `aresponses` (13).
Providers are `anthropic` (11,501), `azure` (303), and `bedrock` (13).

Model groups are dominated by the Claude families — `claude-haiku-4-5` (4,081),
`claude-sonnet-4-5` (3,518), `claude-sonnet-4-6` (2,387), `claude-opus-4-6`
(1,474) — with a long tail including `gpt-5-mini` (279), `kimi-k2-thinking`
(19), and `gpt-oss-120b` (17). Several entries differ only by Bedrock prefix,
which is exactly the fragmentation [[upstream/model-name-normalization]] exists
to collapse.

## Related Concepts

- [What Profiling the Jan–Mar 2026 Extract Proved](jan-mar-2026-findings.md):
  The empirical findings this extract produced, and which documented caveats
  they confirm or overturn.
- [Handling This Data Without Touching PII](pii-handling.md): The working rules
  that let this extract be profiled and analyzed safely.
- [The Two Logging Paths](../platform/logging-paths.md): This extract came from
  the spend-log path, which fixes its fidelity ceiling.
- [LLMoxie Development Timeline](../platform/llmoxie-timeline.md): The timeline
  explains why a Jan–Mar 2026 window could only have come from LiteLLM.
