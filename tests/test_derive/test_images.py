"""Tests for single-image processing."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from PIL import Image

from offlickr.derive.images import process_image


def test_process_image_creates_thumb(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    thumb = tmp_path / "thumbs" / "99001.webp"
    assert thumb.is_file()
    with Image.open(thumb) as img:
        assert max(img.size) <= 240


def test_process_image_creates_display(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    display = tmp_path / "display" / "99001.webp"
    assert display.is_file()
    with Image.open(display) as img:
        assert max(img.size) <= 1600


def test_process_image_copies_original(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    orig = tmp_path / "originals" / "99001.jpg"
    assert orig.is_file()
    assert orig.stat().st_size > 0


def test_process_image_returns_dimensions(small_jpeg: Path, tmp_path: Path) -> None:
    w, h, exif = process_image(small_jpeg, "99001", tmp_path)
    assert w == 800
    assert h == 600
    assert exif is None  # small_jpeg has no EXIF


def test_process_image_extracts_exif(jpeg_with_exif: Path, tmp_path: Path) -> None:
    _, _, exif = process_image(jpeg_with_exif, "99002", tmp_path)
    assert exif is not None
    assert exif.camera_make == "ACME"


def test_process_image_idempotent(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    thumb = tmp_path / "thumbs" / "99001.webp"
    mtime_before = thumb.stat().st_mtime
    process_image(small_jpeg, "99001", tmp_path)
    assert thumb.stat().st_mtime == mtime_before


def test_process_png(small_png: Path, tmp_path: Path) -> None:
    w, h, _ = process_image(small_png, "99003", tmp_path)
    assert w == 640
    assert h == 480
    assert (tmp_path / "originals" / "99003.png").is_file()


def test_process_image_thumb_not_larger_than_display(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    thumb = tmp_path / "thumbs" / "99001.webp"
    display = tmp_path / "display" / "99001.webp"
    with Image.open(thumb) as t, Image.open(display) as d:
        assert t.size[0] <= d.size[0]
        assert t.size[1] <= d.size[1]


def test_heic_import_optional() -> None:
    """Importing derive.images must not raise even if pillow_heif is absent."""
    original = sys.modules.get("pillow_heif")
    sys.modules["pillow_heif"] = None  # type: ignore[assignment]
    try:
        if "offlickr.derive.images" in sys.modules:
            del sys.modules["offlickr.derive.images"]
        mod = importlib.import_module("offlickr.derive.images")
        assert mod is not None
    finally:
        if original is None:
            del sys.modules["pillow_heif"]
        else:
            sys.modules["pillow_heif"] = original
        if "offlickr.derive.images" in sys.modules:
            del sys.modules["offlickr.derive.images"]


def test_process_image_thumb_max_dim_le_display(small_jpeg: Path, tmp_path: Path) -> None:
    process_image(small_jpeg, "99001", tmp_path)
    thumb = tmp_path / "thumbs" / "99001.webp"
    display = tmp_path / "display" / "99001.webp"
    with Image.open(thumb) as t, Image.open(display) as d:
        assert max(t.size) <= max(d.size)


def test_process_image_cache_hit_returns_known_dims(small_jpeg: Path, tmp_path: Path) -> None:
    """Second call with known dims returns those dims without regenerating thumbnails."""
    process_image(small_jpeg, "99001", tmp_path)  # first run — populates cache

    thumb = tmp_path / "thumbs" / "99001.webp"
    mtime_before = thumb.stat().st_mtime

    w2, h2, _exif = process_image(small_jpeg, "99001", tmp_path, known_w=800, known_h=600)
    assert (w2, h2) == (800, 600)

    # Thumbnail must NOT have been regenerated
    assert thumb.stat().st_mtime == mtime_before, "Thumbnail was regenerated on cache hit"
