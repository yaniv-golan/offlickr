"""Ingest orchestrator: joins parsers into a fully populated OfflickrArchive.

Emits ``<output_dir>/data/model.json`` and ``<output_dir>/data/model.schema.json``.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from offlickr import __version__
from offlickr.ingest.account import load_account
from offlickr.ingest.albums import load_albums
from offlickr.ingest.apps_comments import load_apps_comments
from offlickr.ingest.comments import load_my_comments
from offlickr.ingest.contacts import load_contacts
from offlickr.ingest.faves import load_faves
from offlickr.ingest.flickrmail import load_flickrmail
from offlickr.ingest.followers import load_followers
from offlickr.ingest.galleries import load_galleries
from offlickr.ingest.gallery_comments import load_gallery_comments
from offlickr.ingest.group_discussions import load_group_posts
from offlickr.ingest.groups import load_groups
from offlickr.ingest.photos import load_photos
from offlickr.ingest.set_comments import load_set_comments
from offlickr.ingest.testimonials import load_testimonials
from offlickr.issues import IssueCollector
from offlickr.model import ExportMeta, Generator, OfflickrArchive, User


def _write_text_atomic(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _strip_private_from_schema(schema: dict) -> dict:  # type: ignore[type-arg]
    private_fields = {
        "contacts",
        "followers",
        "flickrmail",
        "my_comments",
        "my_group_posts",
        "set_comments",
        "gallery_comments",
    }
    props = schema.get("properties", {})
    for field in private_fields:
        props.pop(field, None)
    return schema


def run_ingest(
    *,
    source: Path,
    output_dir: Path,
    include_private: bool,
    include_private_photos: bool,
    collector: IssueCollector | None = None,
) -> OfflickrArchive:
    account = load_account(source)
    all_photos = load_photos(source, collector=collector)
    if not include_private_photos:
        photos = [p for p in all_photos if p.privacy == "public"]
        private_ids: set[str] = {p.id for p in all_photos if p.privacy != "public"}
    else:
        photos = all_photos
        private_ids = set()

    raw_albums = load_albums(source)
    raw_galleries = load_galleries(source)

    if private_ids:
        albums = [
            a.model_copy(
                update={
                    "photo_ids": [pid for pid in a.photo_ids if pid not in private_ids],
                    "cover_photo_id": (
                        a.cover_photo_id if a.cover_photo_id not in private_ids else None
                    ),
                }
            )
            for a in raw_albums
        ]
        galleries = [
            g.model_copy(
                update={
                    "photo_ids": [pid for pid in g.photo_ids if pid not in private_ids],
                }
            )
            for g in raw_galleries
        ]
    else:
        albums = raw_albums
        galleries = raw_galleries

    archive = OfflickrArchive(
        generator=Generator(
            name="offlickr",
            version=__version__,
            built_at=datetime.now(),
        ),
        export=ExportMeta(
            source_dir=str(source),
            detected_format_version="2026-q1",
        ),
        account=account,
        photos=photos,
        albums=albums,
        galleries=galleries,
        groups=load_groups(source),
        faves=load_faves(source),
        testimonials=load_testimonials(source),
    )

    comment_nsids = {c.user_nsid for p in archive.photos for c in p.comments}
    new_users = {nsid: User(nsid=nsid) for nsid in comment_nsids if nsid not in archive.users}
    archive.users.update(new_users)

    if include_private:
        archive.contacts = load_contacts(source)
        archive.followers = load_followers(source)
        archive.my_comments = load_my_comments(source, collector)
        archive.flickrmail = load_flickrmail(source, collector)
        archive.my_group_posts = load_group_posts(source, collector)
        archive.set_comments = load_set_comments(source, collector)
        archive.gallery_comments = load_gallery_comments(source, collector)
        # Merge apps_comments into photo.comments
        apps_comments_map = load_apps_comments(source, collector)
        if apps_comments_map:
            photo_by_id = {p.id: p for p in archive.photos}
            for photo_id, app_comments in apps_comments_map.items():
                if photo_id in photo_by_id:
                    p = photo_by_id[photo_id]
                    photo_by_id[photo_id] = p.model_copy(
                        update={"comments": list(p.comments) + app_comments}
                    )
            archive = archive.model_copy(
                update={"photos": [photo_by_id.get(p.id, p) for p in archive.photos]}
            )

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    _write_text_atomic(
        data_dir / "model.json",
        archive.model_dump_json(indent=2, exclude_none=True),
    )

    schema = OfflickrArchive.model_json_schema()
    if not include_private:
        schema = _strip_private_from_schema(schema)
    _write_text_atomic(
        data_dir / "model.schema.json",
        json.dumps(schema, indent=2, ensure_ascii=False),
    )

    media_index = [
        {"photo_id": p.id, "filename": p.media.filename}
        for p in archive.photos
        if p.media is not None
    ]
    _write_text_atomic(
        data_dir / "media-index.json",
        json.dumps(media_index, ensure_ascii=False),
    )

    return archive
