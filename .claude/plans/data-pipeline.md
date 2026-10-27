# LLMaven Data Pipeline — Implementation Plan

## Context

LLMaven logs every LiteLLM request via two distinct paths with different schemas
and data completeness guarantees:

1. **ADLS via `AdlLogger`**
   (`src/llmaven/infrastructure/resources/adl_logger.py`) — one JSON file per
   request at `logs/<yyyy>/<mm>/<dd>/<request_id>.json`. Writes the full
   `kwargs` dict from the LiteLLM callback; message content is never truncated.
2. **LiteLLM PostgreSQL via `/spend/logs` API** — consumable via
   `llmaven infra extract`. Stores spend logs with prompts when
   `store_prompts_in_spend_logs: true`, but long messages may be truncated by
   PostgreSQL column limits.

ADLS is the preferred source. PostgreSQL is the fallback for deployments that
predate AdlLogger or where ADLS is not configured.

The core pipeline challenge: each raw record contains the **entire conversation
history** up to that request (cumulative). A pipeline must deduplicate,
normalize across two source schemas, and reshape into flat, queryable Parquet
tables.

---

## Source Modes

The pipeline accepts `--source [adls|litellm|auto]`:

| Mode      | When to use                                                                                                                      |
| --------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `adls`    | ADLS is available for the full date range. Preferred — full message content guaranteed.                                          |
| `litellm` | No ADLS (pre-AdlLogger deployments, or instances without AdlLogger configured). Falls back to PostgreSQL spend logs.             |
| `auto`    | Unknown/mixed. Per-day: checks ADLS for each date; uses ADLS if files exist, falls back to `litellm` for days with no ADLS data. |

`auto` is the safe default for any deployment. The pipeline logs which source
was used for each day in the run stats.

### Source schema differences

Both sources contain the same underlying LiteLLM request data, but in different
shapes:

**ADLS** (`adl_logger.py` output):

```json
{
  "timestamp_start": "2026-01-15T10:00:00",
  "timestamp_end":   "2026-01-15T10:00:05",
  "kwargs": {
    "messages": [...],          // full, never truncated
    "model": "claude-...",
    "end_user": "...",
    "metadata": {...},
    "standard_logging_object": { "id": "chatcmpl-xyz", ... }
  },
  "response": { "choices": [...] },
  "cost": 0.02
}
```

**LiteLLM / PostgreSQL** (what `reader.py` already handles):

```json
{
  "request_id": "chatcmpl-xyz",
  "startTime": "2026-01-15T10:00:00",
  "endTime":   "2026-01-15T10:00:05",
  "model": "claude-...",
  "spend": 0.02,
  "end_user": "...",
  "metadata": {...},
  "proxy_server_request": { "messages": [...] },   // may be truncated
  "response": { "choices": [...] }
}
```

### Normalization adapter (`data/sources.py`)

A thin adapter layer maps both formats to a single common dict before any
further processing. The common format matches what `reader.py` already expects
(PostgreSQL shape), so the ADLS adapter does the translation:

```python
def from_adls(record: dict) -> dict:
    """Map AdlLogger JSON → common format (PostgreSQL shape)."""
    kwargs = record["kwargs"]
    slo = kwargs.get("standard_logging_object", {})
    return {
        "request_id": slo.get("id"),
        "startTime": record["timestamp_start"],
        "endTime": record["timestamp_end"],
        "model": kwargs.get("model"),
        "spend": record.get("cost"),
        "end_user": kwargs.get("end_user"),
        "metadata": kwargs.get("metadata", {}),
        "proxy_server_request": {"messages": kwargs.get("messages", [])},
        "response": record.get("response"),
    }


def from_litellm(record: dict) -> dict:
    """PostgreSQL format — pass through as-is (reader.py already handles it)."""
    return record
```

