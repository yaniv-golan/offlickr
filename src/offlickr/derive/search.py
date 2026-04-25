"""Build and write assets/search.json from an OfflickrArchive."""

from __future__ import annotations

import json
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from offlickr.model import OfflickrArchive


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


def _fold(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()


def build_search_index(archive: OfflickrArchive) -> list[dict[str, object]]:
    album_by_photo: dict[str, list[str]] = {}
    for album in archive.albums:
        for pid in album.photo_ids:
            album_by_photo.setdefault(pid, []).append(album.title)

    return [
        {
            "id": p.id,
            "t": _fold(p.title),
            "d": _fold(_strip_html(p.description_html)),
            "g": [_fold(t.tag) for t in p.tags],
            "a": [_fold(a) for a in album_by_photo.get(p.id, [])],
        }
        for p in archive.photos
    ]


def write_search_index(archive: OfflickrArchive, output_dir: Path) -> None:
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    index = build_search_index(archive)
    content = json.dumps(index, ensure_ascii=False)
    out_path = assets / "search.json"
    if out_path.exists() and out_path.read_text(encoding="utf-8") == content:
        return
    out_path.write_text(content, encoding="utf-8")
