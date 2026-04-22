from pathlib import Path

from tests.conftest import MINI_EXPORT


def test_mini_export_is_a_directory_with_account_profile() -> None:
    assert isinstance(MINI_EXPORT, Path)
    assert MINI_EXPORT.is_dir()
    assert (MINI_EXPORT / "account_profile.json").is_file()
