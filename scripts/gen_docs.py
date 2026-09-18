"""Generate the MkDocs source tree from the OKF knowledge bundle.

``knowledge/`` is the only hand-edited copy of this project's knowledge. It is
an OKF v0.2 bundle: typed frontmatter, ``[[folder/concept]]`` wikilinks, and
folder ``index.md`` listings that ``okf validate --drift`` keeps honest.

None of that renders. This script transforms the bundle into plain Markdown a
documentation engine can build, writing the result to a generated directory
that is never edited by hand:

    knowledge/  +  docs/_overlay/   ->   site_docs/

The transformations, each undoing one OKF-ism:

* frontmatter is dropped, but its ``title`` is re-emitted as an ``H1`` first --
  okf-authored concepts carry no heading, so the title would otherwise be lost
  and MkDocs would fall back to prettifying the filename
* ``[[folder/concept]]`` becomes a relative Markdown link, so MkDocs resolves
  and validates it like any other link
* ``sources:`` is promoted from invisible frontmatter into a ``## Sources``
  section, so provenance survives into the rendered page
* ``log.md`` is skipped -- it is okf's bookkeeping, not a page
* each folder's generated listing gets the overlay's intro paragraph

Wikilink resolution follows the rules the OKF spec uses: ``[[folder/name]]``
labelled with the target's title, ``[[folder/name|Label]]`` labelled
explicitly, and a bare ``[[name]]`` only when that basename is unique across
the bundle. Wikilinks inside fenced blocks and inline code spans are left
alone, so a literal ``[["request_id"]]`` in a sample payload survives.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import sys
from pathlib import Path

import yaml

BUNDLE = Path("knowledge")
OVERLAY = Path("docs/_overlay")
OUT = Path("site_docs")

# Reserved bundle files that are navigation or bookkeeping, not concepts.
SKIP_NAMES = {"log.md"}

H1_RE = re.compile(r"(?m)^#\s+(.+)$")

WIKILINK_RE = re.compile(r"\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]+?))?\]\]")

# Fenced code blocks (``` or ~~~, any info string) and inline code spans.
# Matched so their contents can be passed through untouched.
SKIP_RE = re.compile(
    r"(?m)^[ \t]*(?P<fence>```+|~~~+)(?s:.*?)^[ \t]*(?P=fence)[ \t]*$"
    r"|(?P<code>`+)[^\n]*?(?P=code)"
)


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Return (frontmatter, body). Pages without frontmatter yield an empty dict."""
    if not text.startswith("---"):
        return {}, text
    _, raw, body = text.split("---", 2)
    return yaml.safe_load(raw) or {}, body


def page_title(meta: dict[str, object], body: str, fallback: str) -> str:
    """Prefer the frontmatter title, then the body H1, then the concept ID."""
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    match = H1_RE.search(body)
    return match.group(1).strip() if match else fallback


