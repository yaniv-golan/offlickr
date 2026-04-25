"""Video copy and poster thumbnail generation."""

from __future__ import annotations

import shutil
import subprocess
import warnings
from pathlib import Path

from PIL import Image, ImageDraw

_state = {"warned": False}


def process_video(src: Path, photo_id: str, output_dir: Path) -> None:
    orig_path = output_dir / "originals" / f"{photo_id}{src.suffix}"
    orig_path.parent.mkdir(parents=True, exist_ok=True)
    if not orig_path.exists() or src.stat().st_mtime > orig_path.stat().st_mtime:
        shutil.copy2(src, orig_path)

    thumb_webp = output_dir / "thumbs" / f"{photo_id}.webp"
    if thumb_webp.exists():
        return

    thumb_webp.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(src),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=240:-1",
                    str(thumb_webp),
                ],
                check=True,
                capture_output=True,
            )
            return
        except subprocess.CalledProcessError:
            pass

    if not _state["warned"]:
        msg = (
            "ffmpeg frame extraction failed; using placeholder for video thumbnails"
            if ffmpeg
            else "ffmpeg not found; using placeholder for video thumbnails"
        )
        warnings.warn(msg, stacklevel=1)
        _state["warned"] = True
    img = Image.new("RGB", (240, 180), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)
    draw.polygon([(90, 60), (90, 120), (155, 90)], fill=(224, 224, 224))
    img.save(thumb_webp, "WEBP", quality=80)
