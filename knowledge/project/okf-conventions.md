---
type: Reference
title: OKF Bundle Conventions
description: "The folder layout, frontmatter contract, producer-gate traps, and validation gates this knowledge bundle is maintained under."
tags: [okf, conventions, frontmatter, validation, documentation]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-18T22:57:56Z" }
code_refs: [.claude/skills/okf-memory/SKILL.md, .agents/skills/okf-memory/SKILL.md]
sources:
  - resource: "https://github.com/uw-ssec/llmoxie-analysis/issues/1"
  - resource: llmoxie-analysis .claude/skills/okf-memory/SKILL.md
  - resource: okf 0.4.0 producer-gate behaviour observed in this repository
---

The bundle is a set of Markdown files under version control, read and written
through the `okf` CLI. These are the conventions that keep it valid, and the
traps that are not guessable from the tool's help output.

## Folder layout

Areas are topical, not type-based. `okf create` does not constrain the area
segment of a concept ID, so the folder carries the subject and the `type:`
field carries the kind.

| Folder      | Holds                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| `project/`  | What this project is, how it is planned, how it is documented              |
| `platform/` | LLMoxie itself — the system that produces the data                         |
| `upstream/` | Prototype code inherited from LLMoxie that this project must fix or absorb |
| `caveats/`  | Properties of the data that will mislead anyone who does not know them     |
| `pipeline/` | The design of the thing being built                                        |
| `datasets/` | Specific extracts and the rules for handling them                          |

Drop a prefix the folder already carries: `caveats/end-user-parsing`, not
`caveats/caveat-end-user-parsing`. Keep one where the bare name would be too
generic to stand alone in a search result — `pipeline/pipeline-architecture`
and `pipeline/pipeline-cli` are both correct, because "architecture" and "cli"
are not. Basenames must be unique bundle-wide, because bare-basename wikilink
targets key on them.

Types in use: `Project`, `Entity`, `Fact`, `Decision`, `Process`, `Reference`.

## The description trap

`description:` must be a single line. okf's frontmatter parser reads scalars
positionally and takes only what follows the key on the same line, so a folded
multi-line YAML block — which is still valid YAML, and which Prettier produces
automatically from any long line — parses as **empty**.

Nothing catches this. `okf validate --strict` reports the bundle conformant
while every description is null, and the emptiness is only visible through
`okf show --json` or as blank lines in `okf search` output. Since descriptions
are what search prints for relevance triage, a bundle in this state is
effectively unreadable to an agent while appearing healthy.

`.pre-commit-config.yaml` therefore excludes `^knowledge/` from Prettier. That
exclusion is path-scoped: a bundle kept anywhere else gets folded and silently
emptied. See [[project/knowledge-bundle]] for the case where this happened.

## Producer gate traps

`generated:` and `sources:` are checked by the producer gate, a separate pass
from conformance — a bundle can be reported conformant while the gate fails.

Every `sources:` entry must be a mapping with a `resource:` key. A bare list of
URLs parses into entries with an empty resource and the gate reports
`sources[N] has no 'resource'`. Flow style is worse than wrong: the parser only
reads block-style lines, so `sources: ["..."]` is silently discarded and the
concept ends up with zero recorded sources while the gate stays quiet.

```yaml
sources:
  - resource: https://github.com/uw-ssec/llmoxie-analysis/issues/1
  - resource: reference/llmoxie/src/llmaven/data/reader.py
```

Cite upstream LLMoxie code by its path in the `reference/llmoxie` submodule,
not by the GitHub repo name, so the source resolves in the checkout at the
pinned commit. Commits and history are cited as `reference/llmoxie commit <sha>`.

When a source names a file, list the bare path under `code_refs:` as well.
`sources:` is not searched, so `code_refs` is what makes
`okf search --for-path <file>` return the concept, and `validate --drift` warns
when a listed path stops existing. Matching is literal and does not follow
symlinks: `.claude/skills` links to `.agents/skills`, so a file reachable both
ways needs both paths listed.

`generated.by` must be an actor — either `scheme:something` or
`namespace/name`. A bare `agent` or `human` is not, and neither is a
three-segment path. `generated.at` is an ISO 8601 timestamp, not a date. Pass
`--actor` on every write, using the same token as the `Assisted-by` trailer in
`AI_POLICY.md`.

Titles containing a colon must be quoted, or YAML parses them as a mapping.

## Relationships are inline

OKF has no relationship file. Relationships live at the bottom of each concept
under a `## Related Concepts` heading, as bullets whose link is a real relative
path and whose trailing sentence says *how* the two relate — a bare link says
only that they are related, which is the part an agent traversing the graph
already knows. Retain the heading so `okf relate` appends in the right place
rather than starting a second block.

!!! warning "`okf relate` appends a second block instead of merging"

    Despite the convention above, `okf relate` in 0.4.0 does not append a
    bullet to an existing `## Related Concepts` section. It writes a whole new
    `# Related Concepts` block at the end of the concept, at `H1`. The result
    is a concept with two Related Concepts sections and two top-level
    headings — invalid structure, a duplicated table-of-contents entry, and a
    rendered page with two titles.

    Nothing flags it: `okf validate --strict --drift` reports the bundle
    conformant. After every `relate`, open the concept, merge the new bullet
    into the existing section, and delete the block okf added.

## Gates

`okf validate --strict --drift` must report 0 errors, 0 warnings, and no
producer-gate failure. `--strict` promotes connectivity warnings to errors, so
a concept nothing links to fails rather than quietly accumulating. `--drift`
catches index-vs-frontmatter divergence: a concept's `description` must match
its folder `index.md` bullet verbatim, which is the mechanism that stops index
pages from slowly becoming fiction.

`pixi run verify` runs this command as its `okf-validate` step, but the exit
code is weaker than the bar above. okf exits non-zero only for errors and
producer-gate findings — a broken link, a `..` in `code_refs`, a source with no
`resource`. Warnings print and exit 0, including description drift and a
`code_refs` path that no longer exists, so a green `verify` does not prove
`0 warning(s)`; read the summary line. Warnings are left non-fatal on purpose:
most `code_refs` point into the `reference/` submodules, and a checkout without
them would otherwise fail the gate.

Run the bundle's binary, not whatever is on `PATH`. Multiple okf versions
coexist easily on one machine and they do not agree.

## What does not belong here

No credentials, ever. This bundle records the *name* of an environment variable
and where its value is expected to live, never the value. That covers
`AZURE_STORAGE_CONNECTION_STRING`, `LITELLM_MASTER_KEY`, the SAS token in
`.env.analytics` ([[pipeline/query-layer]]), and anything added later.

Also out of scope: anything the repository already states. Code structure, git
history, and `AGENTS.md` rules are not copied here. This bundle records what is
*not* derivable from reading the code — design rationale, data caveats, and the
history of why the system looks the way it does.

## Related Concepts

- [Where Project Knowledge Lives](knowledge-bundle.md): The decision that put
  this bundle at the repository root and the layout it replaced.
- [LLMoxie Analysis](llmoxie-analysis.md): The project whose knowledge these
  conventions govern.
- [Query Layer: DuckDB and Synapse Serverless](../pipeline/query-layer.md):
  Where the credential-handling rule stated here has its most direct
  consequence.
