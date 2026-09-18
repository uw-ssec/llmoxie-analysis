---
type: Fact
title: LiteLLM Spend Logs and infra extract
description: "The PostgreSQL-backed spend-log path, the REST endpoint that reads it, and the llmaven infra extract command that packages a date range into a zip."
tags: [litellm, postgres, spend-logs, extract, cli]
code_refs:
  - reference/llmoxie/src/llmaven/data/README.md
sources:
  - resource: reference/llmoxie commit 527d163, PR #79, 2026-02-16
  - resource: reference/llmoxie commit 39901b9, PR #100, 2026-03-17
  - resource: reference/llmoxie/src/llmaven/data/README.md
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

LiteLLM tracks per-request spend natively in PostgreSQL. This is the second of
the [[platform/logging-paths]], and — because it predates `AdlLogger` by roughly
fifteen months — it is the only source for the historical record.

## How it is read

`llmaven infra extract` (commit `527d163`, PR #79, 2026-02-16) wraps retrieval.
The PR is instructive: the implementation initially queried the PostgreSQL
database directly and was **switched during review to the REST API endpoint**
(`GET /spend/logs`) instead. Going through the proxy's own API rather than its
database means the extract respects LiteLLM's auth model and does not couple the
analysis tooling to a schema LiteLLM is free to migrate.

A later change (commit `39901b9`, PR #100, 2026-03-17) extended the same command
to also fetch MLflow traces.

### Credentials

| Variable             | Purpose                                     |
| -------------------- | ------------------------------------------- |
| `LITELLM_MASTER_KEY` | Authenticates against the proxy's admin API |
| `LITELLM_BASE_URL`   | Which proxy instance to read from           |

Both are resolved from an env file. They are the reason `--source litellm`
requires different credentials from `--source adls`; see
[[pipeline/pipeline-cli]].

## Usage

```bash
pixi shell -e llmaven
llmaven infra extract \
  --from 2026-01-01 --to 2026-03-31 \
  --out jan-feb-march-2026.zip \
  -e .env
```

The output is a `.zip` of JSONL. The pipeline reads it **in place** via
`zipfile`, without extracting to disk — a deliberate fix for a temp-file leak in
the prototype, tracked in [[project/epic-and-issues]] as issue #2.

## The truncation caveat

!!! warning "Prompts may be absent or truncated"

    Spend logs only contain prompt and response text when the proxy is
    configured with `store_prompts_in_spend_logs: true`. Even then, message
    content may be truncated. This is the defining fidelity difference against
    [[platform/adls-logger]], and the reason every analytical row carries a
    `data_source` column — see [[pipeline/analytics-schema]].

## Row shape

Spend-log rows are the pipeline's _common format_ — the ADLS adapter converts
into this shape rather than the other way around. The fields
[[upstream/reader-flattening]] consumes are:

`request_id`, `startTime`, `endTime`, `end_user`, `model`, `spend`,
`total_tokens`, `api_key`, `metadata.user_api_key_alias`,
`proxy_server_request.messages`, and `response`.

Because this is the common format, `from_litellm(record)` is a pass-through. See
[[pipeline/source-adapters]].

## Benchmark

The January–March 2026 dump — 11,992 requests grouping into 279 sessions in
about ten seconds — came from this path. See [[platform/llmoxie-timeline]] for
why that is necessarily true.

## Related Concepts

- [The Two Logging Paths](logging-paths.md): The spend-log path is the
  lower-fidelity half of the two-path comparison.
- [reader.py — Flattening Requests to Message Blocks](../upstream/reader-flattening.md):
  The reader consumes this row shape once it has been adapted.
- [The llmaven data pipeline run CLI](../pipeline/pipeline-cli.md):
  `llmaven infra extract` produces the zip that the CLI feeds to the pipeline in
  LiteLLM mode.
