# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-08-04

Maintenance release. No functional changes to the pipeline or output.

### Security

- Update locked dependencies to clear every advisory reported by `pip-audit`:
  `pillow` 12.3.0, `click` 8.4.2, `urllib3` 2.7.0, `idna` 3.15, `soupsieve`
  2.8.4, `msgpack` 1.2.1, `pip` 26.1.2. These are `uv.lock` changes, so they
  affect development, CI, and anyone installing from the lockfile. Runtime
  constraints in `pyproject.toml` are unchanged lower bounds, so PyPI installs
  already resolved to fixed versions.
- Pin every GitHub Action to a commit SHA and narrow workflow `permissions` to
  the jobs that need them.

### Changed

- Bump all GitHub Actions to current majors (`checkout` v7, `setup-node` v7,
  `upload-artifact` v7, `download-artifact` v8, `codecov-action` v7,
  `codeql-action` v4.37.1), clearing the Node 20 deprecation warning.
- `release.yml` gained a `workflow_dispatch` trigger that can publish only to
  TestPyPI, so the publish path can be exercised without consuming a real
  version number.

## [0.1.0] - 2026-04-22

Initial release.

Converts a Flickr *Your Flickr Data* export into a self-contained static website. Includes ingest, derive, render, and optional external-asset fetch stages; `minimal-archive` theme; date archive, EXIF sidecar, `--flickr-origin` mode, and bundled WOFF2 fonts.

[Unreleased]: https://github.com/yaniv-golan/offlickr/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/yaniv-golan/offlickr/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/yaniv-golan/offlickr/releases/tag/v0.1.0
