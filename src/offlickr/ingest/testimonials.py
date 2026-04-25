"""Parser for account_testimonials.json. See spec §5.1."""

from __future__ import annotations

import contextlib
import json
from datetime import datetime
from pathlib import Path

from offlickr.model import Testimonial, Testimonials
from offlickr.render.sanitize import sanitize_html


def load_testimonials(source_dir: Path) -> Testimonials:
    path = source_dir / "account_testimonials.json"
    if not path.is_file():
        return Testimonials()
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("testimonials", {})

    def _parse(entries: list[dict]) -> list[Testimonial]:  # type: ignore[type-arg]
        result = []
        for t in entries:
            with contextlib.suppress(KeyError, ValueError):
                result.append(
                    Testimonial(
                        author_or_subject_screen_name=t.get("author_or_subject_screen_name", ""),
                        profile_url=t.get("profile_url", ""),
                        body_html=sanitize_html(t.get("body", "")),
                        created=datetime.fromisoformat(t["created"]),
                    )
                )
        return result

    return Testimonials(
        given=_parse(raw.get("given", [])),
        received=_parse(raw.get("received", [])),
    )
