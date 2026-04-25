"""Load Flickrmail sent/received messages."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from offlickr.issues import IssueCollector
from offlickr.model import FlickrMail, FlickrMailbox
from offlickr.render.sanitize import sanitize_html


def _bool_flag(item: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        v = item.get(key)
        if v is not None:
            try:
                return bool(int(v))
            except (ValueError, TypeError):
                pass
    return None


def _parse_mail(item: dict[str, Any], collector: IssueCollector | None = None) -> FlickrMail | None:
    try:
        return FlickrMail(
            id=str(item["id"]),
            from_nsid=str(item.get("from") or item.get("from_user_id", "")),
            to_nsid=str(item.get("to") or item.get("to_user_id", "")),
            to_user_name=item.get("to_user_name") or item.get("to_username") or None,
            subject=item.get("subject", ""),
            body_html=sanitize_html(item.get("body") or item.get("message", "")),
            date_sent=datetime.fromisoformat(item["date_sent"]),
            have_read=_bool_flag(item, "read", "have_read"),
            have_replied=_bool_flag(item, "replied", "have_replied"),
        )
    except (KeyError, ValueError) as exc:
        if collector:
            collector.add(
                "ingest.flickrmail",
                str(item.get("id", "unknown")),
                str(exc),
            )
        return None


def load_flickrmail(source: Path, collector: IssueCollector | None = None) -> FlickrMailbox:
    sent: list[FlickrMail] = []
    received: list[FlickrMail] = []
    for part in sorted(source.glob("sent_flickrmail_part*.json")):
        raw = json.loads(part.read_text(encoding="utf-8"))
        for item in raw["flickrmail"] if isinstance(raw, dict) else raw:
            m = _parse_mail(item, collector)
            if m:
                sent.append(m)
    for part in sorted(source.glob("received_flickrmail_part*.json")):
        raw = json.loads(part.read_text(encoding="utf-8"))
        for item in raw["flickrmail"] if isinstance(raw, dict) else raw:
            m = _parse_mail(item, collector)
            if m:
                received.append(m)
    sent.sort(key=lambda m: m.date_sent, reverse=True)
    received.sort(key=lambda m: m.date_sent, reverse=True)
    return FlickrMailbox(sent=sent, received=received)
