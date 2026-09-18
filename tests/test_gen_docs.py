"""Tests for the docs generator.

The generator's job is to undo OKF-specific formatting without damaging the
prose around it, so most of these tests are about what it must leave alone:
code spans, fenced blocks, headings that are already correct, and files it does
not own.
"""

from __future__ import annotations

from pathlib import Path

import gen_docs
import pytest

# --- frontmatter -----------------------------------------------------------


def test_split_frontmatter_separates_metadata_from_body() -> None:
    meta, body = gen_docs.split_frontmatter("---\ntitle: A Title\n---\n\nText.\n")
    assert meta == {"title": "A Title"}
    assert body.strip() == "Text."


def test_split_frontmatter_without_frontmatter_returns_whole_body() -> None:
    meta, body = gen_docs.split_frontmatter("# Heading\n\nText.\n")
    assert meta == {}
    assert body.startswith("# Heading")


def test_split_frontmatter_tolerates_empty_frontmatter() -> None:
    meta, _ = gen_docs.split_frontmatter("---\n---\n\nText.\n")
    assert meta == {}


# --- titles ----------------------------------------------------------------


def test_page_title_prefers_frontmatter_over_heading() -> None:
    assert (
        gen_docs.page_title({"title": "From Meta"}, "# From Body", "id") == "From Meta"
    )


def test_page_title_falls_back_to_heading_then_id() -> None:
    assert gen_docs.page_title({}, "# From Body\n\ntext", "id") == "From Body"
    assert gen_docs.page_title({}, "no heading here", "area/slug") == "area/slug"


def test_page_title_ignores_blank_frontmatter_title() -> None:
    assert gen_docs.page_title({"title": "   "}, "# From Body", "id") == "From Body"


# --- wikilinks -------------------------------------------------------------


@pytest.fixture
def index() -> tuple[dict[str, str], dict[str, list[str]]]:
    titles = {
        "caveats/end-user-parsing": "Caveat: end_user Parsing",
        "pipeline/query-layer": "Query Layer",
        "platform/query-layer": "Platform Query Layer",
    }
    basenames: dict[str, list[str]] = {
        "end-user-parsing": ["caveats/end-user-parsing"],
        "query-layer": ["pipeline/query-layer", "platform/query-layer"],
    }
    return titles, basenames


