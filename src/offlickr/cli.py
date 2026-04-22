"""Command-line interface for offlickr."""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from offlickr import __version__
from offlickr.derive.pipeline import run_derive
from offlickr.fetch.runner import run_fetch_external
from offlickr.ingest.pipeline import run_ingest
from offlickr.ingest.zip_cache import extract_zips_if_any, is_zip_input, needs_extraction
from offlickr.issues import IssueCollector
from offlickr.model import OfflickrArchive
from offlickr.render.pages import render_site

EX_USAGE = 64
EX_DATAERR = 65
EX_SOFTWARE = 70
EX_CANTCREAT = 73

DEFAULT_CACHE = Path.home() / ".cache" / "offlickr"

_err = Console(stderr=True)


def _progress(*columns: ProgressColumn) -> Progress:
    return Progress(
        SpinnerColumn(),
        *columns,
        TimeElapsedColumn(),
        console=_err,
        transient=False,
    )


def _extract_with_progress(source: Path, cache_dir: Path) -> Path | None:
    """Extract zips with per-zip progress bars; skips progress on cache hit."""
    if not is_zip_input(source) or not needs_extraction(source, cache_dir):
        return extract_zips_if_any(source, cache_dir)

    current_task: list[TaskID | None] = [None]
    with _progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        def _on_zip_start(name: str, idx: int, total_zips: int, total_bytes: int) -> None:
            current_task[0] = progress.add_task(
                f"Extracting {name} ({idx}/{total_zips})",
                total=max(1, total_bytes),
            )

        def _on_bytes(n: int) -> None:
            if current_task[0] is not None:
                progress.advance(current_task[0], n)

        return extract_zips_if_any(
            source, cache_dir, on_zip_start=_on_zip_start, on_bytes=_on_bytes
        )


def _print_issues(collector: IssueCollector, stage: str) -> None:
    if not collector.has_issues():
        return
    total = sum(len(v) for v in collector.by_category().values())
    _err.print(
        f"[yellow]⚠[/] {total} issue(s) during {stage}"
        " — some data may be missing from your archive:"
    )
    for category, issues in collector.by_category().items():
        _err.print(f"  {category}: {len(issues)} record(s) skipped ({issues[0].reason})")


def _fetch_with_progress(
    output_dir: Path,
    api_key: str,
    *,
    include_thumbnails: bool,
    include_avatars: bool,
    collector: IssueCollector | None = None,
) -> None:
    """Download external assets with MofN progress bars per asset kind."""
    tasks: dict[str, TaskID] = {}
    with _progress(
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn(" "),
        TimeRemainingColumn(),
    ) as progress:
        def _on_progress(kind: str, n: int, total: int) -> None:
            if kind not in tasks:
                label = "Thumbnails" if kind == "thumbnails" else "Avatars   "
                tasks[kind] = progress.add_task(label, total=total)
            progress.update(tasks[kind], completed=n)

        run_fetch_external(
            output_dir=output_dir,
            api_key=api_key,
            include_thumbnails=include_thumbnails,
            include_avatars=include_avatars,
            on_progress=_on_progress,
            collector=collector,
        )


@click.group()
@click.version_option(__version__, prog_name="offlickr")
@click.option(
    "--log-level",
    default="WARNING",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Python logging level.",
    show_default=True,
)
def main(log_level: str) -> None:
    """Turn a Flickr 'Your Flickr Data' export into a self-contained offline website."""
    load_dotenv()
    logging.basicConfig(level=getattr(logging, log_level.upper()))


@main.command()
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    "output_dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory.",
)
@click.option(
    "--cache-dir",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Cache directory for zip extraction.",
    show_default=True,
)
@click.option("--include-private", is_flag=True, help="Serialize private views.")
@click.option("--include-private-photos", is_flag=True, help="Include non-public photos.")
def ingest(
    source: Path,
    output_dir: Path,
    cache_dir: Path | None,
    include_private: bool,
    include_private_photos: bool,
) -> None:
    """Stage 1: parse a Flickr export into validated model.json + model.schema.json."""
    resolved = _extract_with_progress(source, cache_dir or DEFAULT_CACHE) or source
    if not (resolved / "account_profile.json").is_file():
        _err.print(
            f"[red]error:[/] {resolved} does not contain account_profile.json"
            " — expected an extracted Flickr export."
        )
        sys.exit(EX_DATAERR)
    ingest_collector = IssueCollector()
    try:
        with _err.status("Ingesting export…"):
            archive = run_ingest(
                source=resolved,
                output_dir=output_dir,
                include_private=include_private,
                include_private_photos=include_private_photos,
                collector=ingest_collector,
            )
    except Exception as exc:  # pragma: no cover
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_SOFTWARE)
    _print_issues(ingest_collector, "ingest")
    n = len(archive.photos)
    _err.print(
        f"[green]✓[/] Ingested [bold]{n:,}[/] photos  →  {output_dir / 'data' / 'model.json'}"
    )


