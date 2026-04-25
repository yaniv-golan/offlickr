from offlickr.ingest.media import build_media_index, parse_media_filename
from tests.conftest import MINI_EXPORT


def test_parse_media_filename_jpg() -> None:
    result = parse_media_filename("test-photo-one_10000001_o.jpg")
    assert result == ("test-photo-one", "10000001", ".jpg")


def test_parse_media_filename_png() -> None:
    assert parse_media_filename("some-slug_42_o.png") == ("some-slug", "42", ".png")


def test_parse_media_filename_mp4() -> None:
    assert parse_media_filename("clip_99_o.mp4") == ("clip", "99", ".mp4")


def test_parse_media_filename_no_slug() -> None:
    assert parse_media_filename("10000001_abc123_o.jpg") == ("", "10000001", ".jpg")


def test_parse_media_filename_rejects_non_export_filenames() -> None:
    assert parse_media_filename("photo_10000001.json") is None
    assert parse_media_filename("README.md") is None


def test_build_media_index_on_mini_export() -> None:
    index = build_media_index(MINI_EXPORT)
    assert index["10000001"].name == "test-photo-one_10000001_o.jpg"
    assert index["10000004"].suffix == ".png"
    assert index["10000010"].suffix == ".mp4"
    assert "10000005" not in index
