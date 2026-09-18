---
type: Architecture
title: The Docs Site Is Generated From This Bundle
description: "scripts/gen_docs.py transforms knowledge/ plus a small hand-written overlay into the MkDocs source tree, so the site cannot drift from the bundle."
tags: [docs, mkdocs, generation, pipeline, tooling]
sources:
  - resource: llmoxie-analysis scripts/gen_docs.py
  - resource: llmoxie-analysis hooks/nav.py
  - resource: https://github.com/uw-ssec/llmoxie-analysis/discussions/26
generated: { by: "claude-code:claude-opus-5", at: "2026-09-18T18:08:34Z" }
---

This bundle is the only hand-edited copy of the project's knowledge. The
documentation site is generated from it, so the two cannot disagree.

```
knowledge/  +  docs/_overlay/   --[ scripts/gen_docs.py ]-->  site_docs/  --[ mkdocs ]-->  site/
```

`site_docs/` and `site/` are gitignored and rebuilt by `pixi run docs-build`,
which runs the generator first through a `depends-on`. Nobody edits them.

## What the generator undoes

Each transformation removes one thing that is meaningful to okf and meaningless
to a renderer: frontmatter is dropped, since the page title comes from the body
`H1`; `[[folder/concept]]` wikilinks become relative Markdown links so MkDocs
resolves and validates them; `sources:` is promoted out of invisible frontmatter
into a `## Sources` section; `log.md` is skipped as bookkeeping; and each folder
listing gains its intro paragraph from the overlay.

## Why generate rather than maintain two copies

The two were briefly kept in parallel by hand. Within a single day the site was
missing five concepts and one relationship — a fifth of the bundle — with no
signal that anything was wrong. Hand-synchronisation of two directories with the
same content does not survive contact with ordinary work.

Generation also means humans edit OKF-format files through `okf create` and
`okf update` rather than editing rendered pages. That friction is the deliberate
cost. `edit_uri` points at `knowledge/`, so the site's "Edit this page" link
lands on the real source.

## Guarantees

- Nothing in the overlay is dropped. Files of any type, at any depth, are copied
  verbatim, and an overlay file overrides a generated page at the same path.
- Nothing is silently excluded from the site. `mkdocs.yml` sets
  `validation.nav.omitted_files: warn` and the build runs `--strict`, so a page
  that never reaches the navigation fails the build.
- The navigation is derived from the generated tree by `hooks/nav.py`, so adding
  a concept to the bundle puts it in the site with no second list to update.

## The `_` prefix

Files starting with `_` are fragments, not pages. `<section>/_intro.md` is
spliced under a section heading; `_README.md` documents the overlay. They are
never published.

## Related Concepts

- [Where Project Knowledge Lives](knowledge-bundle.md): Why the bundle sits at
  the repository root and stays separate from the site.
- [OKF Bundle Conventions](okf-conventions.md): The format the generator reads.