def build_index(bundle: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Map concept ID -> title, and bare basename -> the IDs that share it."""
    titles: dict[str, str] = {}
    basenames: dict[str, list[str]] = {}
    for path in sorted(bundle.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        cid = path.relative_to(bundle).as_posix()[: -len(".md")]
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        titles[cid] = page_title(meta, body, cid)
        basenames.setdefault(cid.rsplit("/", 1)[-1], []).append(cid)
    return titles, basenames


def resolve_wikilinks(
    body: str,
    here: str,
    titles: dict[str, str],
    basenames: dict[str, list[str]],
    unresolved: list[tuple[str, str]],
) -> str:
    """Rewrite wikilinks to relative Markdown links, skipping code."""

    def replace(match: re.Match[str]) -> str:
        target, label = match.group(1).strip(), match.group(2)
        cid = target if target in titles else None
        if cid is None and "/" not in target and len(basenames.get(target, [])) == 1:
            cid = basenames[target][0]
        if cid is None:
            unresolved.append((here, target))
            return match.group(0)
        rel = posixpath.relpath(f"{cid}.md", posixpath.dirname(here) or ".")
        return f"[{label or titles[cid]}]({rel})"

    parts: list[str] = []
    last = 0
    for skip in SKIP_RE.finditer(body):
        parts.append(WIKILINK_RE.sub(replace, body[last : skip.start()]))
        parts.append(skip.group(0))
        last = skip.end()
    parts.append(WIKILINK_RE.sub(replace, body[last:]))
    return "".join(parts)


def demote_stray_h1(body: str) -> str:
    """Demote any ``H1`` below the opening heading to ``H2``.

    A page has exactly one top-level heading. ``okf relate`` writes its
    ``Related Concepts`` heading at ``H1``, which would give a rendered page a
    second title and a confused table of contents, so anything after the first
    line is pushed down a level. Code segments are left alone.
    """
    parts: list[str] = []
    last = 0
    for skip in SKIP_RE.finditer(body):
        parts.append(body[last : skip.start()])
        parts.append(skip.group(0))
        last = skip.end()
    parts.append(body[last:])

    for index, part in enumerate(parts):
        if index % 2:  # odd indices are the untouched code segments
            continue
        lines = part.split("\n")
        for line_no, line in enumerate(lines):
            if line.startswith("# ") and not (index == 0 and line_no == 0):
                lines[line_no] = "#" + line
        parts[index] = "\n".join(lines)
    return "".join(parts)


def render_sources(meta: dict[str, object]) -> str:
    """Turn the frontmatter sources list into a visible section."""
    sources = meta.get("sources")
    if not isinstance(sources, list) or not sources:
        return ""
    lines = []
    for entry in sources:
        resource = entry.get("resource") if isinstance(entry, dict) else entry
        text = str(resource)
        lines.append(f"- <{text}>" if text.startswith("http") else f"- {text}")
    return "\n\n## Sources\n\n" + "\n".join(lines) + "\n"


def main() -> int:
    """Regenerate the site source tree. Returns a process exit code."""
    if not BUNDLE.is_dir():
        print(f"error: no bundle at {BUNDLE}/", file=sys.stderr)
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    titles, basenames = build_index(BUNDLE)
    unresolved: list[tuple[str, str]] = []
    written = 0

    for path in sorted(BUNDLE.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        rel = path.relative_to(BUNDLE).as_posix()
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        body = resolve_wikilinks(body.strip(), rel, titles, basenames, unresolved)

        # OKF keeps the title in frontmatter and okf-authored concepts carry no
        # H1. Dropping the frontmatter would therefore lose the title entirely,
        # leaving MkDocs to prettify the filename ("Okf conventions"). Restore
        # it as an H1, which is where a renderer expects to find it.
        if not body.lstrip().startswith("# "):
            body = f"# {page_title(meta, body, rel)}\n\n{body}"
        body = demote_stray_h1(body)

        # A folder index is okf's generated listing; give it the overlay intro.
        if path.name == "index.md" and path.parent != BUNDLE:
            intro = OVERLAY / path.parent.name / "_intro.md"
            if intro.is_file():
                head, _, rest = body.partition("\n")
                body = f"{head}\n\n{intro.read_text(encoding='utf-8').strip()}\n{rest}"

        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body.strip() + render_sources(meta) + "\n", encoding="utf-8")
        written += 1

    # Everything in the overlay is copied verbatim, whatever its type --
    # handwritten pages, images, stylesheets, downloads. Overlay files win over
    # anything generated at the same path, which is how a concept page can be
    # overridden by hand. The one exception is the ``_`` prefix, reserved for
    # fragments this script splices into generated pages rather than publishes.
    overlaid = 0
    for path in sorted(OVERLAY.rglob("*")):
        if path.is_dir() or path.name.startswith("_"):
            continue
        dest = OUT / path.relative_to(OVERLAY)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        overlaid += 1

    print(
        f"generated {written} page(s) from {BUNDLE}/, {overlaid} from overlay -> {OUT}/"
    )
    if unresolved:
        for where, target in unresolved:
            print(
                f"error: unresolved wikilink [[{target}]] in {where}", file=sys.stderr
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
