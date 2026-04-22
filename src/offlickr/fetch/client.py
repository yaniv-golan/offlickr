"""Thin sync httpx wrapper around the Flickr REST API."""

from __future__ import annotations

from typing import Any, cast

import httpx

_FLICKR_REST = "https://api.flickr.com/services/rest/"


class FlickrClient:
    def __init__(self, api_key: str, *, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._http = httpx.Client(timeout=timeout)

    def _get(self, method: str, **params: str) -> dict[str, Any]:
        resp = self._http.get(
            _FLICKR_REST,
            params={
                "method": method,
                "api_key": self._api_key,
                "format": "json",
                "nojsoncallback": "1",
                **params,
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        if data.get("stat") != "ok":
            raise ValueError(data.get("message", "Flickr API error"))
        return data

    def get_photo_sizes(self, photo_id: str) -> list[dict[str, Any]]:
        result = self._get("flickr.photos.getSizes", photo_id=photo_id)
        return cast("list[dict[str, Any]]", result["sizes"]["size"])

    def get_person_info(self, nsid: str) -> dict[str, Any]:
        result = self._get("flickr.people.getInfo", user_id=nsid)
        return cast("dict[str, Any]", result["person"])

    def download(self, url: str) -> bytes:
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.content

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> FlickrClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
