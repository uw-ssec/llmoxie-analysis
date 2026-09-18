---
type: Decision
title: "Query Layer: DuckDB and Synapse Serverless"
description: "Two query engines read the same Parquet files — DuckDB for local and notebook work, Azure Synapse Serverless SQL for shared access — with one helper function as the only connection path."
tags: [duckdb, synapse, sql, notebook, credentials, decision]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/10
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/13
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

The pipeline's output is Parquet on a filesystem, not a database. That is a
deliberate choice, and the payoff is here: two entirely different query engines
read the same bytes, and neither owns the data.

| Engine                       | Used for                                   | Reads                                             |
| ---------------------------- | ------------------------------------------ | ------------------------------------------------- |
| DuckDB                       | Local analysis, notebooks, CI tests        | `file://` and `abfs://` via the `azure` extension |
| Azure Synapse Serverless SQL | Shared queries, BI tools, non-Python users | `abfs://` via `OPENROWSET`                        |

There is no ETL between them. There is no schema registry to keep in sync. Both
engines infer the schema from the Parquet footers and both recognize the
`start_date=` Hive partitioning from [[pipeline/storage-layout]].

## `open_db()` — the only connection path

```python
def open_db(env_file: Path | None = None) -> duckdb.Connection
```

One function. It installs and loads the DuckDB `azure` extension, resolves
credentials, and returns a connection ready to read both local and remote
Parquet.

```python
from llmaven.data.connect import open_db

con = open_db()
con.sql("""
    SELECT model, COUNT(*) AS sessions, SUM(net_tokens) AS tokens
    FROM read_parquet('abfs://analytics/output/sessions/**/*.parquet',
                      hive_partitioning = true)
    WHERE start_date >= DATE '2026-08-01'
    GROUP BY 1
    ORDER BY tokens DESC
""")
```

Centralizing this matters more than it looks. Without it, every notebook grows
its own five-line credential preamble, those preambles drift, and one of them
eventually ends up committed with a live token in it.

## Credentials

`open_db()` resolves credentials in order:

1. **`az login` / `DefaultAzureCredential`** — the default and the preferred
   path. Nothing is stored in the repository, and access follows the operator's
   own Entra identity.
2. **A read-only SAS token** in `.env.analytics` — the fallback, for
   environments where interactive login is not available.

!!! danger "`.env.analytics` must be gitignored"

    This file holds a live credential. It belongs in `.gitignore` before it
    exists on anyone's disk, not after. The SAS token it holds must be
    **read-only** and time-bounded — the query layer never writes, so a
    write-capable token grants strictly more access than any consumer needs.

    Consistent with the wider convention: documentation records the *name* of a
    credential and where it lives, never its value.

## Synapse Serverless SQL

Synapse exists for the users DuckDB does not serve: people with a SQL client and
no Python environment, and BI tools that speak TDS.

```sql
SELECT model, COUNT(*) AS sessions
FROM OPENROWSET(
    BULK 'https://<account>.dfs.core.windows.net/analytics/output/sessions/**',
    FORMAT = 'PARQUET'
) AS rows
GROUP BY model;
```

It is serverless and billed per byte scanned, which makes partition pruning a
cost control rather than just a latency optimization. A query that filters on
`start_date` reads one directory; a query that does not reads the entire
history.

!!! tip "Create views, not copies"

    Where Synapse is used regularly, define `CREATE VIEW` over the `OPENROWSET`
    for each of the four tables. Users get stable table names, and the view
    definition is the one place the storage path is written down. Copying data
    into Synapse-managed tables would reintroduce exactly the sync problem this
    architecture avoids.

## Porting the notebook

`data/analysis.ipynb` currently loads pandas DataFrames directly from raw logs —
it re-runs the reader and the grouping prototype on every execution. Issue #13
ports it to `open_db()` plus Parquet.

The change is not cosmetic:

- **Speed.** Reading pre-computed partitions replaces re-parsing thousands of
  JSON blobs on every kernel restart.
- **Consistency.** The notebook and any scheduled report read the _same_ rows,
  produced by the same transform. Today a notebook can silently disagree with
  the pipeline because it runs an older copy of the grouping code.
- **Scope.** The notebook stops being an implementation of the pipeline and
  becomes a consumer of it.

The caveats do not disappear in the port. A notebook querying `agent_type` still
needs to know about [[caveats/responses-api-gap]]; one summing `total_spend`
still needs [[caveats/cost-token-double-counting]]. Those are properties of the
data, not of the access method.

## Related Concepts

- [Analytics Schema — Four Tables](analytics-schema.md): The tables and join
  keys that every query in this layer targets.
- [Storage Layout and Parquet I/O](storage-layout.md): Hive partitioning is what
  makes date-filtered queries cheap in both engines.
- [Caveat: Cost and Token Double-Counting](../caveats/cost-token-double-counting.md):
  The first thing any query summing spend or tokens must account for.
- [Caveat: The Responses API Output Gap](../caveats/responses-api-gap.md):
  Queries that slice by client or count assistant messages are affected by this
  gap.
