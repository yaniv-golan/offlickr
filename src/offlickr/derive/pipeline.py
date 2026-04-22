"""Stage 2 orchestrator: parallel media processing + search index."""

from __future__ import annotations

import json
import multiprocessing
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from offlickr.derive.images import process_image
from offlickr.derive.search import write_search_index
from offlickr.derive.video import process_video
from offlickr.issues import IssueCollector
from offlickr.model import Exif, OfflickrArchive


def _write_text_atomic(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _worker_init() -> None:
    """Called once per spawned worker; images.py already sets MAX_IMAGE_PIXELS on import."""
    pass


def _process_one(args: tuple[str, str, str, str, int, int, int]) -> dict[str, Any]:
    """Worker: process one photo's media. Returns partial update dict."""
    photo_id, filename, source_dir_str, output_dir_str, known_w, known_h, rotation = args
    src = Path(source_dir_str) / filename
    output_dir = Path(output_dir_str)
    ext = Path(filename).suffix.lower()
    kind = "video" if ext in {".mp4", ".mov", ".m4v"} else "image"
    result: dict[str, Any] = {"photo_id": photo_id}
    if not src.is_file():
        result["error"] = f"media file not found: {src.name}"
        return result
    try:
        if kind == "image":
            w, h, exif = process_image(
                src, photo_id, output_dir, known_w=known_w, known_h=known_h,
                rotation=rotation,
            )
            result["width"] = w
            result["height"] = h
            if exif:
                result["exif"] = exif.model_dump(exclude_none=True)
        else:
            process_video(src, photo_id, output_dir)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def run_derive(  # noqa: PLR0912
    *,
    output_dir: Path,
    jobs: int = 0,
    on_progress: Callable[[], None] | None = None,
    collector: IssueCollector | None = None,
) -> None:
    model_path = output_dir / "data" / "model.json"
    media_index_path = output_dir / "data" / "media-index.json"
    if not model_path.exists():
        raise FileNotFoundError(f"model.json not found at {model_path}")
    if not media_index_path.exists():
        raise FileNotFoundError(f"media-index.json not found at {media_index_path}")

    archive = OfflickrArchive.model_validate(json.loads(model_path.read_text(encoding="utf-8")))
    media_index: list[dict[str, str]] = json.loads(media_index_path.read_text(encoding="utf-8"))
    source_dir = archive.export.source_dir

    if jobs <= 0:
        jobs = min(os.cpu_count() or 1, 4)

    # Dimensions already stored from a previous derive run — skip image re-open on cache hit.
    photo_dims: dict[str, tuple[int, int]] = {
        p.id: (p.media.width or 0, p.media.height or 0)
        for p in archive.photos
        if p.media and p.media.width and p.media.height
    }
    photo_rotation: dict[str, int] = {p.id: p.rotation for p in archive.photos}

    args_list = [
        (
            entry["photo_id"],
            entry["filename"],
            source_dir,
            str(output_dir),
            *photo_dims.get(entry["photo_id"], (0, 0)),
            photo_rotation.get(entry["photo_id"], 0),
        )
        for entry in media_index
    ]

    updates: dict[str, dict[str, Any]] = {}

    def _collect(res: dict[str, Any]) -> None:
        pid = res.pop("photo_id")
        updates[pid] = res
        if on_progress:
            on_progress()

    if jobs == 1:
        for a in args_list:
            _collect(_process_one(a))
    else:
        mp_ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=jobs, mp_context=mp_ctx, initializer=_worker_init
        ) as pool:
            for fut in as_completed(pool.submit(_process_one, a) for a in args_list):
                _collect(fut.result())

    if collector:
        for photo_id, entry in updates.items():
            if "error" in entry:
                collector.add("derive.media", photo_id, entry["error"])

    for photo in archive.photos:
        upd = updates.get(photo.id)
        if upd and photo.media:
            if "width" in upd:
                photo.media.width = upd["width"]
            if "height" in upd:
                photo.media.height = upd["height"]
            if "exif" in upd:
                photo.exif = Exif.model_validate(upd["exif"])

    _write_text_atomic(model_path, archive.model_dump_json(indent=2, exclude_none=True))

    write_search_index(archive, output_dir)
