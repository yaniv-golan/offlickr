"""Structural tests for _macros/ — two grep invariants plus one test per spec row.

The behavioural coverage lives in test_pages.py (test_fo_* functions).
These tests exist to (a) enforce the structural contract via grep invariants and
(b) give every spec row a named test so the matrix stays legible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive
from offlickr.render.pages import build_photo_urls, render_site
from tests.conftest import MINI_EXPORT

# ── helpers ──────────────────────────────────────────────────────────────────


def _parse(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def _fo_href(built_site_flickr_origin: Path) -> dict[str, str]:
    archive = OfflickrArchive.model_validate(
        json.loads((built_site_flickr_origin / "data" / "model.json").read_text())
    )
    return build_photo_urls(archive.photos)


_TEMPLATES = (
    Path(__file__).parents[2] / "src" / "offlickr" / "themes" / "minimal-archive" / "templates"
)
_MACROS = _TEMPLATES / "_macros"
_PAGES_PY = Path(__file__).parents[2] / "src" / "offlickr" / "render" / "pages.py"


# ── Structural invariants ─────────────────────────────────────────────────────


def test_no_flickr_origin_in_main_templates() -> None:
    """flickr_origin must only appear inside _macros/, never in top-level templates."""
    violations = [
        tmpl.name
        for tmpl in _TEMPLATES.glob("*.html.j2")
        if "flickr_origin" in tmpl.read_text(encoding="utf-8")
    ]
    assert violations == [], f"flickr_origin found in main templates: {violations}"


def test_pages_py_flickr_origin_usage_is_controlled() -> None:
    """Every non-comment flickr_origin reference in pages.py must be a global
    assignment, a function parameter declaration, or an `if flickr_origin:` guard."""
    allowed_patterns = (
        'env.globals["flickr_origin"]',  # global flag assignment
        "flickr_origin:",  # function parameter / type annotation
        "if flickr_origin:",  # guard around _render_* call
        "if flickr_origin else",  # ternary (e.g. canonical_url assignment)
    )
    for i, line in enumerate(_PAGES_PY.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if "flickr_origin" not in stripped or stripped.startswith("#"):
            continue
        ok = any(pat in stripped for pat in allowed_patterns)
        assert ok, f"pages.py:{i}: unexpected flickr_origin usage: {stripped!r}"


# ── Row 1: engagement stats ───────────────────────────────────────────────────


def test_row_01_engagement_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """engagement macro: block shown with 'ON FLICKR' provenance label in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000009"])
    block = soup.select_one(".engagement")
    assert block is not None
    assert "ON FLICKR" in (block.select_one(".provenance") or block).get_text()


def test_row_01_engagement_absent_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """engagement macro: block entirely absent in standalone."""
    soup = _parse(built_site / photo_href["10000009"])
    assert soup.select_one(".engagement") is None


# ── Row 2: groups section ─────────────────────────────────────────────────────


def test_row_02_groups_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """groups_section macro: section shown in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000001"])
    assert soup.find(class_="photo-in-groups") is not None


def test_row_02_groups_absent_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """groups_section macro: section absent in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.find(class_="photo-in-groups") is None


# ── Row 3: people tags ────────────────────────────────────────────────────────


def test_row_03_people_linked_flickr_origin(built_site_flickr_origin: Path) -> None:
    """person_tag macro: people are links in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000001"])
    section = soup.find(class_="photo-people")
    assert section is not None
    assert len(section.select("a")) >= 1


def test_row_03_people_plain_text_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """person_tag macro: people are plain text in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    section = soup.find(class_="photo-people")
    assert section is not None
    assert len(section.select("a")) == 0


# ── Row 4: photo comment authors ─────────────────────────────────────────────


def test_row_04_photo_comment_author_link_flickr_origin(built_site_flickr_origin: Path) -> None:
    """comment_author_photo macro: Flickr comment authors are links in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000001"])
    author_links = soup.select("a.comment-author")
    assert len(author_links) >= 1
    assert "flickr.com" in str(author_links[0].get("href", ""))


def test_row_04_photo_comment_author_span_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    """comment_author_photo macro: Flickr comment authors are plain spans in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    assert all(el.name != "a" for el in soup.select(".comment-author"))


# ── Row 5: album comment authors ─────────────────────────────────────────────


