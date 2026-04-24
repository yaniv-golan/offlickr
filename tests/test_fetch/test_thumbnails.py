# tests/test_fetch/test_thumbnails.py
from __future__ import annotations

import re
from pathlib import Path

import httpx
import respx
from PIL import Image

from offlickr.fetch.client import FlickrClient
from offlickr.fetch.thumbnails import fetch_fave_thumbnails, pick_thumb, pick_thumb_url
from offlickr.issues import IssueCollector

_REST_RE = re.compile(r"https://api\.flickr\.com/services/rest/.*")


def test_pick_thumb_prefers_small_320_over_large_square() -> None:
    sizes = [
        {"label": "Large Square", "source": "https://x.com/q.jpg", "width": "150", "height": "150"},
        {"label": "Small 320", "source": "https://x.com/n.jpg", "width": "320", "height": "213"},
        {"label": "Small", "source": "https://x.com/s.jpg", "width": "240", "height": "160"},
    ]
    url, w, h = pick_thumb(sizes)
    assert url == "https://x.com/n.jpg"
    assert w == 320
    assert h == 213


def test_pick_thumb_returns_dimensions() -> None:
    sizes = [{"label": "Small", "source": "https://x.com/s.jpg", "width": "240", "height": "160"}]
    url, w, h = pick_thumb(sizes)
    assert (w, h) == (240, 160)


def test_pick_thumb_falls_back_to_large_square() -> None:
    sizes = [{"label": "Large Square", "source": "https://x.com/q.jpg", "width": "150", "height": "150"}]
    url, w, h = pick_thumb(sizes)
    assert url == "https://x.com/q.jpg"


def test_pick_thumb_returns_none_for_empty() -> None:
    assert pick_thumb([]) is None


def test_pick_thumb_url_backward_compat() -> None:
    sizes = [{"label": "Small", "source": "https://x.com/s.jpg", "width": "240", "height": "160"}]
    assert pick_thumb_url(sizes) == "https://x.com/s.jpg"


@respx.mock
def test_fetch_fave_thumbnails_returns_path_and_dimensions(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={
            "stat": "ok",
            "sizes": {"size": [
                {"label": "Small 320", "source": "https://live.staticflickr.com/x/111_n.jpg",
                 "width": "320", "height": "213"},
            ]},
        })
    )
    respx.get("https://live.staticflickr.com/x/111_n.jpg").mock(
        return_value=httpx.Response(200, content=b"JPEG_DATA")
    )
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["111"], client, tmp_path)
    assert result == {"111": ("fave-thumbs/111.jpg", 320, 213)}
    assert (tmp_path / "fave-thumbs" / "111.jpg").read_bytes() == b"JPEG_DATA"


@respx.mock
def test_fetch_fave_thumbnails_reads_dimensions_from_cached_file(tmp_path: Path) -> None:
    (tmp_path / "fave-thumbs").mkdir()
    img = Image.new("RGB", (320, 213), color=(100, 100, 100))
    img.save(tmp_path / "fave-thumbs" / "111.jpg")
    # No HTTP mock — if it makes a request, respx will raise
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["111"], client, tmp_path)
    assert result["111"][0] == "fave-thumbs/111.jpg"
    assert result["111"][1] == 320
    assert result["111"][2] == 213


@respx.mock
def test_fetch_fave_thumbnails_skips_on_api_error(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "Photo not found"})
    )
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["999"], client, tmp_path)
    assert result == {}


@respx.mock
def test_fetch_fave_thumbnails_reports_api_error(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "Photo not found"})
    )
    collector = IssueCollector()
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["999"], client, tmp_path, collector=collector)
    assert result == {}
    assert collector.has_issues()
    cats = collector.by_category()
    assert "fetch.thumbnail" in cats
    assert cats["fetch.thumbnail"][0].item_id == "999"
    assert cats["fetch.thumbnail"][0].reason != ""
