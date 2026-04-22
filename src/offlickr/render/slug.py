"""Unicode-aware tag slug generator. Deduplicates with -N suffix."""

from __future__ import annotations

from slugify import slugify


def slugify_tags(tags: list[str]) -> dict[str, str]:
    """Return {original_tag: slug} mapping. Collision-free."""
    result: dict[str, str] = {}
    used: set[str] = set()
    for tag in tags:
        base = slugify(tag, allow_unicode=True) or "tag"
        slug = base
        n = 2
        while slug in used:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)
        result[tag] = slug
    return result
