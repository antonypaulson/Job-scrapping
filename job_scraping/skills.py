"""Extract and group skills the same way the 2018 notebooks did.

The original collector searched job-ad text for a fixed vocabulary, then
collapsed degree synonyms (BA/BS vs Bachelor, MS vs Master). That idea is
kept here so the Texas 2018 CSV and new public-API pulls share one analyzer.
"""

from __future__ import annotations

import ast
import re
from typing import Iterable, Optional

import pandas as pd

# Phrase matches use substring search on lowercased text (original behavior).
PHRASE_SKILLS = [
    "revpro",
    "sql",
    "tableau",
    "saas",
    "python",
    "stata",
    "excel",
    "word",
    "power point",
    "powerpoint",
    "microsoft office",
    "crm",
    "oracle",
    "enterprise",
    "finance",
    "cloud",
    "big data",
    "accounting",
    "forecasting",
    "computer science",
    "statistics",
    "economics",
    "modeling",
    "modelling",
    "marketing",
    "sales",
    "hospitality",
    "healthcare",
    "business",
    "food",
    "logistics",
    "logistic",
    "operation",
    "entertainment",
    "human resources",
    "mba",
    "bachelor",
    "masters",
    "master",
    "phd",
    "degree",
    "pandas",
    "spark",
    "aws",
    "azure",
    "gcp",
    "snowflake",
    "dbt",
    "airflow",
    "power bi",
    "looker",
    "tensorflow",
    "pytorch",
    "machine learning",
    "deep learning",
    "nlp",
    "docker",
    "kubernetes",
]

# Short tokens need word boundaries so "R" does not match "senior".
BOUNDED_SKILLS = [
    "sas",
    "r",
    "poc",
    "sap",
    "bs",
    "ba",
    "ms",
    "ma",
    "ba/bs",
    "bs/ba",
    "java",
    "ml",
    "ai",
    "etl",
    "nlp",
]

SKILL_ALIASES = {
    "power point": "powerpoint",
    "powerpoint": "powerpoint",
    "microsoft office": "microsoft office",
    "ms office": "microsoft office",
    "logistic": "logistics",
    "logistics": "logistics",
    "model": "modeling",
    "modeling": "modeling",
    "modelling": "modeling",
    "masters": "master",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "power bi": "power bi",
    "powerbi": "power bi",
}

# Columns the 2018 visualization notebook expected (lowercase except education).
ORIGINAL_SKILL_COLUMNS = [
    "revpro",
    "sql",
    "tableau",
    "saas",
    "sas",
    "r",
    "poc",
    "sap",
    "python",
    "stata",
    "excel",
    "java",
    "word",
    "power point",
    "microsoft office",
    "crm",
    "oracle",
    "enterprise",
]
ORIGINAL_INDUSTRY_COLUMNS = [
    "finance",
    "accounting",
    "forecasting",
    "marketing",
    "sales",
    "hospitality",
    "entertainment",
    "healthcare",
    "food",
    "logistic",
    "human resources",
]
ORIGINAL_DEGREE_COLUMNS = ["computer science", "statistics", "economics"]
EXPERIENCE_COLUMNS = [str(year) for year in range(1, 11)]

_YEARS_RE = re.compile(
    r"(?:at least\s+)?"
    r"(?P<low>\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"(?:\s*[-–to]{1,3}\s*(?P<high>\d+))?"
    r"\s*\+?\s*years?",
    re.IGNORECASE,
)
_WORD_YEARS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def canonicalize(skill: str) -> str:
    key = skill.strip().lower()
    return SKILL_ALIASES.get(key, key)


def extract_keywords(text: str) -> list[str]:
    """Return matched skills plus a years token when the ad mentions experience."""
    if not text:
        return []
    lowered = text.lower()
    found: list[str] = []
    seen: set[str] = set()

    for phrase in PHRASE_SKILLS:
        if phrase in lowered:
            token = canonicalize(phrase)
            if token not in seen:
                seen.add(token)
                found.append(token)

    # Keep the original extra substring match for "model" (too short for the phrase list).
    if re.search(r"\bmodel(?:ing|ling)?\b", lowered) and "modeling" not in seen:
        seen.add("modeling")
        found.append("modeling")

    for token in BOUNDED_SKILLS:
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            canon = canonicalize(token)
            if canon not in seen:
                seen.add(canon)
                found.append(canon)

    years = extract_experience_years(lowered)
    if years is not None:
        found.append(str(years))
    return found


