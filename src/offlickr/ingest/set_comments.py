"""Load sets_comments_part*.json (comments on albums). See spec §4.1."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from offlickr.issues import IssueCollector
from offlickr.model import Comment
from offlickr.render.sanitize import sanitize_html


def load_set_comments(
    source_dir: Path, collector: IssueCollector | None = None
) -> dict[str, list[Comment]]:
    result: dict[str, list[Comment]] = {}
    for part in sorted(source_dir.glob("sets_comments_part*.json")):
        for item in json.loads(part.read_text(encoding="utf-8")):
            try:
                album_id = str(item["photoset_id"])
                comment = Comment(
                    id=str(item["comment_id"]),
                    date=datetime.fromisoformat(item["date"]),
                    user_nsid=str(item.get("user", "")),
                    body_html=sanitize_html(item.get("comment", "")),
                    url=item.get("url", ""),
                )
                result.setdefault(album_id, []).append(comment)
            except (KeyError, TypeError, ValueError) as exc:
                if collector:
                    collector.add(
                        "ingest.set_comment",
                        str(item.get("photoset_id", "unknown")),
                        str(exc),
                    )
                continue
    return result
