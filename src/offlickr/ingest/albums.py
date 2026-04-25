"""Parser for albums.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import Album
from offlickr.render.sanitize import sanitize_html


def load_albums(source_dir: Path) -> list[Album]:
    path = source_dir / "albums.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    albums = [Album.from_json(a) for a in data.get("albums", [])]
    return [
        a.model_copy(update={"description_html": sanitize_html(a.description_html)}) for a in albums
    ]