def extract_experience_years(text: str) -> Optional[int]:
    match = _YEARS_RE.search(text or "")
    if not match:
        return None
    raw = (match.group("high") or match.group("low")).lower()
    if raw in _WORD_YEARS:
        value = _WORD_YEARS[raw]
    else:
        value = int(raw)
    if 1 <= value <= 10:
        return value
    return None


def parse_skill_list(value: object) -> list[str]:
    """Parse a skill list stored as a Python list, CSV cell, or pipe-delimited string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [canonicalize(str(item)) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [canonicalize(str(item)) for item in parsed if str(item).strip()]
        except (SyntaxError, ValueError):
            inner = text.strip("[]")
            return [canonicalize(part) for part in inner.split(",") if part.strip()]
    if "|" in text:
        return [canonicalize(part) for part in text.split("|") if part.strip()]
    return [canonicalize(part) for part in text.split(",") if part.strip()]


def flags_from_skills(skills: Iterable[str]) -> dict[str, int]:
    tokens = [canonicalize(str(item)) for item in skills if str(item).strip()]
    years_tokens = [token for token in tokens if token in EXPERIENCE_COLUMNS]
    skill_tokens = {token for token in tokens if token not in EXPERIENCE_COLUMNS}

    flags: dict[str, int] = {}
    for column in (
        ORIGINAL_SKILL_COLUMNS
        + ORIGINAL_INDUSTRY_COLUMNS
        + ORIGINAL_DEGREE_COLUMNS
        + ["cloud", "big data", "python", "saas"]
    ):
        flags[column] = int(canonicalize(column) in skill_tokens or column in skill_tokens)

    # Original notebook used the "power point" column name.
    if "powerpoint" in skill_tokens:
        flags["power point"] = 1
        flags["powerpoint"] = 1

    bachelor_raw = skill_tokens.intersection({"ba", "bs", "ba/bs", "bs/ba", "bachelor"})
    master_raw = skill_tokens.intersection({"ma", "ms", "master", "masters", "mba"})
    bachelor = int(bool(bachelor_raw))
    master = int(bool(master_raw))
    master_pref = int(bachelor == 1 and master == 1)
    if master_pref:
        bachelor = 0
        master = 0

    flags["Bachelor"] = bachelor
    flags["Master"] = master
    flags["Master_pref"] = master_pref
    flags["degree"] = int("degree" in skill_tokens and bachelor == 0 and master == 0 and master_pref == 0)
    flags["phd"] = int("phd" in skill_tokens)

    for year in EXPERIENCE_COLUMNS:
        flags[year] = 0
    if years_tokens:
        flags[years_tokens[-1]] = 1
    return flags


def analyze_jobs(frame: pd.DataFrame) -> pd.DataFrame:
    """Add skill / education / experience flag columns to a jobs table."""
    work = frame.copy()
    if "locations" not in work.columns and "location" in work.columns:
        work["locations"] = work["location"]
    if "company" in work.columns:
        work["company"] = work["company"].fillna("Unknown").replace("", "Unknown")

    skill_lists: list[list[str]] = []
    for _, row in work.iterrows():
        existing = []
        for column in ("skills", "description", "tags"):
            if column in work.columns:
                existing.extend(parse_skill_list(row.get(column)))
        blob = " ".join(
            str(row.get(column) or "")
            for column in ("title", "description_text", "description")
            if column in work.columns
        )
        extracted = extract_keywords(blob)
        merged: list[str] = []
        seen: set[str] = set()
        for token in existing + extracted:
            token = str(token).strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            merged.append(canonicalize(token) if not token.isdigit() else token)
        skill_lists.append(merged)

    work["skills"] = ["|".join(items) for items in skill_lists]
    flag_rows = [flags_from_skills(items) for items in skill_lists]
    flags = pd.DataFrame(flag_rows, index=work.index)
    for column in flags.columns:
        work[column] = flags[column]
    return work.reset_index(drop=True)


def category_totals(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Sums used by the bar / pie charts."""

    def _sum(columns: list[str]) -> dict[str, int]:
        totals = {}
        for column in columns:
            if column in frame.columns:
                totals[column] = int(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())
            else:
                totals[column] = 0
        return totals

    return {
        "skills": _sum(ORIGINAL_SKILL_COLUMNS),
        "industries": _sum(ORIGINAL_INDUSTRY_COLUMNS),
        "education": _sum(["Bachelor", "Master", "Master_pref"]),
        "degrees": _sum(ORIGINAL_DEGREE_COLUMNS),
        "experience": _sum(EXPERIENCE_COLUMNS),
    }
