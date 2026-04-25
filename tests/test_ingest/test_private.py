import json
import shutil
from pathlib import Path

from offlickr.ingest.apps_comments import load_apps_comments
from offlickr.ingest.comments import load_my_comments
from offlickr.ingest.flickrmail import load_flickrmail
from offlickr.ingest.gallery_comments import load_gallery_comments
from offlickr.ingest.group_discussions import load_group_posts
from offlickr.ingest.pipeline import run_ingest
from offlickr.ingest.set_comments import load_set_comments
from offlickr.issues import IssueCollector
from tests.conftest import MINI_EXPORT


def test_load_my_comments(tmp_path: Path) -> None:
    comments = load_my_comments(MINI_EXPORT)
    assert len(comments) == 2
    assert all(c.photo_id for c in comments)
    assert all(c.body_html for c in comments)


def test_load_my_comments_missing_returns_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert load_my_comments(empty) == []


def test_load_flickrmail(tmp_path: Path) -> None:
    mailbox = load_flickrmail(MINI_EXPORT)
    assert len(mailbox.sent) == 1
    assert len(mailbox.received) == 1
    assert mailbox.sent[0].subject == "Hi there"
    assert mailbox.received[0].have_read is True


def test_load_flickrmail_missing_returns_empty_mailbox(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    mailbox = load_flickrmail(empty)
    assert mailbox.sent == []
    assert mailbox.received == []


def test_load_group_posts(tmp_path: Path) -> None:
    posts = load_group_posts(MINI_EXPORT)
    assert len(posts) == 1
    assert posts[0].group_name == "Test Group"


def test_load_group_posts_missing_returns_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert load_group_posts(empty) == []


def test_load_my_comments_reports_malformed_record(tmp_path: Path) -> None:
    (tmp_path / "photos_comments_part1.json").write_text(
        json.dumps(
            {
                "comments": [
                    {
                        "photo_id": "123",
                        "date": "2020-01-01T00:00:00",
                        "comment": "hi",
                        "comment_url": "",
                    },
                    {"broken": True},  # missing photo_id and date — triggers KeyError/ValueError
                ]
            }
        ),
        encoding="utf-8",
    )
    collector = IssueCollector()
    result = load_my_comments(tmp_path, collector)
    assert len(result) == 1
    assert result[0].photo_id == "123"
    assert collector.has_issues()
    cats = collector.by_category()
    assert "ingest.comment" in cats
    assert cats["ingest.comment"][0].reason != ""


def test_load_gallery_comments_reports_malformed_record(tmp_path: Path) -> None:
    (tmp_path / "galleries_comments_part1.json").write_text(
        json.dumps(
            [
                {
                    "gallery_id": "gal1",
                    "comment_id": "c1",
                    "date": "2020-01-01T00:00:00",
                    "user": "u1",
                    "comment": "ok",
                },
                {"no_gallery_id": True},  # missing gallery_id — triggers KeyError
            ]
        ),
        encoding="utf-8",
    )
    collector = IssueCollector()
    result = load_gallery_comments(tmp_path, collector)
    assert "gal1" in result
    assert len(result["gal1"]) == 1
    assert collector.has_issues()
    assert "ingest.gallery_comment" in collector.by_category()


def test_load_apps_comments_reports_malformed_record(tmp_path: Path) -> None:
    (tmp_path / "apps_comments_part1.json").write_text(
        json.dumps(
            [
                {
                    "photo_id": "p1",
                    "comment_id": "c1",
                    "date": "2020-01-01T00:00:00",
                    "user": "u1",
                    "comment": "ok",
                },
                {"no_photo_id": True},  # missing photo_id — triggers KeyError
            ]
        ),
        encoding="utf-8",
    )
    collector = IssueCollector()
    result = load_apps_comments(tmp_path, collector)
    assert "p1" in result
    assert collector.has_issues()
    assert "ingest.apps_comment" in collector.by_category()


def test_load_set_comments_reports_malformed_record(tmp_path: Path) -> None:
    (tmp_path / "sets_comments_part1.json").write_text(
        json.dumps(
            [
                {
                    "photoset_id": "set1",
                    "comment_id": "c1",
                    "date": "2020-01-01T00:00:00",
                    "user": "u1",
                    "comment": "ok",
                },
                {"no_set_id": True},  # missing photoset_id — triggers KeyError
            ]
        ),
        encoding="utf-8",
    )
    collector = IssueCollector()
    result = load_set_comments(tmp_path, collector)
    assert "set1" in result
    assert collector.has_issues()
    assert "ingest.set_comment" in collector.by_category()


def test_load_group_posts_reports_malformed_record(tmp_path: Path) -> None:
    data = {
        "discussions": [
            {
                "group_id": "g1",
                "group_name": "My Group",
                "topic_id": "t1",
                "topic_title": "Topic",
                "reply_id": "r1",
                "body": "Hello",
                "date": "2020-01-01T00:00:00",
            },
            {"broken": True},  # missing date — fromisoformat("") raises ValueError
        ]
    }
    (tmp_path / "group_discussions.json").write_text(json.dumps(data), encoding="utf-8")
    collector = IssueCollector()
    result = load_group_posts(tmp_path, collector)
    assert len(result) == 1
    assert result[0].group_name == "My Group"
    assert collector.has_issues()
    assert "ingest.group_post" in collector.by_category()


def test_load_flickrmail_reports_malformed_message(tmp_path: Path) -> None:
    data = [
        {
            "id": "msg1",
            "from": "u1",
            "to": "u2",
            "subject": "Hi",
            "body": "Hello",
            "date_sent": "2020-01-01T00:00:00",
        },
        {"broken": True},  # missing id and date_sent — triggers KeyError
    ]
    (tmp_path / "sent_flickrmail_part1.json").write_text(json.dumps(data), encoding="utf-8")
    collector = IssueCollector()
    mailbox = load_flickrmail(tmp_path, collector)
    assert len(mailbox.sent) == 1
    assert mailbox.sent[0].subject == "Hi"
    assert collector.has_issues()
    assert "ingest.flickrmail" in collector.by_category()


def test_run_ingest_threads_collector_to_parsers(tmp_path: Path) -> None:
    # Copy mini-export and add a malformed comment file
    export_dir = tmp_path / "export"
    shutil.copytree(MINI_EXPORT, export_dir)
    (export_dir / "photos_comments_part999.json").write_text(
        json.dumps({"comments": [{"broken": True}]}),
        encoding="utf-8",
    )
    collector = IssueCollector()
    run_ingest(
        source=export_dir,
        output_dir=tmp_path / "out",
        include_private=True,
        include_private_photos=False,
        collector=collector,
    )
    assert collector.has_issues()
    assert "ingest.comment" in collector.by_category()
