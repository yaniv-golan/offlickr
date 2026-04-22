import json
import os
import shutil
import zipfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from offlickr.cli import EX_DATAERR, main
from tests.conftest import MINI_EXPORT


def test_ingest_command_runs_on_mini_export(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "data" / "model.json").is_file()
    assert (out / "data" / "model.schema.json").is_file()


def test_ingest_errors_on_missing_account_profile(tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["ingest", str(bad), "-o", str(tmp_path / "out")])
    assert result.exit_code == EX_DATAERR


def test_include_private_photos_flag(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(
        main,
        ["ingest", str(MINI_EXPORT), "-o", str(out), "--include-private-photos"],
    )
    assert result.exit_code == 0
    model_text = (out / "data" / "model.json").read_text()
    assert '"10000006"' in model_text


def test_ingest_on_zip_directory(tmp_path: Path) -> None:
    """Ingest command auto-extracts zips and produces model.json."""
    zip_dir = tmp_path / "zips"
    zip_dir.mkdir()
    sample_zip = zip_dir / "data.zip"
    with zipfile.ZipFile(sample_zip, "w") as zf:
        for name in [
            "account_profile.json",
            "account_testimonials.json",
            "albums.json",
            "galleries.json",
            "groups.json",
            "contacts_part001.json",
            "followers_part001.json",
            "faves_part001.json",
        ]:
            zf.write(MINI_EXPORT / name, name)
        for p in MINI_EXPORT.glob("photo_*.json"):
            zf.write(p, p.name)
        for p in MINI_EXPORT.glob("test-photo-*.jpg"):
            zf.write(p, p.name)
        for p in MINI_EXPORT.glob("test-photo-*.png"):
            zf.write(p, p.name)
        for p in MINI_EXPORT.glob("test-photo-*.mp4"):
            zf.write(p, p.name)

    cache_dir = tmp_path / "cache"
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["ingest", str(zip_dir), "-o", str(out), "--cache-dir", str(cache_dir)],
    )
    assert result.exit_code == 0, result.output
    assert (out / "data" / "model.json").is_file()


def test_derive_command_runs_on_ingest_output(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(main, ["derive", str(out), "--jobs", "1"])
    assert result.exit_code == 0, result.output
    assert (out / "assets" / "search.json").is_file()


def test_render_command(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    runner.invoke(main, ["derive", str(out), "--jobs", "1"])
    result = runner.invoke(main, ["render", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "index.html").is_file()


def test_hide_unsafe_flag_accepted(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    runner.invoke(main, ["derive", str(out), "--jobs", "1"])
    result = runner.invoke(main, ["render", str(out), "--hide-unsafe"])
    assert result.exit_code == 0


def test_include_missing_media_flag_accepted(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    runner.invoke(main, ["derive", str(out), "--jobs", "1"])
    result = runner.invoke(main, ["render", str(out), "--include-missing-media"])
    assert result.exit_code == 0


def test_log_level_flag_accepted(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(
        main,
        ["--log-level", "DEBUG", "ingest", str(MINI_EXPORT), "-o", str(out)],
    )
    assert result.exit_code == 0


def test_build_command(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(
        main,
        ["build", str(MINI_EXPORT), "-o", str(out), "--jobs", "1"],
    )
    assert result.exit_code == 0, result.output
    assert (out / "index.html").is_file()
    assert (out / "about.html").is_file()
    assert (out / "assets" / "search.json").is_file()


def test_inspect_command_shows_stats(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "out"
    runner.invoke(main, ["ingest", str(MINI_EXPORT), "-o", str(out)])
    result = runner.invoke(main, ["inspect", str(out)])
    assert result.exit_code == 0
    text = result.output.lower()
    assert "photos" in text
    assert "9" in result.output   # 9 public photos
    assert "date range" in text or "date" in text
    assert "built at" in text
    assert "estimated" in text or "stage" in text  # §8 requires estimated build time/disk


def test_inspect_errors_on_missing_model(tmp_path: Path) -> None:
    runner = CliRunner()
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(main, ["inspect", str(empty)])
    assert result.exit_code == EX_DATAERR


def test_fetch_external_requires_api_key(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "model.json").write_text('{"faves": [], "users": {}}')
    runner = CliRunner()
    # Suppress load_dotenv and strip FLICKR_API_KEY so the option is genuinely absent.
    env_no_key = {k: v for k, v in os.environ.items() if k != "FLICKR_API_KEY"}
    with patch("offlickr.cli.load_dotenv"), patch.dict(os.environ, env_no_key, clear=True):
        result = runner.invoke(main, ["fetch-external", str(tmp_path)], catch_exceptions=False)
    assert result.exit_code != 0
    assert "FLICKR_API_KEY" in result.output or "api-key" in result.output.lower()


def test_build_archive_external_none_does_not_require_key(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "build", str(MINI_EXPORT), "-o", str(tmp_path),
            "--archive-external", "none", "--jobs", "1",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_ingest_with_malformed_comments_reports_issue_summary(tmp_path):
    """Malformed comment records are skipped and a warning summary is printed."""
    export_dir = tmp_path / "export"
    shutil.copytree(MINI_EXPORT, export_dir)

    # Add a file with 1 valid + 1 malformed comment (missing required fields)
    (export_dir / "photos_comments_part999.json").write_text(
        json.dumps({"comments": [
            {
                "photo_id": "99999",
                "date": "2020-06-01T00:00:00",
                "comment": "valid comment",
                "comment_url": "",
            },
            {"broken": True},   # triggers KeyError — should be skipped
        ]}),
        encoding="utf-8",
    )

    runner = CliRunner()
    out = tmp_path / "out"
    result = runner.invoke(
        main,
        ["ingest", str(export_dir), "-o", str(out), "--include-private"],
    )

    assert result.exit_code == 0, result.output
    # The CLI should print a warning summary for the skipped record
    assert "issue" in result.output.lower() or "⚠" in result.output, (
        "Expected warning summary in output, got: " + result.output
    )
    model = json.loads((out / "data" / "model.json").read_text())
    # MINI_EXPORT has 2 my_comments; our file adds 1 valid = 3 total (malformed skipped)
    assert len(model["my_comments"]) == 3