After normalization, all pipeline stages see only the common format.
`reader.py`'s `load_messages`, `last_request_per_session`, and
`deduplicate_messages` are reused unchanged.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Source selection (--source adls | litellm | auto)           │
│                                                             │
│  adls:    ADLS logs/<yyyy>/<mm>/<dd>/*.json                 │
│  litellm: LiteLLM /spend/logs API or extracted ZIP          │
│  auto:    per-day — ADLS if files exist, litellm otherwise  │
└──────────────────────────┬──────────────────────────────────┘
                           │ raw records (two possible schemas)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Source adapter  (data/sources.py)                           │
│  from_adls() / from_litellm() → common dict format         │
│  Records source type per day in run stats                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ common format records
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 1 — Session Grouping                                  │
│  last_request_per_session() from data/reader.py             │
│  Skip records with no end_user session_id (SkipStats)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ one canonical record per session
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2 — Normalize                                         │
│  normalize_model_name() from data/reader.py                 │

└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 3 — Transform to relational tables                    │
│  sessions, messages, tool_calls, tool_definitions           │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 4 — Write Parquet (always overwrite, never append)    │
│  output/sessions/start_date=<d>/<instance_id>.parquet       │
│  via fsspec → local  OR  abfs:// (ADLS)                    │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Query layer                                                 │
│  DuckDB on local notebooks (reads Parquet over network)    │
│  Azure Synapse Serverless SQL (same files, zero changes)   │
└─────────────────────────────────────────────────────────────┘
```

### Portability strategy

- Core transform: pure Python + `polars` — zero Azure imports
- File I/O: `fsspec` + `adlfs` for ADLS; `pathlib` for local
- Local dev: use `--source litellm` with an extracted ZIP (no ADLS needed), or
  `--source adls` with `az login`
- Cloud trigger (Container Apps Job) calls the same CLI with `--source auto`

---

## Key Data Caveats

1. **`end_user` fragility** — ~25% of Jan–Mar 2026 sessions had unparsable
   `session_id` (two formats: JSON dict and
   `user_{device_id}_account_{account_uuid}_session_{session_id}` regex).
   Pipeline must log `skipped_session_count` per run, not fail silently.

   **Resolved in grouping (2026-10-27).** `end_user` is now the only source of
   session identity. Both the reader and the streaming scan used to fall back to
   LiteLLM's top-level `session_id`, which is a per-request trace id — it never
   groups anything, it just mints one singleton "session" per ungroupable
   record. Dropping the fallback means those records are now counted out instead
   of silently inflating the output, and `stream_sessions` returns a `SkipStats`
   describing them: record count, the spend and tokens they take with them, how
   many carried a native per-request id, and how many parsed to an account but
   no session.

   **Deferred: a `skipped_requests` table.** The drops are reported in logs and
   returned in memory, but not yet persisted. Stage 3 will add a fifth table so
   the gap is queryable alongside the rest, rather than only visible in a run
   log. Schema sketched under "Deferred Tables" below; it is not part of the
   first relational cut.

2. **Cost/token double-counting** — `total_spend`/`total_tokens` sum across ALL
   requests including re-sent history. Store both: raw sums (as-billed) and
   `net_` variants from the last (canonical) request only.

3. **`last_request_per_session` is the correct strategy** —
   `deduplicate_messages` produces truncated sessions; use it only for
   per-message cross-request analysis.

4. **`msg_idx` = input messages only** — Output/assistant messages have
   `msg_idx = None`. Both `msg_idx` and `block_idx` are needed for correct
   ordering.

5. **`data_source` column** — tag each session row with `'adls'` or `'litellm'`
   so analysts can filter or weight truncation-risk sessions appropriately.

---

## Idempotency Design

### Layer 1 — Manifest (skip already-processed sources)

`pipeline_state_{instance}.json` at the output root tracks
`{source_path: content_hash}`. Source files in the manifest are skipped on
re-runs. One manifest per instance. `--full-refresh` ignores it entirely.

### Layer 2 — Partition overwrite (never append)

```
output/
  sessions/
    start_date=2026-01-15/
      llmaven-prod.parquet   ← always overwritten, never appended
      llmaven-dev.parquet
  messages/
    start_date=2026-01-15/
      llmaven-prod.parquet
  tool_definitions/
    llmaven-prod.parquet     ← no date partition; upsert new hashes on each run
  pipeline_state_llmaven-prod.json
```

Every `(date, instance)` file is an atomic full replacement (write to temp,
rename). Session IDs are deterministic — re-processing the same source produces
byte-identical rows.

DuckDB skips non-matching instance files after reading their Parquet footer
stats (min/max for `instance_id` column, a few KB per file). Overhead vs Hive
directory pruning is negligible at this scale.

### Sliding window for multi-day sessions

Always reprocess the last `lookback_days=7` days regardless of manifest state,
so late-arriving records for ongoing sessions are captured correctly. Sessions
older than 7 days are stable.

---

## Multi-Instance Aggregation

```bash
# Each instance is a separate pipeline run
llmaven data pipeline run --instance llmaven-prod --source auto --from 2026-01-01 --to 2026-09-08
llmaven data pipeline run --instance llmaven-dev  --source auto --from 2026-01-01 --to 2026-09-08
```

```sql
-- Cross-instance, start_date auto-extracted via Hive partitioning
SELECT instance_id, data_source, COUNT(*)
FROM read_parquet('sessions/**/*.parquet', hive_partitioning=true)
GROUP BY 1, 2;

