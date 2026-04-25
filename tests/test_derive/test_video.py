from pathlib import Path

import pytest

from offlickr.derive.video import process_video


def test_process_video_copies_original(tiny_mp4: Path, tmp_path: Path) -> None:
    process_video(tiny_mp4, "99004", tmp_path)
    orig = tmp_path / "originals" / "99004.mp4"
    assert orig.is_file()


def test_process_video_writes_webp_placeholder_when_no_ffmpeg(
    tiny_mp4: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    process_video(tiny_mp4, "99004", tmp_path)
    webp = tmp_path / "thumbs" / "99004.webp"
    assert webp.is_file()
    assert webp.stat().st_size > 0
