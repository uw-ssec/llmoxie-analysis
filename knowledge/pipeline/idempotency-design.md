---
type: Decision
title: "Idempotency: Manifest and Partition Overwrite"
description: Two independent layers — a content-hash manifest that skips unchanged inputs and whole-partition overwrite that makes reprocessing safe — let any run be repeated without duplicating or corrupting data.
tags: [idempotency, manifest, state, lookback, reprocessing, decision]
status: draft
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/7
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/11
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

The pipeline runs on a schedule against a data source that is still being
written to. Yesterday's blobs may be complete; today's certainly are not. A run
must therefore be safe to repeat over a range it has already processed — not
merely harmless, but _exactly_ reproducing the prior output when the inputs have
not changed.

Two independent layers achieve this. They solve different problems and neither
substitutes for the other.

## Layer 1 — the manifest, for efficiency

`data/state.py` maintains a per-instance JSON manifest:

```text
output/pipeline_state_<instance_id>.json
```

```json
{
  "adls/2026-06-01/req-0001.json": "e3b0c44298fc1c14...",
  "adls/2026-06-01/req-0002.json": "9f86d081884c7d65..."
}
```

The mapping is `source_path → content_hash`. Before reading a source object, the
pipeline hashes it (or its metadata digest, where the store provides one) and
compares. Unchanged inputs are skipped.

```python
class PipelineState:
    def __init__(self, output_root: str, instance_id: str, fs): ...
    def is_processed(self, source_path: str, content_hash: str) -> bool: ...
    def mark_processed(self, source_path: str, content_hash: str) -> None: ...
    def get_watermark(self) -> date | None: ...
    def clear(self) -> None: ...
```

!!! note "The manifest is an optimization, not a correctness mechanism"

    Deleting the manifest must never change the output — only how long the run
    takes. If skipping a file could change results, the skip logic is wrong.
    This is the invariant to test first.

**Per-instance, not global.** The filename carries `instance_id`, so two
concurrent runs against different date ranges never contend for the same state
file. It is also why `instance_id` is a required CLI argument rather than a
default.

## Layer 2 — partition overwrite, for correctness

Efficiency is the manifest's job. Correctness is the write path's.

Every run writes **whole partitions**, always overwriting, never appending. When
a day is reprocessed, `start_date=2026-06-01/<instance>.parquet` is replaced in
full via the temp-plus-rename described in [[pipeline/storage-layout]].

This is what makes reprocessing genuinely safe. There is no append that could
double a row, no merge key that could be wrong, no delete-then-insert window
where a reader sees a partially-populated day. The old partition is valid right
up until the moment the new one replaces it.

!!! danger "Appending would make every caveat in this bundle worse"

    Session reconstruction is a grouping operation over a whole day. The
    session-level aggregates it produces — turn counts, token sums, tool-call
    counts — are only correct when computed over the complete day. Appending
    partial results would produce duplicate `session_id` rows carrying
    *different* aggregate values, and no downstream query could tell which was
    right. See [[caveats/cost-token-double-counting]] for how badly summed
    columns already behave when their grain is misunderstood.

## The sliding lookback

Scheduled runs process the last `lookback_days=7` days, not just yesterday.

Two reasons, both real:

1. **Late-arriving data.** The ADLS logger writes asynchronously and can fail
   silently ([[platform/adls-logger]]). A blob may land hours after the request
   it records.
2. **Sessions that span the boundary.** A conversation started on day _N_ and
   continued on day _N+1_ is only fully reconstructible once both days are
   available.

The manifest keeps the cost of this bounded: reprocessing seven days re-reads
seven days of _paths_, but hashes short-circuit the six days that have not
changed. A typical scheduled run reprocesses one day's worth of content while
re-verifying a week's worth of completeness.

## `--full-refresh`

```bash
llmaven data pipeline run --instance prod --from 2026-05-08 --to 2026-09-17 --full-refresh
```

`--full-refresh` **neither reads nor writes the manifest.** It is a clean
rebuild: every source object in range is read, every partition in range is
overwritten, and the state file is left exactly as it was.

That last detail is deliberate. A full refresh run is usually diagnostic — "does
the current code reproduce what is on disk?" — and it should not disturb the
scheduled job's incremental state as a side effect. If a genuine reset is
wanted, `PipelineState.clear()` is the explicit way to ask for it.

## The test that proves it

Issue #11 specifies the gate: run the pipeline twice over the same fixture range
and assert the output Parquet files are **byte-identical**.

```python
first = run_pipeline(...)  # writes to tmp_path
digest_1 = {p: sha256(p.read_bytes()) for p in tmp_path.rglob("*.parquet")}

second = run_pipeline(...)  # same args, same fixtures
digest_2 = {p: sha256(p.read_bytes()) for p in tmp_path.rglob("*.parquet")}

assert digest_1 == digest_2
```

Byte-identity, not row-set equality, is the bar. It is stricter than necessary
for analytical correctness, and that is the point — it catches nondeterminism
that a set comparison would hide:

- unsorted rows from a dict or set iteration
- an unstable `tool_set_hash` (see [[pipeline/analytics-schema]] — sort before
  hashing)
- a wall-clock timestamp or run ID leaking into a data column
- Parquet metadata varying between writes

Each of those is a latent bug that would eventually make two "identical" runs
disagree. A byte-comparison test finds them on the first CI run instead of six
months later in a reconciliation.

## Related Concepts

- [Storage Layout and Parquet I/O](storage-layout.md): The atomic
  temp-plus-rename write is the mechanism partition overwrite depends on.
- [Pipeline Architecture](pipeline-architecture.md): "Always overwrite, never
  append" is stated there as an architectural rule; this concept is its
  implementation.
- [The llmaven data pipeline run CLI](pipeline-cli.md): `--full-refresh` and
  `--instance` are the two flags that expose this design to operators.
- [Scheduled Execution on Azure Container Apps](container-apps-job.md): The
  scheduled job is the reason a sliding lookback is needed at all.
