"""Shared job-posting record used by collectors and the analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

PERSISTED_FIELDS = (
    "title",
    "company",
    "location",
    "date",
    "salary",
    "url",
    "source",
)


@dataclass
class JobPosting:
    title: str
    company: str
    location: str = ""
    date: str = ""
    salary: str = ""
    url: str = ""
    source: str = ""
    description: str = field(default="", repr=False)
    tags: list[str] = field(default_factory=list)

    def to_public_row(self, include_description: bool = False) -> dict[str, Any]:
        """Fields safe to write to the sample CSV (no long scraped text by default)."""
        row = {name: getattr(self, name) for name in PERSISTED_FIELDS}
        row["tags"] = "|".join(self.tags)
        if include_description:
            row["description"] = self.description
        return row


def jobs_to_rows(
    jobs: Iterable[JobPosting],
    include_description: bool = False,
) -> list[dict[str, Any]]:
    return [job.to_public_row(include_description=include_description) for job in jobs]


def html_to_text(html: Optional[str]) -> str:
    """Strip tags from a public job-ad HTML blob."""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return _strip_tags_fallback(html)
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def _strip_tags_fallback(html: str) -> str:
    text = []
    in_tag = False
    for char in html:
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            text.append(" ")
            continue
        if not in_tag:
            text.append(char)
    return " ".join("".join(text).split())
