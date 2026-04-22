"""HTML sanitization for user-supplied content from the Flickr export."""

from __future__ import annotations

import re

import nh3

ALLOWED_TAGS: set[str] = {
    "a",
    "b",
    "i",
    "em",
    "strong",
    "br",
    "p",
    "blockquote",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
}

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "rel", "title", "class"},
    "*": {"title"},
}

_SAFE_URL_SCHEMES = {"http", "https", "mailto"}
_EXTERNAL_REL = "noopener noreferrer external"
_REQUIRED_REL = frozenset({"noopener", "noreferrer", "external"})
# Captures the full opening <a> tag including closing >
_A_TAG_RE = re.compile(r"(<a\b[^>]*>)", re.IGNORECASE)
_REL_ATTR_RE = re.compile(r'\brel="([^"]*)"', re.IGNORECASE)


def _stamp_rel(match: re.Match[str]) -> str:
    tag = match.group(1)
    if "href=" not in tag.lower():
        return tag
    m = _REL_ATTR_RE.search(tag)
    if m:
        existing = set(m.group(1).split())
        if _REQUIRED_REL.issubset(existing):
            return tag
        merged = " ".join(sorted(existing | _REQUIRED_REL))
        return tag[: m.start()] + f'rel="{merged}"' + tag[m.end() :]
    return tag[:-1] + f' rel="{_EXTERNAL_REL}">'


def sanitize_html(html: str) -> str:
    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel=None,
        url_schemes=_SAFE_URL_SCHEMES,
    )
    return _A_TAG_RE.sub(_stamp_rel, cleaned)


_HREF_ATTR_RE = re.compile(r'href="([^"]+)"')


def rewrite_photo_urls(html: str, url_map: dict[str, str]) -> str:
    """Replace href values that appear in url_map with their local equivalents."""
    if not url_map:
        return html

    def _replace(match: re.Match[str]) -> str:
        url = match.group(1)
        local = url_map.get(url)
        return f'href="{local}"' if local else match.group(0)

    return _HREF_ATTR_RE.sub(_replace, html)
