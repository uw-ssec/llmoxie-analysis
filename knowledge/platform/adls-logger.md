---
type: Fact
title: AdlLogger — Azure Data Lake Logging
description: "The LiteLLM callback that writes one untruncated JSON blob per request to ADLS Gen2, its record envelope, its path convention, and its silent failure mode."
tags: [adls, logging, azure, litellm-callback]
sources:
  - resource: reference/llmoxie/src/llmaven/infrastructure/resources/adl_logger.py
  - resource: reference/llmoxie commit b0f1961, PR #123, 2026-05-08
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

`AdlLogger` is a LiteLLM custom-callback class that persists each completed
request as a standalone JSON blob in Azure Data Lake Storage Gen2. It is the
preferred of the [[platform/logging-paths]] because it stores message bodies
intact.

It landed 2026-05-08 in commit `b0f1961` (PR #123). The same PR also updated the
LiteLLM `Dockerfile` to `COPY adl_logger.py` into the image rather than relying
on a docker-compose volume mount, so the callback works in Container Apps
production deployments where volume mounts are unavailable. LiteLLM loads it via
`callbacks: adl_logger.proxy_handler_instance` in `config.yaml`, resolving the
module-level singleton `proxy_handler_instance = AdlLogger()`.

## Configuration

| Variable                          | Required                                       | Default        |
| --------------------------------- | ---------------------------------------------- | -------------- |
| `AZURE_STORAGE_CONNECTION_STRING` | Yes — constructor raises `ValueError` if unset | —              |
| `ADLS_CONTAINER`                  | No                                             | `litellm-logs` |

## Path convention

```python
f"logs/{start_time.year}/{start_time.month:02d}/{start_time.day:02d}/{request_id}.json"
```

Zero-padded month and day, one file per request. The day-level directory is the
natural read unit, which is why the pipeline's storage layer exposes
`read_adls_day(date, fs)` — see [[pipeline/storage-layout]].

`request_id` comes from the standard logging object's `id`, with a fallback of
`f"{os.getpid()}_{start_time.strftime('%H%M%S%f')}"` when absent.

## Record envelope

```python
record = {
    "timestamp_start": start_time.isoformat(),
    "timestamp_end": end_time.isoformat(),
    "kwargs": kwargs,
    "response": response_obj.model_dump()
    if hasattr(response_obj, "model_dump")
    else None,
    "cost": litellm.completion_cost(completion_response=response_obj),
}
```

The analytically useful payload is nested at
`record["kwargs"]["standard_logging_object"]`. Everything the pipeline needs —
`id`, `startTime`, `endTime`, `end_user`, `model`, `response_cost`,
`total_tokens`, `messages`, `response`, and the `metadata` block carrying
`user_api_key_hash` and `user_api_key_alias` — lives there. The adapter that
reshapes this into the LiteLLM row format is documented in
[[pipeline/source-adapters]].

Blobs are written with `upload_blob(blob_data, overwrite=True)`, so a replayed
request is idempotent at the blob level.

## The silent failure mode

!!! danger "Write failures are invisible to the caller"

    The entire body of the callback is wrapped in a bare `except Exception`
    that only logs `"Failed to write to ADLS: %s"`. This is deliberate — a
    logging fault must never fail a user's inference request — but it has a
    direct analytical consequence: **absence of a blob is not evidence that no
    request occurred.**

Concretely, this means ADLS record counts are a _lower bound_. When ADLS and
LiteLLM counts disagree for the same day, the LiteLLM count is more likely to be
the complete one, even though its message bodies are lower fidelity. Any
reconciliation report should treat a shortfall on the ADLS side as expected
rather than anomalous.

## Related Concepts

- [The Two Logging Paths](logging-paths.md): The ADLS path is one of the two
  recording paths compared there.
- [Source Adapters and Auto Detection](../pipeline/source-adapters.md):
  `from_adls` is the adapter that reshapes these blob records into the common
  shape.
- [LLMoxie Development Timeline](llmoxie-timeline.md): The timeline explains why
  2026-05-08 is the hard start date for this logging path.
