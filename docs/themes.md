# Themes

offlickr ships one built-in theme. The default is `minimal-archive`.

## Built-in themes

### `minimal-archive` (default)

White background, serif headings, justified photo grid. Prioritizes content longevity — designed to look clean 20 years from now. Client-side search (debounced substring, NFC-normalized).

### `flickr-classic` (planned)

Evokes flickr.com circa 2020. Dark-on-white grid, tab navigation, photo detail with right-rail comments. Not yet available.

## Selecting a theme

```bash
offlickr build ~/flickr-export -o ~/archive --theme flickr-classic
offlickr render ~/archive --theme flickr-classic
```

## Custom themes

A theme is a directory with this structure:

```
my-theme/
  templates/
    base.html.j2
    photostream.html.j2
    photo.html.j2
    about.html.j2
    albums_index.html.j2
    album.html.j2
    galleries_index.html.j2
    gallery.html.j2
    tags_index.html.j2
    tag.html.j2
    map.html.j2
    faves_index.html.j2
    groups_index.html.j2
    testimonials.html.j2
    private/                  # rendered only when --include-private
      contacts.html.j2
      followers.html.j2
      flickrmail_sent.html.j2
      flickrmail_received.html.j2
      my_comments.html.j2
      my_group_posts.html.j2
  static/
    style.css
    search.js
    [any other static assets]
```

Pass a filesystem path instead of a name:

```bash
offlickr build ~/flickr-export -o ~/archive --theme /path/to/my-theme
```

### Template variables

Every template receives at minimum:

- `account`: the `Account` model (screen_name, join_date, description_html, etc.)
- `base_url`: a relative path prefix to reach the site root (e.g. `../` for pages one level deep, `""` for root-level pages).

Page-specific variables are documented in [docs/data-model.md](data-model.md).
