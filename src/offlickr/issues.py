"""Accumulate non-fatal pipeline issues for end-of-stage reporting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Issue:
    category: str
    item_id: str
    reason: str


class IssueCollector:
    def __init__(self) -> None:
        self._issues: list[Issue] = []

    def add(self, category: str, item_id: str, reason: str) -> None:
        self._issues.append(Issue(category, item_id, reason))

    def has_issues(self) -> bool:
        return bool(self._issues)

    def by_category(self) -> dict[str, list[Issue]]:
        result: dict[str, list[Issue]] = {}
        for issue in self._issues:
            result.setdefault(issue.category, []).append(issue)
        return result
