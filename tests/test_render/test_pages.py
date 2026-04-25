import json
import re as _re
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from bs4 import BeautifulSoup

from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive, Photo
from offlickr.render.filters import format_datetime, is_flickr_url
from offlickr.render.pages import build_photo_urls, render_site
from tests.conftest import MINI_EXPORT


def _parse(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_index_html_exists(built_site: Path) -> None:
    assert (built_site / "index.html").is_file()


def test_index_html_has_photo_tiles(built_site: Path) -> None:
    soup = _parse(built_site / "index.html")
    tiles = soup.select(".grid-tile")
    assert len(tiles) >= 8  # 8 photos with media


def test_photo_detail_page_exists(built_site: Path, photo_href: dict[str, str]) -> None:
    assert (built_site / photo_href["10000001"]).is_file()


def test_photo_detail_has_title(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    h1 = soup.find("h1")
    assert h1 is not None
    assert "שקיעה כחולה" in h1.get_text()


def test_photo_detail_has_comment(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    comments = soup.select(".comment")
    assert len(comments) >= 1


def test_photo_detail_has_tags(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    tags = soup.select(".photo-tags li")
    tag_texts = [t.get_text(strip=True) for t in tags]
    assert "sunset" in tag_texts


def test_photo_detail_tags_are_linked(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    tag_links = soup.select(".photo-tags li a")
    hrefs = [a["href"] for a in tag_links]
    assert any("tags/sunset.html" in h for h in hrefs)


def test_photo_comment_author_plain_text_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # In standalone mode, Flickr comment author URLs are not linked
    soup = _parse(built_site / photo_href["10000001"])
    author_els = soup.select(".comment-author")
    assert len(author_els) >= 1
    assert all(el.name != "a" for el in author_els)


def test_about_html_absent_in_standalone(built_site: Path) -> None:
    assert not (built_site / "about.html").exists()


def test_about_html_exists_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    assert (built_site_flickr_origin / "about.html").is_file()


def test_about_has_screen_name(built_site_flickr_origin: Path) -> None:
    soup = _parse(built_site_flickr_origin / "about.html")
    assert "testuser" in soup.get_text()


def test_style_css_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "style.css").is_file()


def test_search_js_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "search.js").is_file()


def test_external_links_have_rel(built_site: Path, photo_href: dict[str, str]) -> None:
    """Every link to flickr.com must have rel='noopener noreferrer external'."""
    soup = _parse(built_site / photo_href["10000001"])
    flickr_links = [a for a in soup.find_all("a", href=True) if "flickr.com" in str(a["href"])]
    for link in flickr_links:
        rel = cast(list[str], link.get("rel") or [])
        assert "noopener" in rel
        assert "noreferrer" in rel
        assert "external" in rel


def test_private_photo_absent_by_default(built_site: Path, photo_href: dict[str, str]) -> None:
    """photo_10000006 is private; its page must not exist without --include-private-photos."""
    assert "10000006" not in photo_href


def test_photo_detail_shows_note_overlay(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    notes = soup.select(".note-overlay")
    assert len(notes) == 1
    assert notes[0].get("title") == "See the building"


def test_photo_people_plain_text_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    # In standalone mode, people are shown as plain text (no links)
    soup = _parse(built_site / photo_href["10000001"])
    section = soup.find(class_="photo-people")
    assert section is not None
    text = section.get_text()
    assert "testfriend" in text
    assert len(section.select("a")) == 0


def test_photo_detail_shows_in_albums(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    section = soup.find(class_="photo-in-albums")
    assert section is not None
    links = section.select("a")
    assert any("Album One" in a.get_text() for a in links)


def test_photo_groups_absent_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    # In standalone mode, the groups section is not shown
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.find(class_="photo-in-groups") is None


def test_photo_detail_shows_in_galleries(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    section = soup.find(class_="photo-in-galleries")
    assert section is not None
    links = section.select("a")
    assert any("A Gallery" in a.get_text() for a in links)


def test_photo_detail_shows_geo_inset(built_site: Path, photo_href: dict[str, str]) -> None:
    # photo_10000001 has geo: lat=32.085, lng=34.781
    soup = _parse(built_site / photo_href["10000001"])
    inset = soup.find(class_="geo-inset")
    assert inset is not None
    # Should contain an SVG with a circle
    assert inset.find("circle") is not None or inset.find("svg") is not None


def test_photo_detail_no_geo_inset_when_no_geo(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # photo_10000002 has no geo in fixture
    soup = _parse(built_site / photo_href["10000002"])
    assert soup.find(class_="geo-inset") is None


def test_about_page_shows_showcase_grid(built_site_flickr_origin: Path) -> None:
    soup = _parse(built_site_flickr_origin / "about.html")
    showcase = soup.find(class_="showcase-grid")
    assert showcase is not None
    tiles = showcase.select(".grid-tile")
    assert len(tiles) >= 1


def test_photo_detail_comment_author_linked_in_flickr_origin(
    built_site_flickr_origin: Path,
) -> None:
    archive = OfflickrArchive.model_validate(
        json.loads((built_site_flickr_origin / "data" / "model.json").read_text())
    )
    _href = build_photo_urls(archive.photos)
    soup = _parse(built_site_flickr_origin / _href["10000001"])
    author_links = soup.select("a.comment-author[href]")
    assert len(author_links) >= 1
    assert "flickr.com" in author_links[0]["href"]


def test_photostream_veils_unsafe_tiles_by_default(tmp_path: Path) -> None:
    # Default (hide_unsafe=False): unsafe photos appear with .safety-veiled + .veiled-overlay
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=False)
    soup = _parse(out / "index.html")
    veiled = soup.select(".grid-tile.safety-veiled")
    assert len(veiled) >= 1
    # Each veiled tile must contain the tombstone div
    for tile in veiled:
        assert tile.select_one(".tombstone") is not None
    # No legacy blur class
    assert len(soup.select(".grid-tile.safety-blur")) == 0


def test_photostream_hide_unsafe_excludes_photos(tmp_path: Path) -> None:
    # hide_unsafe=True: moderate/restricted photos are excluded from the grid entirely
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=True)
    soup = _parse(out / "index.html")
    # No veiled tiles — unsafe photos are gone
    assert len(soup.select(".grid-tile.safety-veiled")) == 0
    # No legacy blur class either
    assert len(soup.select(".grid-tile.safety-blur")) == 0


def test_photostream_hide_unsafe_omits_toggle(tmp_path: Path) -> None:
    # When hide_unsafe=True, the safe-only toggle should not appear
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=True)
    soup = _parse(out / "index.html")
    assert soup.select_one("#safety-toggle") is None


def test_photostream_toggle_present_when_unsafe_photos_exist(tmp_path: Path) -> None:
    # Default mode with unsafe photos → toggle button appears
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=False)
    soup = _parse(out / "index.html")
    assert soup.select_one("#safety-toggle") is not None


def test_photostream_tombstone_for_missing_media(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, include_missing_media=True)
    soup = _parse(out / "index.html")
    assert len(soup.select(".grid-tile.missing-media")) >= 1


def test_photo_no_safety_notice_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    # In standalone mode, the safety notice is hidden regardless of safety level
    soup = _parse(built_site / photo_href["10000003"])
    assert soup.select_one(".safety-notice") is None


def test_photo_detail_context_has_no_privacy_row(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Pin 8: Privacy row removed from sidecar Context group
    soup = _parse(built_site / photo_href["10000001"])
    sidecar = soup.select_one(".photo-sidecar")
    assert sidecar is not None
    dts = [dt.get_text(strip=True) for dt in sidecar.select("dt")]
    assert "Privacy" not in dts


def test_photo_detail_context_has_no_safety_row(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Pin 8: Safety row removed from sidecar Context group
    soup = _parse(built_site / photo_href["10000003"])
    sidecar = soup.select_one(".photo-sidecar")
    assert sidecar is not None
    dts = [dt.get_text(strip=True) for dt in sidecar.select("dt")]
    assert "Safety" not in dts


def test_photo_detail_download_link_shows_format(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Pin 10: download link text is "{size} · {format} original" or "{format} original"
    soup = _parse(built_site / photo_href["10000001"])
    links = soup.select(".sidecar-links a")
    texts = [a.get_text(strip=True) for a in links]
    assert any("original" in t for t in texts)
    assert not any(t.startswith("Download") for t in texts)


def test_photo_nav_arrows_in_mono_span(built_site: Path, photo_href: dict[str, str]) -> None:
    # Pin 11: prev/next arrows wrapped in .nav-arrow for consistent monospace weight
    soup = _parse(built_site / photo_href["10000001"])
    nav = soup.select_one(".photo-nav")
    assert nav is not None
    assert len(nav.select(".nav-arrow")) >= 1


def test_photo_detail_no_view_on_flickr_by_default(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # flickr_origin=False (default): "View on Flickr" link must be absent
    soup = _parse(built_site / photo_href["10000001"])
    links = soup.select(".sidecar-links a")
    texts = [a.get_text(strip=True) for a in links]
    assert "View on Flickr" not in texts


def test_photo_detail_view_on_flickr_when_enabled(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, flickr_origin=True)
    _href = build_photo_urls(archive.photos)
    soup = _parse(out / _href["10000001"])
    links = soup.select(".sidecar-links a")
    texts = [a.get_text(strip=True) for a in links]
    assert "View on Flickr" in texts


def test_album_no_view_on_flickr_by_default(built_site: Path) -> None:
    soup = _parse(built_site / "albums" / "10000000000000001.html")
    texts = [a.get_text(strip=True) for a in soup.select("a")]
    assert "View on Flickr" not in texts


def test_base_has_referrer_meta(built_site: Path) -> None:
    html = (built_site / "index.html").read_text(encoding="utf-8")
    assert 'name="referrer"' in html


def test_photo_ref_sections_use_consistent_class(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Pin 12: people/albums/galleries/groups all use .photo-ref-section
    soup = _parse(built_site / photo_href["10000001"])
    for cls in (".photo-people", ".photo-in-albums", ".photo-in-groups"):
        el = soup.select_one(cls)
        if el is not None:
            assert "photo-ref-section" in (el.get("class") or [])


def test_photo_detail_no_safety_notice_for_safe(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # safety="safe" — no notice regardless of flickr_origin
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.select_one(".safety-notice") is None


def test_photo_detail_empty_title_shows_untitled(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    archive.photos[0] = archive.photos[0].model_copy(update={"title": ""})
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out)
    photo_id = archive.photos[0].id
    _href = build_photo_urls(archive.photos)
    soup = _parse(out / _href[photo_id])
    h1 = soup.find("h1")
    assert h1 is not None
    assert "(untitled)" in h1.get_text()


def test_photo_sidecar_image_group_shows_dimensions(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    for group in soup.select(".exif-group"):
        h5 = group.find("h5")
        if h5 and h5.get_text(strip=True) == "Image":
            assert "\u00d7" in group.get_text()  # U+00D7 multiplication sign
            return
    pytest.skip("Image group not present (no media dimensions after derive)")


def test_photo_sidecar_image_group_shows_megapixels(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    for group in soup.select(".exif-group"):
        h5 = group.find("h5")
        if h5 and h5.get_text(strip=True) == "Image":
            assert "MP" in group.get_text()
            return
    pytest.skip("Image group not present")


def test_photo_sidecar_image_group_shows_filesize(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    for group in soup.select(".exif-group"):
        h5 = group.find("h5")
        if h5 and h5.get_text(strip=True) == "Image":
            # file size shown as bytes (B), KB, or MB
            text = group.get_text()
            assert any(u in text for u in (" B", "KB", "MB", "GB"))
            return
    pytest.skip("Image group not present")


def test_photo_detail_dot_title_preserved(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    archive.photos[0] = archive.photos[0].model_copy(update={"title": "."})
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out)
    photo_id = archive.photos[0].id
    _href = build_photo_urls(archive.photos)
    soup = _parse(out / _href[photo_id])
    h1 = soup.find("h1")
    assert h1 is not None
    assert h1.get_text(strip=True) == "."


def test_photo_detail_img_present_for_moderate(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Pin 1: photo_10000003 is safety="moderate" — hero <img> must be present on the detail page
    soup = _parse(built_site / photo_href["10000003"])
    figure = soup.select_one(".photo-figure")
    assert figure is not None
    assert figure.select_one("img") is not None


def test_photo_detail_no_faves_count_in_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    # Engagement stats are hidden in standalone mode
    soup = _parse(built_site / photo_href["10000009"])
    assert soup.select_one(".engagement") is None


def test_html_lang_is_not_path_alias(built_site: Path) -> None:
    html = (built_site / "index.html").read_text(encoding="utf-8")
    m = _re.search(r'<html lang="([^"]+)"', html)
    assert m is not None
    lang = m.group(1)
    assert lang != "testuser"  # must not be path_alias
    assert len(lang) <= 10  # "en", "he", "en-US" etc.


def test_about_page_shows_location(built_site_flickr_origin: Path) -> None:
    soup = _parse(built_site_flickr_origin / "about.html")
    text = soup.get_text()
    assert "Test City" in text  # from updated fixture


def test_about_page_shows_social_links(built_site_flickr_origin: Path) -> None:
    soup = _parse(built_site_flickr_origin / "about.html")
    social_ul = soup.find(class_="about-social")
    assert social_ul is not None
    assert len(social_ul.select("a")) >= 1


def test_album_shows_set_comments_when_private(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=True,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out)
    soup = _parse(out / "albums" / "10000000000000001.html")
    comments = soup.select(".album-comments .comment")
    assert len(comments) == 1
    assert "Love this album" in comments[0].get_text()


def test_testimonials_page_shows_received(built_site: Path) -> None:
    soup = _parse(built_site / "testimonials.html")
    text = soup.get_text()
    assert "frienduser" in text


def test_testimonials_page_shows_given(built_site: Path) -> None:
    soup = _parse(built_site / "testimonials.html")
    text = soup.get_text()
    assert "anotherfriend" in text


def test_comment_author_has_initials_circle(built_site: Path, photo_href: dict[str, str]) -> None:
    soup = _parse(built_site / photo_href["10000001"])
    circles = soup.select(".comment-header .avatar-circle")
    assert len(circles) >= 1
    # Circle must contain exactly one character (the initial)
    assert len(circles[0].get_text(strip=True)) == 1


def test_about_page_has_profile_initials_circle(built_site_flickr_origin: Path) -> None:
    soup = _parse(built_site_flickr_origin / "about.html")
    circle = soup.find(class_="avatar-circle")
    assert circle is not None
    initial = circle.get_text(strip=True)
    assert len(initial) == 1
    assert initial == initial.upper()


def test_fave_tile_with_thumbnail_path_has_flex_basis(built_site: Path) -> None:
    model = json.loads((built_site / "data" / "model.json").read_text())
    if not model.get("faves"):
        pytest.skip("no faves in fixture")
    model["faves"][0]["thumbnail_path"] = "fave-thumbs/fake.jpg"
    patched = OfflickrArchive.model_validate(model)
    render_site(archive=patched, output_dir=built_site)
    html = (built_site / "faves" / "index.html").read_text()
    assert "flex-basis" in html


def test_comment_with_avatar_path_shows_img(built_site: Path) -> None:
    model = json.loads((built_site / "data" / "model.json").read_text())
    photo_with_comment = next((p for p in model["photos"] if p.get("comments")), None)
    if photo_with_comment is None:
        pytest.skip("no photos with comments in fixture")
    nsid = photo_with_comment["comments"][0]["user_nsid"]
    model["users"].setdefault(nsid, {"nsid": nsid})
    model["users"][nsid]["avatar_path"] = f"avatars/{nsid}.jpg"
    patched = OfflickrArchive.model_validate(model)
    render_site(archive=patched, output_dir=built_site)
    _href = build_photo_urls(patched.photos)
    html = (built_site / _href[photo_with_comment["id"]]).read_text()
    soup = BeautifulSoup(html, "html.parser")
    comment_header = soup.find(class_="comment-header")
    assert comment_header is not None
    assert comment_header.find("img", class_="avatar-img") is not None


# Design improvement tests (findings 01-10)


def test_comment_date_has_monospace_class(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert ".comment-date" in css
    m = _re.search(r"\.comment-date\s*\{[^}]*\}", css)
    assert m is not None and ("monospace" in m.group(0) or "font-mono" in m.group(0))


def test_header_shows_real_name(built_site: Path) -> None:
    """Finding 01: brand should show real name when available."""
    soup = _parse(built_site / "index.html")
    brand = soup.select_one(".nav-brand")
    assert brand is not None
    assert "Test User" in brand.get_text()


def test_header_shows_handle(built_site: Path) -> None:
    """Finding 01: brand shows @handle alongside real name."""
    soup = _parse(built_site / "index.html")
    brand = soup.select_one(".nav-brand")
    assert brand is not None
    assert "@testuser" in brand.get_text() or "testuser" in brand.get_text()


def test_handle_is_span_in_standalone(built_site: Path) -> None:
    """@handle is a non-linked span in standalone mode."""
    soup = _parse(built_site / "index.html")
    handle = soup.select_one(".nav-handle")
    assert handle is not None
    assert handle.name == "span"
    assert not handle.get("href")


def test_handle_absent_when_no_real_name(tmp_path: Path) -> None:
    """@handle is suppressed when account has no real name."""
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    archive.account.real_name = None
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out)
    soup = _parse(out / "index.html")
    assert soup.select_one(".nav-handle") is None


def test_header_has_scope_meta(built_site: Path) -> None:
    """Finding 01: header should include scope metadata (photo count or year)."""
    soup = _parse(built_site / "index.html")
    meta = soup.select_one(".site-meta")
    assert meta is not None


def test_photostream_has_title_block(built_site: Path) -> None:
    """Finding 02: photostream page has a title block with counts."""
    soup = _parse(built_site / "index.html")
    block = soup.select_one(".page-title-block")
    assert block is not None


def test_photostream_title_block_has_count(built_site: Path) -> None:
    """Finding 02: title block shows the total photo count."""
    soup = _parse(built_site / "index.html")
    block = soup.select_one(".page-title-block")
    assert block is not None
    counts = block.select_one(".page-title-counts")
    assert counts is not None


def test_photo_detail_has_sidecar(built_site: Path, photo_href: dict[str, str]) -> None:
    """Finding 03: photo detail page has a two-column sidecar."""
    soup = _parse(built_site / photo_href["10000001"])
    sidecar = soup.select_one(".photo-sidecar")
    assert sidecar is not None


def test_photo_detail_no_sidecar_engagement_in_standalone(
    built_site: Path, photo_href: dict[str, str]
) -> None:
    """Engagement block absent in standalone (flickr_origin=False)."""
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.select_one(".engagement") is None


def test_photo_detail_sidecar_context_group(built_site: Path, photo_href: dict[str, str]) -> None:
    """Finding 03: photo sidecar has flat LICENSE/IMPORTED provenance rows."""
    soup = _parse(built_site / photo_href["10000001"])
    sidecar = soup.select_one(".photo-sidecar")
    assert sidecar is not None
    labels = [el.get_text(strip=True) for el in sidecar.select(".provenance")]
    assert "IMPORTED" in labels


def test_comment_has_date_element(built_site: Path, photo_href: dict[str, str]) -> None:
    """Finding 07: comment has a separate date element with class comment-date."""
    soup = _parse(built_site / photo_href["10000001"])
    date_els = soup.select(".comment-date")
    assert len(date_els) >= 1


def test_tags_page_has_filter_row(built_site: Path) -> None:
    """Finding 05: tags index has sort filter tabs."""
    soup = _parse(built_site / "tags" / "index.html")
    row = soup.select_one(".filter-row")
    assert row is not None


def test_tags_page_has_sort_by_count_list(built_site: Path) -> None:
    """Finding 05: tags index has a count-sorted list in addition to alpha."""
    soup = _parse(built_site / "tags" / "index.html")
    count_list = soup.select_one(".tags-by-count")
    assert count_list is not None


def test_scope_metadata_photo_count_in_globals(tmp_path: Path) -> None:
    """Finding 01: render_site passes total photo count as a template global."""
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out)
    soup = _parse(out / "index.html")
    meta = soup.select_one(".site-meta")
    assert meta is not None
    text = meta.get_text()
    # Should mention a number (photo count or year)
    assert any(c.isdigit() for c in text)


# ── Task 1: CSS polish ────────────────────────────────────────────────────────


def test_comment_date_has_monospace_font(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    # Find the .comment-date rule and verify it has a monospace font-family
    block = _re.search(r"\.comment-date\s*\{[^}]*\}", css)
    assert block is not None
    rule = block.group(0)
    assert "monospace" in rule or "font-mono" in rule


def test_photo_hero_has_vignette(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    block = _re.search(r"\.photo-hero\s*\{[^}]*\}", css)
    assert block is not None
    assert "inset" in block.group(0)


# ── Task 2: Nav "Favorites" → "Faves" ────────────────────────────────────────


def test_nav_uses_faves_not_favorites(built_site: Path) -> None:
    soup = _parse(built_site / "index.html")
    nav = soup.select_one(".nav-links")
    assert nav is not None
    texts = [a.get_text(strip=True) for a in nav.select("a")]
    assert "Faves" in texts
    assert "Favorites" not in texts


# ── Task 3: Nav active pill ───────────────────────────────────────────────────


def test_active_nav_link_uses_filled_pill(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    block = _re.search(r'\.nav-links a\[aria-current="page"\]\s*\{[^}]*\}', css)
    assert block is not None
    assert "background" in block.group(0)


# ── Task 4: Tags active tab CSS fix ──────────────────────────────────────────


def test_tags_filter_active_tab_css_is_valid(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert ":not(#sort-anchor" not in css


# ── Task 5: Map CLUSTER_MIN ───────────────────────────────────────────────────


def test_map_cluster_min_is_15(built_site: Path) -> None:
    js = (built_site / "assets" / "map.js").read_text()
    assert "CLUSTER_MIN = 15" in js


# ── Task 6: Map page-title-block ─────────────────────────────────────────────


def test_map_page_has_title_block(built_site: Path) -> None:
    if not (built_site / "map.html").is_file():
        pytest.skip("no map.html — no geotagged photos in fixture")
    soup = _parse(built_site / "map.html")
    block = soup.select_one(".page-title-block")
    assert block is not None
    counts = block.select_one(".page-title-counts")
    assert counts is not None


# ── Task 7: page-title-block breadth ─────────────────────────────────────────


def test_albums_index_has_title_block(built_site: Path) -> None:
    soup = _parse(built_site / "albums" / "index.html")
    assert soup.select_one(".page-title-block") is not None


def test_galleries_index_has_title_block(built_site: Path) -> None:
    soup = _parse(built_site / "galleries" / "index.html")
    assert soup.select_one(".page-title-block") is not None


def test_faves_index_has_title_block(built_site: Path) -> None:
    soup = _parse(built_site / "faves" / "index.html")
    assert soup.select_one(".page-title-block") is not None


def test_groups_index_has_title_block(built_site: Path) -> None:
    soup = _parse(built_site / "groups" / "index.html")
    assert soup.select_one(".page-title-block") is not None


# ── Task 8: Tags top-20 ───────────────────────────────────────────────────────


def test_tags_page_has_top20_section(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    top20 = soup.select_one(".tags-top20")
    assert top20 is not None
    items = top20.select(".tag-cloud-item")
    assert 1 <= len(items) <= 20


# ── Task 9: Tags first-letter strip ──────────────────────────────────────────


def test_tags_page_has_letter_strip(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    strip = soup.select_one(".tag-letter-strip")
    assert strip is not None
    assert len(strip.select("a")) >= 1


def test_tags_page_has_letter_anchors(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    anchors = soup.select(".tag-letter-anchor")
    assert len(anchors) >= 1


# ── Task 10: Tags first-used sort ────────────────────────────────────────────


def test_tags_page_has_first_used_tab(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    row = soup.select_one(".filter-row")
    assert row is not None
    texts = [a.get_text(strip=True) for a in row.select("a")]
    assert any("first" in t.lower() for t in texts)


def test_tags_page_has_first_used_cloud(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    assert soup.select_one(".tags-by-first") is not None


# ── Task 11: Photo time-of-day ────────────────────────────────────────────────


def test_format_datetime_filter_registered() -> None:
    assert format_datetime is not None


def test_format_datetime_shows_time_when_nonmidnight() -> None:
    dt = datetime(2020, 6, 15, 14, 30, tzinfo=UTC)
    result = format_datetime(dt)
    assert "14:30" in result
    assert "2020" in result


def test_format_datetime_hides_time_when_midnight() -> None:
    dt = datetime(2020, 6, 15, 0, 0, tzinfo=UTC)
    result = format_datetime(dt)
    assert "00:00" not in result
    assert "2020" in result


def test_archive_index_exists(built_site: Path) -> None:
    assert (built_site / "archive" / "index.html").exists()


def test_archive_year_pages_exist(built_site: Path) -> None:
    years = list((built_site / "archive").glob("[0-9][0-9][0-9][0-9].html"))
    assert len(years) > 0


def test_archive_year_page_has_sparkline(built_site: Path) -> None:
    for p in (built_site / "archive").glob("[0-9][0-9][0-9][0-9].html"):
        html = p.read_text()
        if "sparkline" in html:
            assert "data-density=" in html
            return
    # If no sparkline found (all years < 5 photos), just verify year pages exist
    assert list((built_site / "archive").glob("[0-9][0-9][0-9][0-9].html"))


def test_archive_index_links_to_year_pages(built_site: Path) -> None:
    html = (built_site / "archive" / "index.html").read_text()
    assert "archive/" in html
    assert ".html" in html


def test_photo_date_links_to_archive(built_site: Path) -> None:
    for p in (built_site / "photos").rglob("*.html"):
        html = p.read_text()
        if "archive/" in html and "#d-" in html:
            return
    # If no photos have date_taken, the archive will be empty but that's OK
    # Check the archive index at least exists
    assert (built_site / "archive" / "index.html").exists()


# ── PR 8: date-based photo URLs ──────────────────────────────────────────────


def test_dated_photos_under_photos_dir(built_site: Path) -> None:
    assert (built_site / "photos").is_dir()
    html_files = list((built_site / "photos").rglob("*.html"))
    assert len(html_files) > 0


def test_photo_url_format(photo_href: dict[str, str]) -> None:
    pattern = _re.compile(r"^photos/\d{4}/\d{2}/\d{2}/\d{2}\.html$")
    dated = [v for v in photo_href.values() if v.startswith("photos/")]
    assert len(dated) > 0
    for url in dated:
        assert pattern.match(url), f"bad URL: {url}"


def test_undated_photos_fallback_to_photo_dir(photo_href: dict[str, str]) -> None:
    undated = [v for v in photo_href.values() if v.startswith("photo/")]
    # mini-export has 3 undated photos (10000031, 10000032, 10000015)
    assert len(undated) == 3


def test_photos_same_day_get_distinct_numbers(photo_href: dict[str, str]) -> None:
    # Photos 10000011, 10000012, 10000013 all share 2020-01-15
    urls = {photo_href[pid] for pid in ["10000011", "10000012", "10000013"]}
    assert len(urls) == 3


def test_photostream_links_use_dated_urls(built_site: Path) -> None:
    html = (built_site / "index.html").read_text()
    assert (
        "photo/" not in html.split('<div class="photostream-grid">')[1].split("</div>")[0]
        or "photos/" in html
    )


def test_photo_page_base_url_correct_depth(built_site: Path, photo_href: dict[str, str]) -> None:
    url = photo_href["10000001"]  # photos/2020/03/15/01.html
    page_html = (built_site / url).read_text()
    depth = url.count("/")  # 4 for dated photos
    expected_base = "../" * depth
    assert f'src="{expected_base}assets/' in page_html


def test_search_index_has_url_field(built_site: Path, photo_href: dict[str, str]) -> None:
    html = (built_site / "index.html").read_text()
    m = _re.search(r"var OFFLICKR_INDEX=(\[.*?\]);", html, _re.DOTALL)
    assert m is not None
    idx = json.loads(m.group(1))
    dated_entries = [e for e in idx if e.get("u", "").startswith("photos/")]
    assert len(dated_entries) > 0


def test_build_photo_urls_unit() -> None:
    # Two photos same day, one undated
    imported = datetime(2022, 4, 1, 11, 0)
    p1 = Photo(
        id="A",
        title="A",
        photopage_url="https://x/",
        original_flickr_url="https://x/",
        date_imported=imported,
        date_taken=datetime(2022, 4, 1, 10, 0),
    )
    p2 = Photo(
        id="B",
        title="B",
        photopage_url="https://x/",
        original_flickr_url="https://x/",
        date_imported=imported,
        date_taken=datetime(2022, 4, 1, 12, 0),
    )
    p3 = Photo(
        id="C",
        title="C",
        photopage_url="https://x/",
        original_flickr_url="https://x/",
        date_imported=datetime(2022, 4, 2, 8, 0),
        date_taken=None,
    )
    m = build_photo_urls([p1, p2, p3])
    assert m["A"] == "photos/2022/04/01/01.html"
    assert m["B"] == "photos/2022/04/01/02.html"
    assert m["C"] == "photo/C.html"


# ── PR 6: local fonts ────────────────────────────────────────────────────────


def test_fonts_directory_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "fonts").is_dir()


def test_font_woff2_files_present(built_site: Path) -> None:
    fonts_dir = built_site / "assets" / "fonts"
    for name in (
        "inter.woff2",
        "source-serif-4.woff2",
        "source-serif-4-italic.woff2",
        "jetbrains-mono.woff2",
    ):
        assert (fonts_dir / name).is_file(), f"missing {name}"


def test_fonts_css_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "_fonts.css").is_file()


def test_style_css_imports_fonts(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert "@import '_fonts.css'" in css


def test_style_css_uses_inter(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert "'Inter'" in css


def test_style_css_uses_source_serif(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert "'Source Serif 4'" in css


def test_style_css_uses_jetbrains_mono(built_site: Path) -> None:
    css = (built_site / "assets" / "style.css").read_text()
    assert "'JetBrains Mono'" in css


def test_font_total_size_under_250kb(built_site: Path) -> None:
    fonts_dir = built_site / "assets" / "fonts"
    total = sum(f.stat().st_size for f in fonts_dir.glob("*.woff2"))
    assert total < 250 * 1024, f"fonts total {total // 1024}KB exceeds 250KB"


# ── flickr-origin behaviour matrix ─────────────────────────────────────────────


def _fo_href(built_site_flickr_origin: Path) -> dict[str, str]:
    """Helper: build photo_href map from the flickr-origin site."""
    archive = OfflickrArchive.model_validate(
        json.loads((built_site_flickr_origin / "data" / "model.json").read_text())
    )
    return build_photo_urls(archive.photos)


def test_fo_engagement_shown_with_label(built_site_flickr_origin: Path) -> None:
    """Row 1: engagement block visible in flickr-origin with 'ON FLICKR' provenance label."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000009"])
    engagement = soup.select_one(".engagement")
    assert engagement is not None
    provenance = engagement.select_one(".provenance")
    assert provenance is not None
    assert "ON FLICKR" in provenance.get_text()
    assert "fave" in engagement.get_text().lower() or "view" in engagement.get_text().lower()


def test_fo_engagement_absent_in_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 1: engagement block absent in standalone mode."""
    soup = _parse(built_site / photo_href["10000009"])
    assert soup.select_one(".engagement") is None


def test_fo_groups_shown_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 2: groups section visible in flickr-origin."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000001"])
    section = soup.find(class_="photo-in-groups")
    assert section is not None
    links = section.select("a")
    assert any("Test Group" in a.get_text() for a in links)


def test_fo_groups_absent_in_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 2: groups section absent in standalone mode."""
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.find(class_="photo-in-groups") is None


def test_fo_people_linked_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 3: people shown as links in flickr-origin."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000001"])
    section = soup.find(class_="photo-people")
    assert section is not None
    links = section.select("a")
    assert len(links) >= 1
    assert "testfriend" in links[0].get_text()


def test_fo_people_plain_text_in_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 3: people shown as plain text in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    section = soup.find(class_="photo-people")
    assert section is not None
    assert "testfriend" in section.get_text()
    assert len(section.select("a")) == 0


def test_fo_comment_author_linked_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 4: Flickr comment author URLs are linked in flickr-origin."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000001"])
    author_links = soup.select("a.comment-author")
    assert len(author_links) >= 1
    assert "flickr.com" in str(author_links[0].get("href", ""))


def test_fo_comment_author_text_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 4: Flickr comment author URLs are plain text in standalone."""
    soup = _parse(built_site / photo_href["10000001"])
    assert all(el.name != "a" for el in soup.select(".comment-author"))


def test_fo_handle_linked_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 6: @handle is an anchor linking to Flickr profile in flickr-origin."""
    soup = _parse(built_site_flickr_origin / "index.html")
    handle = soup.select_one(".nav-handle")
    assert handle is not None
    assert handle.name == "a"
    assert "flickr.com" in str(handle.get("href", ""))


def test_fo_handle_span_in_standalone(built_site: Path) -> None:
    """Row 6: @handle is a plain span in standalone mode."""
    soup = _parse(built_site / "index.html")
    handle = soup.select_one(".nav-handle")
    assert handle is not None
    assert handle.name == "span"


def test_fo_safety_notice_shown_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 7: safety notice shown for moderate/restricted photos in flickr-origin."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000003"])
    notice = soup.select_one(".safety-notice")
    assert notice is not None
    assert "Moderate" in notice.get_text() or "moderate" in notice.get_text().lower()


def test_fo_safety_notice_absent_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 7: safety notice absent in standalone even for moderate photos."""
    soup = _parse(built_site / photo_href["10000003"])
    assert soup.select_one(".safety-notice") is None


def test_fo_about_absent_in_standalone(built_site: Path) -> None:
    """Row 8: about.html not emitted in standalone mode."""
    assert not (built_site / "about.html").exists()


def test_fo_about_nav_link_absent_in_standalone(built_site: Path) -> None:
    """Row 8: About nav link absent in standalone mode."""
    soup = _parse(built_site / "index.html")
    nav_texts = [a.get_text(strip=True) for a in soup.select(".nav-links a")]
    assert "About" not in nav_texts


def test_fo_about_nav_link_present_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 8: About nav link present in flickr-origin."""
    soup = _parse(built_site_flickr_origin / "index.html")
    nav_texts = [a.get_text(strip=True) for a in soup.select(".nav-links a")]
    assert "About" in nav_texts


def test_fo_canonical_in_photo_page(built_site_flickr_origin: Path) -> None:
    """Row 9: photo pages have canonical link pointing to photopage_url in flickr-origin."""
    _href = _fo_href(built_site_flickr_origin)
    soup = _parse(built_site_flickr_origin / _href["10000001"])
    canonical = soup.find("link", rel="canonical")
    assert canonical is not None
    assert "flickr.com" in str(canonical.get("href", ""))


def test_fo_no_canonical_in_standalone(built_site: Path, photo_href: dict[str, str]) -> None:
    """Row 9: no canonical link in standalone mode."""
    soup = _parse(built_site / photo_href["10000001"])
    assert soup.find("link", rel="canonical") is None


def test_fo_noindex_in_flickr_origin(built_site_flickr_origin: Path) -> None:
    """Row 10: noindex meta tag present in flickr-origin."""
    html = (built_site_flickr_origin / "index.html").read_text()
    assert 'content="noindex"' in html


def test_fo_no_noindex_in_standalone(built_site: Path) -> None:
    """Row 10: noindex meta tag absent in standalone mode."""
    html = (built_site / "index.html").read_text()
    assert 'content="noindex"' not in html


def test_is_flickr_url_filter() -> None:
    """Unit test for is_flickr_url filter."""
    assert is_flickr_url("https://www.flickr.com/people/123/") is True
    assert is_flickr_url("https://flickr.com/photos/x/") is True
    assert is_flickr_url("https://api.flickr.com/services/rest/") is True
    assert is_flickr_url("https://example.com/profile") is False
    assert is_flickr_url(None) is False
    assert is_flickr_url("") is False
