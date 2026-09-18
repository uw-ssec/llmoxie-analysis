# Datasets
* [Jan–Mar 2026 Spend-Log Extract](jan-mar-2026-extract.md) - A 1.0 GB local extract of 90 daily LiteLLM spend-log files covering 2026-01-02 through 2026-03-24, holding 13,291 requests in a rectangular 31-column shape.
* [What Profiling the Jan–Mar 2026 Extract Proved](jan-mar-2026-findings.md) - Structure-only profiling confirmed four documented caveats with real numbers, and surfaced three new ones — an unreliable cache flag, a useless native session_id, and an 11% failure rate that must be filtered before any metric.
* [Handling This Data Without Touching PII](pii-handling.md) - The working rule for analyzing gateway logs — name the sensitive fields, never read their values into a transcript or a document, and profile with counts rather than samples.
