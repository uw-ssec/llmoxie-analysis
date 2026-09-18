---
type: Entity
title: LLMoxie Platform
description: "The UW SSEC open-source AI control plane whose LiteLLM gateway produces the request logs analyzed here, built in three layers under NSF NAIRR award 240292."
tags: [llmoxie, platform, litellm, nairr, ssec]
sources:
  - resource: reference/llmoxie
  - resource: https://github.com/uw-ssec/rse-plugins
  - resource: https://nairrpilot.org/projects/awarded?_requestNumber=NAIRR240292
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

LLMoxie is UW SSEC's open-source AI control plane, developed under NSF NAIRR
award #240292 and the Schmidt Sciences Virtual Institutes for Scientific
Software (VISS) program. It exists to give scientific researchers open,
transparent access to large language models on cloud and HPC systems, with
observability and an agentic coding framework on top.

It is the upstream system for [[project/llmoxie-analysis]]: every row this repo
analyzes originates as a request through LLMoxie's gateway.

## Three layers

| Layer                    | What it is                                                                                                                                                                           | Relevance to analysis                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| **1 — Inference Engine** | Azure Foundry Models, AWS Bedrock, GCP Vertex AI, or vLLM on HPC GPU nodes                                                                                                           | Determines raw model identifiers, which is why [[upstream/model-name-normalization]] exists |
| **2 — API Gateway**      | LiteLLM (unified OpenAI-compatible endpoint, auth, RPM/TPM limits, per-user and per-team budgets, spend tracking, PII masking via Microsoft Presidio) plus MLflow, PostgreSQL, MinIO | **This is where the data comes from** — see [[platform/logging-paths]]                      |
| **3 — RSE-Plugins**      | Claude Code plugins organized Plugin → Agent → Skill for research workflows                                                                                                          | Explains the `agent_type` dimension in [[pipeline/analytics-schema]]                        |

Layer 2 is the control plane LLMoxie itself provides, and it is the only layer
the analysis pipeline reads from. A local Docker Compose stack mirrors the cloud
architecture — same PostgreSQL, MinIO, MLflow, LiteLLM, Qdrant — which is what
makes the local verification path in [[pipeline/pipeline-cli]] possible without
Azure credentials.

## The LLMaven → LLMoxie rename

The project was renamed from **LLMaven** to **LLMoxie**. The old name is not a
mistake when you encounter it — it legitimately persists in:

- the CLI itself (`llmaven infra extract ...`)
- the Python package path (`src/llmaven/...`)
- the upstream README title and badge URLs
- private deployment repos (`llmaven-deploy`, `llmaven-infra`,
  `llmaven-onboard`, `llmaven-demo`)

Treat `llmaven` in a code path as current and correct; treat `LLMoxie` as the
project's name in prose.

## Scale and standing

At the time of writing the gateway serves 150+ users. The work has been accepted
to KDD 2026 (SciSoc track). The codebase is BSD-3-Clause.

## Related Concepts

- [LLMoxie Analysis](../project/llmoxie-analysis.md): This analysis package is
  the downstream consumer of the platform's request logs.
- [LLMoxie Development Timeline](llmoxie-timeline.md): The timeline records how
  the platform arrived at its current three-layer shape.
- [The Two Logging Paths](logging-paths.md): Layer 2 is where both
  request-recording paths are configured.
