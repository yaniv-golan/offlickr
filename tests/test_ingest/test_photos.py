from offlickr.ingest.photos import load_photos
from tests.conftest import MINI_EXPORT

EXPECTED_TOTAL_PHOTOS = 50


def test_load_photos_count() -> None:
    photos = load_photos(MINI_EXPORT)
    assert len(photos) == EXPECTED_TOTAL_PHOTOS


def test_loaded_photo_has_slug_from_media_filename() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    assert photos["10000001"].slug == "test-photo-one"


def test_missing_media_photo_has_null_media() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    assert photos["10000005"].media is None


def test_photos_sorted_by_date_taken_desc_with_date_imported_fallback() -> None:
    photos = load_photos(MINI_EXPORT)
    for earlier, later in zip(photos[1:], photos[:-1], strict=True):
        earlier_date = earlier.date_taken or earlier.date_imported
        later_date = later.date_taken or later.date_imported
        assert later_date >= earlier_date


def test_photo_notes_parsed() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    p = photos["10000001"]
    assert len(p.notes) == 1
    assert p.notes[0].id == "n1"
    assert p.notes[0].x == 10
    assert p.notes[0].body == "See the building"
    assert p.notes[0].author_nsid == "77777777@N00"


def test_photo_people_parsed() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    p = photos["10000001"]
    assert len(p.people) == 1
    assert p.people[0].nsid == "77777777@N00"
    assert p.people[0].username == "testfriend"


def test_photo_album_refs_parsed() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    p = photos["10000001"]
    assert len(p.album_refs) == 1
    assert p.album_refs[0].id == "10000000000000001"
    assert p.album_refs[0].title == "Album One"


def test_photo_groups_parsed() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    p = photos["10000001"]
    assert len(p.groups) == 1
    assert p.groups[0].id == "11111111@N00"
    assert p.groups[0].name == "Test Group"


def test_photo_missing_media_has_slug_default() -> None:
    photos = {p.id: p for p in load_photos(MINI_EXPORT)}
    # photo_10000005 has no media file
    assert photos["10000005"].media is None
    assert photos["10000005"].slug == "photo-10000005"
