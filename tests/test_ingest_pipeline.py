import json
from pathlib import Path

from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive
from tests.conftest import MINI_EXPORT

EXPECTED_PUBLIC_PHOTOS = 48  # 50 total - 2 non-public (10000006 friends, 10000033 only you)
EXPECTED_TOTAL_PHOTOS = 50
EXPECTED_ALBUMS = 3
EXPECTED_GALLERIES = 1
EXPECTED_GROUPS = 1
EXPECTED_FAVES = 2


def test_run_ingest_on_mini_export_produces_valid_archive(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=output_dir,
        include_private=False,
        include_private_photos=False,
    )

    assert isinstance(archive, OfflickrArchive)
    assert archive.account.nsid == "99999999@N00"
    photo_ids = {p.id for p in archive.photos}
    assert "10000006" not in photo_ids
    assert len(archive.photos) == EXPECTED_PUBLIC_PHOTOS
    assert len(archive.albums) == EXPECTED_ALBUMS
    assert len(archive.galleries) == EXPECTED_GALLERIES
    assert len(archive.groups) == EXPECTED_GROUPS
    assert len(archive.faves) == EXPECTED_FAVES

    assert (output_dir / "data" / "model.json").is_file()
    assert (output_dir / "data" / "model.schema.json").is_file()
    serialized = (output_dir / "data" / "model.json").read_text(encoding="utf-8")
    assert "flickrmail" not in serialized.lower()
    assert "contacts" not in serialized.lower()


def test_run_ingest_with_include_private_photos(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "out",
        include_private=False,
        include_private_photos=True,
    )
    photo_ids = {p.id for p in archive.photos}
    assert "10000006" in photo_ids
    assert len(archive.photos) == EXPECTED_TOTAL_PHOTOS


def test_run_ingest_emits_media_index(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path,
        include_private=False,
        include_private_photos=False,
    )
    media_index_path = tmp_path / "data" / "media-index.json"
    assert media_index_path.is_file(), "media-index.json not emitted"
    entries = json.loads(media_index_path.read_text())
    assert isinstance(entries, list)
    # mini-export has 48 public photos; photo_10000005 has no media file → 47 entries
    assert len(entries) == 47
    ids = {e["photo_id"] for e in entries}
    assert "10000005" not in ids  # no media file
    assert all("filename" in e for e in entries)


def test_run_ingest_with_include_private_serializes_contacts(tmp_path: Path) -> None:
    out = tmp_path / "out"
    run_ingest(
        source=MINI_EXPORT,
        output_dir=out,
        include_private=True,
        include_private_photos=False,
    )
    serialized = (out / "data" / "model.json").read_text(encoding="utf-8")
    assert "Alice A." in serialized
    assert "Charlie C." in serialized


def test_include_private_populates_flickrmail(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path, include_private=True, include_private_photos=False
    )
    model = json.loads((tmp_path / "data" / "model.json").read_text())
    assert "flickrmail" in model
    assert len(model["flickrmail"]["sent"]) == 1
    assert len(model["flickrmail"]["received"]) == 1


def test_include_private_populates_my_comments(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path, include_private=True, include_private_photos=False
    )
    model = json.loads((tmp_path / "data" / "model.json").read_text())
    assert len(model["my_comments"]) == 2


def test_include_private_populates_my_group_posts(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path, include_private=True, include_private_photos=False
    )
    model = json.loads((tmp_path / "data" / "model.json").read_text())
    assert len(model["my_group_posts"]) == 1


def test_run_ingest_populates_users_from_comment_authors(tmp_path: Path) -> None:
    archive = run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "out",
        include_private=False,
        include_private_photos=False,
    )
    assert "77777777@N00" in archive.users
    assert archive.users["77777777@N00"].nsid == "77777777@N00"


def test_include_private_populates_set_comments(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path, include_private=True, include_private_photos=False
    )
    model = json.loads((tmp_path / "data" / "model.json").read_text())
    assert "set_comments" in model
    assert "10000000000000001" in model["set_comments"]
    assert len(model["set_comments"]["10000000000000001"]) == 1
    assert model["set_comments"]["10000000000000001"][0]["body_html"] == "Love this album!"


def test_set_comments_absent_without_include_private(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT, output_dir=tmp_path, include_private=False, include_private_photos=False
    )
    model = json.loads((tmp_path / "data" / "model.json").read_text())
    assert "set_comments" not in model


def test_include_private_populates_gallery_comments(tmp_path: Path) -> None:
    run_ingest(
        source=MINI_EXPORT,
        output_dir=tmp_path / "g",
        include_private=True,
        include_private_photos=False,
    )
    model = json.loads((tmp_path / "g" / "data" / "model.json").read_text())
    assert "gallery_comments" in model
