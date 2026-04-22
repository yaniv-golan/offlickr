"""Tests for offlickr.model."""

from __future__ import annotations

import json
from datetime import datetime

from offlickr.model import (
    Account,
    Album,
    AlbumBackRef,
    Exif,
    Fave,
    FlickrMail,
    Gallery,
    GroupPost,
    GroupRef,
    Note,
    OfflickrArchive,
    OutgoingComment,
    PersonRef,
    Photo,
    User,
)
from tests.conftest import MINI_EXPORT

EXPECTED_VIEW_COUNT = 17
EXPECTED_GEO_LAT = 32.085
EXPECTED_TAG_COUNT = 2
EXPECTED_PHOTO_COUNT = 3


def test_account_parses_from_profile_json() -> None:
    data = json.loads((MINI_EXPORT / "account_profile.json").read_text())
    account = Account.from_json(data)

    assert account.nsid == "99999999@N00"
    assert account.path_alias == "testuser"
    assert account.screen_name == "testuser"
    assert account.real_name == "Test User"
    assert account.profile_url == "https://www.flickr.com/people/testuser/"
    assert account.pro_user is False
    assert account.stats.view_counts["total"] == EXPECTED_VIEW_COUNT
    assert account.showcase_photo_ids == ["10000001"]


def test_photo_parses_from_photo_json() -> None:
    data = json.loads((MINI_EXPORT / "photo_10000001.json").read_text())
    photo = Photo.from_json(data)

    assert photo.id == "10000001"
    assert photo.title == "שקיעה כחולה"
    assert photo.privacy == "public"
    assert photo.safety == "safe"
    assert photo.counts["views"] == 1
    assert photo.counts["comments"] == 1
    assert photo.license == "CC BY-NC-SA 4.0"
    assert photo.geo is not None
    assert round(photo.geo.lat, 3) == EXPECTED_GEO_LAT
    assert len(photo.tags) == EXPECTED_TAG_COUNT
    assert photo.tags[0].tag == "sunset"
    assert photo.tags[1].tag == "שקיעה"
    assert len(photo.comments) == 1
    assert photo.comments[0].user_nsid == "77777777@N00"
    assert photo.photopage_url == "https://www.flickr.com/photos/testuser/10000001/"
    assert photo.original_flickr_url.startswith("https://live.staticflickr.com/")


def test_photo_without_geo_has_none() -> None:
    data = json.loads((MINI_EXPORT / "photo_10000008.json").read_text())
    photo = Photo.from_json(data)
    assert photo.geo is None


def test_private_photo_privacy_field() -> None:
    data = json.loads((MINI_EXPORT / "photo_10000006.json").read_text())
    photo = Photo.from_json(data)
    assert photo.privacy == "friends"


def test_album_parses() -> None:
    data = json.loads((MINI_EXPORT / "albums.json").read_text())
    album = Album.from_json(data["albums"][0])
    assert album.id == "10000000000000001"
    assert album.title == "Album One"
    assert album.photo_count == EXPECTED_PHOTO_COUNT
    assert album.photo_ids == ["10000001", "10000002", "10000003"]
    assert album.cover_photo_id == "10000001"


def test_album_with_missing_cover() -> None:
    data = json.loads((MINI_EXPORT / "albums.json").read_text())
    album = Album.from_json(data["albums"][1])
    assert album.cover_photo_id is None


def test_gallery_parses() -> None:
    data = json.loads((MINI_EXPORT / "galleries.json").read_text())
    g = Gallery.from_json(data["galleries"][0])
    assert g.id == "72157600000000000"
    assert g.photo_ids == ["10000001", "98765432"]


def test_groupref_parses() -> None:
    data = json.loads((MINI_EXPORT / "groups.json").read_text())
    g = GroupRef.from_json(data["groups"][0])
    assert g.id == "11111111@N00"
    assert g.user_role == "member"


def test_user_from_nsid() -> None:
    u = User(nsid="77777777@N00")
    assert u.nsid == "77777777@N00"
    assert u.screen_name is None
    assert u.avatar_path is None


