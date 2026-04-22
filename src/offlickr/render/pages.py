"""Page emitters for the offlickr render stage."""

from __future__ import annotations

import collections
import importlib.resources
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, PackageLoader

from offlickr.model import Comment, Gallery, Note, OfflickrArchive
from offlickr.render.filters import register_filters
from offlickr.render.pagination import paginate
from offlickr.render.slug import slugify_tags

PHOTOS_PER_PAGE = 60


def _build_env(theme: str) -> Environment:
    theme_path = Path(theme)
    if theme_path.is_dir():
        loader: PackageLoader | FileSystemLoader = FileSystemLoader(
            str(theme_path / "templates")
        )
    else:
        loader = PackageLoader("offlickr", f"themes/{theme}/templates")
    env = Environment(loader=loader, autoescape=True)
    register_filters(env)
    return env


def _copy_static(theme: str, output_dir: Path) -> None:
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    theme_path = Path(theme)
    if theme_path.is_dir():
        static_dir = theme_path / "static"
        if static_dir.is_dir():
            for src in static_dir.iterdir():
                if src.is_file():
                    shutil.copy2(src, assets / src.name)
        return
    pkg_path = importlib.resources.files("offlickr").joinpath(f"themes/{theme}/static")
    for src in pkg_path.iterdir():
        if hasattr(src, "is_file") and src.is_file():
            shutil.copy2(str(src), assets / src.name)


def _set_env_globals(env: Environment, theme: str, output_dir: Path) -> None:
    """Populate Jinja2 globals used across all templates for file:// compatibility."""
    search_json = output_dir / "assets" / "search.json"
    env.globals["search_index"] = (
        json.loads(search_json.read_text(encoding="utf-8")) if search_json.exists() else []
    )
    try:
        world_svg = importlib.resources.files("offlickr").joinpath(
            f"themes/{theme}/static/world.svg"
        )
        env.globals["world_svg_content"] = world_svg.read_text(encoding="utf-8")
    except Exception:
        env.globals["world_svg_content"] = ""


def render_site(
    archive: OfflickrArchive,
    output_dir: Path,
    theme: str = "minimal-archive",
    on_progress: Callable[[], None] | None = None,
    include_missing_media: bool = False,
    hide_unsafe: bool = False,
) -> None:
    env = _build_env(theme)
    _copy_static(theme, output_dir)
    _set_env_globals(env, theme, output_dir)
    env.globals["photo_url_map"] = {p.photopage_url: f"photo/{p.id}.html" for p in archive.photos}
    all_tags = sorted({t.tag for p in archive.photos for t in p.tags})
    env.globals["tag_slug_map"] = slugify_tags(all_tags)
    has_map = any(p.geo is not None for p in archive.photos)
    gallery_refs = _build_gallery_refs(archive)

    # Remove stale private output when not rendering private views (#1).
    if archive.contacts is None:
        private_dir = output_dir / "private"
        if private_dir.exists():
            shutil.rmtree(private_dir)

    _render_photostream(
        archive, output_dir, env, has_map=has_map,
        include_missing_media=include_missing_media,
        hide_unsafe=hide_unsafe,
    )
    _render_photo_pages(
        archive, output_dir, env,
        has_map=has_map, on_progress=on_progress, gallery_refs=gallery_refs,
        hide_unsafe=hide_unsafe,
    )
    _render_about(archive, output_dir, env, has_map=has_map)
    _render_albums(archive, output_dir, env, has_map=has_map, hide_unsafe=hide_unsafe)
    _render_galleries(archive, output_dir, env, has_map=has_map, hide_unsafe=hide_unsafe)
    _render_tags(archive, output_dir, env, has_map=has_map, hide_unsafe=hide_unsafe)
    if has_map:
        _render_map(archive, output_dir, env)
    _render_faves(archive, output_dir, env, has_map=has_map)
    _render_groups(archive, output_dir, env, has_map=has_map)
    _render_testimonials(archive, output_dir, env, has_map=has_map)
    if archive.contacts is not None:
        _render_private_views(archive, output_dir, env, has_map=has_map)


