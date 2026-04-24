"""Orchestrate external asset fetching and patch model.json in-place."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from offlickr.fetch.avatars import fetch_user_avatars
from offlickr.fetch.client import FlickrClient
from offlickr.fetch.thumbnails import fetch_fave_thumbnails
from offlickr.issues import IssueCollector


def run_fetch_external(
    output_dir: Path,
    api_key: str,
    *,
    include_thumbnails: bool = True,
    include_avatars: bool = True,
    on_progress: Callable[[str, int, int], None] | None = None,
    collector: IssueCollector | None = None,
) -> None:
    """Download avatars/thumbnails and patch output_dir/data/model.json in-place."""
    model_path = output_dir / "data" / "model.json"
    model: dict[str, Any] = json.loads(model_path.read_text(encoding="utf-8"))

    with FlickrClient(api_key) as client:
        if include_thumbnails:
            photo_ids = [f["photo_id"] for f in model.get("faves", [])]
            fetched = 0

            def _thumb_progress() -> None:
                nonlocal fetched
                fetched += 1
                if on_progress:
                    on_progress("thumbnails", fetched, len(photo_ids))

            thumb_map = fetch_fave_thumbnails(
                photo_ids, client, output_dir, on_progress=_thumb_progress,
                collector=collector,
            )
            for fave in model.get("faves", []):
                pid = fave["photo_id"]
                if pid in thumb_map:
                    path, w, h = thumb_map[pid]
                    fave["thumbnail_path"] = path
                    if w:
                        fave["thumbnail_width"] = w
                    if h:
                        fave["thumbnail_height"] = h

        if include_avatars:
            nsids = list(model.get("users", {}).keys())
            fetched_a = 0

            def _avatar_progress() -> None:
                nonlocal fetched_a
                fetched_a += 1
                if on_progress:
                    on_progress("avatars", fetched_a, len(nsids))

            known_screen_names = {
                nsid for nsid, u in model.get("users", {}).items()
                if u.get("screen_name")
            }
            avatar_map, screen_name_map = fetch_user_avatars(
                nsids, client, output_dir, on_progress=_avatar_progress,
                collector=collector, known_screen_names=known_screen_names,
            )
            for nsid, user in model.get("users", {}).items():
                if nsid in avatar_map:
                    user["avatar_path"] = avatar_map[nsid]
                if nsid in screen_name_map:
                    user["screen_name"] = screen_name_map[nsid]

    model_path.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