@main.command()
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--jobs",
    default=0,
    type=int,
    help="Parallel workers. Default: min(cpu_count, 4).",
)
def derive(output_dir: Path, jobs: int) -> None:
    """Stage 2: generate thumbnails, display images, originals, and search index."""
    media_index_path = output_dir / "data" / "media-index.json"
    if not media_index_path.exists():
        _err.print(f"[red]error:[/] {media_index_path} not found — run 'offlickr ingest' first.")
        sys.exit(EX_DATAERR)
    total = len(json.loads(media_index_path.read_text(encoding="utf-8")))
    derive_collector = IssueCollector()
    try:
        with _progress(
            TextColumn("[bold]Processing media[/]  "),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn(" "),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("", total=total)
            run_derive(
                output_dir=output_dir,
                jobs=jobs,
                on_progress=lambda: progress.advance(task),
                collector=derive_collector,
            )
    except FileNotFoundError as exc:
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_DATAERR)
    except Exception as exc:  # pragma: no cover
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_SOFTWARE)
    _print_issues(derive_collector, "derive")
    _err.print(f"[green]✓[/] Processed [bold]{total:,}[/] media files")


@main.command()
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--theme",
    default="minimal-archive",
    show_default=True,
    help="Theme name or path to custom theme directory.",
)
@click.option(
    "--hide-unsafe",
    is_flag=True,
    help="Blur thumbnails for moderate/restricted photos.",
)
@click.option(
    "--include-missing-media",
    is_flag=True,
    help="Show tombstone tiles for photos with no media file.",
)
def render(output_dir: Path, theme: str, hide_unsafe: bool, include_missing_media: bool) -> None:
    """Stage 3: render model.json into a static site."""
    model_path = output_dir / "data" / "model.json"
    if not model_path.exists():
        _err.print(f"[red]error:[/] {model_path} not found — run 'offlickr ingest' first.")
        sys.exit(EX_DATAERR)
    try:
        archive = OfflickrArchive.model_validate(
            json.loads(model_path.read_text(encoding="utf-8"))
        )
        total = len(archive.photos)
        with _progress(
            TextColumn("[bold]Rendering site[/]    "),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn(" "),
        ) as progress:
            task = progress.add_task("", total=total)
            render_site(
                archive=archive,
                output_dir=output_dir,
                theme=theme,
                on_progress=lambda: progress.advance(task),
                hide_unsafe=hide_unsafe,
                include_missing_media=include_missing_media,
            )
    except Exception as exc:  # pragma: no cover
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_SOFTWARE)
    index_html = output_dir / "index.html"
    _err.print(f"[green]✓[/] Rendered [bold]{total:,}[/] photo pages  →  {index_html}")


@main.command("fetch-external")
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--api-key",
    envvar="FLICKR_API_KEY",
    required=True,
    help="Flickr API key. Also read from FLICKR_API_KEY env var.",
)
@click.option(
    "--what",
    type=click.Choice(["avatars", "thumbnails", "full"]),
    default="full",
    show_default=True,
    help="Which external assets to fetch.",
)
def fetch_external(output_dir: Path, api_key: str, what: str) -> None:
    """Stage 2b: download avatars and/or fave thumbnails from Flickr."""
    fetch_collector = IssueCollector()
    try:
        _fetch_with_progress(
            output_dir=output_dir,
            api_key=api_key,
            include_thumbnails=what in ("thumbnails", "full"),
            include_avatars=what in ("avatars", "full"),
            collector=fetch_collector,
        )
    except Exception as exc:
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_SOFTWARE)
    _print_issues(fetch_collector, "fetch-external")
    _err.print(f"[green]✓[/] External assets fetched into [bold]{output_dir}[/]")


