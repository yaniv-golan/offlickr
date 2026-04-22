"""Download thumbnail images for favorited photos from Flickr."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from offlickr.fetch.client import FlickrClient
from offlickr.issues import IssueCollector

# Prefer sizes that preserve natural aspect ratios; fall back to square crops.
_PREFERRED = ("Small 320", "Small", "Medium 640", "Medium", "Large Square", "Square")


def pick_thumb(sizes: list[dict[str, Any]]) -> tuple[str, int, int] | None:
    """Return (url, width, height) for the best available size, or None."""
    by_label: dict[str, dict[str, Any]] = {str(s["label"]): s for s in sizes}
    for label in _PREFERRED:
        if label in by_label:
            s = by_label[label]
            return str(s["source"]), int(s.get("width", 0)), int(s.get("height", 0))
    if sizes:
        s = sizes[0]
        return str(s["source"]), int(s.get("width", 0)), int(s.get("height", 0))
    return None


def pick_thumb_url(sizes: list[dict[str, Any]]) -> str | None:
    result = pick_thumb(sizes)
    return result[0] if result else None


def _read_image_size(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return 0, 0


def fetch_fave_thumbnails(
    photo_ids: list[str],
    client: FlickrClient,
    output_dir: Path,
    *,
    on_progress: Callable[[], None] | None = None,
    collector: IssueCollector | None = None,
) -> dict[str, tuple[str, int, int]]:
    """Return {photo_id: (relative_path, width, height)} for downloaded thumbnails."""
    thumbs_dir = output_dir / "fave-thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, tuple[str, int, int]] = {}
    for photo_id in photo_ids:
        dest = thumbs_dir / f"{photo_id}.jpg"
        rel = f"fave-thumbs/{photo_id}.jpg"
        if dest.exists():
            result[photo_id] = (rel, *_read_image_size(dest))
            if on_progress:
                on_progress()
            continue
        try:
            sizes = client.get_photo_sizes(photo_id)
            picked = pick_thumb(sizes)
            if picked:
                url, w, h = picked
                tmp = dest.with_suffix(".tmp")
                tmp.write_bytes(client.download(url))
                tmp.rename(dest)
                result[photo_id] = (rel, w, h)
        except Exception as exc:
            dest.with_suffix(".tmp").unlink(missing_ok=True)
            if collector:
                collector.add("fetch.thumbnail", photo_id, str(exc))
        if on_progress:
            on_progress()
    return result
