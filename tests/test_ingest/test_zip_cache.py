from __future__ import annotations

import zipfile
from pathlib import Path

from offlickr.ingest.zip_cache import cache_key_for_zips, extract_zips_if_any, is_zip_input

SHA256_HEX_LEN = 64


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_is_zip_input_true_when_zips_present(tmp_path: Path) -> None:
    _make_zip(tmp_path / "a.zip", {"x.json": b"{}"})
    assert is_zip_input(tmp_path) is True


def test_is_zip_input_false_for_extracted_dir(tmp_path: Path) -> None:
    (tmp_path / "account_profile.json").write_text("{}")
    assert is_zip_input(tmp_path) is False


def test_cache_key_is_stable_across_calls(tmp_path: Path) -> None:
    _make_zip(tmp_path / "a.zip", {"x.json": b"{}"})
    k1 = cache_key_for_zips(tmp_path)
    k2 = cache_key_for_zips(tmp_path)
    assert k1 == k2
    assert len(k1) == SHA256_HEX_LEN


def test_cache_key_changes_when_zip_contents_change(tmp_path: Path) -> None:
    _make_zip(tmp_path / "a.zip", {"x.json": b"{}"})
    k1 = cache_key_for_zips(tmp_path)
    (tmp_path / "a.zip").unlink()
    _make_zip(tmp_path / "a.zip", {"y.json": b"{}"})
    k2 = cache_key_for_zips(tmp_path)
    assert k1 != k2


def test_extract_zips_produces_flat_namespace(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "one.zip", {"a.json": b"{}", "b.json": b"{}"})
    _make_zip(src / "two.zip", {"c.json": b"{}"})
    cache = tmp_path / "cache"

    out = extract_zips_if_any(src, cache_dir=cache)

    assert out is not None
    assert (out / "a.json").is_file()
    assert (out / "b.json").is_file()
    assert (out / "c.json").is_file()


def test_extract_zips_returns_none_for_extracted_input(tmp_path: Path) -> None:
    (tmp_path / "account_profile.json").write_text("{}")
    assert extract_zips_if_any(tmp_path, cache_dir=tmp_path / "cache") is None
