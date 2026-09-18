---
type: Process
title: Model Name Normalization
description: The ordered rewrite rules that collapse provider-prefixed model identifiers into a single canonical family-and-version label for grouping.
tags: [models, normalization, bedrock, grouping]
sources:
  - resource: uw-ssec/llmoxie data/reader.py, normalize_model_name()
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

The same underlying model reaches the gateway under many different strings
depending on which provider routed it, which SDK the client used, and whether a
CLI flag supplied it. Grouping spend or usage "by model" without normalizing
first produces a long tail of near-duplicate categories.

`normalize_model_name(model)` in [[upstream/reader-flattening]] resolves this.
Issue #4 of [[project/epic-and-issues]] requires the pipeline to reuse it rather
than reimplement it, so that [[pipeline/analytics-schema]]'s `model` column is
consistent with existing upstream analyses.

## The rules, in order

Order matters — several rules would mis-fire if applied earlier or later.

1. **CLI flag form.** `--model X` becomes `claude-X`.
2. **Provider prefixes**, stripped in this sequence: `^bedrock/us\.anthropic\.`
   → `^bedrock/anthropic\.` → `^us\.anthropic\.` → `^anthropic/` →
   `^perplexity/` → `^bedrock/` → `^bedrock-`. The longest, most specific
   prefixes are tried first so that `bedrock/us.anthropic.` is not partially
   consumed by the bare `bedrock/` rule.
3. **Family reordering.** `^(claude)-(\d+)-(\d+)-(haiku|sonnet|opus)` is
   rewritten to `\1-\4-\2.\3` — moving the family name ahead of the version and
   joining the version parts with a dot.
4. **Date suffix.** `-20\d{6}` is removed.
5. **Version suffix.** `-v\d+(?::\d+)?` is removed.
6. **Residual version pairs.** A trailing `-(\d+)-(\d+)` becomes `-\1.\2`.

## Worked example

```
bedrock/anthropic.claude-4-6-sonnet-20250929-v1:0
  → claude-4-6-sonnet-20250929-v1:0      (rule 2)
  → claude-sonnet-4.6-20250929-v1:0      (rule 3)
  → claude-sonnet-4.6-v1:0               (rule 4)
  → claude-sonnet-4.6                    (rule 5)
```

## Why this matters analytically

The [[platform/llmoxie-platform]] gateway fronts several inference backends, and
the same Claude model is reachable through more than one of them. Without
normalization, a cost-by-model report splits a single model across several rows,
each undercounted, and a naive "most-used model" answer is simply wrong.

!!! note "Normalization is lossy by design"

    Provider routing and exact snapshot dates are discarded. If an analysis
    needs to distinguish Bedrock traffic from direct-API traffic, or to pin an
    exact model snapshot, it must retain the raw string alongside the
    normalized one — normalization answers "which model family", not "which
    deployment".

## Related Concepts

- [reader.py — Flattening Requests to Message Blocks](reader-flattening.md): The
  normalization function lives inside the reader module.
- [Analytics Schema — Four Tables](../pipeline/analytics-schema.md): The
  normalized label is what lands in the `model` column of every table.
