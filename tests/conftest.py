"""Shared pytest fixtures and helpers for offlickr tests."""

from __future__ import annotations

from pathlib import Path

MINI_EXPORT: Path = Path(__file__).parent / "fixtures" / "mini-export"
