---
type: Fact
title: The Two Logging Paths
description: "LLMoxie records every request twice over — to Azure Data Lake as untruncated JSON and to LiteLLM's PostgreSQL spend logs — and the two differ in fidelity, coverage, and era."
tags: [logging, adls, litellm, data-source, fidelity]
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: reference/llmoxie/src/llmaven/infrastructure/resources/adl_logger.py
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

A request through the [[platform/llmoxie-platform]] gateway can leave a trace in
two independent places. Understanding which one a given dataset came from is the
first question to ask of any LLMoxie analysis, because the two are not
equivalent.

## Side by side

|                   | **ADLS**                                                       | **LiteLLM spend logs**                                                                         |
| ----------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Mechanism         | `AdlLogger` LiteLLM callback writing JSON blobs                | LiteLLM's own PostgreSQL spend tracking                                                        |
| Retrieval         | Read blobs from the container via `fsspec`/`adlfs`             | `GET /spend/logs` REST endpoint, wrapped by `llmaven infra extract`                            |
| Message fidelity  | **Untruncated** — full prompt and response bodies              | **Possibly truncated**; requires `store_prompts_in_spend_logs: true` to contain prompts at all |
| Layout            | One JSON file per request, `logs/YYYY/MM/DD/<request_id>.json` | Rows in a table, exported as JSONL inside a `.zip`                                             |
| Available since   | 2026-05-08 (`b0f1961`, PR #123)                                | Since the proxy pivot; covers the historical record                                            |
| Failure mode      | Silent — write errors are logged and swallowed                 | Loud — the REST call fails visibly                                                             |
| `data_source` tag | `'adls'`                                                       | `'litellm'`                                                                                    |

## Which one to prefer

**ADLS is the preferred source.** It is the only one guaranteed to carry
complete message bodies, and message content is the substance of nearly every
analysis question worth asking about a coding-assistant gateway.

LiteLLM is the fallback, and for anything before 2026-05-08 it is the _only_
option — see [[platform/llmoxie-timeline]]. That asymmetry is exactly why
`--source auto` resolves per day rather than per run; see
[[pipeline/source-adapters]].

!!! warning "Fidelity is not uniform across a single dataset"

    A backfill spanning the 2026-05-08 boundary will contain both kinds of row.
    Averaging a message-length metric across that boundary compares untruncated
    text against possibly-truncated text. This is the entire reason
    [[pipeline/analytics-schema]] carries `data_source` on every row of every
    table.

## Detail

- ADLS write mechanics, record envelope, and the silent-failure behavior:
  [[platform/adls-logger]]
- The spend-log endpoint, the `infra extract` command, and the zip layout:
  [[platform/litellm-spend-logs]]
- How both are normalized to one common record shape:
  [[pipeline/source-adapters]]

## Related Concepts

- [AdlLogger — Azure Data Lake Logging](adls-logger.md): The ADLS blob path is
  the preferred, untruncated of the two.
- [LiteLLM Spend Logs and infra extract](litellm-spend-logs.md): The spend-log
  path is the fallback and the only source for the earliest eras.
- [Source Adapters and Auto Detection](../pipeline/source-adapters.md): The
  adapter layer is where the pipeline reconciles the two paths into one record
  shape.