def test_fave_parses() -> None:
    data = json.loads((MINI_EXPORT / "faves_part001.json").read_text())
    fave = Fave.from_json(data["faves"][0])
    assert fave.photo_id == "98765432"
    assert fave.photo_url_short == "http://flic.kr/p/ABCDE"


def test_archive_round_trips_through_json(tmp_path: object) -> None:
    archive = OfflickrArchive(
        generator={  # type: ignore[arg-type]
            "name": "offlickr",
            "version": "0.1.0.dev0",
            "built_at": datetime.fromisoformat("2026-04-22T12:00:00"),
        },
        export={"source_dir": str(MINI_EXPORT), "detected_format_version": "2026-q1"},  # type: ignore[arg-type]
        account=Account.from_json(json.loads((MINI_EXPORT / "account_profile.json").read_text())),
        photos=[],
        albums=[],
        galleries=[],
        groups=[],
        faves=[],
        testimonials={"given": [], "received": []},  # type: ignore[arg-type]
        users={},
    )
    out = tmp_path / "model.json"  # type: ignore[operator]
    out.write_text(archive.model_dump_json(indent=2))
    loaded = OfflickrArchive.model_validate_json(out.read_text())
    assert loaded.account.nsid == archive.account.nsid


def test_photo_exif_defaults_to_none() -> None:
    data = json.loads((MINI_EXPORT / "photo_10000001.json").read_text())
    photo = Photo.from_json(data)
    assert photo.exif is None


def test_exif_model_fields() -> None:
    exif = Exif(
        camera_make="ACME",
        camera_model="Cam-1",
        focal_length_mm=50.0,
        aperture=2.8,
        shutter_speed="1/250s",
        iso=400,
        date_taken=datetime(2020, 3, 15, 12, 0, 0),
    )
    assert exif.camera_make == "ACME"
    assert exif.iso == 400


def test_outgoing_comment_model() -> None:
    oc = OutgoingComment(
        comment_id="oc1",
        photo_id="123",
        photo_url="https://www.flickr.com/photos/x/123/",
        body_html="Great shot!",
        date=datetime(2021, 5, 10, 14, 23),
    )
    assert oc.comment_id == "oc1"


def test_flickr_mail_model() -> None:
    fm = FlickrMail(
        id="fm001",
        from_nsid="99999999@N00",
        to_nsid="12345678@N00",
        to_user_name="frienduser",
        subject="Hi",
        body_html="<p>Hello</p>",
        date_sent=datetime(2021, 3, 15, 10, 0),
    )
    assert fm.subject == "Hi"


def test_group_post_model() -> None:
    gp = GroupPost(
        group_id="11111111@N00",
        group_name="Test Group",
        topic_id="tp001",
        topic_title="Share sunsets",
        reply_id="rp001",
        body_html="<p>My sunset.</p>",
        date=datetime(2021, 7, 1, 20, 0),
    )
    assert gp.group_name == "Test Group"


def test_archive_schema_is_json_schema_object() -> None:
    schema = OfflickrArchive.model_json_schema()
    assert schema["type"] == "object"
    assert "account" in schema["properties"]
    assert "photos" in schema["properties"]


def test_note_fields() -> None:
    n = Note(id="n1", x=10, y=20, w=100, h=50, body="See the building", author_nsid="99999999@N00")
    assert n.id == "n1"
    assert n.x == 10
    assert n.body == "See the building"
    assert n.author_nsid == "99999999@N00"


def test_person_ref_fields() -> None:
    p = PersonRef(nsid="77777777@N00", username="testfriend", profile_url="https://www.flickr.com/people/testfriend/")
    assert p.nsid == "77777777@N00"
    assert p.username == "testfriend"


def test_album_back_ref_fields() -> None:
    a = AlbumBackRef(id="10000000000000001", title="Album One", url_flickr="https://www.flickr.com/photos/testuser/sets/10000000000000001/")
    assert a.id == "10000000000000001"
    assert a.title == "Album One"


def test_photo_has_notes_people_album_refs_groups_fields() -> None:
    photo = Photo(
        id="1",
        title="t",
        date_imported=datetime.now(),
        photopage_url="https://x",
        original_flickr_url="https://y",
    )
    assert photo.notes == []
    assert photo.people == []
    assert photo.album_refs == []
    assert photo.groups == []
