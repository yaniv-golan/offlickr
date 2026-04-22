"""Tests for offlickr.render.sanitize."""

from __future__ import annotations

from jinja2 import Environment

from offlickr.render.filters import register_filters
from offlickr.render.sanitize import rewrite_photo_urls, sanitize_html


def test_allows_basic_formatting() -> None:
    html = "<p>Hello <b>world</b>!<br>See <a href='https://example.com'>here</a>.</p>"
    out = sanitize_html(html)
    assert "<b>world</b>" in out
    assert "<br>" in out or "<br />" in out
    assert 'href="https://example.com"' in out


def test_strips_scripts_and_event_handlers() -> None:
    html = "<p onclick='alert(1)'>x</p><script>bad()</script>"
    out = sanitize_html(html)
    assert "onclick" not in out
    assert "<script" not in out


def test_rewrites_external_link_rel() -> None:
    html = '<a href="https://www.flickr.com/groups/foo/">group</a>'
    out = sanitize_html(html)
    assert 'rel="noopener noreferrer external"' in out


def test_allows_list_and_code_tags() -> None:
    html = "<ul><li>one</li></ul><code>x = 1</code>"
    out = sanitize_html(html)
    assert "<ul>" in out
    assert "<li>one</li>" in out
    assert "<code>" in out


def test_preserves_hebrew_text() -> None:
    html = "<p>שלום עולם</p>"
    out = sanitize_html(html)
    assert "שלום עולם" in out


def test_rewrite_photo_urls_replaces_known_url() -> None:
    html = '<a href="https://www.flickr.com/photos/testuser/10000002/">see this</a>'
    url_map = {"https://www.flickr.com/photos/testuser/10000002/": "photo/10000002.html"}
    result = rewrite_photo_urls(html, url_map)
    assert 'href="photo/10000002.html"' in result


def test_rewrite_photo_urls_leaves_unknown_urls() -> None:
    html = '<a href="https://example.com/other/">link</a>'
    url_map = {"https://www.flickr.com/photos/testuser/10000002/": "photo/10000002.html"}
    result = rewrite_photo_urls(html, url_map)
    assert 'href="https://example.com/other/"' in result


def test_augments_partial_rel() -> None:
    html = '<a href="https://example.com" rel="nofollow">link</a>'
    out = sanitize_html(html)
    assert "noopener" in out
    assert "noreferrer" in out
    assert "external" in out
    assert "nofollow" in out


def test_strips_img_tags() -> None:
    # img is not an allowed tag — remote tracking pixels and JS srcs are both blocked
    assert sanitize_html('<img src="javascript:alert(1)" alt="x">') == ""
    assert sanitize_html('<img src="https://tracker.example.com/px.gif" alt="">') == ""


def test_allows_mailto_links() -> None:
    html = '<a href="mailto:user@example.com">email</a>'
    out = sanitize_html(html)
    assert 'href="mailto:user@example.com"' in out


def test_rewrite_urls_jinja2_filter() -> None:
    env = Environment(autoescape=False)
    register_filters(env)
    env.globals["photo_url_map"] = {
        "https://www.flickr.com/photos/u/10000002/": "photo/10000002.html"
    }
    tmpl = env.from_string('{{ html | rewrite_urls(base_url) }}')
    result = tmpl.render(
        html='<a href="https://www.flickr.com/photos/u/10000002/">see</a>',
        base_url="../",
    )
    assert 'href="../photo/10000002.html"' in result
