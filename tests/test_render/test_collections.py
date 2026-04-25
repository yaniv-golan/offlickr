from pathlib import Path

from bs4 import BeautifulSoup


def _parse(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_albums_index_exists(built_site: Path) -> None:
    assert (built_site / "albums" / "index.html").is_file()


def test_album_detail_exists(built_site: Path) -> None:
    assert (built_site / "albums" / "10000000000000001.html").is_file()


def test_album_detail_has_photos(built_site: Path) -> None:
    soup = _parse(built_site / "albums" / "10000000000000001.html")
    tiles = soup.select(".grid-tile")
    assert len(tiles) >= 1


def test_galleries_index_exists(built_site: Path) -> None:
    assert (built_site / "galleries" / "index.html").is_file()


def test_tags_index_exists(built_site: Path) -> None:
    assert (built_site / "tags" / "index.html").is_file()


def test_tags_index_has_cloud(built_site: Path) -> None:
    soup = _parse(built_site / "tags" / "index.html")
    cloud_items = soup.select(".tag-cloud-item")
    assert len(cloud_items) >= 1


def test_tag_detail_exists_for_sunset(built_site: Path) -> None:
    assert (built_site / "tags" / "sunset.html").is_file()


def test_map_html_exists_when_geo_present(built_site: Path) -> None:
    assert (built_site / "map.html").is_file()
