## 2026-09-19
* **Update**: Linked `platform/litellm-spend-logs.md` to `upstream/session-reconstruction.md` (A single `.jsonl` export, as `dbexport.sh` produces, selects that module's streaming code path instead of the DataFrame path a zip takes.).
* **Update**: Linked `caveats/end-user-parsing.md` to `datasets/jan-mar-2026-findings.md` (Its count of 13,221 distinct native `session_id` values across 13,291 records is why upstream's fallback to that column inflates session counts.).
* **Update**: Updated concept `datasets/jan-mar-2026-findings.md`.
* **Update**: Updated concept `platform/litellm-spend-logs.md`.
* **Update**: Updated concept `upstream/session-reconstruction.md`.
* **Update**: Updated concept `caveats/end-user-parsing.md`.
* **Update**: Updated concept `upstream/reader-flattening.md`.
* **Update**: Updated concept `project/eval-authoring-lessons.md`.
* **Update**: Linked `project/eval-authoring-lessons.md` to `project/pixi-gate-quirks.md` (The pixi task shell quirk that corrupted the skill sync.).
* **Update**: Linked `project/pixi-gate-quirks.md` to `project/skill-evals.md` (The evals this knowledge came from.).
* **Update**: Linked `project/skill-evals.md` to `project/pixi-gate-quirks.md` (What building the skill evals taught about this tool or practice.).
* **Creation**: Documented concept `project/pixi-gate-quirks.md` (Pixi Task and Verify Gate Quirks).
* **Update**: Linked `project/eval-authoring-lessons.md` to `project/skill-evals.md` (The evals this knowledge came from.).
* **Update**: Linked `project/skill-evals.md` to `project/eval-authoring-lessons.md` (What building the skill evals taught about this tool or practice.).
* **Update**: Linked `project/inspect-conventions.md` to `project/skill-evals.md` (The evals this knowledge came from.).
* **Update**: Linked `project/skill-evals.md` to `project/inspect-conventions.md` (What building the skill evals taught about this tool or practice.).
* **Update**: Linked `project/harbor-conventions.md` to `project/skill-evals.md` (The evals this knowledge came from.).
* **Update**: Linked `project/skill-evals.md` to `project/harbor-conventions.md` (What building the skill evals taught about this tool or practice.).
* **Update**: Updated concept `project/skill-evals.md`.
* **Update**: Updated concept `project/current-state.md`.
* **Creation**: Documented concept `project/eval-authoring-lessons.md` (Lessons for Writing Verifiers and Sample Rules).
* **Creation**: Documented concept `project/inspect-conventions.md` (Inspect Conventions for Skill Samples).
* **Creation**: Documented concept `project/harbor-conventions.md` (Harbor Conventions for Skill Tasks).
* **Update**: Updated concept `project/skill-evals.md`.
* **Update**: Linked `project/skill-evals-plan.md` to `project/skill-evals.md` (The design and decision log this plan implements.).
* **Update**: Linked `project/skill-evals.md` to `project/skill-evals-plan.md` (The plan that implements this design, with the decisions made while planning it.).
* **Update**: Updated concept `project/skill-evals-plan.md`.
* **Update**: Updated concept `project/skill-evals.md`.
* **Update**: Linked `project/skill-evals-plan.md` to `project/skill-evals.md` (The design and decision log this plan implements.).
* **Update**: Linked `project/skill-evals.md` to `project/skill-evals-plan.md` (The plan that implements this design, with the decisions made while planning it.).
* **Creation**: Documented concept `project/skill-evals-plan.md` (Skill Evals Implementation Plan).
* **Update**: Updated concept `project/skill-evals.md`.

## 2026-09-18
* **Update**: Linked `project/knowledge-bundle.md` to `project/docs-pipeline.md` (What the separated docs site is: hand-written Markdown under docs/, with no copy of this bundle's content.).
* **Update**: Linked `project/docs-pipeline.md` to `project/knowledge-bundle.md` (Why the bundle sits at the repository root and stays separate from the site.).
* **Update**: Updated concept `project/docs-pipeline.md`.
* **Update**: Updated concept `project/okf-conventions.md`.
* **Update**: Updated concept `project/okf-conventions.md`.
* **Update**: Updated concept `project/okf-conventions.md`.
* **Update**: Updated concept `project/okf-conventions.md`.
* **Update**: Updated concept `project/llmoxie-analysis.md`.
* **Update**: Updated concept `project/knowledge-bundle.md`.
* **Update**: Updated concept `project/okf-conventions.md`.
* **Update**: Updated concept `project/llmoxie-analysis.md`.
* **Update**: Updated concept `project/knowledge-bundle.md`.
* **Update**: Linked `project/knowledge-bundle.md` to `project/docs-pipeline.md` (How the separated docs site is kept in step with this bundle without a second hand-maintained copy).
* **Creation**: Documented concept `project/docs-pipeline.md` (The Docs Site Is Generated From This Bundle).
* **Update**: Linked `project/llmoxie-analysis.md` to `project/cross-viss-demo.md` (Why this repository's scaffolding is further along than its analysis code, and which audience each part serves).
* **Creation**: Documented concept `project/cross-viss-demo.md` (Cross-VISS Demo and the Repository's Two Purposes).
* **Creation**: Documented concept `project/current-state.md` (What Exists and What Is Only Designed).
* **Creation**: Documented concept `project/skill-evals.md` (Skill Evaluation with Inspect and Harbor).
* **Creation**: Documented concept `project/knowledge-bundle.md` (Where Project Knowledge Lives).
* **Creation**: Documented concept `project/okf-conventions.md` (OKF Bundle Conventions).
* **Creation**: Documented concept `upstream/session-reconstruction.md` (group_sessions.py — Reconstructing Conversations).
* **Creation**: Documented concept `upstream/reader-flattening.md` (reader.py — Flattening Requests to Message Blocks).
* **Creation**: Documented concept `upstream/model-name-normalization.md` (Model Name Normalization).
* **Creation**: Documented concept `project/llmoxie-analysis.md` (LLMoxie Analysis).
* **Creation**: Documented concept `project/epic-and-issues.md` (Epic #1 and the Implementation Issues).
* **Creation**: Documented concept `platform/logging-paths.md` (The Two Logging Paths).
* **Creation**: Documented concept `platform/llmoxie-timeline.md` (LLMoxie Development Timeline).
* **Creation**: Documented concept `platform/llmoxie-platform.md` (LLMoxie Platform).
* **Creation**: Documented concept `platform/litellm-spend-logs.md` (LiteLLM Spend Logs and infra extract).
* **Creation**: Documented concept `platform/adls-logger.md` (AdlLogger — Azure Data Lake Logging).
* **Creation**: Documented concept `pipeline/storage-layout.md` (Storage Layout and Parquet I/O).
* **Creation**: Documented concept `pipeline/source-adapters.md` (Source Adapters and Auto Detection).
* **Creation**: Documented concept `pipeline/query-layer.md` (Query Layer: DuckDB and Synapse Serverless).
* **Creation**: Documented concept `pipeline/pipeline-cli.md` (The llmaven data pipeline run CLI).
* **Creation**: Documented concept `pipeline/pipeline-architecture.md` (Pipeline Architecture).
* **Creation**: Documented concept `pipeline/idempotency-design.md` (Idempotency: Manifest and Partition Overwrite).
* **Creation**: Documented concept `pipeline/container-apps-job.md` (Scheduled Execution on Azure Container Apps).
* **Creation**: Documented concept `pipeline/analytics-schema.md` (Analytics Schema — Four Tables).
* **Creation**: Documented concept `datasets/pii-handling.md` (Handling This Data Without Touching PII).
* **Creation**: Documented concept `datasets/jan-mar-2026-findings.md` (What Profiling the Jan–Mar 2026 Extract Proved).
* **Creation**: Documented concept `datasets/jan-mar-2026-extract.md` (Jan–Mar 2026 Spend-Log Extract).
* **Creation**: Documented concept `caveats/responses-api-gap.md` (Caveat: The Responses API Output Gap).
* **Creation**: Documented concept `caveats/end-user-parsing.md` (Caveat: end_user Parsing Fragility).
* **Creation**: Documented concept `caveats/dedup-vs-last-request.md` (Caveat: last_request_per_session vs deduplicate_messages).
* **Creation**: Documented concept `caveats/cost-token-double-counting.md` (Caveat: Cost and Token Double-Counting).
* **Creation**: Initialized OKF v0.2 knowledge bundle.
