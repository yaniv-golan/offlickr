"""Download thumbnail images for favorited photos from Flickr."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from offlickr.fetch.client import FlickrClient
from offlickr.issues import IssueCollector

_PREFERRED = ("Large Square", "Square", "Small")


def pick_thumb_url(sizes: list[dict[str, Any]]) -> str | None:
    by_label: dict[str, str] = {str(s["label"]): str(s["source"]) for s in sizes}
    for label in _PREFERRED:
        if label in by_label:
            return by_label[label]
    return str(sizes[0]["source"]) if sizes else None


def fetch_fave_thumbnails(
    photo_ids: list[str],
    client: FlickrClient,
    output_dir: Path,
    *,
    on_progress: Callable[[], None] | None = None,
    collector: IssueCollector | None = None,
) -> dict[str, str]:
    """Return {photo_id: relative_path} for successfully downloaded thumbnails."""
    thumbs_dir = output_dir / "fave-thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for photo_id in photo_ids:
        dest = thumbs_dir / f"{photo_id}.jpg"
        rel = f"fave-thumbs/{photo_id}.jpg"
        if dest.exists():
            result[photo_id] = rel
            if on_progress:
                on_progress()
            continue
        try:
            sizes = client.get_photo_sizes(photo_id)
            url = pick_thumb_url(sizes)
            if url:
                tmp = dest.with_suffix(".tmp")
                tmp.write_bytes(client.download(url))
                tmp.rename(dest)
                result[photo_id] = rel
        except Exception as exc:
            dest.with_suffix(".tmp").unlink(missing_ok=True)
            if collector:
                collector.add("fetch.thumbnail", photo_id, str(exc))
        if on_progress:
            on_progress()
    return result
