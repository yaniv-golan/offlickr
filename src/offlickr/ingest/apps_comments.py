"""Load apps_comments_part*.json (third-party app comments on photos). See spec §4.1."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from offlickr.issues import IssueCollector
from offlickr.model import Comment
from offlickr.render.sanitize import sanitize_html


def load_apps_comments(
    source_dir: Path, collector: IssueCollector | None = None
) -> dict[str, list[Comment]]:
    """Return mapping photo_id → list[Comment] from apps_comments_part*.json files."""
    result: dict[str, list[Comment]] = {}
    for part in sorted(source_dir.glob("apps_comments_part*.json")):
        for item in json.loads(part.read_text(encoding="utf-8")):
            try:
                photo_id = str(item["photo_id"])
                comment = Comment(
                    id=str(item["comment_id"]),
                    date=datetime.fromisoformat(item["date"]),
                    user_nsid=str(item.get("user", "")),
                    body_html=sanitize_html(item.get("comment", "")),
                    url=item.get("url", ""),
                )
                result.setdefault(photo_id, []).append(comment)
            except (KeyError, TypeError, ValueError) as exc:
                if collector:
                    collector.add(
                        "ingest.apps_comment",
                        str(item.get("photo_id", "unknown")),
                        str(exc),
                    )
                continue
    return result
