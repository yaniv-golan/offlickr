"""Process one image: thumbnail, display, original copy, EXIF."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageOps

from offlickr.derive.exif import extract_exif
from offlickr.model import Exif

try:
    from pillow_heif import register_heif_opener as _register_heif  # type: ignore[import-not-found]

    _register_heif()
except ImportError:
    pass

Image.MAX_IMAGE_PIXELS = 400_000_000  # allow large panoramas (default is ~178 MP)

THUMB_LONGEST = 240
DISPLAY_LONGEST = 1600


def _needs_regen(src: Path, dst: Path) -> bool:
    return not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime


_FLICKR_ROTATION: dict[int, Image.Transpose] = {
    90: Image.Transpose.ROTATE_270,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_90,
}


def process_image(
    src: Path,
    photo_id: str,
    output_dir: Path,
    *,
    known_w: int = 0,
    known_h: int = 0,
    rotation: int = 0,
) -> tuple[int, int, Exif | None]:
    """Return (width, height, exif). Creates thumb, display, and copies original."""
    thumb_path = output_dir / "thumbs" / f"{photo_id}.webp"
    display_path = output_dir / "display" / f"{photo_id}.webp"
    orig_path = output_dir / "originals" / f"{photo_id}{src.suffix}"

    orig_path.parent.mkdir(parents=True, exist_ok=True)
    if _needs_regen(src, orig_path):
        shutil.copy2(src, orig_path)

    if not _needs_regen(src, thumb_path) and not _needs_regen(src, display_path):
        if known_w and known_h:
            return known_w, known_h, None  # dimensions already in model.json
        with Image.open(src) as raw_img:
            w, h = raw_img.size
            if raw_img.getexif().get(274, 1) in (5, 6, 7, 8):  # 90/270° EXIF swaps dims
                w, h = h, w
        if rotation in (90, 270):
            w, h = h, w
        return w, h, None  # EXIF unchanged; pipeline keeps existing model.json value

    with Image.open(src) as raw_img:
        transposed = ImageOps.exif_transpose(raw_img)
        flickr_xpose = _FLICKR_ROTATION.get(rotation)
        if flickr_xpose is not None:
            transposed = transposed.transpose(flickr_xpose)
        w, h = transposed.size
        rgb = transposed.convert("RGB")

        # Shrink to display size in-place (one full-res buffer, no copy).
        display_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.thumbnail((DISPLAY_LONGEST, DISPLAY_LONGEST), Image.Resampling.LANCZOS)
        rgb.save(display_path, "WEBP", quality=85)

        # Shrink display-sized buffer to thumb (BICUBIC: ~40% faster, imperceptible at 240px).
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.thumbnail((THUMB_LONGEST, THUMB_LONGEST), Image.Resampling.BICUBIC)
        rgb.save(thumb_path, "WEBP", quality=80)

    return w, h, extract_exif(src)
