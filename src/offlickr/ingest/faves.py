"""Parser for faves_part*.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import Fave


def load_faves(source_dir: Path) -> list[Fave]:
    result: list[Fave] = []
    for path in sorted(source_dir.glob("faves_part*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result.extend(Fave.from_json(f) for f in data.get("faves", []))
    return result