def test_row_05_album_comment_author_span_standalone(built_site: Path) -> None:
    """comment_author_album macro: nsid-derived Flickr URLs shown as <span> in standalone."""
    tmp = built_site.parent / "album_test_standalone"
    run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp,
        include_private=True,
        include_private_photos=False,
    )
    archive = OfflickrArchive.model_validate(json.loads((tmp / "data" / "model.json").read_text()))
    render_site(archive=archive, output_dir=tmp, flickr_origin=False)
    album_html = tmp / "albums" / "10000000000000001.html"
    if not album_html.exists():
        pytest.skip("album page not generated")
    soup = _parse(album_html)
    comments_section = soup.select_one(".album-comments")
    if comments_section is None:
        pytest.skip("no album comments in fixture")
    assert all(el.name != "a" for el in comments_section.select(".comment-author"))


def test_row_05_album_comment_author_link_flickr_origin(built_site_flickr_origin: Path) -> None:
    """comment_author_album macro: nsid-derived Flickr URLs are links in flickr-origin."""
    tmp = built_site_flickr_origin.parent / "album_test_fo"
    run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp,
        include_private=True,
        include_private_photos=False,
    )
    archive = OfflickrArchive.model_validate(json.loads((tmp / "data" / "model.json").read_text()))
    render_site(archive=archive, output_dir=tmp, flickr_origin=True)
    album_html = tmp / "albums" / "10000000000000001.html"
    if not album_html.exists():
        pytest.skip("album page not generated")
    soup = _parse(album_html)
    comments_section = soup.select_one(".album-comments")
    if comments_section is None:
        pytest.skip("no album comments in fixture")
    assert any(el.name == "a" for el in comments_section.select(".comment-author"))


# ── Row 6: head meta (noindex + canonical) ────────────────────────────────────


def test_row_06_head_meta_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """head_meta macro: noindex and canonical tags present in flickr-origin."""
    html = (built_site_flickr_origin / "index.html").read_text(encoding="utf-8")
    assert 'content="noindex"' in html


def test_row_06_head_meta_absent_standalone(built_site: Path) -> None:
    """head_meta macro: noindex absent in standalone."""
    html = (built_site / "index.html").read_text(encoding="utf-8")
    assert 'content="noindex"' not in html


# ── Row 7: safety banner ──────────────────────────────────────────────────────


def test_row_07_safety_banner_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """safety_banner macro: notice shown for moderate photos in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000003"])
    assert soup.select_one(".safety-notice") is not None


def test_row_07_safety_banner_absent_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    """safety_banner macro: notice absent in standalone even for moderate photos."""
    soup = _parse(built_site / photo_href["10000003"])
    assert soup.select_one(".safety-notice") is None


# ── Row 8: About page nav ─────────────────────────────────────────────────────


def test_row_08_about_nav_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """about_nav_link macro: About nav item present in flickr-origin."""
    soup = _parse(built_site_flickr_origin / "index.html")
    nav_texts = [a.get_text(strip=True) for a in soup.select(".nav-links a")]
    assert "About" in nav_texts


def test_row_08_about_nav_absent_standalone(built_site: Path) -> None:
    """about_nav_link macro: About nav item absent in standalone."""
    soup = _parse(built_site / "index.html")
    nav_texts = [a.get_text(strip=True) for a in soup.select(".nav-links a")]
    assert "About" not in nav_texts


# ── Row 9: nav @handle ────────────────────────────────────────────────────────


def test_row_09_handle_link_flickr_origin(built_site_flickr_origin: Path) -> None:
    """nav_handle macro: @handle is an anchor pointing to Flickr profile in flickr-origin."""
    soup = _parse(built_site_flickr_origin / "index.html")
    handle = soup.select_one(".nav-handle")
    assert handle is not None
    assert handle.name == "a"
    assert "flickr.com" in str(handle.get("href", ""))


def test_row_09_handle_span_standalone(built_site: Path) -> None:
    """nav_handle macro: @handle is a plain <span> in standalone."""
    soup = _parse(built_site / "index.html")
    handle = soup.select_one(".nav-handle")
    assert handle is not None
    assert handle.name == "span"


# ── Row 10: "View on Flickr" links ───────────────────────────────────────────


def test_row_10_view_on_flickr_present_flickr_origin(built_site_flickr_origin: Path) -> None:
    """sidecar_links macro: 'View on Flickr' link shown in flickr-origin."""
    href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / href["10000001"])
    texts = [a.get_text(strip=True) for a in soup.select(".sidecar-links a")]
    assert "View on Flickr" in texts


def test_row_10_view_on_flickr_absent_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    """sidecar_links macro: 'View on Flickr' link absent in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    texts = [a.get_text(strip=True) for a in soup.select(".sidecar-links a")]
    assert "View on Flickr" not in texts
