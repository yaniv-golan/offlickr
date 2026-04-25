from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

_ALLOWED_EXTERNAL_HOSTS = {
    "www.flickr.com",
    "flickr.com",
    "flic.kr",
    "github.com",
    # social links rendered from account profile
    "www.instagram.com",
    "instagram.com",
    "twitter.com",
    "www.twitter.com",
    "www.facebook.com",
    "facebook.com",
    "www.tumblr.com",
    "tumblr.com",
}


def _all_html_files(root: Path) -> list[Path]:
    return list(root.rglob("*.html"))


def test_all_internal_links_resolve(built_site: Path) -> None:
    broken = []
    for html_file in _all_html_files(built_site):
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            parsed = urlparse(href)
            if parsed.scheme:
                continue  # external — handled separately
            if href.startswith("#"):
                continue
            # Strip fragment before resolving the path
            path_part = parsed.path
            if not path_part:
                continue
            target = (html_file.parent / path_part).resolve()
            if not target.exists():
                broken.append(f"{html_file.relative_to(built_site)} -> {href}")
    assert not broken, "Broken internal links:\n" + "\n".join(broken)


def test_all_external_links_are_allowed_hosts(built_site: Path) -> None:
    disallowed = []
    for html_file in _all_html_files(built_site):
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https"):
                full = parsed.netloc.lower()
                host = full.removeprefix("www.")
                if full not in _ALLOWED_EXTERNAL_HOSTS and host not in _ALLOWED_EXTERNAL_HOSTS:
                    disallowed.append(f"{html_file.relative_to(built_site)}: {href}")
    assert not disallowed, "Disallowed external links:\n" + "\n".join(disallowed)