-- Per-user across instances (account_uuid stable across instances)
SELECT account_uuid,
  SUM(CASE WHEN instance_id = 'llmaven-prod' THEN net_output_tokens ELSE 0 END) AS prod_tokens,
  SUM(CASE WHEN instance_id = 'llmaven-dev'  THEN net_output_tokens ELSE 0 END) AS dev_tokens
FROM sessions GROUP BY account_uuid;
```

---

## Table Schema

### `sessions` (one row per session)

| column                    | type               | notes                                           |
| ------------------------- | ------------------ | ----------------------------------------------- |
| `instance_id`             | str                | e.g. `llmaven-prod`                             |
| `data_source`             | str                | `adls` or `litellm` — flags truncation risk     |
| `session_id`              | str                | from `end_user`                                 |
| `account_uuid`            | str                | stable across instances                         |
| `device_id`               | str                |                                                 |
| `agent_type`              | str                | `claude_code`, `copilot`, `opencode`, `unknown` |
| `model`                   | str                | normalized via `normalize_model_name`           |
| `start_time`              | timestamp[us, UTC] |                                                 |
| `end_time`                | timestamp[us, UTC] |                                                 |
| `duration_seconds`        | float              |                                                 |
| `request_count`           | int                |                                                 |
| `total_input_tokens_raw`  | int                | summed across all requests (billing view)       |
| `total_output_tokens_raw` | int                |                                                 |
| `total_cost_usd_raw`      | float              | as-billed                                       |
| `net_input_tokens`        | int                | from last request only (analysis view)          |
| `net_output_tokens`       | int                |                                                 |
| `message_count`           | int                |                                                 |
| `user_message_count`      | int                |                                                 |
| `assistant_message_count` | int                |                                                 |
| `has_tool_calls`          | bool               |                                                 |
| `tool_set_hash`           | str                | FK → tool_definitions                           |
| `system_prompt_hash`      | str                | sha256                                          |

### `messages` (one row per message in the canonical session history)

| column           | type | notes                         |
| ---------------- | ---- | ----------------------------- |
| `instance_id`    | str  |                               |
| `session_id`     | str  | FK → sessions                 |
| `message_idx`    | int  | 0-based position              |
| `role`           | str  | user, assistant, system, tool |
| `content_text`   | str  |                               |
| `approx_tokens`  | int  |                               |
| `model`          | str  | assistant messages only       |
| `has_tool_calls` | bool |                               |

### `tool_calls` (one row per tool invocation)

| column            | type | notes |
| ----------------- | ---- | ----- |
| `instance_id`     | str  |       |
| `session_id`      | str  |       |
| `message_idx`     | int  |       |
| `tool_call_idx`   | int  |       |
| `tool_name`       | str  |       |
| `tool_input_json` | str  |       |
| `result_content`  | str  |       |

### Deferred — `skipped_requests` (not in the first cut)

One row per request dropped from grouping, so the reconciliation gap between
request-level and session-level totals is queryable rather than log-only. Added
after the four tables above land; `SkipStats` is the in-memory aggregate that
stands in until then.

| column                  | type  | notes                                          |
| ----------------------- | ----- | ---------------------------------------------- |
| `instance_id`           | str   |                                                |
| `request_id`            | str   |                                                |
| `start_time`            | ts    |                                                |
| `account_uuid`          | str   | `""` when `end_user` did not parse at all      |
| `device_id`             | str   | as above                                       |
| `spend`                 | float | counts toward request totals, not session ones |
| `total_tokens`          | int   | as above                                       |
| `had_native_session_id` | bool  | the per-request trace id, never a session key  |

### `tool_definitions` (deduplicated lookup)

| column              | type      | notes                             |
| ------------------- | --------- | --------------------------------- |
| `tool_set_hash`     | str       | sha256 of sorted definitions JSON |
| `tool_name`         | str       |                                   |
| `description`       | str       |                                   |
| `input_schema_json` | str       |                                   |
| `first_seen`        | timestamp |                                   |

---

## DuckDB Querying from Local Notebooks

```python
from data.connect import open_db

