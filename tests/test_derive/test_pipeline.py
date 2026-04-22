"""Integration test: run_derive on the mini-export output."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import offlickr.derive.images as _img_mod
from offlickr.derive.pipeline import run_derive
from offlickr.ingest.pipeline import run_ingest
from offlickr.issues import IssueCollector
from tests.conftest import MINI_EXPORT


def _ingest(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    run_ingest(
        source=MINI_EXPORT,
        output_dir=out,
        include_private=False,
        include_private_photos=False,
    )
    return out


def test_run_derive_creates_thumbs(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)
    thumbs = list((out / "thumbs").glob("*.webp")) + list((out / "thumbs").glob("*.svg"))
    assert len(thumbs) >= 8  # 8 photos with image media + 1 video placeholder


def test_run_derive_creates_display(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)
    displays = list((out / "display").glob("*.webp"))
    assert len(displays) >= 7  # 7 public image photos (video gets no display webp)


def test_run_derive_updates_model_dimensions(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)
    model = json.loads((out / "data" / "model.json").read_text())
    photos_with_media = [p for p in model["photos"] if p.get("media")]
    image_photos = [p for p in photos_with_media if p["media"]["kind"] == "image"]
    assert any(p["media"].get("width") for p in image_photos)


def test_run_derive_creates_search_json(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)
    assert (out / "assets" / "search.json").is_file()


def test_run_derive_idempotent(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)
    mtime = (out / "assets" / "search.json").stat().st_mtime
    run_derive(output_dir=out, jobs=1)
    assert (out / "assets" / "search.json").stat().st_mtime == mtime


def test_run_derive_second_run_skips_image_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a re-run where cache is fresh, Image.open must not be called for images."""
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=1)  # first run — populates cache and model.json dimensions

    open_calls: list[str] = []
    real_open = _img_mod.Image.open

    def _spy_open(path: object, *a: object, **kw: object) -> object:
        open_calls.append(str(path))
        return real_open(path, *a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(_img_mod.Image, "open", _spy_open)
    run_derive(output_dir=out, jobs=1)  # second run — should read dims from model.json

    assert open_calls == [], f"Image.open was called on cache hit: {open_calls}"


def test_run_derive_multi_worker_creates_all_thumbs(tmp_path: Path) -> None:
    """jobs=2 produces the correct thumbnail count (same as jobs=1)."""
    out = _ingest(tmp_path)
    run_derive(output_dir=out, jobs=2)
    thumbs = list((out / "thumbs").glob("*.webp")) + list((out / "thumbs").glob("*.svg"))
    assert len(thumbs) >= 8


def test_run_derive_reports_media_errors(tmp_path: Path) -> None:
    out = _ingest(tmp_path)
    collector = IssueCollector()

    def _fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("corrupt file")

    with patch("offlickr.derive.pipeline.process_image", _fail):
        run_derive(output_dir=out, jobs=1, collector=collector)

    assert collector.has_issues()
    cats = collector.by_category()
    assert "derive.media" in cats
    # Every image photo should have reported an error
    assert all(i.reason == "corrupt file" for i in cats["derive.media"])