@main.command()
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    "output_dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option("--cache-dir", default=None, type=click.Path(file_okay=False, path_type=Path))
@click.option("--theme", default="minimal-archive", show_default=True)
@click.option("--jobs", default=0, type=int)
@click.option("--include-private", is_flag=True)
@click.option("--include-private-photos", is_flag=True)
@click.option(
    "--hide-unsafe",
    is_flag=True,
    help="Blur thumbnails for moderate/restricted photos.",
)
@click.option(
    "--include-missing-media",
    is_flag=True,
    help="Show tombstone tiles for photos with no media file.",
)
@click.option(
    "--archive-external",
    type=click.Choice(["none", "avatars", "thumbnails", "full"]),
    default="none",
    show_default=True,
    help="Download external assets (avatars/thumbnails) from Flickr API.",
)
@click.option(
    "--flickr-api-key",
    envvar="FLICKR_API_KEY",
    default=None,
    help="Flickr API key (required when --archive-external != none).",
)
def build(
    source: Path,
    output_dir: Path,
    cache_dir: Path | None,
    theme: str,
    jobs: int,
    include_private: bool,
    include_private_photos: bool,
    hide_unsafe: bool,
    include_missing_media: bool,
    archive_external: str,
    flickr_api_key: str | None,
) -> None:
    """Run all three stages: ingest → derive → render."""
    resolved = _extract_with_progress(source, cache_dir or DEFAULT_CACHE) or source
    if not (resolved / "account_profile.json").is_file():
        _err.print("[red]error:[/] account_profile.json not found.")
        sys.exit(EX_DATAERR)
    try:
        # Stage 1: ingest
        build_ingest_collector = IssueCollector()
        with _err.status("[bold][1/3][/] Ingesting export…"):
            archive = run_ingest(
                source=resolved,
                output_dir=output_dir,
                include_private=include_private,
                include_private_photos=include_private_photos,
                collector=build_ingest_collector,
            )
        _print_issues(build_ingest_collector, "ingest")
        n_photos = len(archive.photos)
        n_albums = len(archive.albums or [])
        n_groups = len(archive.groups or [])
        _err.print(
            f"[green]✓[/] [bold][1/3][/] Ingested "
            f"[bold]{n_photos:,}[/] photos · "
            f"[bold]{n_albums}[/] albums · "
            f"[bold]{n_groups}[/] groups"
        )

        # Stage 2: derive
        build_derive_collector = IssueCollector()
        total_media = sum(1 for p in archive.photos if p.media is not None)
        with _progress(
            TextColumn("[bold][2/3][/] Processing media  "),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn(" "),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("", total=total_media)
            run_derive(
                output_dir=output_dir,
                jobs=jobs,
                on_progress=lambda: progress.advance(task),
                collector=build_derive_collector,
            )
        _print_issues(build_derive_collector, "derive")
        _err.print(f"[green]✓[/] [bold][2/3][/] Processed [bold]{total_media:,}[/] media files")

        # Stage 2b: optional external asset fetch
        if archive_external != "none":
            if not flickr_api_key:
                _err.print(
                    "[red]error:[/] --archive-external requires FLICKR_API_KEY or --flickr-api-key"
                )
                sys.exit(EX_USAGE)
            fetch_collector = IssueCollector()
            _fetch_with_progress(
                output_dir=output_dir,
                api_key=flickr_api_key,
                include_thumbnails=archive_external in ("thumbnails", "full"),
                include_avatars=archive_external in ("avatars", "full"),
                collector=fetch_collector,
            )
            _print_issues(fetch_collector, "fetch-external")
            _err.print("[green]✓[/] External assets fetched")

        # Stage 3: render — reload model.json (picks up derive + any external asset updates)
        archive = OfflickrArchive.model_validate(
            json.loads((output_dir / "data" / "model.json").read_text(encoding="utf-8"))
        )
        with _progress(
            TextColumn("[bold][3/3][/] Rendering site    "),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn(" "),
        ) as progress:
            task = progress.add_task("", total=n_photos)
            render_site(
                archive=archive,
                output_dir=output_dir,
                theme=theme,
                on_progress=lambda: progress.advance(task),
                hide_unsafe=hide_unsafe,
                include_missing_media=include_missing_media,
            )
        _err.print(f"[green]✓[/] [bold][3/3][/] Rendered [bold]{n_photos:,}[/] photo pages")

    except Exception as exc:  # pragma: no cover
        _err.print(f"[red]error:[/] {exc}")
        sys.exit(EX_SOFTWARE)

    click.echo(f"Site ready at {output_dir / 'index.html'}")


def _print_derive_estimates(archive: OfflickrArchive) -> None:
    """Print estimated run times and disk usage for the given archive."""
    photos = archive.photos
    n_media = sum(1 for p in photos if p.media is not None)
    total_bytes = sum(p.media.bytes for p in photos if p.media and p.media.bytes)
    total_mb = total_bytes / (1024 * 1024)
    est_derive_s = max(1, n_media // 2)
    est_render_s = max(1, len(photos) // 33)
    est_thumbs_mb = n_media * 30 / 1024
    est_display_mb = n_media * 200 / 1024
    click.echo("")
    click.echo("Estimated (first run, --jobs 4):")
    click.echo("  Stage 1 ingest : < 30 s")
    click.echo(f"  Stage 2 derive : ~{est_derive_s:,} s")
    click.echo(f"  Stage 3 render : ~{est_render_s:,} s")
    click.echo("Estimated disk usage:")
    click.echo(f"  Originals : {total_mb:,.0f} MB")
    click.echo(f"  Thumbs    : ~{est_thumbs_mb:,.0f} MB")
    click.echo(f"  Display   : ~{est_display_mb:,.0f} MB")
    click.echo(f"  Total     : ~{total_mb + est_thumbs_mb + est_display_mb:,.0f} MB")


@main.command()
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def inspect(output_dir: Path) -> None:
    """Print a summary of a built archive (reads data/model.json)."""
    model_path = output_dir / "data" / "model.json"
    if not model_path.exists():
        _err.print(f"[red]error:[/] {model_path} not found — run 'offlickr ingest' first.")
        sys.exit(EX_DATAERR)
    archive = OfflickrArchive.model_validate(
        json.loads(model_path.read_text(encoding="utf-8"))
    )
    photos = archive.photos
    geo_count = sum(1 for p in photos if p.geo is not None)
    video_count = sum(1 for p in photos if p.media and p.media.kind == "video")
    missing_media = sum(1 for p in photos if p.media is None)
    total_bytes = sum(p.media.bytes for p in photos if p.media and p.media.bytes)
    total_mb = total_bytes / (1024 * 1024)

    dates = [p.date_taken or p.date_imported for p in photos]
    if dates:
        earliest = min(dates).strftime("%Y-%m-%d")
        latest = max(dates).strftime("%Y-%m-%d")
        date_range = f"{earliest} → {latest}"
    else:
        date_range = "n/a"

    own_nsid = archive.account.nsid
    external_user_nsids = {
        c.user_nsid for p in photos for c in p.comments
        if c.user_nsid != own_nsid
    }
    local_ids = {p.id for p in photos}
    external_photo_count = sum(
        1 for g in archive.galleries
        for pid in g.photo_ids
        if pid not in local_ids
    )

    click.echo(f"Archive   : {archive.account.screen_name} ({archive.account.nsid})")
    click.echo(f"Built at  : {archive.generator.built_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"Date range: {date_range}")
    click.echo(f"Photos    : {len(photos):,}")
    click.echo(f"  with geo       : {geo_count:,}")
    click.echo(f"  videos         : {video_count:,}")
    click.echo(f"  missing media  : {missing_media:,}")
    click.echo(f"Media size: {total_mb:,.0f} MB (originals not yet derived = 0)")
    click.echo(f"Albums    : {len(archive.albums):,}")
    click.echo(f"Galleries : {len(archive.galleries):,}")
    click.echo(f"  ext photos     : {external_photo_count:,}")
    click.echo(f"Groups    : {len(archive.groups):,}")
    click.echo(f"Favorites : {len(archive.faves):,}")
    click.echo(f"Users idx : {len(archive.users):,}")
    click.echo(f"Ext users : {len(external_user_nsids):,}")

    _print_derive_estimates(archive)


@main.command()
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--port", default=8000, show_default=True)
@click.option("--host", default="127.0.0.1", show_default=True)
def serve(output_dir: Path, port: int, host: str) -> None:
    """Serve a built site locally via http.server."""
    os.chdir(output_dir)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(output_dir))
    with http.server.HTTPServer((host, port), handler) as httpd:
        click.echo(f"Serving {output_dir} at http://{host}:{port}")
        click.echo("Press Ctrl+C to stop.")
        with contextlib.suppress(KeyboardInterrupt):
            httpd.serve_forever()


if __name__ == "__main__":
    main()
