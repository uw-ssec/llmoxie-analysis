---
type: Decision
title: Where Project Knowledge Lives
description: "Project memory is the OKF bundle at knowledge/ in the repository root, kept separate from any documentation site, because code_refs resolve against the bundle's parent directory."
tags: [okf, knowledge-base, decision, code-refs, layout]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-18T23:22:00Z" }
sources:
  - resource: "https://github.com/uw-ssec/okf-agent-memory"
  - resource: "Project owner direction, 2026-09-17 — keep the OKF bundle and the docs site separate for now"
  - resource: "okf 0.4.0 code_refs resolution, established empirically in a scratch repository"
---

Project memory is the OKF v0.2 bundle at `knowledge/` in the repository root.
It is versioned with the code, written only through the `okf` CLI, and kept
separate from any human-facing documentation site.

## Why the repository root

`code_refs` is the frontmatter field that lets a concept declare the source
paths it governs, and it drives both `okf search --for-path <file>` and the
`--drift` check. Its resolution rule is the constraint that fixes the bundle's
location:

- Paths must be relative, and must not contain `..`. A `..` is a gate failure
  under `--strict`, not a warning.
- They resolve against the **bundle's parent directory**, with the bundle
  directory itself as a fallback. They are not resolved against the repository
  root or the git root.

With the bundle at `knowledge/`, the parent is the repository root, so
`src/llmoxie_analysis/reader.py` resolves as written. A bundle nested one level
deeper — `docs/knowledge/`, say — cannot reach `src/` at all without the
forbidden `..`, and `--drift` reports every such reference as a path that does
not exist.

This behaviour is not documented; it was established empirically against okf
0.4.0 in a scratch repository, including confirming that `git init` does not
change the resolution root.

## Why it is separate from the documentation site

An earlier arrangement made a single directory serve as both the OKF bundle
root and a MkDocs `docs_dir`, on the reasoning that a copy step between two
directories would create two truths that could silently disagree. That
reasoning still holds on its own terms, and a hybrid — a format that serves
agent retrieval and a modern rendering engine from one source — is worth
exploring later. It was set aside for now as a project direction, on the
owner's call, in favour of keeping the two concerns apart.

Two concrete problems also counted against the fused layout:

1. A bundle inside `docs/` is one level too deep for `code_refs` to reach the
   source tree, as above.
2. Prettier's exclusion is path-scoped to `^knowledge/`. A bundle anywhere else
   is formatted, its `description:` lines are folded into multi-line YAML, and
   okf reads every one of them as empty while `validate --strict` still reports
   the bundle conformant. This is not hypothetical: all 26 concepts in the
   earlier `docs/` bundle were in exactly this state when they were migrated.

## Superseded

The rejected alternative, recorded because the reasoning may be revisited if the
hybrid idea is picked up: keep one directory serving both readers, with no
generation step and no second copy, accepting a small set of file-layout
constraints as the price. What defeated it here was not the reasoning but the
two mechanical constraints above, neither of which is visible until a bundle is
already in that position.

## Related Concepts

- [OKF Bundle Conventions](okf-conventions.md): The layout, frontmatter
  contract, and gates this bundle is maintained under.
- [LLMoxie Analysis](llmoxie-analysis.md): The project whose knowledge this
  bundle captures.
- [Epic #1 and the Implementation Issues](epic-and-issues.md): Each closing
  issue is an occasion to update the concept that documents it.
- [The Docs Site Is Hand-Written and Separate From This Bundle](docs-pipeline.md):
  What the separated docs site is: hand-written Markdown under `docs/`, with no
  copy of this bundle's content.
