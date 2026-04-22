# External Asset Fetching

By default, offlickr builds your archive without making any network requests.
Fave thumbnails and user avatars from other Flickr accounts are shown as
text placeholders. To include them as actual images, enable external fetching.

## Quick start

```bash
# Add to your .env file (recommended):
echo "FLICKR_API_KEY=your_key_here" >> .env

# Then build with external assets:
offlickr build ~/flickr-export -o ~/archive --archive-external full

# Or fetch separately after building:
offlickr fetch-external ~/archive --what full
```

## Getting an API key

1. Go to https://www.flickr.com/services/apps/create/ and create a non-commercial app.
2. Copy your **API key** (not the secret — only the key is needed).
3. Either add it to a `.env` file in the project directory, or export it:

```bash
# .env file (auto-loaded):
FLICKR_API_KEY=your_key_here

# Or as a shell export:
export FLICKR_API_KEY=your_key_here
```

offlickr automatically loads `.env` from the current working directory on startup.

## Modes

| Mode | What gets fetched |
|---|---|
| `none` | Nothing — no network requests (default) |
| `avatars` | Buddy-icon JPGs for every user referenced in your archive |
| `thumbnails` | Square thumbnails for faved photos (up to 150×150 px, largest available) |
| `full` | Both avatars and thumbnails |

## `build --archive-external`

Add the flag to your `build` command to fetch assets as part of the build:

```bash
offlickr build ~/flickr-export -o ~/archive \
  --archive-external full \
  --flickr-api-key YOUR_KEY   # or omit if FLICKR_API_KEY is in .env
```

Fetching happens between the derive and render stages, so the rendered site
always reflects the freshly downloaded assets.

## `fetch-external` (standalone)

If you've already built the site and just want to update assets without a full
rebuild:

```bash
offlickr fetch-external ~/archive --what avatars
offlickr render ~/archive          # re-render to pick up new assets
```

**Options:**
- `--what {avatars,thumbnails,full}` — which assets to fetch (default: `full`)
- `--api-key TEXT` — Flickr API key (also read from `FLICKR_API_KEY`)

## Where assets are stored

Downloaded assets land directly in the output directory alongside the rest of
the site:

```
~/archive/
  avatars/<nsid>.jpg          # user buddy icons
  fave-thumbs/<photo_id>.jpg  # faved photo thumbnails
  data/model.json             # patched in-place with paths
```

Re-runs skip files that already exist, so subsequent fetches only download
what's new or missing.

## Flickr API Terms of Use

The Flickr API ToS discourages permanent image caching as a replacement for
Flickr hosting. offlickr's external fetch is intended as a personal archive
aid. You are responsible for complying with the ToS in your jurisdiction and
use case. offlickr defaults to `--archive-external none` so the tool works
fully without any fetching, and never bundles fetched content with the package.
