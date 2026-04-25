"""Synthetic image fixtures for derive tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PIL.ExifTags import Base


@pytest.fixture()
def small_jpeg(tmp_path: Path) -> Path:
    """800x600 JPEG — no EXIF."""
    img = Image.new("RGB", (800, 600), color=(200, 100, 50))
    path = tmp_path / "slug_99001_o.jpg"
    img.save(path, "JPEG", quality=85)
    return path


@pytest.fixture()
def jpeg_with_exif(tmp_path: Path) -> Path:
    """120x80 JPEG with Make/Model/ISO EXIF."""
    img = Image.new("RGB", (120, 80))
    exif = img.getexif()
    exif[Base.Make] = "ACME"
    exif[Base.Model] = "Cam-1"
    exif[Base.ISOSpeedRatings] = 400
    path = tmp_path / "exif_99002_o.jpg"
    img.save(path, "JPEG", exif=exif.tobytes())
    return path


@pytest.fixture()
def small_png(tmp_path: Path) -> Path:
    img = Image.new("RGB", (640, 480), color=(50, 150, 200))
    path = tmp_path / "slug_99003_o.png"
    img.save(path, "PNG")
    return path


@pytest.fixture()
def tiny_mp4(tmp_path: Path) -> Path:
    path = tmp_path / "slug_99004_o.mp4"
    path.write_bytes(b"\x00" * 32)
    return path
