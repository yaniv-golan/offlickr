# Getting started

## Install

```bash
pipx install offlickr
# or
uv tool install offlickr
```

If installing from source:

```bash
git clone https://github.com/yaniv-golan/offlickr
cd offlickr
uv sync --all-extras --dev
```

## Request your Flickr data

1. Sign in to flickr.com.
2. Go to **You → Settings → Your Flickr Data**.
3. Click **Request my Flickr Data**.
4. Flickr emails you (typically within a few hours to a day) with links to download ~5 zip files. Put them all in one folder.

## Quickstart

```bash
# Download your Flickr zips to one folder, then:
offlickr build ~/Downloads/flickr-export -o ~/my-flickr-archive
offlickr serve ~/my-flickr-archive    # opens http://127.0.0.1:8000
```

`offlickr build` runs all three stages automatically: ingest → derive → render.

## Running stages individually

For larger archives you may want to re-run only one stage (e.g. to change the theme without redoing thumbnail generation):

```bash
# Stage 1: parse the export into model.json
offlickr ingest ~/Downloads/flickr-export -o ~/my-flickr-archive

# Stage 2: generate thumbnails, display images, and search index
offlickr derive ~/my-flickr-archive --jobs 4

# Stage 3: render the static site
offlickr render ~/my-flickr-archive --theme minimal-archive
```

See [docs/cli-reference.md](cli-reference.md) for all options.

## Do you need a Flickr API key?

No — the core workflow (`ingest → derive → render`) makes no network requests and requires no account or API key.

A key is only needed for the optional `fetch-external` stage, which downloads avatars and fave thumbnails from other Flickr accounts. If you skip that stage (or don't use `--archive-external` with `build`), you never need one.

**To get a free API key** (non-commercial use, approved in minutes):

1. Sign in at [flickr.com/services/apps/create](https://www.flickr.com/services/apps/create).
2. Choose **Apply for a Non-Commercial Key**.
3. Fill in the app name and description (e.g. "Personal archive with offlickr").
4. Copy the **Key** value — you don't need the Secret.
5. Set it in your environment before running `fetch-external`:

```bash
export FLICKR_API_KEY=your_key_here
offlickr fetch-external ~/my-flickr-archive
```

Or put `FLICKR_API_KEY=your_key_here` in a `.env` file in the directory where you run offlickr — it's loaded automatically.

## Privacy

Private photos (privacy not public) are excluded by default. Use `--include-private-photos` to include them.

Private views — contacts, followers, flickrmail, your comments, group posts, and album/gallery comments — are excluded by default. Use `--include-private` to include them.

## What to keep

`offlickr build` produces two distinct things. Understanding the difference matters for storage and long-term preservation.

### The data layer — archive this

| Path | What it is |
| ---- | ---------- |
| `data/model.json` | All your metadata: photos, albums, comments, EXIF, people. Portable JSON; can be processed by any future tool. |
| `originals/` | Your original photo and video files, copied from the Flickr export. |

These two together are your archive. Everything else can be regenerated from them.

### The rendered site — regeneratable

| Path | Regenerate with |
| ---- | --------------- |
| `thumbs/` | `offlickr derive` |
| `display/` | `offlickr derive` |
| `*.html`, `assets/` | `offlickr render` |

If storage space is a concern, deleting `thumbs/` and `display/` is safe — they are derived from the originals and can be recreated at any time. The HTML site is a view of the data, not the data itself.

### Don't delete the Flickr export ZIPs

The ZIP files Flickr sent you (`~/Downloads/flickr-export/` or wherever you put them) are the canonical source. offlickr reads from them — it does not replace them. Keep them alongside your offlickr output.

### Minimum cold-storage footprint

```text
flickr-export/       ← your original Flickr ZIPs (from Flickr)
my-flickr-archive/
  data/
    model.json       ← all metadata, enriched by offlickr
  originals/         ← your photos and videos
```

This is roughly the size of your original photos with no overhead. The full output directory (including `thumbs/`, `display/`, and the site HTML) can always be rebuilt from this set.
