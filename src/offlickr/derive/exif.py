"""Extract EXIF metadata from an image via Pillow."""

from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ExifTags import Base

from offlickr.model import Exif


def _to_float(val: Any) -> float | None:
    try:
        if hasattr(val, "numerator") and hasattr(val, "denominator"):
            return val.numerator / val.denominator if val.denominator else None
        return float(val)
    except (TypeError, ZeroDivisionError):
        return None


def _shutter_str(val: Any) -> str | None:
    f = _to_float(val)
    if f is None or f <= 0:
        return None
    if f >= 1:
        return f"{int(f)}s"
    return f"1/{round(1 / f)}s"


def extract_exif(image_path: Path) -> Exif | None:
    try:
        with Image.open(image_path) as img:
            raw = img.getexif()
    except Exception:
        return None
    if not raw:
        return None

    def _get(tag: int) -> Any:
        return raw.get(tag)

    make = _get(Base.Make)
    model_ = _get(Base.Model)
    lens = _get(Base.LensModel)
    focal = _to_float(_get(Base.FocalLength))
    aperture = _to_float(_get(Base.FNumber))
    shutter = _shutter_str(_get(Base.ExposureTime))
    iso_raw = _get(Base.ISOSpeedRatings)
    iso = int(iso_raw) if iso_raw is not None else None
    dt_str = _get(Base.DateTimeOriginal)
    dt: datetime | None = None
    if dt_str:
        with contextlib.suppress(ValueError):
            dt = datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")

    if not any([make, model_, lens, focal, aperture, shutter, iso, dt]):
        return None
    return Exif(
        camera_make=str(make).strip() if make else None,
        camera_model=str(model_).strip() if model_ else None,
        lens_model=str(lens).strip() if lens else None,
        focal_length_mm=round(focal, 2) if focal else None,
        aperture=round(aperture, 2) if aperture else None,
        shutter_speed=shutter,
        iso=iso,
        date_taken=dt,
    )