def _render_photostream(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *,
    has_map: bool, include_missing_media: bool = False, hide_unsafe: bool = False,
) -> None:
    template = env.get_template("photostream.html.j2")
    photos = archive.photos
    pages = paginate(photos, PHOTOS_PER_PAGE)
    total = len(pages)
    for i, page_photos in enumerate(pages, 1):
        if i == 1:
            out_path = output_dir / "index.html"
            base = ""
        else:
            out_path = output_dir / "photostream" / f"page-{i}.html"
            base = "../"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if i == 1:
            prev_url = None
            next_url = "photostream/page-2.html" if total > 1 else None
        elif i == total:
            prev_url = "../index.html" if i == 2 else f"page-{i - 1}.html"
            next_url = None
        else:
            prev_url = "../index.html" if i == 2 else f"page-{i - 1}.html"
            next_url = f"page-{i + 1}.html"

        pagination = (
            {"current": i, "total": total, "prev_url": prev_url, "next_url": next_url}
            if total > 1
            else None
        )
        out_path.write_text(
            template.render(
                account=archive.account,
                photos=page_photos,
                base_url=base,
                pagination=pagination,
                has_map=has_map,
                include_missing_media=include_missing_media,
                hide_unsafe=hide_unsafe,
            ),
            encoding="utf-8",
        )


def _build_gallery_refs(archive: OfflickrArchive) -> dict[str, list[Gallery]]:
    refs: dict[str, list[Gallery]] = {}
    for gallery in archive.galleries:
        for pid in gallery.photo_ids:
            refs.setdefault(pid, []).append(gallery)
    return refs


def _transform_notes(
    notes: list[Note], rotation: int, display_w: int, display_h: int
) -> list[Note]:
    """Remap note pixel coords from pre-Flickr-rotation space into display space."""
    if not notes or rotation == 0 or not display_w or not display_h:
        return notes
    pre_w = display_h if rotation in (90, 270) else display_w
    pre_h = display_w if rotation in (90, 270) else display_h
    result: list[Note] = []
    for note in notes:
        x, y, w, h = note.x, note.y, note.w, note.h
        if rotation == 90:
            nx, ny, nw, nh = pre_h - y - h, x, h, w
        elif rotation == 180:
            nx, ny, nw, nh = pre_w - x - w, pre_h - y - h, w, h
        elif rotation == 270:
            nx, ny, nw, nh = y, pre_w - x - w, h, w
        else:
            nx, ny, nw, nh = x, y, w, h
        result.append(note.model_copy(update={"x": nx, "y": ny, "w": nw, "h": nh}))
    return result


def _render_photo_pages(
    archive: OfflickrArchive,
    output_dir: Path,
    env: Environment,
    *,
    has_map: bool,
    on_progress: Callable[[], None] | None = None,
    gallery_refs: dict[str, list[Gallery]] | None = None,
    hide_unsafe: bool = False,
) -> None:
    template = env.get_template("photo.html.j2")
    photos_dir = output_dir / "photo"
    photos_dir.mkdir(parents=True, exist_ok=True)
    n = len(archive.photos)
    _gallery_refs = gallery_refs or {}
    for i, photo in enumerate(archive.photos):
        prev_photo = archive.photos[i + 1] if i + 1 < n else None
        next_photo = archive.photos[i - 1] if i > 0 else None
        display_notes = (
            _transform_notes(
                photo.notes, photo.rotation,
                photo.media.width or 0, photo.media.height or 0,
            )
            if photo.media else photo.notes
        )
        (photos_dir / f"{photo.id}.html").write_text(
            template.render(
                account=archive.account,
                photo=photo,
                display_notes=display_notes,
                base_url="../",
                prev_photo=prev_photo,
                next_photo=next_photo,
                has_map=has_map,
                hide_unsafe=hide_unsafe,
                gallery_refs=_gallery_refs.get(photo.id, []),
                users=archive.users,
            ),
            encoding="utf-8",
        )
        if on_progress:
            on_progress()


def _render_about(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *, has_map: bool
) -> None:
    template = env.get_template("about.html.j2")
    has_testimonials = bool(archive.testimonials.given or archive.testimonials.received)
    archive_counts = {
        "Photos": len(archive.photos),
        "Albums": len(archive.albums or []),
        "Galleries": len(archive.galleries or []),
        "Groups": len(archive.groups or []),
        "Favorites": len(archive.faves or []),
    }
    photo_by_id = {p.id: p for p in archive.photos}
    showcase_photos = [
        photo_by_id[pid]
        for pid in archive.account.showcase_photo_ids
        if pid in photo_by_id and photo_by_id[pid].media
    ]
    (output_dir / "about.html").write_text(
        template.render(
            account=archive.account,
            base_url="",
            has_testimonials=has_testimonials,
            has_map=has_map,
            archive_counts=archive_counts,
            showcase_photos=showcase_photos,
        ),
        encoding="utf-8",
    )


