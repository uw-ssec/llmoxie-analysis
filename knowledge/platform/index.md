# Platform
* [AdlLogger — Azure Data Lake Logging](adls-logger.md) - The LiteLLM callback that writes one untruncated JSON blob per request to ADLS Gen2, its record envelope, its path convention, and its silent failure mode.
* [LiteLLM Spend Logs and infra extract](litellm-spend-logs.md) - The PostgreSQL-backed spend-log path, the REST endpoint and the database-backup export that read it, and the llmaven infra extract command that packages a date range into a zip.
* [LLMoxie Platform](llmoxie-platform.md) - The UW SSEC open-source AI control plane whose LiteLLM gateway produces the request logs analyzed here, built in three layers under NSF NAIRR award 240292.
* [LLMoxie Development Timeline](llmoxie-timeline.md) - How the upstream repository evolved across 99 commits from a Rubin-era RAG prototype into a LiteLLM control plane with data-lake logging and session grouping.
* [The Two Logging Paths](logging-paths.md) - LLMoxie records every request twice over — to Azure Data Lake as untruncated JSON and to LiteLLM's PostgreSQL spend logs — and the two differ in fidelity, coverage, and era.
