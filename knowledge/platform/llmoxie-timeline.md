---
type: Fact
title: LLMoxie Development Timeline
description: How the upstream repository evolved across 99 commits from a Rubin-era RAG prototype into a LiteLLM control plane with data-lake logging and session grouping.
tags: [llmoxie, history, timeline, provenance]
sources:
  - resource: reference/llmoxie git history, 99 commits, 763da8d..ec5d8b2
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

Reconstructed from the full commit history of `uw-ssec/llmoxie` — 99 commits
from `763da8d` (2024-11-12) to `ec5d8b2` (2026-09-11). This matters to
[[project/llmoxie-analysis]] because the shape of the data changes over time,
and a dataset's fidelity depends on _when_ it was captured.

## Phases

### 1. RAG system (2024-11 → 2025-07)

The repository did not start as a gateway. It began as a retrieval system:

- `2024-11-12` `763da8d` — Initial commit
- `2024-12-03` `91a8797` — **Merged Rubin-RAG into LLMaven**
- `2025-02` → `2025-03` — GPU and embedding experiments, a Streamlit RAG chatbot
  with PDF upload, FastAPI `retrieve` / `generate` endpoints, scraping and
  RAG-evaluation scripts (PRs #20–#23)
- `2025-07-02` `9389473` — `feat: Support running on osx-arm64` (#26)

### 2. Pivot to the LiteLLM proxy (2025-10 → 2026-01)

- `2025-10-21` `8d14ee5` — **WIP: proxy logger** — the pivot begins
- `2025-10-22` `36161bc` — Add docker container (#30)
- `2025-10-24` `5f73fd5` — API key auth for proxy (#31)
- `2025-11-14` `aad0892` — LLMaven API refactored with FastAPI + Streamlit (#36)
- `2025-12-04` `1fa18c1` — Infrastructure management refactor (#40)
- `2026-01-02` `dbf4118` — Agentic RAG with multi-vector hybrid search (#54)
- `2026-01-29` `2d60960` — LiteLLM pinned to v1.81.0-stable (#81)

### 3. Extraction and observability (2026-02 → 2026-05)

- `2026-02-16` `527d163` — **Create infra command to extract spend log data out
  of litellm** (#79) — birth of `llmaven infra extract`. Notably, the PR
  switched mid-review from querying PostgreSQL directly to the REST API
  endpoint; see [[platform/litellm-spend-logs]]
- `2026-03-10` `2704678` — README rewritten around the three-layer architecture
- `2026-03-17` `39901b9` — `infra extract` extended with MLflow trace fetching
  (#100)
- `2026-04-16` `8dfb417` — Use `jsonlines` instead of manual JSON handling
  (#116)
- `2026-05-06` `fbb42e9` — zizmor workflow security linting adopted (#124)
- `2026-05-08` `b0f1961` — **feat: Azure Data Lake logging** (#123) — the
  `AdlLogger` lands; see [[platform/adls-logger]]

### 4. Session grouping (2026-09)

- `2026-09-11` `ec5d8b2` — **feat: group raw request logs into per-session
  conversations** (#151) — the prototype that
  [[upstream/session-reconstruction]] describes, and the prerequisite for this
  repo's pipeline

## The inference that matters most

!!! important "ADLS logging postdates the benchmark dataset"

    `AdlLogger` landed on **2026-05-08**. The dataset everyone quotes — 11,992
    requests grouped into 279 sessions — is the **January–March 2026** dump.
    That data was captured months _before_ data-lake logging existed, so it can
    only have come from the LiteLLM/PostgreSQL path.

This is not a footnote. It is the reason `--source auto` performs _per-day_
detection rather than choosing one backend for the whole run: any historical
backfill necessarily crosses the 2026-05-08 boundary, with LiteLLM-sourced days
on one side and ADLS-sourced days on the other. Auto mode is a
historical-backfill requirement, not merely an operational convenience. See
[[pipeline/source-adapters]].

It also means the well-known "~25% of sessions have unparsable session*id"
figure is a measurement of \_LiteLLM-sourced* data specifically — see
[[caveats/end-user-parsing]].

## Related Concepts

- [LLMoxie Platform](llmoxie-platform.md): The timeline ends at the platform as
  it exists today.
- [AdlLogger — Azure Data Lake Logging](adls-logger.md): Data-lake logging is
  the capability introduced in the third phase of this history.
- [Source Adapters and Auto Detection](../pipeline/source-adapters.md): The
  mid-history logging cutover is the reason per-day source detection is a
  correctness requirement.