def _render_albums(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *,
    has_map: bool, hide_unsafe: bool = False,
) -> None:
    photo_by_id = {p.id: p for p in archive.photos}
    cover_thumbs: dict[str, str] = {}
    for album in archive.albums:
        cover_id = album.cover_photo_id
        if cover_id and cover_id in photo_by_id and photo_by_id[cover_id].media:
            cover_thumbs[album.id] = cover_id
        elif album.photo_ids:
            for pid in album.photo_ids:
                if pid in photo_by_id and photo_by_id[pid].media:
                    cover_thumbs[album.id] = pid
                    break

    albums_dir = output_dir / "albums"
    albums_dir.mkdir(parents=True, exist_ok=True)

    index_tmpl = env.get_template("albums_index.html.j2")
    (albums_dir / "index.html").write_text(
        index_tmpl.render(
            account=archive.account,
            albums=archive.albums,
            cover_thumbs=cover_thumbs,
            base_url="../",
            has_map=has_map,
            hide_unsafe=hide_unsafe,
        ),
        encoding="utf-8",
    )

    set_comments: dict[str, list[Comment]] = archive.set_comments or {}
    detail_tmpl = env.get_template("album.html.j2")
    for album in archive.albums:
        photos = [photo_by_id[pid] for pid in album.photo_ids if pid in photo_by_id]
        (albums_dir / f"{album.id}.html").write_text(
            detail_tmpl.render(
                account=archive.account,
                album=album,
                photos=photos,
                base_url="../",
                has_map=has_map,
                hide_unsafe=hide_unsafe,
                comments=set_comments.get(album.id, []),
            ),
            encoding="utf-8",
        )


def _render_galleries(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *,
    has_map: bool, hide_unsafe: bool = False,
) -> None:
    photo_by_id = {p.id: p for p in archive.photos}
    galleries_dir = output_dir / "galleries"
    galleries_dir.mkdir(parents=True, exist_ok=True)

    index_tmpl = env.get_template("galleries_index.html.j2")
    (galleries_dir / "index.html").write_text(
        index_tmpl.render(
            account=archive.account,
            galleries=archive.galleries,
            base_url="../",
            has_map=has_map,
            hide_unsafe=hide_unsafe,
        ),
        encoding="utf-8",
    )

    gallery_comments: dict[str, list[Comment]] = archive.gallery_comments or {}
    detail_tmpl = env.get_template("gallery.html.j2")
    for gallery in archive.galleries:
        photo_items: list[dict[str, object]] = []
        for pid in gallery.photo_ids:
            if pid in photo_by_id:
                photo_items.append({"local": True, "photo": photo_by_id[pid]})
            else:
                photo_items.append(
                    {"local": False, "url": f"https://www.flickr.com/photos/x/{pid}/"}
                )
        (galleries_dir / f"{gallery.id}.html").write_text(
            detail_tmpl.render(
                account=archive.account,
                gallery=gallery,
                photo_items=photo_items,
                base_url="../",
                has_map=has_map,
                hide_unsafe=hide_unsafe,
                comments=gallery_comments.get(gallery.id, []),
            ),
            encoding="utf-8",
        )


def _render_tags(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *,
    has_map: bool, hide_unsafe: bool = False,
) -> None:
    tag_photos: dict[str, list[object]] = collections.defaultdict(list)
    for photo in archive.photos:
        for t in photo.tags:
            tag_photos[t.tag].append(photo)

    all_tags = sorted(tag_photos.keys())
    slug_map = slugify_tags(all_tags)

    counts = {t: len(ps) for t, ps in tag_photos.items()}
    max_count = max(counts.values()) if counts else 1
    min_count = min(counts.values()) if counts else 1
    span = max(max_count - min_count, 1)

    def _bucket(count: int) -> int:
        return int(1 + 4 * (count - min_count) / span)

    tag_entries = [
        {"tag": t, "slug": slug_map[t], "count": counts[t], "bucket": _bucket(counts[t])}
        for t in sorted(all_tags, key=str.casefold)
    ]

    tags_dir = output_dir / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)

    index_tmpl = env.get_template("tags_index.html.j2")
    (tags_dir / "index.html").write_text(
        index_tmpl.render(
            account=archive.account,
            tag_entries=tag_entries,
            base_url="../",
            has_map=has_map,
            hide_unsafe=hide_unsafe,
        ),
        encoding="utf-8",
    )

    detail_tmpl = env.get_template("tag.html.j2")
    for tag, slug in slug_map.items():
        (tags_dir / f"{slug}.html").write_text(
            detail_tmpl.render(
                account=archive.account,
                tag=tag,
                photos=tag_photos[tag],
                base_url="../",
                has_map=has_map,
                hide_unsafe=hide_unsafe,
            ),
            encoding="utf-8",
        )


