"""Pagination helpers."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def paginate(items: list[T], page_size: int) -> list[list[T]]:
    if not items:
        return [[]]
    return [items[i : i + page_size] for i in range(0, len(items), page_size)]
