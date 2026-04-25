"""Parser for photo_<id>.json files. Joins with media-file index. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.ingest.media import build_media_index, parse_media_filename
from offlickr.issues import IssueCollector
from offlickr.model import Media, Photo
from offlickr.render.sanitize import sanitize_html

VIDEO_EXTS = {".mp4", ".mov", ".m4v"}


def _media_from_path(path: Path) -> Media:
    ext = path.suffix.lower()
    kind = "video" if ext in VIDEO_EXTS else "image"
    return Media(
        filename=path.name,
        ext=ext,
        kind=kind,
        bytes=path.stat().st_size,
    )


def _slug_from_filename(name: str) -> str | None:
    parsed = parse_media_filename(name)
    if parsed is None:
        return None
    slug = parsed[0]
    return slug or None


def load_photos(source_dir: Path, collector: IssueCollector | None = None) -> list[Photo]:
    media_index = build_media_index(source_dir)
    photos: list[Photo] = []
    for path in sorted(source_dir.glob("photo_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            photo = Photo.from_json(data)
            photo = photo.model_copy(
                update={
                    "description_html": sanitize_html(photo.description_html),
                    "comments": [
                        c.model_copy(update={"body_html": sanitize_html(c.body_html)})
                        for c in photo.comments
                    ],
                }
            )
            media_path = media_index.get(photo.id)
            if media_path is not None:
                photo = photo.model_copy(
                    update={
                        "media": _media_from_path(media_path),
                        "slug": _slug_from_filename(media_path.name),
                    }
                )
            else:
                photo = photo.model_copy(update={"slug": f"photo-{photo.id}"})
            photos.append(photo)
        except Exception as exc:
            photo_id = path.stem.removeprefix("photo_")
            if collector:
                collector.add("ingest.photo", photo_id, str(exc))
            continue

    photos.sort(
        key=lambda p: p.date_taken or p.date_imported,
        reverse=True,
    )
    return photos
