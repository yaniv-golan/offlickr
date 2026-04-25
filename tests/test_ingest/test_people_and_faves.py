from pathlib import Path

from offlickr.ingest.contacts import load_contacts
from offlickr.ingest.faves import load_faves
from offlickr.ingest.followers import load_followers
from tests.conftest import MINI_EXPORT

EXPECTED_FAVES = 2


def test_load_contacts() -> None:
    contacts = load_contacts(MINI_EXPORT)
    assert contacts["Alice A."].profile_url == "https://www.flickr.com/people/alice/"


def test_load_followers() -> None:
    followers = load_followers(MINI_EXPORT)
    assert "Charlie C." in followers


def test_load_faves() -> None:
    faves = load_faves(MINI_EXPORT)
    assert len(faves) == EXPECTED_FAVES
    assert faves[0].photo_id == "98765432"


def test_contacts_missing_returns_empty(tmp_path: Path) -> None:
    assert load_contacts(tmp_path) == {}


def test_followers_missing_returns_empty(tmp_path: Path) -> None:
    assert load_followers(tmp_path) == {}


def test_faves_missing_returns_empty(tmp_path: Path) -> None:
    assert load_faves(tmp_path) == []
