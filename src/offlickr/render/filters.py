"""Jinja2 template filters for offlickr."""

from __future__ import annotations

import re
from datetime import datetime
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
    return dt.strftime("%B %-d, %Y")


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


def register_filters(env: Environment) -> None:
    env.filters["format_date"] = format_date
    env.filters["format_date_str"] = format_date_str
    env.filters["privacy_label"] = privacy_label
    env.filters["striptags"] = striptags
    env.filters["format_number"] = format_number
    env.filters["add_geo_pin"] = add_geo_pin
    env.filters["rewrite_urls"] = rewrite_urls
    env.filters["safe_url"] = safe_url
