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

## Privacy

Private photos (privacy not public) are excluded by default. Use `--include-private-photos` to include them.

Private views — contacts, followers, flickrmail, your comments, group posts, and album/gallery comments — are excluded by default. Use `--include-private` to include them.