def _render_map(archive: OfflickrArchive, output_dir: Path, env: Environment) -> None:
    geo_photos = [
        {"id": p.id, "title": p.title, "lat": p.geo.lat, "lng": p.geo.lng}
        for p in archive.photos
        if p.geo is not None
    ]
    template = env.get_template("map.html.j2")
    (output_dir / "map.html").write_text(
        template.render(
            account=archive.account,
            geo_photos=geo_photos,
            base_url="",
            has_map=True,
        ),
        encoding="utf-8",
    )


def _render_faves(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *, has_map: bool
) -> None:
    template = env.get_template("faves_index.html.j2")
    faves_dir = output_dir / "faves"
    faves_dir.mkdir(parents=True, exist_ok=True)
    pages = paginate(archive.faves, PHOTOS_PER_PAGE)
    total = len(pages)
    for i, page_faves in enumerate(pages, 1):
        if i == 1:
            out_path = faves_dir / "index.html"
            prev_url = None
        else:
            out_path = faves_dir / f"page-{i}.html"
            prev_url = "index.html" if i == 2 else f"page-{i - 1}.html"
        next_url = f"page-{i + 1}.html" if i < total else None
        pagination = (
            {"current": i, "total": total, "prev_url": prev_url, "next_url": next_url}
            if total > 1
            else None
        )
        out_path.write_text(
            template.render(
                account=archive.account,
                faves=page_faves,
                base_url="../",
                pagination=pagination,
                has_map=has_map,
            ),
            encoding="utf-8",
        )


def _render_groups(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *, has_map: bool
) -> None:
    template = env.get_template("groups_index.html.j2")
    groups_dir = output_dir / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    (groups_dir / "index.html").write_text(
        template.render(
            account=archive.account,
            groups=archive.groups,
            base_url="../",
            has_map=has_map,
        ),
        encoding="utf-8",
    )


def _render_private_views(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *, has_map: bool
) -> None:
    private_dir = output_dir / "private"
    private_dir.mkdir(parents=True, exist_ok=True)

    def _render(template_name: str, path: Path, base_url: str = "../../", **ctx: object) -> None:
        tmpl = env.get_template(f"private/{template_name}")
        path.write_text(
            tmpl.render(account=archive.account, base_url=base_url, has_map=has_map, **ctx),
            encoding="utf-8",
        )

    if archive.contacts:
        _render("contacts.html.j2", private_dir / "contacts.html", base_url="../",
                contacts=archive.contacts)
    if archive.followers:
        _render("followers.html.j2", private_dir / "followers.html", base_url="../",
                followers=archive.followers)
    if archive.flickrmail:
        flickrmail_dir = private_dir / "flickrmail"
        flickrmail_dir.mkdir(exist_ok=True)
        _render("flickrmail_sent.html.j2", flickrmail_dir / "sent.html",
                messages=archive.flickrmail.sent)
        _render("flickrmail_received.html.j2", flickrmail_dir / "received.html",
                messages=archive.flickrmail.received)
    if archive.my_comments:
        _render("my_comments.html.j2", private_dir / "my-comments.html", base_url="../",
                comments=archive.my_comments)
    if archive.my_group_posts:
        _render("my_group_posts.html.j2", private_dir / "my-group-posts.html", base_url="../",
                posts=archive.my_group_posts)


def _render_testimonials(
    archive: OfflickrArchive, output_dir: Path, env: Environment, *, has_map: bool
) -> None:
    template = env.get_template("testimonials.html.j2")
    (output_dir / "testimonials.html").write_text(
        template.render(
            account=archive.account,
            testimonials=archive.testimonials,
            base_url="",
            has_map=has_map,
        ),
        encoding="utf-8",
    )
