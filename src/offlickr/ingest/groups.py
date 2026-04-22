"""Parser for groups.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import GroupRef


def load_groups(source_dir: Path) -> list[GroupRef]:
    path = source_dir / "groups.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [GroupRef.from_json(g) for g in data.get("groups", [])]
