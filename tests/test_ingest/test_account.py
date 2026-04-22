from offlickr.ingest.account import load_account
from offlickr.model import Account
from tests.conftest import MINI_EXPORT


def test_load_account_from_mini_export() -> None:
    account = load_account(MINI_EXPORT)
    assert account.nsid == "99999999@N00"
    assert account.screen_name == "testuser"


def test_account_location_parsed_from_city_country() -> None:
    data = {
        "nsid": "99@N00",
        "screen_name": "t",
        "join_date": "2010-01-01T00:00:00",
        "pro_user": "no",
        "profile_url": "https://flickr.com/people/t/",
        "city": "Tel Aviv",
        "country": "Israel",
        "hometown": "",
    }
    account = Account.from_json(data)
    assert account.location is not None
    assert account.location["city"] == "Tel Aviv"
    assert account.location["country"] == "Israel"


def test_account_social_parsed() -> None:
    data = {
        "nsid": "99@N00",
        "screen_name": "t",
        "join_date": "2010-01-01T00:00:00",
        "pro_user": "no",
        "profile_url": "https://flickr.com/people/t/",
        "social": {
            "instagram": "@testuser",
            "twitter": "",
            "facebook": "",
            "pintrest": "",
            "tumblr": "",
        },
    }
    account = Account.from_json(data)
    assert account.social is not None
    assert account.social["instagram"] == "testuser"  # leading @ stripped at ingest


def test_account_location_none_when_all_empty() -> None:
    data = {
        "nsid": "99@N00",
        "screen_name": "t",
        "join_date": "2010-01-01T00:00:00",
        "pro_user": "no",
        "profile_url": "https://flickr.com/people/t/",
        "city": "",
        "country": "",
        "hometown": "",
    }
    account = Account.from_json(data)
    assert account.location is None
