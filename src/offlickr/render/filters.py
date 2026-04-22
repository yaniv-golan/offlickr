"""Jinja2 template filters for offlickr."""

from __future__ import annotations

import re
from datetime import datetime
from math import gcd
from typing import Any, cast
from urllib.parse import urlparse

from jinja2 import Environment, pass_environment
from jinja2 import Environment as _JinjaEnv

from offlickr.render.sanitize import rewrite_photo_urls as _rewrite_photo_urls

_PRIVACY_LABELS = {
    "public": "Public",
    "friends": "Friends",
    "family": "Family",
    "friends-family": "Friends & Family",
    "private": "Private",
}


def format_date(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.hour == 0 and dt.minute == 0:
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    return f"{dt.strftime('%B')} {dt.day}, {dt.year} · {dt.strftime('%H:%M')}"


def format_date_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return format_date(value)
    try:
        return format_date(datetime.fromisoformat(str(value)))
    except (ValueError, TypeError):
        return str(value)


def privacy_label(value: str) -> str:
    return _PRIVACY_LABELS.get(value, value)


def striptags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def format_number(value: object) -> str:
    try:
        return f"{int(value):,}"  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return str(value)


def add_geo_pin(svg_content: str, lat: float, lng: float) -> str:
    """Inject a pin circle into a world SVG string (equirectangular projection)."""
    m = re.search(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', svg_content)
    if not m:
        return svg_content
    W, H = float(m.group(1)), float(m.group(2))
    x = (lng + 180) / 360 * W
    y = (90 - lat) / 180 * H
    r = max(W, H) * 0.010
    pin = (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
        f'fill="#cc0000" stroke="#fff" stroke-width="{r * 0.4:.1f}"/>'
    )
    return svg_content.replace("</svg>", f"{pin}</svg>", 1)


@pass_environment
def rewrite_urls(env: _JinjaEnv, html: str, base_url: str) -> str:
    """Jinja2 filter: rewrite Flickr photo page URLs to local relative paths."""
    url_map = cast("dict[str, str]", env.globals.get("photo_url_map", {}))
    if not url_map:
        return html
    prefixed = {k: base_url + v for k, v in url_map.items()}
    return _rewrite_photo_urls(html, prefixed)


def safe_url(url: str | None) -> str:
    """Return url only when the scheme is http or https; empty string otherwise."""
    if not url:
        return ""
    try:
        scheme = urlparse(url).scheme.lower()
    except Exception:
        return ""
    return url if scheme in ("http", "https") else ""


def is_flickr_url(url: str | None) -> bool:
    """Return True when url belongs to flickr.com or a subdomain."""
    if not url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host == "flickr.com" or host.endswith(".flickr.com")


def photo_title(title: str) -> str:
    """Return title if non-empty, else '(untitled)'."""
    return title.strip() or "(untitled)"


def format_camera(make: str | None, model: str | None) -> str:
    """Combine make and model, stripping make prefix when model already starts with it."""
    make = (make or "").strip()
    model = (model or "").strip()
    if not make:
        return model
    if not model:
        return make
    if model.lower().startswith(make.lower()):
        return model
    return f"{make} {model}"


def format_focal_mm(mm: float | None) -> str:
    """Format focal length: integer if whole number, else one decimal place."""
    if mm is None:
        return ""
    if mm == int(mm):
        return f"{int(mm)}mm"
    return f"{mm:.1f}mm"


def format_megapixels(w: int | None, h: int | None) -> str:
    if not w or not h:
        return ""
    return f"{w * h / 1_000_000:.1f} MP"


def format_aspect(w: int | None, h: int | None) -> str:
    if not w or not h:
        return ""
    g = gcd(w, h)
    return f"{w // g}:{h // g}"


def format_filesize(size: int | None) -> str:
    if size is None:
        return ""
    for unit, threshold in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if size >= threshold:
            val = size / threshold
            return f"{val:.1f} {unit}" if val < 100 else f"{int(val)} {unit}"
    return f"{size} B"


_MEDIA_TYPE_MAP = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".gif": "GIF",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".heic": "HEIC",
    ".heif": "HEIF",
    ".webp": "WebP",
    ".mp4": "MP4",
    ".mov": "MOV",
    ".m4v": "M4V",
}


def format_media_type(ext: str | None) -> str:
    if not ext:
        return ""
    return _MEDIA_TYPE_MAP.get(ext.lower(), ext.lstrip(".").upper())


def month_name(dt: datetime | None) -> str:
    return dt.strftime("%b") if dt else ""


def month_name_full(dt: datetime | None) -> str:
    return dt.strftime("%B") if dt else ""


def date_short(dt: datetime | None) -> str:
    """Format a date as '20 Sep 2024' — short month, no comma, no leading zero."""
    if dt is None:
        return ""
    return f"{dt.day} {dt.strftime('%b')} {dt.year}"


def register_filters(env: Environment) -> None:
    env.filters["format_date"] = format_date
    env.filters["date_short"] = date_short
    env.filters["format_datetime"] = format_datetime
    env.filters["format_date_str"] = format_date_str
    env.filters["privacy_label"] = privacy_label
    env.filters["striptags"] = striptags
    env.filters["format_number"] = format_number
    env.filters["add_geo_pin"] = add_geo_pin
    env.filters["rewrite_urls"] = rewrite_urls
    env.filters["safe_url"] = safe_url
    env.filters["is_flickr_url"] = is_flickr_url
    env.filters["month_name"] = month_name
    env.filters["month_name_full"] = month_name_full
    env.filters["photo_title"] = photo_title
    env.filters["format_camera"] = format_camera
    env.filters["format_focal_mm"] = format_focal_mm
    env.filters["format_megapixels"] = format_megapixels
    env.filters["format_aspect"] = format_aspect
    env.filters["format_filesize"] = format_filesize
    env.filters["format_media_type"] = format_media_type