con = open_db()  # reads ADLS URL + auth from .env.analytics; registers views

con.execute("SELECT agent_type, data_source, COUNT(*) FROM sessions GROUP BY 1, 2").df()
```

Auth options (configured in `data/connect.py`):

- `az login` once — DuckDB picks up the credential chain automatically
- Read-only SAS token in `.env.analytics` (gitignored) — simpler for sharing

Upgrade path: if data grows, Azure Synapse Serverless SQL points at the same
Parquet files with zero pipeline changes.

---

## Tasks

### Task 1 — Fix and merge PR #151 (`data/group_sessions.py`) ← prerequisite

- Add unit tests with a small `.jsonl` fixture in `data/tests/`
- Replace `print` with `logging`
- Fix temp file leak: use `zipfile` in-memory, no disk extraction
- Fix silent failures in output message path; log `skipped_session_count`

### Task 2 — Source adapter (`data/sources.py`)

- `from_adls(record) -> dict` — maps AdlLogger JSON to common
  (PostgreSQL-shaped) dict
- `from_litellm(record) -> dict` — pass-through (reader.py already handles this
  shape)
- `iter_source(date, mode, adls_fs, litellm_client) -> Iterator[tuple[dict, str]]`
  — yields `(common_record, source_type)` for each request on a given day;
  implements the `auto` per-day detection (check if `logs/<yyyy>/<mm>/<dd>/`
  exists in ADLS and has files)
- Unit-tested with fixture records in both schemas

### Task 3 — Define relational schema (`data/schema.py`)

- Dataclasses for `Session`, `Message`, `ToolCall`, `ToolDefinition`
- Polars/Arrow schema dicts for each table
- `agent_type` detection from metadata / model / tool names
- Reuse `normalize_model_name` from `data/reader.py`

### Task 4 — Transform layer (`data/transform.py`)

- `session_to_row(session, instance_id, data_source) -> Session`
- `session_to_messages`, `session_to_tool_calls`, `session_to_tool_definitions`
- `build_tables(sessions, instance_id, data_source) -> tuple[4 DataFrames]`
- Handle format differences between coding agents gracefully

### Task 5 — fsspec storage abstraction (`data/storage.py`)

- `read_adls_day(date, fs) -> Iterator[dict]` — streams individual JSON files
  from ADLS
- `read_litellm_zip(path) -> Iterator[dict]` — reads from extracted ZIP
- `write_parquet(df, output_path, fs)` — atomic overwrite via temp-then-rename
- Supports `file://` (local) and `abfs://` (ADLS)

### Task 6 — Incremental state tracking (`data/state.py`)

- `PipelineState(output_root, instance_id, fs)` —
  `pipeline_state_{instance}.json`
- `is_processed(path)`, `mark_processed(path, hash)`, `get_watermark()`
- `--full-refresh` clears state; `lookback_days=7` always reprocesses recent
  window

### Task 7 — Top-level pipeline runner (`data/pipeline.py`)

```python
def run_pipeline(
    source_mode: Literal["adls", "litellm", "auto"],
    adls_source: str | None,   # abfs:// URL or None
    litellm_env_file: Path | None,
    output: str,
    instance_id: str,
    from_date: date,
    to_date: date,
    full_refresh: bool = False,
    lookback_days: int = 7,
) -> PipelineRunStats
```

