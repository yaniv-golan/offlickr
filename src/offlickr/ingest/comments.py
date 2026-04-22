"""Load outgoing comments (photos_comments_part*.json)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from offlickr.issues import IssueCollector
from offlickr.model import OutgoingComment
from offlickr.render.sanitize import sanitize_html


def load_my_comments(
    source: Path, collector: IssueCollector | None = None
) -> list[OutgoingComment]:
    result = []
    for part in sorted(source.glob("photos_comments_part*.json")):
        raw = json.loads(part.read_text(encoding="utf-8"))
        # Real export wraps items: {"comments": [...]}; fixture is a bare list.
        items = raw["comments"] if isinstance(raw, dict) else raw
        for item in items:
            try:
                # Real export: "created" field, no "comment_id" (derive from comment_url).
                date_str = item.get("date") or item.get("created", "")
                comment_url = item.get("comment_url", "")
                cid = item.get("comment_id") or (
                    comment_url.split("#comment")[-1] if "#comment" in comment_url else ""
                )
                result.append(
                    OutgoingComment(
                        comment_id=str(cid),
                        photo_id=str(item["photo_id"]),
                        photo_url=item.get("photo_url", ""),
                        body_html=sanitize_html(item.get("comment", "")),
                        date=datetime.fromisoformat(date_str),
                    )
                )
            except (KeyError, ValueError) as exc:
                if collector:
                    collector.add(
                        "ingest.comment",
                        str(item.get("photo_id", "unknown")),
                        str(exc),
                    )
                continue
    result.sort(key=lambda c: c.date, reverse=True)
    return result
