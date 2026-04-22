from pathlib import Path

from bs4 import BeautifulSoup


def _parse(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_faves_index_exists(built_site: Path) -> None:
    assert (built_site / "faves" / "index.html").is_file()


def test_faves_index_has_entries(built_site: Path) -> None:
    soup = _parse(built_site / "faves" / "index.html")
    tombstones = soup.select(".fave-tombstone")
    assert len(tombstones) >= 1


def test_groups_index_exists(built_site: Path) -> None:
    assert (built_site / "groups" / "index.html").is_file()


def test_groups_index_has_flickr_links(built_site: Path) -> None:
    soup = _parse(built_site / "groups" / "index.html")
    links = [
        str(a["href"])
        for a in soup.find_all("a", href=True)
        if "flickr.com" in str(a.get("href", ""))
    ]
    assert len(links) >= 1


def test_testimonials_page_exists(built_site: Path) -> None:
    assert (built_site / "testimonials.html").is_file()
