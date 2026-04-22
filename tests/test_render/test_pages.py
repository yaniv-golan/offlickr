import json
import re as _re
from pathlib import Path
from typing import cast

import pytest
from bs4 import BeautifulSoup

from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive
from offlickr.render.pages import render_site
from tests.conftest import MINI_EXPORT


def _parse(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_index_html_exists(built_site: Path) -> None:
    assert (built_site / "index.html").is_file()


def test_index_html_has_photo_tiles(built_site: Path) -> None:
    soup = _parse(built_site / "index.html")
    tiles = soup.select(".grid-tile")
    assert len(tiles) >= 8  # 8 photos with media


def test_photo_detail_page_exists(built_site: Path) -> None:
    assert (built_site / "photo" / "10000001.html").is_file()


def test_photo_detail_has_title(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    h1 = soup.find("h1")
    assert h1 is not None
    assert "שקיעה כחולה" in h1.get_text()


def test_photo_detail_has_comment(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    comments = soup.select(".comment")
    assert len(comments) >= 1


def test_photo_detail_has_tags(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    tags = soup.select(".photo-tags li")
    tag_texts = [t.get_text(strip=True) for t in tags]
    assert "sunset" in tag_texts


def test_photo_detail_tags_are_linked(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    tag_links = soup.select(".photo-tags li a")
    hrefs = [a["href"] for a in tag_links]
    assert any("tags/sunset.html" in h for h in hrefs)


def test_photo_detail_comment_author_is_linked(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    author_links = soup.select(".comment-author")
    assert len(author_links) >= 1
    href = str(author_links[0].get("href", ""))
    assert "flickr.com/people/" in href


def test_about_html_exists(built_site: Path) -> None:
    assert (built_site / "about.html").is_file()


def test_about_has_screen_name(built_site: Path) -> None:
    soup = _parse(built_site / "about.html")
    assert "testuser" in soup.get_text()


def test_style_css_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "style.css").is_file()


def test_search_js_copied(built_site: Path) -> None:
    assert (built_site / "assets" / "search.js").is_file()


def test_external_links_have_rel(built_site: Path) -> None:
    """Every link to flickr.com must have rel='noopener noreferrer external'."""
    soup = _parse(built_site / "photo" / "10000001.html")
    flickr_links = [a for a in soup.find_all("a", href=True) if "flickr.com" in str(a["href"])]
    for link in flickr_links:
        rel = cast(list[str], link.get("rel") or [])
        assert "noopener" in rel
        assert "noreferrer" in rel
        assert "external" in rel


def test_private_photo_absent_by_default(built_site: Path) -> None:
    """photo_10000006 is private; its page must not exist without --include-private-photos."""
    assert not (built_site / "photo" / "10000006.html").is_file()


def test_photo_detail_shows_note_overlay(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    notes = soup.select(".note-overlay")
    assert len(notes) == 1
    assert notes[0].get("title") == "See the building"


def test_photo_detail_shows_people(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    people = soup.select(".photo-people a")
    assert len(people) >= 1
    assert "testfriend" in people[0].get_text()


def test_photo_detail_shows_in_albums(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    section = soup.find(class_="photo-in-albums")
    assert section is not None
    links = section.select("a")
    assert any("Album One" in a.get_text() for a in links)


def test_photo_detail_shows_in_groups(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    section = soup.find(class_="photo-in-groups")
    assert section is not None
    links = section.select("a[rel]")
    assert len(links) >= 1
    assert "Test Group" in links[0].get_text()


def test_photo_detail_shows_in_galleries(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    section = soup.find(class_="photo-in-galleries")
    assert section is not None
    links = section.select("a")
    assert any("A Gallery" in a.get_text() for a in links)


def test_photo_detail_shows_geo_inset(built_site: Path) -> None:
    # photo_10000001 has geo: lat=32.085, lng=34.781
    soup = _parse(built_site / "photo" / "10000001.html")
    inset = soup.find(class_="geo-inset")
    assert inset is not None
    # Should contain an SVG with a circle
    assert inset.find("circle") is not None or inset.find("svg") is not None


def test_photo_detail_no_geo_inset_when_no_geo(built_site: Path) -> None:
    # photo_10000002 has no geo in fixture
    soup = _parse(built_site / "photo" / "10000002.html")
    assert soup.find(class_="geo-inset") is None


def test_about_page_shows_showcase_grid(built_site: Path) -> None:
    soup = _parse(built_site / "about.html")
    showcase = soup.find(class_="showcase-grid")
    assert showcase is not None
    tiles = showcase.select(".grid-tile")
    assert len(tiles) >= 1


def test_photo_detail_comment_author_has_flickr_link(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    # Comment author should be a link to flickr.com
    author_links = soup.select("a.comment-author[href]")
    assert len(author_links) >= 1
    assert "flickr.com" in author_links[0]["href"]


def test_photostream_blurs_unsafe_thumbnails(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=True)
    soup = _parse(out / "index.html")
    blurred = soup.select(".grid-tile.safety-blur")
    assert len(blurred) >= 1


def test_photostream_no_blur_by_default(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "d",
        include_private=False,
        include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, hide_unsafe=False)
    soup = _parse(out / "index.html")
    assert len(soup.select(".grid-tile.safety-blur")) == 0


def test_photostream_tombstone_for_missing_media(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path / "d",
        include_private=False, include_private_photos=False,
    )
    out = tmp_path / "site"
    render_site(archive=archive, output_dir=out, include_missing_media=True)
    soup = _parse(out / "index.html")
    assert len(soup.select(".grid-tile.missing-media")) >= 1


def test_photo_detail_safety_badge_for_moderate(built_site: Path) -> None:
    # photo_10000003.json will be updated to safety="moderate" in Step 3
    soup = _parse(built_site / "photo" / "10000003.html")
    meta = soup.select_one("dl.photo-meta")
    assert meta is not None
    text = meta.get_text()
    assert "Moderate" in text or "moderate" in text.lower()

def test_photo_detail_shows_faves_count(built_site: Path) -> None:
    # photo_10000009.json has count_faves: 1 — use it to verify the Faves row appears
    soup = _parse(built_site / "photo" / "10000009.html")
    meta = soup.select_one("dl.photo-meta")
    assert meta is not None
    dts = [dt.get_text() for dt in meta.select("dt")]
    assert "Faves" in dts

def test_html_lang_is_not_path_alias(built_site: Path) -> None:
    html = (built_site / "index.html").read_text(encoding="utf-8")
    m = _re.search(r'<html lang="([^"]+)"', html)
    assert m is not None
    lang = m.group(1)
    assert lang != "testuser"  # must not be path_alias
    assert len(lang) <= 10    # "en", "he", "en-US" etc.


def test_about_page_shows_location(built_site: Path) -> None:
    soup = _parse(built_site / "about.html")
    text = soup.get_text()
    assert "Test City" in text  # from updated fixture

def test_about_page_shows_social_links(built_site: Path) -> None:
    soup = _parse(built_site / "about.html")
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

def test_comment_author_has_initials_circle(built_site: Path) -> None:
    soup = _parse(built_site / "photo" / "10000001.html")
    circles = soup.select(".comment-header .avatar-circle")
    assert len(circles) >= 1
    # Circle must contain exactly one character (the initial)
    assert len(circles[0].get_text(strip=True)) == 1


def test_about_page_has_profile_initials_circle(built_site: Path) -> None:
    soup = _parse(built_site / "about.html")
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
    photo_with_comment = next(
        (p for p in model["photos"] if p.get("comments")), None
    )
    if photo_with_comment is None:
        pytest.skip("no photos with comments in fixture")
    nsid = photo_with_comment["comments"][0]["user_nsid"]
    model["users"].setdefault(nsid, {"nsid": nsid})
    model["users"][nsid]["avatar_path"] = f"avatars/{nsid}.jpg"
    patched = OfflickrArchive.model_validate(model)
    render_site(archive=patched, output_dir=built_site)
    html = (built_site / "photo" / f"{photo_with_comment['id']}.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    comment_header = soup.find(class_="comment-header")
    assert comment_header is not None
    assert comment_header.find("img", class_="avatar-img") is not None
