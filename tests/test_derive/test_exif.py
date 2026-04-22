from pathlib import Path

from offlickr.derive.exif import extract_exif


def test_extract_exif_returns_none_when_no_exif(small_jpeg: Path) -> None:
    assert extract_exif(small_jpeg) is None


def test_extract_exif_returns_model_when_exif_present(jpeg_with_exif: Path) -> None:
    result = extract_exif(jpeg_with_exif)
    assert result is not None
    assert result.camera_make == "ACME"
    assert result.camera_model == "Cam-1"
    assert result.iso == 400


def test_extract_exif_returns_none_for_missing_file(tmp_path: Path) -> None:
    result = extract_exif(tmp_path / "no_such.jpg")
    assert result is None
