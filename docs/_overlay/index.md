# LLMoxie Analysis Knowledge Base

This is the knowledge base for **llmoxie-analysis** — the package that turns raw
[LLMoxie](https://github.com/uw-ssec/llmoxie) gateway request logs into a
queryable Parquet warehouse of sessions, messages, tool calls, and tool
definitions.

It records what the code cannot tell you on its own: why the pipeline is shaped
the way it is, what the upstream prototypes actually do, and — most importantly
— the properties of this data that will quietly mislead anyone who queries it
without knowing them.

!!! warning "Read the caveats before trusting a number"

    Session identity comes from parsing a free-form client string; agentic
    clients resend whole conversations so per-request costs cannot simply be
    summed; and one API path's replies are missing from sessions entirely. See
    [Caveats](./caveats/index.md).

## Sections

- [Project](./project/index.md) - what this project is, how the work is planned,
  how these docs are maintained
- [Platform](./platform/index.md) - LLMoxie itself, its two logging paths, and
  how it got here
- [Upstream](./upstream/index.md) - inherited prototype code this project must
  absorb, fix, or preserve
- [Caveats](./caveats/index.md) - data properties that will mislead you if you
  don't know them
- [Datasets](./datasets/index.md) - the actual extracts, what profiling them
  proved, and how to handle them without touching PII
- [Pipeline](./pipeline/index.md) - the four-stage design, its storage layout,
  idempotency, CLI, and query layer

## Start here

| If you want to…                            | Read                                                                                                                                               |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Understand the project in one page         | [LLMoxie Analysis](project/llmoxie-analysis.md)                                                                                                    |
| Know what is being built and in what order | [Epic #1 and the Implementation Issues](project/epic-and-issues.md)                                                                                |
| Query the output                           | [Analytics Schema — Four Tables](pipeline/analytics-schema.md) then [Query Layer: DuckDB and Synapse Serverless](pipeline/query-layer.md)          |
| Run the pipeline                           | [The llmaven data pipeline run CLI](pipeline/pipeline-cli.md)                                                                                      |
| Change how sessions are reconstructed      | [group_sessions.py — Reconstructing Conversations](upstream/session-reconstruction.md)                                                             |
| Touch the raw log data                     | [Handling This Data Without Touching PII](datasets/pii-handling.md) first, then [Jan–Mar 2026 Spend-Log Extract](datasets/jan-mar-2026-extract.md) |
| Add to these docs                          | [Contributing](https://github.com/uw-ssec/llmoxie-analysis/blob/main/CONTRIBUTING.md)                                                              |

## How these docs are organised

Each page states one thing — a decision, a property of the data, or the design
of one pipeline stage — and links to related pages with a sentence explaining
how they relate. The four **Caveats** pages are the ones to read before trusting
any number that comes out of this pipeline.

Pages are plain Markdown rendered by MkDocs Material. To preview the site:

```bash
pixi run docs-serve    # live reload at http://127.0.0.1:8000
pixi run docs-build    # build, failing on any broken reference
```

!!! info "Agents read a different copy"

    The same knowledge is also maintained as an [OKF Agent
    Memory](https://github.com/uw-ssec/okf-agent-memory) bundle under
    `knowledge/` in the repository root, which is what coding agents query
    through `okf search`. The two are kept in step by hand today; see the
    repository discussions for work on merging them into a single source.
