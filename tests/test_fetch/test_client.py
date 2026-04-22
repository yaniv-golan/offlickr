# tests/test_fetch/test_client.py
from __future__ import annotations

import re

import httpx
import pytest
import respx

from offlickr.fetch.client import FlickrClient

_REST_RE = re.compile(r"https://api\.flickr\.com/services/rest/.*")


@respx.mock
def test_get_photo_sizes_returns_list() -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={
            "stat": "ok",
            "sizes": {"size": [
                {"label": "Large Square", "source": "https://live.staticflickr.com/x/123_abc_q.jpg"},
                {"label": "Square", "source": "https://live.staticflickr.com/x/123_abc_s.jpg"},
            ]},
        })
    )
    with FlickrClient("test-key") as client:
        sizes = client.get_photo_sizes("123")
    assert len(sizes) == 2
    assert sizes[0]["label"] == "Large Square"


@respx.mock
def test_get_person_info_returns_dict() -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={
            "stat": "ok",
            "person": {"nsid": "99@N00", "iconserver": "1234", "iconfarm": "5"},
        })
    )
    with FlickrClient("test-key") as client:
        person = client.get_person_info("99@N00")
    assert person["nsid"] == "99@N00"


@respx.mock
def test_api_error_raises() -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "Photo not found"})
    )
    with FlickrClient("test-key") as client, pytest.raises(ValueError, match="Photo not found"):
        client.get_photo_sizes("bad-id")


@respx.mock
def test_download_returns_bytes() -> None:
    respx.get("https://live.staticflickr.com/x/123_abc_q.jpg").mock(
        return_value=httpx.Response(200, content=b"\xff\xd8\xff")
    )
    with FlickrClient("test-key") as client:
        data = client.download("https://live.staticflickr.com/x/123_abc_q.jpg")
    assert data[:3] == b"\xff\xd8\xff"
