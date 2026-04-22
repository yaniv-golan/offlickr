"""Match Flickr export media filenames to photo IDs.

Flickr's export names media as ``<slug>_<photo_id>_o.<ext>``. The slug may be
empty for photos uploaded without a title. See spec §2.1.
"""

from __future__ import annotations

import re
from pathlib import Path

MEDIA_EXTS: tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".heic",
    ".heif",
    ".mp4",
    ".mov",
    ".m4v",
)

# Split filename (without extension) into underscore-delimited tokens.
# Flickr export format: [slug-tokens...]_<photo_id>_o.<ext>
# or with secret:      [slug-tokens...]_<photo_id>_<secret>_o.<ext>
# The photo_id token is the first all-digit token encountered from the left
# that is followed eventually by the literal token "o".


def parse_media_filename(name: str) -> tuple[str, str, str] | None:
    stem, _, ext_raw = name.rpartition(".")
    if not ext_raw or not stem:
        return None
    ext = "." + ext_raw.lower()
    if ext not in MEDIA_EXTS:
        return None

    tokens = stem.split("_")
    # Must end with "o" token
    if not tokens or tokens[-1] != "o":
        return None

    # Tokens before "o": [slug-parts..., photo_id] or [slug-parts..., photo_id, secret]
    pre = tokens[:-1]  # everything before "o"

    # Find leftmost all-digit token — that's the photo_id.
    # Any numeric token after it is the secret/hash (which may also be all-digit).
    photo_id_idx = None
    for i in range(len(pre)):
        if re.fullmatch(r"\d+", pre[i]):
            photo_id_idx = i
            break

    if photo_id_idx is None:
        return None

    photo_id = pre[photo_id_idx]
    slug_parts = pre[:photo_id_idx]
    slug = "_".join(slug_parts)

    return (slug, photo_id, ext)


def build_media_index(source_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        parsed = parse_media_filename(path.name)
        if parsed is None:
            continue
        _slug, photo_id, _ext = parsed
        if photo_id not in index:
            index[photo_id] = path
    return index
