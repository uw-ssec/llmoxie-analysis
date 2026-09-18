"""MkDocs hook that builds the navigation from the generated page tree.

An explicit ``nav:`` in ``mkdocs.yml`` is a second list of every concept, kept
in step by hand. It drifts the moment someone adds a concept to the bundle and
forgets the config -- the exact failure this pipeline exists to remove.

So the nav is derived instead. Sections appear in ``SECTION_ORDER``, which is
editorial and worth choosing; pages within a section are ordered by title,
which is not. Each section's ``index.md`` leads, and pairs with the theme's
``navigation.indexes`` feature to become that section's landing page.

Entries are bare paths, so MkDocs takes each label from the page's own ``H1``
and no title is written down twice.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Broad to specific: what the project is, the system it observes, the code it
# inherits, the traps in the data, the thing being built, the data itself.
SECTION_ORDER = [
    ("project", "Project"),
    ("platform", "Platform"),
    ("upstream", "Upstream"),
    ("caveats", "Caveats"),
    ("pipeline", "Pipeline"),
    ("datasets", "Datasets"),
]

H1_RE = re.compile(r"(?m)^#\s+(.+)$")


def _title(path: Path) -> str:
    match = H1_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else path.stem


def _entries(directory: Path, docs_dir: Path) -> list[Any]:
    """Nav entries for one directory: its index, then pages, then subsections.

    Recurses, so a handwritten page nested at any depth still reaches the nav.
    """
    entries: list[Any] = []
    index = directory / "index.md"
    if index.is_file():
        entries.append(index.relative_to(docs_dir).as_posix())

    pages = (p for p in directory.glob("*.md") if p.name != "index.md")
    entries += [p.relative_to(docs_dir).as_posix() for p in sorted(pages, key=_title)]

    for sub in sorted(p for p in directory.iterdir() if p.is_dir()):
        child = _entries(sub, docs_dir)
        if child:
            entries.append(
                {sub.name.replace("-", " ").replace("_", " ").title(): child}
            )
    return entries


def on_config(config: Any) -> Any:
    """Replace any configured nav with one derived from the page tree."""
    docs_dir = Path(config["docs_dir"])
    nav: list[Any] = []

    root_index = docs_dir / "index.md"
    if root_index.is_file():
        nav.append("index.md")

    ordered = [f for f, _ in SECTION_ORDER]
    labels = dict(SECTION_ORDER)

    # Handwritten pages living at the root, after the home page.
    root_pages = (p for p in docs_dir.glob("*.md") if p.name != "index.md")
    nav += [p.name for p in sorted(root_pages, key=_title)]

    # Listed sections first, in editorial order; then anything else, so a
    # directory nobody thought to list is still reachable rather than dropped.
    directories = [p for p in docs_dir.iterdir() if p.is_dir()]
    directories.sort(
        key=lambda p: (
            ordered.index(p.name) if p.name in ordered else len(ordered),
            p.name,
        )
    )
    for directory in directories:
        entries = _entries(directory, docs_dir)
        if entries:
            label = labels.get(directory.name, directory.name.replace("-", " ").title())
            nav.append({label: entries})

    config["nav"] = nav
    return config
