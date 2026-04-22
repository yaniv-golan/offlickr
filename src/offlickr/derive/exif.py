"""Extract EXIF metadata from an image via Pillow."""

from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ExifTags import TAGS, Base

from offlickr.model import Exif

# Fields excluded from the raw dump entirely (noise / redundant)
_RAW_EXCLUDE = frozenset(
    [
        "XResolution",
        "YResolution",
        "YCbCrPositioning",
        "ComponentsConfiguration",
        "ExifVersion",
        "SubsecTimeOriginal",
        "SubSecTimeOriginal",
        "OffsetTime",
        "OffsetTimeOriginal",
        "OffsetTimeDigitized",
        "FlashPixVersion",
        "InteropIndex",
        "InteropOffset",
        "ThumbnailOffset",
        "ThumbnailLength",
        "JPEGInterchangeFormat",
        "JPEGInterchangeFormatLength",
    ]
)

_EXPOSURE_PROGRAM = {
    0: "Not defined",
    1: "Manual",
    2: "Normal",
    3: "Aperture priority",
    4: "Shutter priority",
    5: "Creative",
    6: "Action",
    7: "Portrait",
    8: "Landscape",
}
_METERING = {
    0: "Unknown",
    1: "Average",
    2: "Center-weighted",
    3: "Spot",
    4: "Multi-spot",
    5: "Multi-segment",
    6: "Partial",
    255: "Other",
}
_ORIENTATION = {
    1: "Horizontal",
    2: "Mirrored horizontal",
    3: "Rotated 180°",
    4: "Mirrored vertical",
    5: "Mirrored horizontal, rotated 270° CW",
    6: "Rotated 90° CW",
    7: "Mirrored horizontal, rotated 90° CW",
    8: "Rotated 270° CW",
}
_COLOR_SPACE = {1: "sRGB", 65535: "Uncalibrated"}
_WHITE_BALANCE = {0: "Auto", 1: "Manual"}


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


def _flash_str(val: Any) -> str | None:
    if val is None:
        return None
    v = int(val)
    fired = bool(v & 0x1)
    if not fired:
        return "Off, did not fire"
    return "Fired"


def extract_exif(image_path: Path) -> Exif | None:  # noqa: PLR0915
    try:
        with Image.open(image_path) as img:
            raw = img.getexif()
            ifd = img.getexif().get_ifd(0x8769)  # ExifIFD
    except Exception:
        return None
    if not raw:
        return None

    def _get(tag: int) -> Any:
        v = raw.get(tag)
        if v is None:
            v = ifd.get(tag)
        return v

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

    focal_35mm_raw = _get(Base.FocalLengthIn35mmFilm)
    focal_35mm = int(focal_35mm_raw) if focal_35mm_raw else None

    exp_prog_raw = _get(Base.ExposureProgram)
    exposure_mode = _EXPOSURE_PROGRAM.get(int(exp_prog_raw)) if exp_prog_raw is not None else None

    flash_raw = _get(Base.Flash)
    flash = _flash_str(flash_raw)

    metering_raw = _get(Base.MeteringMode)
    metering_mode = _METERING.get(int(metering_raw)) if metering_raw is not None else None

    wb_raw = _get(Base.WhiteBalance)
    white_balance = _WHITE_BALANCE.get(int(wb_raw)) if wb_raw is not None else None

    cs_raw = _get(Base.ColorSpace)
    color_space = _COLOR_SPACE.get(int(cs_raw)) if cs_raw is not None else None

    orient_raw = _get(Base.Orientation)
    orientation = _ORIENTATION.get(int(orient_raw)) if orient_raw is not None else None

    software_raw = _get(Base.Software)
    software = str(software_raw).strip() if software_raw else None

    px_w = _get(Base.ExifImageWidth)
    px_h = _get(Base.ExifImageHeight)
    image_width = int(px_w) if px_w is not None else None
    image_height = int(px_h) if px_h is not None else None

    artist_raw = _get(Base.Artist)
    artist = str(artist_raw).strip() if artist_raw else None

    copyright_raw = _get(Base.Copyright)
    copyright_notice = str(copyright_raw).strip() if copyright_raw else None

    # Build raw dump from all known tags
    raw_fields: dict[str, str] = {}
    all_tags: dict[int, Any] = {**dict(raw), **dict(ifd)}
    for tag_id, value in all_tags.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        if tag_name in _RAW_EXCLUDE:
            continue
        with contextlib.suppress(Exception):
            raw_fields[str(tag_name)] = str(value).strip()

    if not any([make, model_, lens, focal, aperture, shutter, iso, dt]):
        return None
    return Exif(
        camera_make=str(make).strip() if make else None,
        camera_model=str(model_).strip() if model_ else None,
        lens_model=str(lens).strip() if lens else None,
        focal_length_mm=round(focal, 2) if focal else None,
        focal_length_35mm=focal_35mm,
        aperture=round(aperture, 2) if aperture else None,
        shutter_speed=shutter,
        iso=iso,
        date_taken=dt,
        exposure_mode=exposure_mode,
        flash=flash,
        metering_mode=metering_mode,
        white_balance=white_balance,
        color_space=color_space,
        orientation=orientation,
        software=software,
        image_width=image_width,
        image_height=image_height,
        raw_fields=raw_fields,
        artist=artist,
        copyright_notice=copyright_notice,
    )
