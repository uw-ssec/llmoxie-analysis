---
type: Reference
title: The llmaven data pipeline run CLI
description: "The single operator-facing command, its flags, the credentials each source mode requires, and the validation that happens before any data is read."
tags: [cli, operations, flags, credentials, reference]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/9
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

One command drives the whole pipeline. It is a thin wrapper: it parses flags,
validates credentials, and calls `run_pipeline()` from
[[pipeline/pipeline-architecture]]. No business logic lives here, which is why
the pipeline can also be invoked directly from a test or a notebook without
going through argument parsing.

```bash
llmaven data pipeline run \
  --instance prod \
  --source auto \
  --from 2026-08-01 \
  --to 2026-09-08 \
  --output abfs://analytics/output/
```

## Flags

| Flag             | Required | Default | Purpose                                                            |
| ---------------- | -------- | ------- | ------------------------------------------------------------------ |
| `--instance`     | **yes**  | —       | Names the run; becomes the output filename and the manifest suffix |
| `--source`       | no       | `auto`  | `adls`, `litellm`, or `auto`                                       |
| `--from`         | yes      | —       | First date to process, inclusive                                   |
| `--to`           | yes      | —       | Last date to process, inclusive                                    |
| `--output`       | yes      | —       | Output root; `file://` or `abfs://`                                |
| `--full-refresh` | no       | off     | Ignore and preserve the manifest; rebuild every partition in range |
| `--env-file`     | no       | —       | Path to a `.env` file for LiteLLM credentials                      |

!!! important "`--instance` has no default on purpose"

    It is the only thing separating two concurrent runs' output files and state
    manifests ([[pipeline/idempotency-design]]). A default would make it easy
    for a developer's ad-hoc backfill to overwrite the production partitions it
    was meant to compare against. Being forced to type `--instance scratch` is
    the entire safeguard.

Suggested convention: `prod` for the scheduled job, `<username>-<purpose>` for
anything manual (`ccore-backfill-may`).

## `--source auto` is the default for a reason

`auto` resolves the source **per day**, not once per run — a consequence of the
2026-05-08 logging cutover documented in [[platform/llmoxie-timeline]]. A range
spanning that boundary is not a mixed-source edge case to be handled manually;
it is the normal case, and `auto` is what makes it correct. See
[[pipeline/source-adapters]] for the resolution logic.

Explicit `--source adls` or `--source litellm` remains available for reproducing
a known result or for isolating a source during debugging.

## Credential validation happens first

Each mode needs different credentials, and the CLI checks for them **before
reading any data**:

| `--source`     | Requires                                    |
| -------------- | ------------------------------------------- |
| `adls`, `auto` | `AZURE_STORAGE_CONNECTION_STRING`           |
| `litellm`      | `LITELLM_MASTER_KEY` and `LITELLM_BASE_URL` |

!!! warning "Fail at second zero, not at day four"

    A 40-day backfill that discovers a missing environment variable on day 4
    has burned several minutes and left a partially-written output tree behind.
    Validating up front turns that into an immediate error message naming the
    exact variable. This is the cheapest reliability improvement in the entire
    CLI.

`--env-file` loads these from a file rather than the ambient environment. As
with `.env.analytics` in [[pipeline/query-layer]], any such file holds live
credentials and must be gitignored.

## The LiteLLM two-step

LiteLLM mode is not a direct database read. The spend logs are extracted to a
zip first ([[platform/litellm-spend-logs]]), and the pipeline consumes the zip:

```bash
# 1. Extract the range to a local archive
llmaven infra extract \
  --source litellm \
  --from 2026-08-01 --to 2026-09-08 \
  --out /tmp/raw.zip

# 2. Run the pipeline against it
python -m data.pipeline \
  --instance test \
  --source litellm \
  --from 2026-08-01 --to 2026-09-08 \
  --adls-source /tmp/raw.zip \
  --output /tmp/out/

# 3. Verify what landed
duckdb -c "SELECT data_source, COUNT(*)
           FROM read_parquet('/tmp/out/sessions/**/*.parquet',
                             hive_partitioning = true)
           GROUP BY 1"
```

The split is useful beyond mechanics: the zip is a stable, re-runnable input.
Extract once, then iterate on transform code against identical bytes as many
times as needed — which is also how the idempotency fixtures in issue #11 are
produced.

## Reading the result

`run_pipeline()` returns a `PipelineRunStats`, and the CLI prints it. The two
numbers worth reading every time:

- **Requests skipped for unparsable `end_user`** — the rate described in
  [[caveats/end-user-parsing]]. A sudden jump means a client changed its
  identifier format, not that traffic dropped.
- **Partitions written versus partitions in range** — a gap means days with no
  data. On a recent range that is a logging failure worth investigating
  ([[platform/adls-logger]] fails silently); on a historical range it may simply
  be a quiet weekend.

## Related Concepts

- [Pipeline Architecture](pipeline-architecture.md): The CLI is a thin wrapper
  over the `run_pipeline` entry point defined there.
- [Idempotency: Manifest and Partition Overwrite](idempotency-design.md):
  `--instance` and `--full-refresh` are the operator-facing surface of that
  design.
- [Source Adapters and Auto Detection](source-adapters.md): What `--source auto`
  actually does on a per-day basis.
- [LiteLLM Spend Logs and infra extract](../platform/litellm-spend-logs.md): The
  extract step that produces the zip LiteLLM mode consumes.
- [Scheduled Execution on Azure Container Apps](container-apps-job.md): The same
  command, run on a schedule with a fixed instance name.