`PipelineRunStats` includes: sessions processed, the `SkipStats` for requests
dropped as ungroupable (count, spend, tokens, native-id and account-only
subsets), days sourced from ADLS, days sourced from litellm.

Standalone:
`python -m data.pipeline --instance llmaven-prod --source auto --from 2026-01-01 --to 2026-09-08`

### Task 8 — `llmaven data pipeline` CLI subcommand (`src/llmaven/cli.py`)

```
llmaven data pipeline run
  --instance NAME          (required)
  --source [adls|litellm|auto]  (default: auto)
  --from DATE
  --to DATE
  --output PATH
  --full-refresh
  --env-file               (reuse ENV_FILE_OPTION for LiteLLM credentials)
```

`auto` and `adls` resolve ADLS connection from `AZURE_STORAGE_CONNECTION_STRING`
in secrets. `litellm` only needs `LITELLM_MASTER_KEY` + `LITELLM_BASE_URL`
(already in secrets).

### Task 9 — `data/connect.py` analyst helper

`open_db(env_file=None) -> duckdb.Connection` — installs `azure` extension,
configures auth, registers `sessions`, `messages`, `tool_calls`,
`tool_definitions` as views over ADLS Parquet.

### Task 10 — Tests (`data/tests/`)

- `fixtures/sample_adls_requests/` — 3 individual JSON files in AdlLogger format
- `fixtures/sample_litellm_requests.jsonl` — same sessions in PostgreSQL format
- `test_sources.py` — verify `from_adls` and `from_litellm` produce identical
  common-format output for the same request; test `auto` day-selection logic
- `test_transform.py` — `net_` vs `raw_` token math, `tool_set_hash` stability,
  `data_source` propagation
- `test_pipeline.py` — full pipeline on fixtures with each source mode;
  idempotency (run twice, identical output); `auto` mode produces correct
  per-day source attribution

### Task 11 — Azure Container Apps Job (`src/llmaven/infrastructure/resources/container_apps.py`)

Following `create_backup_job` pattern. Command:
`["llmaven", "data", "pipeline", "run", "--source", "auto", "--instance", instance_id, ...]`.
`enable_pipeline_job: bool = False` in `LLMavenConfig`.

### Task 12 — Update analysis notebook (`data/analysis.ipynb`)

Port to DuckDB + Parquet via `open_db()`. Include `data_source` breakdown so
analysts can identify sessions where message content may be truncated.

---

## Dependencies to add

| Package   | Purpose                    | Azure-specific?                              |
| --------- | -------------------------- | -------------------------------------------- |
| `polars`  | DataFrame operations       | No                                           |
| `pyarrow` | Parquet read/write         | No                                           |
| `fsspec`  | Storage abstraction        | No                                           |
| `adlfs`   | ADLS Gen2 fsspec backend   | Yes (optional for local `litellm`-only runs) |
| `duckdb`  | Query engine for notebooks | No                                           |

---

## Verification

**Local, no Azure (litellm source):**

```bash
llmaven infra extract --source litellm --from 2026-08-01 --to 2026-09-08 --out /tmp/raw.zip
python -m data.pipeline --instance test --source litellm --from 2026-08-01 --to 2026-09-08 \
  --adls-source /tmp/raw.zip --output /tmp/out/
duckdb -c "SELECT data_source, COUNT(*) FROM read_parquet('/tmp/out/sessions/**/*.parquet', hive_partitioning=true) GROUP BY 1"
```

**Local, with ADLS access (auto source):**

```bash
az login
llmaven data pipeline run --instance llmaven-prod --source auto \
  --from 2026-08-01 --to 2026-09-08 --output /tmp/out/ --env-file .env.secrets
# Check per-day source attribution in run stats output
```

**Idempotency:** run twice, assert row counts and file checksums identical.

**Source parity test:** run `--source adls` and `--source litellm` over the same
date range where both exist; compare session counts and flag any sessions
present in one but not the other.

**Multi-instance:** run for two instances, query with `instance=*` wildcard,
assert both `instance_id` values appear and no session ID collisions.
