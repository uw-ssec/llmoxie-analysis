---
type: Process
title: Handling This Data Without Touching PII
description: "The working rule for analyzing gateway logs — name the sensitive fields, never read their values into a transcript or a document, and profile with counts rather than samples."
tags: [pii, privacy, process, safety, methodology]
sources:
  - resource: structure-only profile of the Jan-Mar 2026 extract
  - resource: uw-ssec/llmoxie LiteLLM Presidio PII masking config
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T15:01:08Z" }
---

Gateway logs are the prompts researchers typed. Treating them as an ordinary
data file is the mistake this concept exists to prevent.

[[datasets/jan-mar-2026-extract]] was profiled in full without a single record
value entering a transcript. The method is repeatable and belongs to the project
rather than to that one extract.

!!! danger "Presidio masking does not protect this extract"

    [[platform/llmoxie-platform]] runs Presidio masking at the gateway, which
    covers what reaches the *provider*. It does not sanitize the log record.
    The stored `proxy_server_request` is the request as received. Assume every
    body field is unmasked.

## The sensitive surface

These fields may carry personal or identifying content. Never print, sample,
quote, or paste their **values** — into a terminal, a transcript, a commit
message, an issue, or a documentation page.

| Field                             | What it holds                            |
| --------------------------------- | ---------------------------------------- |
| `proxy_server_request.messages`   | Full prompt bodies                       |
| `proxy_server_request.system`     | System prompts, often project-specific   |
| `proxy_server_request.tools`      | Tool schemas, may name internal systems  |
| `response.choices`                | Model replies                            |
| `messages`                        | Prompt bodies when populated             |
| `end_user`                        | Device, account, and session identifiers |
| `user`                            | User identifier                          |
| `api_key`                         | Hashed key, still a secret               |
| `requester_ip_address`            | Network address                          |
| `metadata.*`                      | Key aliases, team aliases, user ids      |
| `error_information.error_message` | Often echoes the request                 |
| `error_information.traceback`     | Often echoes the request                 |

Aliases deserve particular care. `user_api_key_alias` and
`user_api_key_team_alias` are human-chosen labels, which in practice means they
are frequently people's names.

## What is safe to work with

The complement is generous enough to do real profiling:

- **Field names** — key inventories, presence counts, null counts.
- **Types** — whether a field is an object, array, string, or number.
- **Cardinality** — how many distinct values a column has, never which ones.
- **Closed vocabularies** — `status`, `call_type`, `custom_llm_provider`,
  `cache_hit`, `error_class`, `error_code`. These are enum-like and produced by
  the gateway, not by a user.
- **Model identifiers** — `model`, `model_group`, `model_id`.
- **Numbers** — token counts, spend, timestamps, and any aggregate over them.
- **Shape of a sensitive value, without the value** — length, or whether it
  contains a given delimiter. This is how `end_user` was characterized in
  [[datasets/jan-mar-2026-findings]] without reading one.

## The working rules

1. **Aggregate, never sample.** `count`, `sum`, `min`, `max`, and `unique` are
   safe. `head`, `first`, and printing a record are not. There is no such thing
   as "just one row to see the shape" — use `keys` and `type` instead.
2. **Select the field, then reduce it in the same command.** Never pipe a
   sensitive field to a pager or a file you will later open.
3. **Guard null before reducing.** `select(.field != null) | .field | keys[]`
   rather than `.field | keys[]?` — the optional operator does not suppress the
   null-input error, and the resulting error spew can be large enough to be
   unreadable.
4. **Derived files inherit the classification.** A Parquet extract of
   `proxy_server_request` is as sensitive as the source. See
   [[pipeline/storage-layout]] for where such outputs belong.
5. **Never commit the data.** The extract lives outside the repository and stays
   there. Only counts and schema descriptions cross into `docs/`.
6. **Quote nothing in documentation.** Every number in this bundle is an
   aggregate. No concept contains an example prompt, an example `end_user`, or
   an example error message — by rule, not by coincidence.

## Worked pattern

Profiling a nested object's structure without reading it:

```bash
# Safe: key names and their frequencies
cat *.jsonl | jq -r 'select(.metadata != null) | .metadata | keys[]' \
  | sort | uniq -c | sort -rn

# Safe: how many records carry a body at all
cat *.jsonl | jq -r '[.proxy_server_request.messages] | length'

# NOT safe: this prints prompt content
cat *.jsonl | jq '.proxy_server_request.messages[0]'
```

The same discipline extends to the pipeline. [[pipeline/pipeline-cli]] should
never gain a command that prints a record, and any debugging aid should report
counts and field names rather than dumping rows.

## Why this is the standard, not caution

[[project/okf-conventions]] already forbids credentials in this bundle on the
grounds that documentation is permanent and public-facing. Prompt bodies are the
same category of problem with a larger blast radius: they are other people's
research, written under an expectation that a shared gateway was infrastructure
rather than an audience.

The profile behind [[datasets/jan-mar-2026-findings]] settled seven substantive
questions about the data and read zero user content doing it. The constraint
cost nothing.

## Related Concepts

- [Jan–Mar 2026 Spend-Log Extract](jan-mar-2026-extract.md): The extract this
  process was developed against and applies to.
- [What Profiling the Jan–Mar 2026 Extract Proved](jan-mar-2026-findings.md):
  Every figure there was produced under these rules.
- [OKF Bundle Conventions](../project/okf-conventions.md): The parallel rule that keeps
  credentials out of this bundle.
- [The LLMoxie Platform](../platform/llmoxie-platform.md): Presidio masking runs
  at the gateway and does not cover the stored log record.
