---
type: Process
title: Scheduled Execution on Azure Container Apps
description: "The pipeline runs as a scheduled Azure Container Apps Job provisioned by Pulumi, following the existing backup-job pattern and gated behind an opt-in config flag."
tags: [azure, container-apps, pulumi, scheduling, infrastructure]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/12
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

The pipeline is a batch job: it starts, processes a date range, writes
partitions, and exits. It is not a service. Azure Container Apps Jobs match that
shape exactly — scheduled, run to completion, billed only while executing — and
LLMoxie already provisions one.

## Follow the backup-job pattern

`container_apps.py` in the upstream infrastructure package already contains
`create_backup_job`, a scheduled Container Apps Job that runs a database backup.
The pipeline job should be built as a sibling of it, not as a new pattern.

That is not just tidiness. `create_backup_job` has already resolved the
non-obvious parts of the Azure resource graph — job resource shape, cron
expression format, managed identity assignment, image reference, environment
wiring, and log configuration. Reimplementing those is how two jobs in the same
stack end up with subtly different retry semantics that nobody notices until one
of them fails quietly.

```python
# Mirror this structure; do not invent a second one.
create_pipeline_job(
    name="llmaven-data-pipeline",
    schedule="0 3 * * *",  # daily, 03:00 UTC
    image=...,
    command=["llmaven", "data", "pipeline", "run"],
    args=["--instance", "prod", "--source", "auto", ...],
    identity=...,
)
```

## Gated behind an opt-in flag

```python
class LLMavenConfig:
    ...
    enable_pipeline_job: bool = False
```

The flag defaults to `False`. Adding the pipeline to the infrastructure package
must not cause a job to appear in every existing deployment on the next
`pulumi up`.

!!! important "Default-off is a requirement, not a preference"

    LLMoxie is deployed by more than one group. A default-on job would start
    writing to an `output/` path that may not exist, using credentials that may
    not be granted, on stacks whose operators never asked for a data pipeline.
    Opt-in keeps the blast radius of this addition at exactly zero for everyone
    who does not set the flag.

It also matches the existing convention — other optional capabilities in
`LLMavenConfig` are gated the same way, so an operator reading the config sees a
consistent set of toggles rather than one special case.

## Schedule and range

The job runs daily and processes a sliding window rather than a single day:

```bash
llmaven data pipeline run \
  --instance prod \
  --source auto \
  --from $(date -u -d '7 days ago' +%Y-%m-%d) \
  --to   $(date -u +%Y-%m-%d) \
  --output abfs://analytics/output/
```

The seven-day window is the `lookback_days` default from
[[pipeline/idempotency-design]], and it is safe precisely because of the
manifest and partition-overwrite layers described there. Without them, a daily
job reprocessing a week would produce seven times the data.

A fixed `--instance prod` is correct here. The scheduled job owns the `prod`
manifest and the `prod` partition files; manual runs use their own instance
names and cannot collide with it ([[pipeline/pipeline-cli]]).

## Identity, not secrets

The job authenticates to ADLS with a **managed identity**, granted
`Storage Blob Data Contributor` on the analytics container. No connection string
is stored in the job definition, in Pulumi config, or in the container image.

This is the same principle as the query layer's preference for `az login` over a
SAS token ([[pipeline/query-layer]]): credentials are granted to an identity,
not copied into configuration. Pulumi config carries resource IDs and role
assignments — never secret values.

## Observing failures

The job's exit code is the signal. A non-zero exit should raise an alert; a zero
exit with zero partitions written should also raise one, because the pipeline
can complete successfully over a range that had no data.

Two failure modes are worth watching specifically:

- **Silent upstream logging failure.** [[platform/adls-logger]] swallows write
  errors, so a day can be genuinely empty while the gateway appears healthy. The
  pipeline will report success over it.
- **Credential expiry or revoked role assignment.** These surface as a startup
  validation failure rather than a partial run, which is the behavior
  [[pipeline/pipeline-cli]] is designed to produce.

## Related Concepts

- [The llmaven data pipeline run CLI](pipeline-cli.md): The job invokes exactly
  this command; nothing about the pipeline is Azure-specific.
- [Idempotency: Manifest and Partition Overwrite](idempotency-design.md): The
  seven-day sliding window is only affordable and safe because of those two
  layers.
- [Storage Layout and Parquet I/O](storage-layout.md): The `abfs://` output
  target the job writes to.
- [LLMoxie Platform](../platform/llmoxie-platform.md): The upstream
  infrastructure package this job is added to.
