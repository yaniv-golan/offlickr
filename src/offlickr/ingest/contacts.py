"""Parser for contacts_part*.json. See spec §5.1."""

from __future__ import annotations

import json
from pathlib import Path

from offlickr.model import User


def load_contacts(source_dir: Path) -> dict[str, User]:
    result: dict[str, User] = {}
    for path in sorted(source_dir.glob("contacts_part*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, url in data.get("contacts", {}).items():
            result[name] = User(nsid=name, screen_name=name, profile_url=url)
    return result
