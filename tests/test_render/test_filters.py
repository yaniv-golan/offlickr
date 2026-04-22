from datetime import datetime

from offlickr.render.filters import (
    add_geo_pin,
    format_aspect,
    format_camera,
    format_date,
    format_filesize,
    format_focal_mm,
    format_media_type,
    format_megapixels,
    photo_title,
    privacy_label,
)


def test_format_date_formats_datetime() -> None:
    dt = datetime(2020, 3, 5, 12, 0, 0)
    assert format_date(dt) == "March 5, 2020"


def test_format_date_none_returns_empty() -> None:
    assert format_date(None) == ""


def test_privacy_label_known() -> None:
    assert privacy_label("public") == "Public"
    assert privacy_label("friends") == "Friends"
    assert privacy_label("family") == "Family"
    assert privacy_label("friends-family") == "Friends & Family"
    assert privacy_label("private") == "Private"


def test_privacy_label_unknown_passthrough() -> None:
    assert privacy_label("custom") == "custom"


def test_photo_title_empty_returns_untitled() -> None:
    assert photo_title("") == "(untitled)"


def test_photo_title_dot_is_preserved() -> None:
    assert photo_title(".") == "."


def test_photo_title_normal_passthrough() -> None:
    assert photo_title("Sunset") == "Sunset"


def test_format_camera_deduplicates_make_prefix() -> None:
    assert format_camera("Canon", "Canon EOS R") == "Canon EOS R"


def test_format_camera_no_dedup_needed() -> None:
    assert format_camera("Nikon", "D70") == "Nikon D70"


def test_format_camera_case_insensitive_dedup() -> None:
    result = format_camera("NIKON CORPORATION", "NIKON CORPORATION NIKON D70")
    assert result == "NIKON CORPORATION NIKON D70"


def test_format_camera_missing_make() -> None:
    assert format_camera(None, "EOS R") == "EOS R"


def test_format_camera_missing_model() -> None:
    assert format_camera("Sony", None) == "Sony"


def test_format_focal_mm_whole_number() -> None:
    assert format_focal_mm(50.0) == "50mm"


def test_format_focal_mm_decimal() -> None:
    assert format_focal_mm(24.5) == "24.5mm"


def test_format_focal_mm_none() -> None:
    assert format_focal_mm(None) == ""


def test_format_filesize_bytes() -> None:
    assert format_filesize(512) == "512 B"


def test_format_filesize_kilobytes() -> None:
    assert format_filesize(2048) == "2.0 KB"


def test_format_filesize_megabytes() -> None:
    assert format_filesize(14_500_000) == "13.8 MB"


def test_format_filesize_none() -> None:
    assert format_filesize(None) == ""


def test_format_megapixels_standard() -> None:
    assert format_megapixels(6000, 4000) == "24.0 MP"


def test_format_megapixels_none() -> None:
    assert format_megapixels(None, None) == ""


def test_format_aspect_three_two() -> None:
    assert format_aspect(6000, 4000) == "3:2"


def test_format_aspect_widescreen() -> None:
    assert format_aspect(1920, 1080) == "16:9"


def test_format_aspect_none() -> None:
    assert format_aspect(None, None) == ""


def test_format_media_type_jpg() -> None:
    assert format_media_type(".jpg") == "JPEG"


def test_format_media_type_png() -> None:
    assert format_media_type(".png") == "PNG"


def test_format_media_type_unknown_uppercases() -> None:
    assert format_media_type(".arw") == "ARW"


def test_add_geo_pin_injects_circle() -> None:
    svg = '<svg viewBox="0 0 960 480"><path d="M0 0"/></svg>'
    result = add_geo_pin(svg, lat=32.085, lng=34.781)
    assert "<circle" in result
    assert "cx=" in result
    assert result.index("<circle") < result.index("</svg>")


def test_add_geo_pin_noop_on_no_viewbox() -> None:
    svg = '<svg><path d="M0 0"/></svg>'
    result = add_geo_pin(svg, lat=32.085, lng=34.781)
    assert result == svg
