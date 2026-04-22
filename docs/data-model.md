# Data model

offlickr parses your Flickr export into a single normalized document, `model.json`, with a JSON Schema at `model.schema.json` in the same directory.

The top-level object (`OfflickrArchive`) contains:

- `generator` — `{ name, version, built_at }`
- `export` — `{ source_dir, detected_format_version }`
- `account` — your profile, stats, and settings
- `photos[]` — every photo, joined with its media file
- `albums[]`, `galleries[]`, `groups[]`, `faves[]`, `testimonials`
- `users{}` — deduped map of every user-ID the archive refers to
- `contacts`, `followers`, `flickrmail`, `my_comments`, `my_group_posts`, `set_comments`, `gallery_comments` — populated only with `--include-private`

For the authoritative field-by-field definition, read the `model.schema.json` that is emitted alongside your build. It is the contract; human docs here are a summary.
