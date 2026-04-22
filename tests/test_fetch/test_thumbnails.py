# tests/test_fetch/test_thumbnails.py
from __future__ import annotations

import re
from pathlib import Path

import httpx
import respx

from offlickr.fetch.client import FlickrClient
from offlickr.fetch.thumbnails import fetch_fave_thumbnails, pick_thumb_url
from offlickr.issues import IssueCollector

_REST_RE = re.compile(r"https://api\.flickr\.com/services/rest/.*")


def test_pick_thumb_url_prefers_large_square() -> None:
    sizes = [
        {"label": "Small", "source": "https://x.com/s.jpg"},
        {"label": "Large Square", "source": "https://x.com/q.jpg"},
        {"label": "Square", "source": "https://x.com/sq.jpg"},
    ]
    assert pick_thumb_url(sizes) == "https://x.com/q.jpg"


def test_pick_thumb_url_falls_back_to_square() -> None:
    sizes = [{"label": "Square", "source": "https://x.com/sq.jpg"}]
    assert pick_thumb_url(sizes) == "https://x.com/sq.jpg"


def test_pick_thumb_url_returns_none_for_empty() -> None:
    assert pick_thumb_url([]) is None


@respx.mock
def test_fetch_fave_thumbnails_downloads_and_returns_paths(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={
            "stat": "ok",
            "sizes": {"size": [{"label": "Large Square", "source": "https://live.staticflickr.com/x/111_a_q.jpg"}]},
        })
    )
    respx.get("https://live.staticflickr.com/x/111_a_q.jpg").mock(
        return_value=httpx.Response(200, content=b"JPEG_DATA")
    )
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["111"], client, tmp_path)
    assert result == {"111": "fave-thumbs/111.jpg"}
    assert (tmp_path / "fave-thumbs" / "111.jpg").read_bytes() == b"JPEG_DATA"


@respx.mock
def test_fetch_fave_thumbnails_skips_existing(tmp_path: Path) -> None:
    (tmp_path / "fave-thumbs").mkdir()
    (tmp_path / "fave-thumbs" / "111.jpg").write_bytes(b"OLD")
    # No HTTP mock — if it makes a request, respx will raise
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["111"], client, tmp_path)
    assert result == {"111": "fave-thumbs/111.jpg"}
    assert (tmp_path / "fave-thumbs" / "111.jpg").read_bytes() == b"OLD"


@respx.mock
def test_fetch_fave_thumbnails_skips_on_api_error(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "Photo not found"})
    )
    with FlickrClient("key") as client:
        result = fetch_fave_thumbnails(["999"], client, tmp_path)
    assert result == {}  # silently skipped


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
