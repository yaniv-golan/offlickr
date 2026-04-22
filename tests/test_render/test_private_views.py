import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from offlickr.derive.pipeline import run_derive
from offlickr.ingest.pipeline import run_ingest
from offlickr.model import OfflickrArchive
from offlickr.render.pages import render_site
from tests.conftest import MINI_EXPORT


@pytest.fixture(scope="session")
def private_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("private_site")
    run_ingest(
        source=MINI_EXPORT,
        output_dir=out,
        include_private=True,
        include_private_photos=False,
    )
    run_derive(output_dir=out, jobs=1)
    archive = OfflickrArchive.model_validate(
        json.loads((out / "data" / "model.json").read_text())
    )
    render_site(archive=archive, output_dir=out)
    return out


def test_private_contacts_page_exists(private_site: Path) -> None:
    assert (private_site / "private" / "contacts.html").is_file()


def test_private_followers_page_exists(private_site: Path) -> None:
    assert (private_site / "private" / "followers.html").is_file()


def test_private_flickrmail_sent_exists(private_site: Path) -> None:
    assert (private_site / "private" / "flickrmail" / "sent.html").is_file()


def test_private_my_comments_exists(private_site: Path) -> None:
    assert (private_site / "private" / "my-comments.html").is_file()


def test_private_my_group_posts_exists(private_site: Path) -> None:
    assert (private_site / "private" / "my-group-posts.html").is_file()


def test_private_flickrmail_has_messages(private_site: Path) -> None:
    soup = BeautifulSoup(
        (private_site / "private" / "flickrmail" / "sent.html").read_text(), "html.parser"
    )
    rows = soup.select(".mail-row")
    assert len(rows) >= 1


def test_private_pages_absent_without_flag(built_site: Path) -> None:
    """built_site fixture uses --include-private=False."""
    assert not (built_site / "private" / "contacts.html").is_file()
    assert not (built_site / "private" / "my-comments.html").is_file()


def test_flickrmail_sent_body_not_double_escaped(private_site: Path) -> None:
    soup = BeautifulSoup(
        (private_site / "private" / "flickrmail" / "sent.html").read_text(), "html.parser"
    )
    body_divs = soup.select(".mail-body")
    assert body_divs, "no .mail-body elements found"
    inner = body_divs[0].decode_contents()
    assert "&lt;p&gt;" not in inner, f"body_html was double-escaped: {inner!r}"
    assert body_divs[0].find("p") is not None, "expected <p> tag inside .mail-body"


def test_flickrmail_received_body_not_double_escaped(private_site: Path) -> None:
    soup = BeautifulSoup(
        (private_site / "private" / "flickrmail" / "received.html").read_text(), "html.parser"
    )
    body_divs = soup.select(".mail-body")
    assert body_divs, "no .mail-body elements found"
    inner = body_divs[0].decode_contents()
    assert "&lt;p&gt;" not in inner, f"body_html was double-escaped: {inner!r}"
    assert body_divs[0].find("p") is not None, "expected <p> tag inside .mail-body"


def test_my_comments_body_not_double_escaped(private_site: Path) -> None:
    soup = BeautifulSoup(
        (private_site / "private" / "my-comments.html").read_text(), "html.parser"
    )
    body_divs = soup.select(".comment-body")
    assert body_divs, "no .comment-body elements found"
    # oc2 fixture has <p>Love the colors here.</p>
    html_bodies = [d for d in body_divs if d.find("p") is not None]
    assert html_bodies, "expected at least one .comment-body containing a <p> tag"
    for div in html_bodies:
        inner = div.decode_contents()
        assert "&lt;p&gt;" not in inner, f"body_html was double-escaped: {inner!r}"


def test_my_group_posts_body_not_double_escaped(private_site: Path) -> None:
    soup = BeautifulSoup(
        (private_site / "private" / "my-group-posts.html").read_text(), "html.parser"
    )
    body_divs = soup.select(".comment-body")
    assert body_divs, "no .comment-body elements found"
    inner = body_divs[0].decode_contents()
    assert "&lt;p&gt;" not in inner, f"body_html was double-escaped: {inner!r}"
    assert body_divs[0].find("p") is not None, "expected <p> tag inside .comment-body"
