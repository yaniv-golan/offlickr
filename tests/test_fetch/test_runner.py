# tests/test_fetch/test_runner.py
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import respx

from offlickr.fetch.runner import run_fetch_external
from offlickr.issues import IssueCollector

_REST_RE = re.compile(r"https://api\.flickr\.com/services/rest/.*")
_THUMB_URL = "https://live.staticflickr.com/x/98765432_abc_q.jpg"
_AVATAR_URL = "https://farm5.staticflickr.com/1234/buddyicons/99@N00.jpg"


def _make_model(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    model = {
        "faves": [{"photo_id": "98765432", "photo_url": "http://flic.kr/p/X"}],
        "users": {"99@N00": {"nsid": "99@N00"}},
    }
    p = data_dir / "model.json"
    p.write_text(json.dumps(model))
    return tmp_path


@respx.mock
def test_run_fetch_external_updates_thumbnail_path(tmp_path: Path) -> None:
    output_dir = _make_model(tmp_path)
    respx.get(_REST_RE).mock(side_effect=[
        httpx.Response(200, json={
            "stat": "ok",
            "sizes": {"size": [{"label": "Large Square", "source": _THUMB_URL}]},
        }),
        httpx.Response(200, json={
            "stat": "ok",
            "person": {"nsid": "99@N00", "iconserver": "1234", "iconfarm": "5",
                       "username": {"_content": "flickruser"}},
        }),
    ])
    respx.get(_THUMB_URL).mock(return_value=httpx.Response(200, content=b"IMG"))
    respx.get(_AVATAR_URL).mock(return_value=httpx.Response(200, content=b"AVT"))

    run_fetch_external(output_dir=output_dir, api_key="key")

    model = json.loads((output_dir / "data" / "model.json").read_text())
    assert model["faves"][0]["thumbnail_path"] == "fave-thumbs/98765432.jpg"
    assert model["users"]["99@N00"]["avatar_path"] == "avatars/99@N00.jpg"
    assert model["users"]["99@N00"]["screen_name"] == "flickruser"


@respx.mock
def test_run_fetch_external_collects_errors(tmp_path: Path) -> None:
    output_dir = _make_model(tmp_path)
    # Both thumbnail and avatar API calls fail
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={"stat": "fail", "message": "not found"})
    )
    collector = IssueCollector()
    run_fetch_external(output_dir=output_dir, api_key="key", collector=collector)
    assert collector.has_issues()
    cats = collector.by_category()
    assert "fetch.thumbnail" in cats or "fetch.avatar" in cats


@respx.mock
def test_run_fetch_external_backfills_screen_name_for_cached_avatar(tmp_path: Path) -> None:
    """Avatar file already present but screen_name missing → API called, file not re-downloaded."""
    output_dir = _make_model(tmp_path)
    (output_dir / "avatars").mkdir()
    (output_dir / "avatars" / "99@N00.jpg").write_bytes(b"CACHED")
    respx.get(_REST_RE).mock(side_effect=[
        httpx.Response(200, json={"stat": "fail", "message": "not found"}),  # thumb
        httpx.Response(200, json={
            "stat": "ok",
            "person": {"nsid": "99@N00", "iconserver": "1234", "iconfarm": "5",
                       "username": {"_content": "backfilled_name"}},
        }),
    ])

    run_fetch_external(output_dir=output_dir, api_key="key")

    model = json.loads((output_dir / "data" / "model.json").read_text())
    assert model["users"]["99@N00"]["screen_name"] == "backfilled_name"
    assert (output_dir / "avatars" / "99@N00.jpg").read_bytes() == b"CACHED"


@respx.mock
def test_run_fetch_external_skips_api_when_screen_name_already_known(tmp_path: Path) -> None:
    """Avatar file AND screen_name already present → no API call at all."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    model = {
        "faves": [],
        "users": {"99@N00": {"nsid": "99@N00", "screen_name": "already_known"}},
    }
    (data_dir / "model.json").write_text(json.dumps(model))
    (tmp_path / "avatars").mkdir()
    (tmp_path / "avatars" / "99@N00.jpg").write_bytes(b"CACHED")

    run_fetch_external(output_dir=tmp_path, api_key="key", include_thumbnails=False)

    # respx would raise if any HTTP call was made (no mocks registered)
    result = json.loads((tmp_path / "data" / "model.json").read_text())
    assert result["users"]["99@N00"]["screen_name"] == "already_known"


@respx.mock
def test_run_fetch_external_include_thumbnails_only(tmp_path: Path) -> None:
    output_dir = _make_model(tmp_path)
    respx.get(_REST_RE).mock(
        return_value=httpx.Response(200, json={
            "stat": "ok",
            "sizes": {"size": [{"label": "Large Square", "source": _THUMB_URL}]},
        })
    )
    respx.get(_THUMB_URL).mock(return_value=httpx.Response(200, content=b"IMG"))

    run_fetch_external(output_dir=output_dir, api_key="key", include_avatars=False)

    model = json.loads((output_dir / "data" / "model.json").read_text())
    assert "thumbnail_path" in model["faves"][0]
    assert "avatar_path" not in model["users"]["99@N00"]
