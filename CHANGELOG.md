# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

[Unreleased]: https://github.com/yaniv-golan/offlickr/compare/v0.1.0...HEAD

## [0.1.0] - 2026-04-22

### Added

- Initial project scaffolding: pyproject with SPDX license, ruff/mypy/pytest config, CI (lint/test/build/audit/docs), release workflow (PyPI OIDC + SLSA + SBOM), CodeQL, dependabot.
- Fixture dataset at `tests/fixtures/mini-export/` with 10 photos covering edge cases (Hebrew text, missing media, private photo, PNG, pretend-video, geo).
- `offlickr.model` with Pydantic v2 models: `Account`, `Photo`, `Album`, `Gallery`, `GroupRef`, `User`, `Fave`, `Media`, `Geo`, `Tag`, `Comment`, `Exif`, `OfflickrArchive`.
- `offlickr.render.sanitize.sanitize_html` — nh3-based HTML sanitizer with external-link rel stamping.
- `offlickr.ingest` parsers: account, albums, galleries, groups, contacts, followers, faves, photos (with media-file join), plus SHA-256-keyed zip extraction cache. Private-data parsers: outgoing comments, gallery/app/set comments, group posts, Flickrmail, testimonials, contacts, followers.
- `offlickr ingest <source> -o <output>` CLI subcommand with `--include-private` and `--include-private-photos` flags, emitting validated `model.json` + `model.schema.json`.
- `offlickr.derive`: parallel media processing via `ProcessPoolExecutor` (spawn context); cascade resize — single full-res decode produces WebP thumbnail (240px, BICUBIC) and display image (1600px) in one pass; EXIF extraction; video passthrough with ffmpeg/SVG fallback; NFC-normalised client-side `search.json`. Dimensions cached across reruns.
- `offlickr derive <output_dir>` CLI subcommand with `--jobs` flag.
- `offlickr fetch-external <output_dir>` — downloads user avatars and fave thumbnails from the Flickr API. `--what avatars|thumbnails|full`.
- `offlickr.render`: Jinja2 site rendering with `minimal-archive` theme — paginated photostream (60/page), photo detail pages (EXIF, comments, tags, map), albums, galleries, groups, tags, map, faves, testimonials, and private views (outgoing comments, group posts, Flickrmail sent/received, contacts, followers).
- `offlickr render <output_dir>` and `offlickr build <source> -o <output>` (all stages in one command, with `--archive-external` flag).
- `offlickr inspect <output_dir>` — prints archive summary and derive time estimates.
- `offlickr serve <output_dir>` — local preview server.
- `IssueCollector`: non-fatal pipeline failures (malformed ingest records, failed media processing, failed asset downloads) are now accumulated and printed as a per-stage summary to stderr. Exit code stays 0; users see exactly which records were skipped and why.
- Per-zip progress bars during extraction (name + percentage). Per-asset-kind progress bars during external fetch.
- `docs/getting-started.md`, `docs/cli-reference.md`, `docs/data-model.md`, `docs/themes.md`, `docs/external-fetching.md`.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).

[0.1.0]: https://github.com/yaniv-golan/offlickr/releases/tag/v0.1.0
