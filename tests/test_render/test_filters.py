from datetime import datetime

from offlickr.render.filters import add_geo_pin, format_date, privacy_label


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


def test_add_geo_pin_injects_circle() -> None:
    svg = '<svg viewBox="0 0 960 480"><path d="M0 0"/></svg>'
    result = add_geo_pin(svg, lat=32.085, lng=34.781)
    assert '<circle' in result
    assert 'cx=' in result
    assert result.index('<circle') < result.index('</svg>')


def test_add_geo_pin_noop_on_no_viewbox() -> None:
    svg = '<svg><path d="M0 0"/></svg>'
    result = add_geo_pin(svg, lat=32.085, lng=34.781)
    assert result == svg
