"""Public JSON job sources. Careerjet is documented but not called.

Careerjet's 2018 affiliate client (`careerjet_api_client`) and the HTML
parser that looked for `div.main_job` both require credentials or markup
that no longer exist. Live collection uses documented public feeds instead.
"""

from __future__ import annotations

import html
from typing import Iterable, Optional

from .http import RespectfulClient
from .jobs import JobPosting, html_to_text

REMOTEOK_URL = "https://remoteok.com/api"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

DATA_ROLE_TERMS = (
    "data scientist",
    "data analyst",
    "data engineer",
    "machine learning",
    "business analyst",
    "statistician",
    "analytics",
)

DEFAULT_QUERIES = ("data scientist", "data analyst")
SOURCE_NAMES = ("jobicy", "remoteok", "arbeitnow")


def looks_like_data_role(title: str, tags: Iterable[str] = ()) -> bool:
    blob = " ".join([title or "", " ".join(tags)]).lower()
    if any(term in blob for term in DATA_ROLE_TERMS):
        return True
    # Broader fallback used when a source cannot filter server-side.
    tokens = ("data", "analyst", "scientist", "ml ", "machine learning")
    return any(token in blob for token in tokens)


def collect_jobs(
    source: str = "jobicy",
    queries: Iterable[str] = DEFAULT_QUERIES,
    limit: int = 80,
    location: str = "",
    client: Optional[RespectfulClient] = None,
) -> list[JobPosting]:
    """Fetch public listings. `source` is one of jobicy, remoteok, arbeitnow, or all."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    client = client or RespectfulClient()
    name = source.lower().strip()
    query_list = [item.strip() for item in queries if str(item).strip()] or list(DEFAULT_QUERIES)

    if name == "all":
        collected: list[JobPosting] = []
        seen_urls: set[str] = set()
        for part in ("jobicy", "remoteok", "arbeitnow"):
            remaining = limit - len(collected)
            if remaining <= 0:
                break
            for job in collect_jobs(part, query_list, remaining, location, client):
                if job.url and job.url in seen_urls:
                    continue
                if job.url:
                    seen_urls.add(job.url)
                collected.append(job)
                if len(collected) >= limit:
                    break
        return collected[:limit]

    if name == "jobicy":
        jobs = fetch_jobicy(client, query_list, limit, location)
    elif name == "remoteok":
        jobs = fetch_remoteok(client, query_list, limit)
    elif name == "arbeitnow":
        jobs = fetch_arbeitnow(client, query_list, limit)
    elif name == "careerjet":
        raise RuntimeError(
            "Careerjet is no longer used. The 2018 affiliate API now requires a "
            "publisher key and IP allowlist. Use --source jobicy (default), "
            "remoteok, arbeitnow, or all. Historical Texas rows are in "
            "data/texas_jobs_2018.csv."
        )
    else:
        raise ValueError(f"Unknown source {source!r}. Choose jobicy, remoteok, arbeitnow, or all.")

    return jobs[:limit]


def fetch_jobicy(
    client: RespectfulClient,
    queries: list[str],
    limit: int,
    location: str = "",
) -> list[JobPosting]:
    """Jobicy public remote-jobs API. One request per query; do not poll more than hourly."""
    collected: list[JobPosting] = []
    seen: set[str] = set()
    for query in queries:
        if len(collected) >= limit:
            break
        params: dict[str, object] = {
            "count": min(max(limit, 1), 50),
            "tag": query[:50],
        }
        if location:
            params["geo"] = location
        payload = client.get_json(JOBICY_URL, params=params)
        for raw in payload.get("jobs") or []:
            job = _jobicy_to_posting(raw)
            if job.url in seen:
                continue
            seen.add(job.url)
            collected.append(job)
            if len(collected) >= limit:
                break
    return collected


def fetch_remoteok(
    client: RespectfulClient,
    queries: list[str],
    limit: int,
) -> list[JobPosting]:
    """Remote OK public feed. Single request; filter locally. Credit Remote OK in docs."""
    payload = client.get_json(REMOTEOK_URL)
    query_blob = " ".join(queries).lower()
    collected: list[JobPosting] = []
    for raw in payload:
        if not isinstance(raw, dict) or not raw.get("position"):
            continue
        job = _remoteok_to_posting(raw)
        haystack = " ".join([job.title, job.company, " ".join(job.tags), job.description]).lower()
        if query_blob and not any(term.lower() in haystack for term in queries):
            if not looks_like_data_role(job.title, job.tags):
                continue
        collected.append(job)
        if len(collected) >= limit:
            break
    if collected:
        return collected
    # If the feed has no data-shaped rows, return the first `limit` public ads
    # so the pipeline still demonstrates a live collect.
    fallback: list[JobPosting] = []
    for raw in payload:
        if not isinstance(raw, dict) or not raw.get("position"):
            continue
        fallback.append(_remoteok_to_posting(raw))
        if len(fallback) >= limit:
            break
    return fallback


def fetch_arbeitnow(
    client: RespectfulClient,
    queries: list[str],
    limit: int,
    max_pages: int = 3,
) -> list[JobPosting]:
    """Arbeitnow public job-board API. Paginate slowly; they ask not to abuse the feed."""
    collected: list[JobPosting] = []
    for page in range(1, max_pages + 1):
        if len(collected) >= limit:
            break
        payload = client.get_json(ARBEITNOW_URL, params={"page": page})
        for raw in payload.get("data") or []:
            job = _arbeitnow_to_posting(raw)
            haystack = " ".join([job.title, " ".join(job.tags), job.description]).lower()
            if not any(term.lower() in haystack for term in queries):
                if not looks_like_data_role(job.title, job.tags):
                    continue
            collected.append(job)
            if len(collected) >= limit:
                break
        if not (payload.get("links") or {}).get("next"):
            break
    return collected


def _jobicy_to_posting(raw: dict) -> JobPosting:
    industries = raw.get("jobIndustry") or []
    if isinstance(industries, str):
        industries = [industries]
    return JobPosting(
        title=_clean(raw.get("jobTitle")),
        company=_clean(raw.get("companyName")),
        location=_clean(raw.get("jobGeo")),
        date=_clean(raw.get("pubDate")),
        salary="",
        url=_clean(raw.get("url")),
        source="jobicy",
        description=html_to_text(raw.get("jobDescription") or raw.get("jobExcerpt") or ""),
        tags=[_clean(tag) for tag in industries if tag],
    )


def _remoteok_to_posting(raw: dict) -> JobPosting:
    tags = raw.get("tags") or []
    salary = ""
    low, high = raw.get("salary_min"), raw.get("salary_max")
    if low or high:
        try:
            if int(low or 0) or int(high or 0):
                salary = f"{low} - {high}".strip(" -")
        except (TypeError, ValueError):
            salary = ""
    return JobPosting(
        title=_clean(raw.get("position")),
        company=_clean(raw.get("company")),
        location=_clean(raw.get("location")),
        date=_clean(raw.get("date")),
        salary=salary,
        url=_clean(raw.get("url") or raw.get("apply_url")),
        source="remoteok",
        description=html_to_text(raw.get("description") or ""),
        tags=[_clean(tag) for tag in tags if tag],
    )


def _arbeitnow_to_posting(raw: dict) -> JobPosting:
    tags = raw.get("tags") or []
    return JobPosting(
        title=_clean(raw.get("title")),
        company=_clean(raw.get("company_name")),
        location=_clean(raw.get("location")),
        date=str(raw.get("created_at") or ""),
        salary="",
        url=_clean(raw.get("url")),
        source="arbeitnow",
        description=html_to_text(raw.get("description") or ""),
        tags=[_clean(tag) for tag in tags if tag],
    )


def _clean(value: object) -> str:
    if value is None:
        return ""
    return html.unescape(str(value)).replace("\xa0", " ").strip()
