# tests/test_fetch/test_avatars.py
from __future__ import annotations

import re
from pathlib import Path

import httpx
import respx

from offlickr.fetch.avatars import avatar_url, fetch_user_avatars
from offlickr.fetch.client import FlickrClient
from offlickr.issues import IssueCollector

_REST_RE = re.compile(r"https://api\.flickr\.com/services/rest/.*")


def test_avatar_url_with_iconserver() -> None:
    person = {"nsid": "99@N00", "iconserver": "1234", "iconfarm": "5"}
    assert avatar_url(person) == "https://farm5.staticflickr.com/1234/buddyicons/99@N00.jpg"


def test_avatar_url_no_icon_returns_none() -> None:
    person = {"nsid": "99@N00", "iconserver": "0", "iconfarm": "0"}
    assert avatar_url(person) is None


@respx.mock
def test_fetch_user_avatars_downloads_and_returns_paths(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(
            200,
            json={
                "stat": "ok",
                "person": {
                    "nsid": "99@N00",
                    "iconserver": "1234",
                    "iconfarm": "5",
                    "username": {"_content": "testuser"},
                },
            },
        )
    )
    respx.get("https://farm5.staticflickr.com/1234/buddyicons/99@N00.jpg").mock(
        return_value=httpx.Response(200, content=b"AVATAR_DATA")
    )
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(["99@N00"], client, tmp_path)
    assert avatar_map == {"99@N00": "avatars/99@N00.jpg"}
    assert screen_names == {"99@N00": "testuser"}
    assert (tmp_path / "avatars" / "99@N00.jpg").read_bytes() == b"AVATAR_DATA"


@respx.mock
def test_fetch_user_avatars_returns_screen_name_even_without_icon(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(
            200,
            json={
                "stat": "ok",
                "person": {
                    "nsid": "99@N00",
                    "iconserver": "0",
                    "iconfarm": "0",
                    "username": {"_content": "noicon_user"},
                },
            },
        )
    )
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(["99@N00"], client, tmp_path)
    assert avatar_map == {}
    assert screen_names == {"99@N00": "noicon_user"}


@respx.mock
def test_fetch_user_avatars_skips_existing_when_screen_name_known(tmp_path: Path) -> None:
    (tmp_path / "avatars").mkdir()
    (tmp_path / "avatars" / "99@N00.jpg").write_bytes(b"OLD")
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(
            ["99@N00"], client, tmp_path, known_screen_names={"99@N00"}
        )
    assert avatar_map == {"99@N00": "avatars/99@N00.jpg"}
    assert screen_names == {}
    assert (tmp_path / "avatars" / "99@N00.jpg").read_bytes() == b"OLD"


@respx.mock
def test_fetch_user_avatars_fetches_screen_name_when_avatar_cached_but_name_unknown(
    tmp_path: Path,
) -> None:
    (tmp_path / "avatars").mkdir()
    (tmp_path / "avatars" / "99@N00.jpg").write_bytes(b"OLD")
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(
            200,
            json={
                "stat": "ok",
                "person": {
                    "nsid": "99@N00",
                    "iconserver": "1234",
                    "iconfarm": "5",
                    "username": {"_content": "belated_name"},
                },
            },
        )
    )
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(["99@N00"], client, tmp_path)
    assert avatar_map == {"99@N00": "avatars/99@N00.jpg"}
    assert screen_names == {"99@N00": "belated_name"}
    assert (tmp_path / "avatars" / "99@N00.jpg").read_bytes() == b"OLD"  # not re-downloaded


@respx.mock
def test_fetch_user_avatars_silently_skips_api_error(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "User not found"})
    )
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(["99@N00"], client, tmp_path)
    assert avatar_map == {}
    assert screen_names == {}


@respx.mock
def test_fetch_user_avatars_reports_api_error(tmp_path: Path) -> None:
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "User not found"})
    )
    collector = IssueCollector()
    with FlickrClient("key") as client:
        avatar_map, screen_names = fetch_user_avatars(
            ["99@N00"], client, tmp_path, collector=collector
        )
    assert avatar_map == {}
    assert screen_names == {}
    assert collector.has_issues()
    cats = collector.by_category()
    assert "fetch.avatar" in cats
    assert cats["fetch.avatar"][0].item_id == "99@N00"
    assert cats["fetch.avatar"][0].reason != ""
