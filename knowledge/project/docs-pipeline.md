---
type: Architecture
title: The Docs Site Is Hand-Written and Separate From This Bundle
description: "The MkDocs site is plain Markdown under docs/ with an explicit nav in mkdocs.yml; it has no connection to knowledge/, and the earlier generator (scripts/gen_docs.py, hooks/nav.py) was removed."
tags: [docs, mkdocs, site, tooling]
generated: { by: "claude-code:claude-fable-5-1", at: "2026-09-18T23:22:00Z" }
code_refs: [mkdocs.yml, "docs/**"]
sources:
  - resource: llmoxie-analysis mkdocs.yml
  - resource: llmoxie-analysis commit 408fe21 (the removed generator)
  - resource: "https://github.com/uw-ssec/llmoxie-analysis/discussions/26"
---

The documentation site is an ordinary hand-written MkDocs Material site. Pages
are plain Markdown under `docs/`, the navigation is an explicit `nav:` list in
`mkdocs.yml`, and `pixi run docs-build` runs `mkdocs build --strict` with no
generation step in front of it. `edit_uri` points at `docs/`.

The site and this bundle are not connected. Nothing in `knowledge/` is rendered
into the site, and nothing under `docs/` is read by okf. The site is for human
readers of the project; the bundle is project memory for agents, reached through
`okf search`.

## Guarantees

- `mkdocs.yml` sets `validation.nav.omitted_files: warn` and the build runs
  `--strict`, so a page that exists under `docs/` but is missing from `nav:`
  fails the build, as does a broken link.
- `site/` is build output and is gitignored.

## Superseded

The site was briefly generated from this bundle (PR #29, 2026-09-18):

```
knowledge/  +  docs/_overlay/   --[ scripts/gen_docs.py ]-->  site_docs/  --[ mkdocs ]-->  site/
```

`scripts/gen_docs.py` dropped frontmatter, re-emitted `title` as an `H1`,
resolved `[[folder/concept]]` wikilinks to relative links, promoted `sources:`
into a visible section, and spliced `_intro.md` fragments from `docs/_overlay/`
into folder listings. `hooks/nav.py` derived the navigation from the generated
tree. The motivation was that a hand-synchronised parallel copy of the bundle
went five concepts and one relationship stale within a day.

The project owner removed the generator, the nav hook, the overlay, and their
tests the same day, in favour of a regular starter docs site with no connection
to `knowledge/`. The drift problem does not return, because the site no longer
carries a copy of the bundle's content at all.

## Related Concepts

- [Where Project Knowledge Lives](knowledge-bundle.md): Why the bundle sits at
  the repository root and stays separate from the site.
