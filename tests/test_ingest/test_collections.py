from pathlib import Path

from offlickr.ingest.albums import load_albums
from offlickr.ingest.galleries import load_galleries
from offlickr.ingest.groups import load_groups
from tests.conftest import MINI_EXPORT

EXPECTED_ALBUMS = 2
EXPECTED_GALLERIES = 1
EXPECTED_GROUPS = 1


def test_load_albums() -> None:
    albums = load_albums(MINI_EXPORT)
    assert len(albums) == EXPECTED_ALBUMS
    assert albums[0].title == "Album One"
    assert albums[1].cover_photo_id is None


def test_load_galleries() -> None:
    galleries = load_galleries(MINI_EXPORT)
    assert len(galleries) == EXPECTED_GALLERIES
    assert "98765432" in galleries[0].photo_ids


def test_load_groups() -> None:
    groups = load_groups(MINI_EXPORT)
    assert len(groups) == EXPECTED_GROUPS
    assert groups[0].user_role == "member"


def test_load_albums_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert load_albums(tmp_path) == []


def test_load_galleries_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert load_galleries(tmp_path) == []


def test_load_groups_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert load_groups(tmp_path) == []
