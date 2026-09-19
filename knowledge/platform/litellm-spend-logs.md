---
type: Fact
title: LiteLLM Spend Logs and infra extract
description: "The PostgreSQL-backed spend-log path, the REST endpoint and the database-backup export that read it, and the llmaven infra extract command that packages a date range into a zip."
tags: [litellm, postgres, spend-logs, extract, cli]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-19T00:11:08Z" }
code_refs: [reference/llmoxie/src/llmaven/data/README.md, reference/llmoxie/src/llmaven/cli.py, reference/llmoxie/scripts/dbexport.sh]
sources:
  - resource: "reference/llmoxie commit 527d163, PR #79, 2026-02-16"
  - resource: "reference/llmoxie commit 39901b9, PR #100, 2026-03-17"
  - resource: "reference/llmoxie commit 3e9a694, PR #167, 2026-09-18"
  - resource: reference/llmoxie/scripts/dbexport.sh (182 lines)
  - resource: reference/llmoxie/tests/infrastructure/test_cli_extract.py
  - resource: reference/llmoxie/src/llmaven/data/README.md
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

### The extract no longer fails on a bad day

Commit `3e9a694` (PR #167, 2026-09-18) is titled "Support pagination in data
download", but the request loop is still one `GET /spend/logs` per day with
`start_date`, `end_date`, and `summarize=false`; no paging parameter was added.
What changed is the error handling, from fail-fast to skip-and-continue:

- An HTTP error with a status of 500 or above prints a message and sleeps 60
  seconds. The day is **not re-requested** — the code comment says "before
  retrying", but execution carries on with the failed response. Any other HTTP
  error still aborts the extract.
- A body that is not valid JSON, or is not a list, used to abort with exit
  code 1. It now prints `skipping` for that day and continues, and the command
  exits 0.
- A day with no records is no longer written into the zip. Previously every
  day in the range had a member, empty or not.

!!! warning "A missing day in the zip is now ambiguous"

    A day can be absent because the gateway had no traffic or because the
    request for it failed. The zip does not distinguish the two and the exit
    code is 0 either way; only the command's console output does. An extract
    made at or after `3e9a694` needs its day coverage checked against the
    requested range before anything is computed from it.

This is read from the code and the updated upstream tests
(`test_http_error_skips_day_and_continues` and siblings), not from running an
extract.

## A second way to read it: straight from a database backup

The same commit adds `scripts/dbexport.sh`, which bypasses the REST endpoint. It
downloads the latest `pg_dump` backup from Azure Blob (`az://pg-backups/llmaven`,
database `litellm_db`, or a local file via `--dump`), restores only
`LiteLLM_SpendLogs` into a throwaway `postgres:17` Docker container, and writes
`COPY (SELECT row_to_json(t) …)` output to a single JSONL file (default
`spend_logs.jsonl`) that it describes as "compatible with reader.py". It needs
`az`, `docker`, `pg_restore`, and `psql` on the path.

This partly reverses the PR #79 decision above: the export is coupled to
LiteLLM's table schema and to the backup job's blob layout, in exchange for one
bulk read instead of one HTTP request per day.

Two quirks come with it. `row_to_json()` mis-escapes backslash-quote pairs inside
JSONB text, so the script pipes every line through a sanitizer that repairs what
it can and **skips, with a warning on stderr, any row it cannot parse**. And the
`end_user` value arrives with literal `\"` sequences, which is why
`_parse_end_user` gained a second `json.loads` attempt — see
[[upstream/reader-flattening]].

Because the output is one `.jsonl` file, feeding it to `group_sessions` selects
that module's streaming code path rather than the DataFrame path a zip takes;
see [[upstream/session-reconstruction]].

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
- [group_sessions.py — Reconstructing Conversations](../upstream/session-reconstruction.md):
  A single `.jsonl` export, as `dbexport.sh` produces, selects that module's
  streaming code path instead of the DataFrame path a zip takes.
