"""Load group discussion posts (group_discussions.json)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from offlickr.issues import IssueCollector
from offlickr.model import GroupPost
from offlickr.render.sanitize import sanitize_html


def _parse_group_url(url: str) -> tuple[str, str]:
    """Return (group_id, topic_id) parsed from a Flickr group discussion URL."""
    m = re.search(r"/groups/([^/]+)/discuss/([^/]+)", url)
    return (m.group(1), m.group(2)) if m else ("", "")


def load_group_posts(
    source: Path, collector: IssueCollector | None = None
) -> list[GroupPost]:
    path = source / "group_discussions.json"
    if not path.is_file():
        return []
    result = []
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Real export wraps items: {"discussions": [...]}; fixture is a bare list.
    items = raw["discussions"] if isinstance(raw, dict) else raw
    for item in items:
        try:
            url = item.get("url", "")
            parsed_group_id, parsed_topic_id = _parse_group_url(url)
            date_str = item.get("date") or item.get("created", "")
            result.append(
                GroupPost(
                    group_id=str(item.get("group_id") or parsed_group_id),
                    group_name=item.get("group_name", ""),
                    topic_id=str(item.get("topic_id") or parsed_topic_id),
                    # Real export: "subject" is the topic title.
                    topic_title=item.get("topic_title") or item.get("subject", ""),
                    reply_id=str(item.get("reply_id", "")),
                    # Real export: "message"; fixture: "body".
                    body_html=sanitize_html(item.get("body") or item.get("message", "")),
                    date=datetime.fromisoformat(date_str),
                )
            )
        except (KeyError, ValueError) as exc:
            if collector:
                collector.add(
                    "ingest.group_post",
                    str(item.get("group_id") or item.get("url", "unknown")),
                    str(exc),
                )
            continue
    result.sort(key=lambda p: p.date, reverse=True)
    return result
