"""Download Flickr buddy-icon avatars for user NSIDs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from offlickr.fetch.client import FlickrClient
from offlickr.issues import IssueCollector


def avatar_url(person: dict[str, Any]) -> str | None:
    iconserver = int(person.get("iconserver", 0))
    iconfarm = int(person.get("iconfarm", 0))
    nsid = person.get("nsid", "")
    if iconserver > 0:
        return f"https://farm{iconfarm}.staticflickr.com/{iconserver}/buddyicons/{nsid}.jpg"
    return None


def fetch_user_avatars(
    nsids: list[str],
    client: FlickrClient,
    output_dir: Path,
    *,
    on_progress: Callable[[], None] | None = None,
    collector: IssueCollector | None = None,
    known_screen_names: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return (avatar_map, screen_name_map) keyed by nsid.

    If a cached avatar exists but the nsid is not in *known_screen_names*, the
    API is still called to retrieve the username (but the file is not downloaded
    again).  Pass known_screen_names=None to use the old skip-all behaviour.
    """
    avatars_dir = output_dir / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    screen_names: dict[str, str] = {}
    for nsid in nsids:
        dest = avatars_dir / f"{nsid}.jpg"
        rel = f"avatars/{nsid}.jpg"
        file_cached = dest.exists()
        name_known = known_screen_names is not None and nsid in known_screen_names
        if file_cached and name_known:
            result[nsid] = rel
            if on_progress:
                on_progress()
            continue
        try:
            person = client.get_person_info(nsid)
            username_data = person.get("username", {})
            sn = (
                username_data.get("_content", "")
                if isinstance(username_data, dict)
                else str(username_data)
            )
            if sn:
                screen_names[nsid] = sn
            if not file_cached:
                url = avatar_url(person)
                if url:
                    tmp = dest.with_suffix(".tmp")
                    tmp.write_bytes(client.download(url))
                    tmp.rename(dest)
            if dest.exists():
                result[nsid] = rel
        except Exception as exc:
            dest.with_suffix(".tmp").unlink(missing_ok=True)
            if collector:
                collector.add("fetch.avatar", nsid, str(exc))
        if on_progress:
            on_progress()
    return result, screen_names
