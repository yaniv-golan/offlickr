# CLI reference

offlickr automatically loads a `.env` file from the current working directory
on startup, so you can store `FLICKR_API_KEY` there instead of exporting it
in your shell.

---

## `offlickr ingest <source> -o <output>`

Stage 1: parse a Flickr export (extracted directory or folder of zip files) into a normalized model.

**Options:**

- `-o, --output PATH` (required) — output directory. `model.json` and `model.schema.json` are written to `<output>/data/`.
- `--cache-dir PATH` — directory for zip extraction cache (default: `~/.cache/offlickr`).
- `--include-private` — serialize private views (contacts, followers) into `model.json`.
- `--include-private-photos` — include photos with privacy not equal to public.

**Exit codes (sysexits.h):**

- `0` success
- `65` input does not look like a Flickr export (missing `account_profile.json`)
- `70` internal error

---

## `offlickr derive <output_dir>`

Stage 2: generate thumbnails (240px WebP), display images (1600px WebP), copy originals, extract EXIF, and emit a client-side search index.

**Options:**

- `--jobs INTEGER` — parallel worker processes. Default: `min(cpu_count, 4)`. Pass `1` to disable parallelism.

Reads `<output_dir>/data/model.json` and `<output_dir>/data/media-index.json`. Writes under `<output_dir>/assets/` (thumbs, display, originals, search.json).

---

## `offlickr fetch-external <output_dir>`

Stage 2b (optional): download avatars and fave thumbnails from the Flickr API and patch `model.json` in-place.

**Options:**

- `--api-key TEXT` — Flickr API key. Also read from `FLICKR_API_KEY` env var or `.env` file. **Required.**
- `--what {avatars,thumbnails,full}` — which assets to fetch (default: `full`).

Assets are stored in `<output_dir>/avatars/` and `<output_dir>/fave-thumbs/`. Re-runs skip files that already exist.

See [external-fetching.md](external-fetching.md) for details.

---

## `offlickr render <output_dir>`

Stage 3: render `model.json` into a static HTML site.

**Options:**

- `--theme TEXT` — theme name or path to a custom theme directory (default: `minimal-archive`).
- `--hide-unsafe` — exclude moderate/restricted photos from the photostream entirely (build-time; use for shared archives).
- `--include-missing-media` — show tombstone tiles for photos with no media file.
- `--include-exif-pii` — include identifying EXIF fields (Artist, Copyright, camera/lens serial numbers) in photo pages. Stripped by default.

Reads `<output_dir>/data/model.json`. Writes `index.html`, `about.html`, `photo/<id>.html`, `archive/index.html`, `archive/YYYY.html` (one per year), `archive/undated.html`, and copies theme static assets.

---

## `offlickr build <source> -o <output>`

Convenience command that chains ingest → derive → (optional fetch) → render.

**Options:**

- `-o, --output PATH` (required) — output directory.
- `--cache-dir PATH` — zip extraction cache directory.
- `--theme TEXT` — theme name or path (default: `minimal-archive`).
- `--jobs INTEGER` — parallel workers for derive stage.
- `--include-private` — include private views.
- `--include-private-photos` — include non-public photos.
- `--hide-unsafe` — exclude moderate/restricted photos from the photostream entirely (build-time; use for shared archives).
- `--include-missing-media` — show tombstone tiles for photos with no media file.
- `--include-exif-pii` — include identifying EXIF fields (Artist, Copyright, camera/lens serial numbers) in photo pages.
- `--archive-external {none,avatars,thumbnails,full}` — download external assets from Flickr API between derive and render (default: `none`).
- `--flickr-api-key TEXT` — Flickr API key, required when `--archive-external` is not `none`. Also read from `FLICKR_API_KEY` env var or `.env` file.

---

## `offlickr inspect <output_dir>`

Print a summary of a built archive (photo counts, date range, estimated build times).

---

## `offlickr serve <output_dir>`

Serve a built site locally via Python's built-in `http.server`.

**Options:**

- `--port INTEGER` — port to listen on (default: `8000`).
- `--host TEXT` — host to bind to (default: `127.0.0.1`).

Press `Ctrl+C` to stop the server.