def test_wikilink_is_labelled_with_the_target_title(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    unresolved: list[tuple[str, str]] = []
    out = gen_docs.resolve_wikilinks(
        "See [[pipeline/query-layer]].", "caveats/a.md", titles, basenames, unresolved
    )
    assert out == "See [Query Layer](../pipeline/query-layer.md)."
    assert unresolved == []


def test_wikilink_honours_an_explicit_label(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    out = gen_docs.resolve_wikilinks(
        "See [[pipeline/query-layer|the query layer]].",
        "caveats/a.md",
        titles,
        basenames,
        [],
    )
    assert out == "See [the query layer](../pipeline/query-layer.md)."


def test_bare_basename_resolves_only_when_unique(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    unresolved: list[tuple[str, str]] = []
    out = gen_docs.resolve_wikilinks(
        "[[end-user-parsing]] and [[query-layer]]",
        "pipeline/a.md",
        titles,
        basenames,
        unresolved,
    )
    assert "[Caveat: end_user Parsing](../caveats/end-user-parsing.md)" in out
    # Ambiguous: two concepts share the basename, so it is left alone and reported.
    assert "[[query-layer]]" in out
    assert unresolved == [("pipeline/a.md", "query-layer")]


def test_unknown_target_is_reported_and_left_intact(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    unresolved: list[tuple[str, str]] = []
    out = gen_docs.resolve_wikilinks(
        "[[nope/missing]]", "a.md", titles, basenames, unresolved
    )
    assert out == "[[nope/missing]]"
    assert unresolved == [("a.md", "nope/missing")]


def test_link_from_a_root_page_has_no_parent_prefix(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    out = gen_docs.resolve_wikilinks(
        "[[pipeline/query-layer]]", "index.md", titles, basenames, []
    )
    assert out == "[Query Layer](pipeline/query-layer.md)"


def test_wikilinks_inside_code_are_left_alone(
    index: tuple[dict[str, str], dict[str, list[str]]],
) -> None:
    titles, basenames = index
    body = (
        "Prose [[pipeline/query-layer]] here.\n\n"
        "```python\n"
        'df = frame[["request_id"]]\n'
        "other = [[pipeline/query-layer]]\n"
        "```\n\n"
        "Inline `[[pipeline/query-layer]]` too.\n"
    )
    out = gen_docs.resolve_wikilinks(body, "caveats/a.md", titles, basenames, [])
    assert "Prose [Query Layer](../pipeline/query-layer.md) here." in out
    assert 'df = frame[["request_id"]]' in out
    assert "other = [[pipeline/query-layer]]" in out
    assert "Inline `[[pipeline/query-layer]]` too." in out


# --- headings --------------------------------------------------------------


def test_leading_heading_is_preserved_and_later_ones_demoted() -> None:
    out = gen_docs.demote_stray_h1("# Title\n\ntext\n\n# Related Concepts\n\n- a\n")
    assert out.startswith("# Title")
    assert "## Related Concepts" in out
    assert "\n# Related Concepts" not in out


def test_existing_subheadings_are_untouched() -> None:
    body = "# Title\n\n## Section\n\n### Sub\n"
    assert gen_docs.demote_stray_h1(body) == body


def test_hash_comments_in_code_are_not_headings() -> None:
    body = "# Title\n\n```bash\n# not a heading\nls\n```\n"
    out = gen_docs.demote_stray_h1(body)
    assert "# not a heading" in out
    assert "## not a heading" not in out


# --- sources ---------------------------------------------------------------


def test_sources_render_urls_as_autolinks_and_text_plainly() -> None:
    out = gen_docs.render_sources(
        {
            "sources": [
                {"resource": "https://example.com/1"},
                {"resource": "a local note"},
            ]
        }
    )
    assert "## Sources" in out
    assert "- <https://example.com/1>" in out
    assert "- a local note" in out


def test_absent_or_empty_sources_render_nothing() -> None:
    assert gen_docs.render_sources({}) == ""
    assert gen_docs.render_sources({"sources": []}) == ""


# --- end to end ------------------------------------------------------------


@pytest.fixture
def generated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the generator over a miniature bundle and return the output dir."""
    bundle, overlay, out = tmp_path / "k", tmp_path / "o", tmp_path / "site_docs"

    (bundle / "caveats").mkdir(parents=True)
    (bundle / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Root\n')
    (bundle / "log.md").write_text("## 2026-01-01\n* Creation\n")
    (bundle / "caveats" / "index.md").write_text(
        "# Caveats\n* [A](alpha.md) - First.\n"
    )
    (bundle / "caveats" / "alpha.md").write_text(
        "---\ntitle: Alpha Concept\n"
        "sources:\n  - resource: https://example.com/src\n---\n\n"
        "Body text linking to [[caveats/beta]].\n\n# Related Concepts\n\n- x\n"
    )
    (bundle / "caveats" / "beta.md").write_text(
        "---\ntitle: Beta Concept\n---\n\n# Beta Concept\n\nAlready has a heading.\n"
    )

    (overlay / "caveats").mkdir(parents=True)
    (overlay / "index.md").write_text("# Hand-written Home\n")
    (overlay / "caveats" / "_intro.md").write_text("An intro paragraph.\n")
    (overlay / "guide.md").write_text("# A Guide\n")
    (overlay / "extra.css").write_text("body { }\n")

    monkeypatch.setattr(gen_docs, "BUNDLE", bundle)
    monkeypatch.setattr(gen_docs, "OVERLAY", overlay)
    monkeypatch.setattr(gen_docs, "OUT", out)
    assert gen_docs.main() == 0
    return out


def test_frontmatter_is_stripped_and_title_becomes_a_heading(generated: Path) -> None:
    alpha = (generated / "caveats" / "alpha.md").read_text()
    assert not alpha.startswith("---")
    assert alpha.startswith("# Alpha Concept")


def test_a_concept_with_its_own_heading_is_not_given_a_second(generated: Path) -> None:
    beta = (generated / "caveats" / "beta.md").read_text()
    assert beta.count("# Beta Concept") == 1


def test_sources_are_promoted_into_the_page(generated: Path) -> None:
    assert (
        "## Sources\n\n- <https://example.com/src>"
        in (generated / "caveats" / "alpha.md").read_text()
    )


def test_okf_bookkeeping_is_not_published(generated: Path) -> None:
    assert not (generated / "log.md").exists()


def test_section_index_receives_the_overlay_intro(generated: Path) -> None:
    index = (generated / "caveats" / "index.md").read_text()
    assert "An intro paragraph." in index
    assert index.startswith("# Caveats")


def test_overlay_overrides_a_generated_page(generated: Path) -> None:
    assert (generated / "index.md").read_text().startswith("# Hand-written Home")


def test_overlay_files_of_any_type_are_copied(generated: Path) -> None:
    assert (generated / "guide.md").exists()
    assert (generated / "extra.css").read_text() == "body { }\n"


def test_overlay_fragments_are_not_published(generated: Path) -> None:
    assert not (generated / "caveats" / "_intro.md").exists()


def test_output_is_rebuilt_from_scratch(
    generated: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = generated / "stale.md"
    stale.write_text("# Left over\n")
    monkeypatch.setattr(gen_docs, "BUNDLE", tmp_path / "k")
    monkeypatch.setattr(gen_docs, "OVERLAY", tmp_path / "o")
    monkeypatch.setattr(gen_docs, "OUT", generated)
    assert gen_docs.main() == 0
    assert not stale.exists()


def test_an_unresolved_wikilink_fails_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, out = tmp_path / "k", tmp_path / "out"
    bundle.mkdir()
    (bundle / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Root\n')
    (bundle / "a.md").write_text("---\ntitle: A\n---\n\nLink to [[missing/thing]].\n")
    monkeypatch.setattr(gen_docs, "BUNDLE", bundle)
    monkeypatch.setattr(gen_docs, "OVERLAY", tmp_path / "absent")
    monkeypatch.setattr(gen_docs, "OUT", out)
    assert gen_docs.main() == 1


def test_a_missing_bundle_fails_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gen_docs, "BUNDLE", tmp_path / "nope")
    monkeypatch.setattr(gen_docs, "OUT", tmp_path / "out")
    assert gen_docs.main() == 1
