import json
from pathlib import Path
from typing import cast

from offlickr.derive.search import build_search_index, write_search_index
from offlickr.ingest.pipeline import run_ingest
from tests.conftest import MINI_EXPORT


def _archive(tmp_path: Path):  # type: ignore[no-untyped-def]
    return run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "out",
        include_private=False,
        include_private_photos=False,
    )


def test_build_search_index_has_entry_per_photo(tmp_path: Path) -> None:
    archive = _archive(tmp_path)
    index = build_search_index(archive)
    assert len(index) == len(archive.photos)
    assert all("id" in e and "t" in e for e in index)


def test_search_index_tags_normalized(tmp_path: Path) -> None:
    archive = _archive(tmp_path)
    index = build_search_index(archive)
    # photo_10000001 has tags "sunset" and "שקיעה"
    entry = next(e for e in index if e["id"] == "10000001")
    tags = cast(list[str], entry["g"])
    assert "sunset" in tags
    assert "שקיעה" in tags


def test_write_search_index_creates_file(tmp_path: Path) -> None:
    archive = _archive(tmp_path)
    write_search_index(archive, tmp_path / "out")
    search_path = tmp_path / "out" / "assets" / "search.json"
    assert search_path.is_file()
    data = json.loads(search_path.read_text())
    assert isinstance(data, list)
    assert len(data) > 0
