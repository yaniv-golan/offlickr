"""Parser for galleries.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import Gallery
from offlickr.render.sanitize import sanitize_html


def load_galleries(source_dir: Path) -> list[Gallery]:
    path = source_dir / "galleries.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    galleries = [Gallery.from_json(g) for g in data.get("galleries", [])]
    return [
        g.model_copy(update={"description_html": sanitize_html(g.description_html)})
        for g in galleries
    ]
