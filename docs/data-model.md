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

Each photo's `exif` object is populated by `offlickr derive`. It has three tiers of fields:

- **Level 1 (always shown):** `make`, `model`, `lens_make`, `lens_model`, `focal_length`, `focal_length_35mm`, `f_number`, `exposure_time`, `iso`.
- **Level 2 (shown in a collapsed panel):** `exposure_mode`, `flash`, `metering_mode`, `white_balance`, `color_space`, `orientation`, `software`, `image_width`, `image_height`.
- **Level 3 (raw dump, collapsed):** `raw_fields` — all EXIF tags extracted from the file.
- **PII fields (opt-in via `--include-exif-pii`):** `artist`, `copyright_notice`, `camera_serial`, `lens_serial` — stripped from rendered output by default.

For the authoritative field-by-field definition, read the `model.schema.json` that is emitted alongside your build. It is the contract; human docs here are a summary.
