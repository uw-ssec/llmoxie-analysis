---
type: Process
title: Storage Layout and Parquet I/O
description: "The single module that owns every read and write, the Hive-partitioned output path it produces, and the atomic write that makes partition overwrite safe."
tags: [storage, parquet, adls, abfs, hive-partitioning, io]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/6
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

`data/storage.py` is the only module in the pipeline that touches a filesystem.
Everything above it — adapters, transforms, schema — deals in Python objects and
DataFrames. That boundary is what makes [[pipeline/pipeline-architecture]]'s
"transform core imports nothing from Azure" rule enforceable rather than
aspirational: there is exactly one file to audit.

## The three functions

| Function                             | Reads / writes                     | Notes                                                                              |
| ------------------------------------ | ---------------------------------- | ---------------------------------------------------------------------------------- |
| `read_adls_day(fs, container, date)` | One day of ADLS blobs              | Yields raw JSON records from the blob layout described in [[platform/adls-logger]] |
| `read_litellm_zip(path)`             | A zip from `llmaven infra extract` | Yields raw spend-log rows; see [[platform/litellm-spend-logs]]                     |
| `write_parquet(df, path, fs)`        | One Parquet partition              | Atomic: writes `<path>.tmp`, then renames                                          |

Both readers yield records, not lists. A day of ADLS blobs is thousands of
individual JSON objects, and the pipeline never needs more than one in memory at
a time before it is handed to an adapter.

## Path convention

```text
output/
  sessions/
    start_date=2026-06-01/
      <instance_id>.parquet
    start_date=2026-06-02/
      <instance_id>.parquet
  messages/
    start_date=2026-06-01/
      <instance_id>.parquet
  tool_calls/
    ...
  tool_definitions/
    ...
```

Two things are doing work in that layout.

**`start_date=<d>` is Hive partitioning.** DuckDB, Spark, and Synapse Serverless
all recognize the `key=value` directory convention and expose `start_date` as a
real column without it being stored in the Parquet files. A query filtered to a
date range reads only the matching directories. This is the single
highest-leverage decision in the storage layer, and it is free.

**`<instance_id>.parquet` is the unit of overwrite.** Each pipeline run writes
one file per partition, named for the run's instance. Reprocessing a day means
replacing that one file, not mutating a directory. See
[[pipeline/idempotency-design]] for how that plays out across reruns.

!!! important "Partition by `start_date`, not by ingestion date"

    `start_date` is the date the *session* began, derived from the data. It is
    not the date the pipeline ran. A session that starts at 23:55 and runs past
    midnight belongs entirely to the day it started. This keeps a session's rows
    in one partition across all four tables, which is what makes a partition-scoped
    join correct.

## URL schemes

`write_parquet` and the readers accept both:

- `file:///tmp/out/` — local development and tests
- `abfs://container@account.dfs.core.windows.net/` — Azure Data Lake Gen2

The `adlfs` import that provides `abfs://` is **guarded**:

```python
try:
    import adlfs
except ImportError:
    adlfs = None
```

A developer running the pipeline against a local extract zip should not need
Azure credentials, an Azure SDK, or a network connection. If `adlfs` is missing
and an `abfs://` path is requested, the failure is a clear message at startup,
not an `ImportError` traceback three stages into a run.

## The atomic write

```python
tmp = f"{path}.tmp"
fs.makedirs(dirname(path), exist_ok=True)
df.write_parquet(tmp)
fs.mv(tmp, path)  # atomic rename within the same filesystem
```

!!! warning "Never write directly to the final path"

    A pipeline that crashes mid-write leaves a truncated Parquet file at the
    path a query expects to be valid. Every subsequent read of that partition
    fails, and the failure looks like data corruption rather than a failed run.
    The temp-plus-rename pattern means a partition is either the previous
    complete version or the new complete version — never a half of either.

Both local filesystems and ADLS Gen2 (which has real directories and atomic
rename, unlike flat blob storage) support this. It is the reason the output
target is Gen2 specifically.

## Related Concepts

- [Pipeline Architecture](pipeline-architecture.md): Storage is stage four, and
  the layering rule that isolates it is stated there.
- [Idempotency: Manifest and Partition Overwrite](idempotency-design.md): The
  atomic write is the mechanism that makes partition overwrite a safe operation.
- [Analytics Schema — Four Tables](analytics-schema.md): Each of the four tables
  gets its own partitioned directory tree under this layout.
- [Query Layer: DuckDB and Synapse Serverless](query-layer.md): Hive
  partitioning is what lets the query layer prune by date without a catalog.
