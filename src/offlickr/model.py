"""Pydantic models for the offlickr archive. See spec §4."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountStats(BaseModel):
    model_config = ConfigDict(extra="allow")
    view_counts: dict[str, int] = Field(default_factory=dict)


class Account(BaseModel):
    model_config = ConfigDict(extra="allow")

    nsid: str
    path_alias: str | None = None
    screen_name: str
    real_name: str | None = None
    profile_url: str
    join_date: datetime
    pro_user: bool
    description_html: str = ""
    website_url: str | None = None
    showcase_photo_ids: list[str] = Field(default_factory=list)
    stats: AccountStats = Field(default_factory=AccountStats)
    location: dict[str, str] | None = None
    social: dict[str, str] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Account:
        join_date = datetime.fromisoformat(data["join_date"])
        pro_user = str(data.get("pro_user", "no")).lower() == "yes"
        stats_raw = data.get("stats", {})
        stats = AccountStats(view_counts=stats_raw.get("view_counts", {}))

        city = str(data.get("city", "")).strip()
        country = str(data.get("country", "")).strip()
        hometown = str(data.get("hometown", "")).strip()
        location = (
            {"country": country, "city": city, "hometown": hometown}
            if (city or country or hometown)
            else None
        )

        social_raw = data.get("social") or {}
        social_filtered = {
            k: str(v).removeprefix("@") if k in {"instagram", "twitter"} else str(v)
            for k, v in social_raw.items()
        }
        social = social_filtered if any(social_filtered.values()) else None

        return cls(
            nsid=data["nsid"],
            path_alias=data.get("path_alias") or None,
            screen_name=data["screen_name"],
            real_name=data.get("real_name") or None,
            profile_url=data["profile_url"],
            join_date=join_date,
            pro_user=pro_user,
            description_html=data.get("description", "") or "",
            website_url=data.get("website_url") or None,
            showcase_photo_ids=list(data.get("showcase", {}).get("photos", [])),
            stats=stats,
            location=location,
            social=social,
        )


class Geo(BaseModel):
    lat: float
    lng: float
    accuracy: int | None = None
    context: int | None = None


class Exif(BaseModel):
    camera_make: str | None = None
    camera_model: str | None = None
    lens_model: str | None = None
    focal_length_mm: float | None = None
    aperture: float | None = None
    shutter_speed: str | None = None
    iso: int | None = None
    date_taken: datetime | None = None


class Tag(BaseModel):
    tag: str
    user_profile_url: str
    date_create: datetime


class Testimonial(BaseModel):
    author_or_subject_screen_name: str
    profile_url: str
    body_html: str
    created: datetime


class Note(BaseModel):
    id: str | None = None
    x: int
    y: int
    w: int
    h: int
    body: str
    author_nsid: str


class PersonRef(BaseModel):
    nsid: str
    username: str
    profile_url: str


class AlbumBackRef(BaseModel):
    id: str
    title: str
    url_flickr: str


class Comment(BaseModel):
    id: str
    date: datetime
    user_nsid: str
    body_html: str
    url: str


class Media(BaseModel):
    filename: str
    ext: str
    kind: str  # "image" or "video"
    width: int | None = None
    height: int | None = None
    bytes: int | None = None


class GroupRef(BaseModel):
    id: str
    name: str
    url_flickr: str
    user_role: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> GroupRef:
        return cls(
            id=str(data["id"]),
            name=data.get("name", ""),
            url_flickr=data.get("url", ""),
            user_role=data.get("user_role"),
        )


class Photo(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    description_html: str = ""
    date_taken: datetime | None = None
    date_imported: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    license: str = ""
    privacy: str = "public"
    safety: str = "safe"
    rotation: int = 0
    geo: Geo | None = None
    photopage_url: str
    original_flickr_url: str
    tags: list[Tag] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    slug: str | None = None
    media: Media | None = None
    exif: Exif | None = None
    notes: list[Note] = Field(default_factory=list)
    people: list[PersonRef] = Field(default_factory=list)
    album_refs: list[AlbumBackRef] = Field(default_factory=list)
    groups: list[GroupRef] = Field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Photo:
        def _parse_date(s: str | None) -> datetime | None:
            if not s or s == "0000-00-00 00:00:00":
                return None
            return datetime.fromisoformat(s)

        geo_list = data.get("geo") or []
        geo = None
        if isinstance(geo_list, list) and geo_list:
            g = geo_list[0]
            geo = Geo(
                lat=int(g["latitude"]) / 1_000_000,
                lng=int(g["longitude"]) / 1_000_000,
                accuracy=g.get("accuracy"),
                context=g.get("context"),
            )

        counts = {
            "views": int(data.get("count_views", 0)),
            "faves": int(data.get("count_faves", 0)),
            "comments": int(data.get("count_comments", 0)),
            "tags": int(data.get("count_tags", 0)),
            "notes": int(data.get("count_notes", 0)),
        }

        tags = [
            Tag(
                tag=t["tag"],
                user_profile_url=t["user"],
                date_create=datetime.fromisoformat(t["date_create"]),
            )
            for t in data.get("tags", [])
        ]

        comments = [
            Comment(
                id=c["id"],
                date=datetime.fromisoformat(c["date"]),
                user_nsid=c["user"],
                body_html=c.get("comment", ""),
                url=c["url"],
            )
            for c in data.get("comments", [])
        ]

        notes = [
            Note(
                id=str(n["id"]) if "id" in n else None,
                x=int(n["x"]),
                y=int(n["y"]),
                w=int(n.get("w") or n.get("width", 0)),
                h=int(n.get("h") or n.get("height", 0)),
                body=n.get("note") or n.get("text", ""),
                author_nsid=n.get("author") or n.get("user", ""),
            )
            for n in data.get("notes", [])
        ]

        people = [
            PersonRef(
                nsid=per["nsid"],
                username=per.get("username", per["nsid"]),
                profile_url=per.get("userurl", ""),
            )
            for per in data.get("people", [])
            if "nsid" in per
        ]

        album_refs = [
            AlbumBackRef(
                id=str(a["id"]),
                title=a.get("title", ""),
                url_flickr=a.get("url", ""),
            )
            for a in data.get("albums", [])
        ]

        photo_groups = [GroupRef.from_json(g) for g in data.get("groups", [])]

        return cls(
            id=str(data["id"]),
            title=data.get("name", ""),
            description_html=data.get("description", "") or "",
            date_taken=_parse_date(data.get("date_taken")),
            date_imported=datetime.fromisoformat(data["date_imported"]),
            counts=counts,
            license=data.get("license", ""),
            privacy=data.get("privacy", "public"),
            safety=data.get("safety", "safe"),
            rotation=int(data.get("rotation", 0)),
            geo=geo,
            photopage_url=data["photopage"],
            original_flickr_url=data["original"],
            tags=tags,
            comments=comments,
            notes=notes,
            people=people,
            album_refs=album_refs,
            groups=photo_groups,
        )


def _cover_id_from_url(url: str) -> str | None:
    if not url:
        return None
    parts = url.rstrip("/").rsplit("/", 1)
    tail = parts[-1] if parts else ""
    return tail or None


class Album(BaseModel):
    id: str
    title: str
    description_html: str = ""
    photo_count: int
    view_count: int
    created: datetime
    last_updated: datetime
    cover_photo_id: str | None = None
    photo_ids: list[str] = Field(default_factory=list)
    url_flickr: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Album:
        return cls(
            id=str(data["id"]),
            title=data.get("title", ""),
            description_html=data.get("description", "") or "",
            photo_count=int(data.get("photo_count", 0)),
            view_count=int(data.get("view_count", 0)),
            created=datetime.fromtimestamp(int(data["created"])),
            last_updated=datetime.fromtimestamp(int(data["last_updated"])),
            cover_photo_id=_cover_id_from_url(data.get("cover_photo", "")),
            photo_ids=[str(x) for x in data.get("photos", [])],
            url_flickr=data["url"],
        )


class Gallery(BaseModel):
    id: str
    title: str
    description_html: str = ""
    photo_count: int
    view_count: int
    photo_ids: list[str] = Field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Gallery:
        return cls(
            id=str(data["id"]),
            title=data.get("title", ""),
            description_html=data.get("description", "") or "",
            photo_count=int(data.get("photo_count", 0)),
            view_count=int(data.get("view_count", 0)),
            photo_ids=[str(x) for x in data.get("photos", [])],
        )


class User(BaseModel):
    nsid: str
    screen_name: str | None = None
    profile_url: str | None = None
    avatar_path: str | None = None


class Fave(BaseModel):
    photo_id: str
    photo_url_short: str
    photo_url_flickr: str | None = None
    owner_nsid: str | None = None
    thumbnail_path: str | None = None
    thumbnail_width: int | None = None
    thumbnail_height: int | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Fave:
        return cls(
            photo_id=str(data["photo_id"]),
            photo_url_short=data.get("photo_url", ""),
        )


class Testimonials(BaseModel):
    given: list[Testimonial] = Field(default_factory=list)
    received: list[Testimonial] = Field(default_factory=list)


class OutgoingComment(BaseModel):
    comment_id: str
    photo_id: str
    photo_url: str
    body_html: str
    date: datetime


class FlickrMail(BaseModel):
    id: str
    from_nsid: str
    to_nsid: str
    to_user_name: str | None = None
    subject: str
    body_html: str
    date_sent: datetime
    date_deleted: datetime | None = None
    have_read: bool | None = None
    have_replied: bool | None = None


class FlickrMailbox(BaseModel):
    sent: list[FlickrMail] = Field(default_factory=list)
    received: list[FlickrMail] = Field(default_factory=list)


class GroupPost(BaseModel):
    group_id: str
    group_name: str
    topic_id: str
    topic_title: str
    reply_id: str
    body_html: str
    date: datetime


class Generator(BaseModel):
    name: str
    version: str
    built_at: datetime


class ExportMeta(BaseModel):
    source_dir: str
    detected_format_version: str


class OfflickrArchive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generator: Generator
    export: ExportMeta
    account: Account
    photos: list[Photo] = Field(default_factory=list)
    albums: list[Album] = Field(default_factory=list)
    galleries: list[Gallery] = Field(default_factory=list)
    groups: list[GroupRef] = Field(default_factory=list)
    faves: list[Fave] = Field(default_factory=list)
    testimonials: Testimonials = Field(default_factory=Testimonials)
    users: dict[str, User] = Field(default_factory=dict)

    # private-view fields, populated only when --include-private is set
    contacts: dict[str, User] | None = None
    followers: dict[str, User] | None = None
    flickrmail: FlickrMailbox | None = None
    my_comments: list[OutgoingComment] | None = None
    my_group_posts: list[GroupPost] | None = None
    set_comments: dict[str, list[Comment]] | None = None
    gallery_comments: dict[str, list[Comment]] | None = None
