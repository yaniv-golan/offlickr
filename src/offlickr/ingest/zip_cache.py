"""Extract Flickr export zips with an on-disk, content-keyed cache.

The cache key is SHA-256 over (for each zip, in name-sorted order):
    filename | file size | central-directory bytes
This catches silent file replacement and corruption, not just mtime.
See spec §2.2.
"""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Callable
from pathlib import Path


def is_zip_input(source_dir: Path) -> bool:
    return any(source_dir.glob("*.zip"))


def cache_key_for_zips(source_dir: Path) -> str:
    h = hashlib.sha256()
    for zpath in sorted(source_dir.glob("*.zip")):
        h.update(zpath.name.encode("utf-8"))
        h.update(str(zpath.stat().st_size).encode("ascii"))
        with zipfile.ZipFile(zpath) as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                h.update(info.filename.encode("utf-8"))
                h.update(str(info.file_size).encode("ascii"))
                h.update(str(info.CRC).encode("ascii"))
    return h.hexdigest()


def needs_extraction(source_dir: Path, cache_dir: Path) -> bool:
    """Return True if source_dir contains zips that haven't been cached yet."""
    if not is_zip_input(source_dir):
        return False
    key = cache_key_for_zips(source_dir)
    return not (cache_dir / "extracted" / key / ".extracted.ok").is_file()


def extract_zips_if_any(
    source_dir: Path,
    cache_dir: Path,
    *,
    on_zip_start: Callable[[str, int, int, int], None] | None = None,
    on_bytes: Callable[[int], None] | None = None,
) -> Path | None:
    """Extract zips in *source_dir* (if any) into a content-keyed cache subdir.

    Returns the extracted directory path, or ``None`` if *source_dir* already
    contains an extracted export (no zips present).

    Callbacks are only invoked when extraction actually happens (not on cache hit):
    - on_zip_start(name, idx_1based, total_zips, total_uncompressed_bytes)
    - on_bytes(n_bytes) — called after each zip entry is extracted
    """
    if not is_zip_input(source_dir):
        return None
    key = cache_key_for_zips(source_dir)
    out = cache_dir / "extracted" / key
    marker = out / ".extracted.ok"
    if marker.is_file():
        return out
    out.mkdir(parents=True, exist_ok=True)
    zips = sorted(source_dir.glob("*.zip"))
    for i, zpath in enumerate(zips):
        with zipfile.ZipFile(zpath) as zf:
            entries = zf.infolist()
            if on_zip_start:
                total_bytes = sum(e.file_size for e in entries)
                on_zip_start(zpath.name, i + 1, len(zips), total_bytes)
            for entry in entries:
                zf.extract(entry, out)
                if on_bytes:
                    on_bytes(entry.file_size)
    marker.write_text("ok\n")
    return out
