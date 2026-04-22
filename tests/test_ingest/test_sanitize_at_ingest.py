import contextlib
import json
import shutil
from pathlib import Path

from offlickr.ingest.account import load_account
from offlickr.ingest.albums import load_albums
from offlickr.ingest.galleries import load_galleries
from offlickr.ingest.photos import load_photos

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini-export"


def test_photo_description_is_sanitized(tmp_path: Path) -> None:
    """Script tags in photo descriptions must be stripped."""
    src = FIXTURE / "photo_10000001.json"
    evil = tmp_path / "photo_10000001.json"
    data = json.loads(src.read_text())
    data["description"] = '<script>alert(1)</script><p>Nice</p>'
    evil.write_text(json.dumps(data))
    # copy other fixture files so media index works
    for f in FIXTURE.iterdir():
        if f.name != "photo_10000001.json":
            with contextlib.suppress(Exception):
                shutil.copy2(f, tmp_path / f.name)
    photos = load_photos(tmp_path)
    photo = next(p for p in photos if p.id == "10000001")
    assert "<script>" not in photo.description_html
    assert "Nice" in photo.description_html


def test_photo_comment_body_is_sanitized(tmp_path: Path) -> None:
    src = FIXTURE / "photo_10000001.json"
    evil = tmp_path / "photo_10000001.json"
    data = json.loads(src.read_text())
    if data.get("comments"):
        data["comments"][0]["comment"] = '<script>xss()</script>legit'
    else:
        data["comments"] = [{"id": "c1", "date": "2020-01-01 00:00:00",
                              "user": "99@N00", "comment": "<script>xss()</script>legit",
                              "url": "https://flickr.com/x"}]
    evil.write_text(json.dumps(data))
    for f in FIXTURE.iterdir():
        if f.name != "photo_10000001.json":
            with contextlib.suppress(Exception):
                shutil.copy2(f, tmp_path / f.name)
    photos = load_photos(tmp_path)
    photo = next(p for p in photos if p.id == "10000001")
    assert all("<script>" not in c.body_html for c in photo.comments)


def test_account_description_is_sanitized() -> None:
    account = load_account(FIXTURE)
    assert "<script>" not in account.description_html


def test_album_description_is_sanitized() -> None:
    albums = load_albums(FIXTURE)
    assert all("<script>" not in a.description_html for a in albums)


def test_gallery_description_is_sanitized() -> None:
    galleries = load_galleries(FIXTURE)
    assert all("<script>" not in g.description_html for g in galleries)
