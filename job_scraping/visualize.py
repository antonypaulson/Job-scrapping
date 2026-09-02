"""Matplotlib charts from the 2018 project, runnable on any analyzed jobs table."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .skills import (
    ORIGINAL_DEGREE_COLUMNS,
    ORIGINAL_INDUSTRY_COLUMNS,
    ORIGINAL_SKILL_COLUMNS,
    category_totals,
)

SKILL_LABELS = [
    "RevPro",
    "SQL",
    "tableau",
    "Saas",
    "SAS",
    "R",
    "POC",
    "SAP",
    "python",
    "Stata",
    "Excel",
    "Java",
    "Word",
    "Power Point",
    "Microsoft Office",
    "CRM",
    "Oracle",
    "Enterprise",
]


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(
            "This table is missing analysis columns: "
            + ", ".join(missing)
            + ". Run job_scraping.skills.analyze_jobs first."
        )


def plot_jobs_by_technology(frame: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    totals = category_totals(frame)["skills"]
    values = [totals[column] for column in ORIGINAL_SKILL_COLUMNS]
    axis = ax or plt.gca()
    ypos = np.arange(len(SKILL_LABELS))
    axis.barh(ypos, values, align="center", alpha=0.7, color="#2a6f97")
    axis.set_yticks(ypos, SKILL_LABELS)
    axis.invert_yaxis()
    axis.set_xlabel("Jobs")
    axis.set_title("Jobs by technology")
    return axis


def plot_jobs_by_sector(frame: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    totals = category_totals(frame)["industries"]
    values = [totals[column] for column in ORIGINAL_INDUSTRY_COLUMNS]
    axis = ax or plt.gca()
    ypos = np.arange(len(ORIGINAL_INDUSTRY_COLUMNS))
    axis.barh(ypos, values, align="center", alpha=0.7, color="#01497c")
    axis.set_yticks(ypos, ORIGINAL_INDUSTRY_COLUMNS)
    axis.invert_yaxis()
    axis.set_xlabel("Jobs")
    axis.set_title("Jobs by sector")
    return axis


def plot_jobs_by_education(frame: pd.DataFrame, axs: Optional[Iterable[plt.Axes]] = None):
    totals = category_totals(frame)
    edu_labels = ["Bachelor", "Master", "Master preferred"]
    edu_values = [totals["education"][key] for key in ("Bachelor", "Master", "Master_pref")]
    deg_values = [totals["degrees"][key] for key in ORIGINAL_DEGREE_COLUMNS]

    if axs is None:
        _, axs = plt.subplots(1, 2, figsize=(12, 4))
    left, right = list(axs)
    if sum(edu_values) == 0:
        left.text(0.5, 0.5, "No education flags", ha="center", va="center")
        left.axis("off")
    else:
        left.pie(
            edu_values,
            explode=(0, 0, 0.08),
            labels=edu_labels,
            autopct=lambda pct: f"{pct:.1f}%" if pct > 0 else "",
            pctdistance=0.7,
        )
    right.bar(ORIGINAL_DEGREE_COLUMNS, deg_values, color="#2c7da0")
    right.set_ylabel("Number of jobs")
    right.tick_params(axis="x", rotation=20)
    left.figure.suptitle("Jobs by education")
    return left, right


def plot_jobs_by_experience(frame: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    totals = category_totals(frame)["experience"]
    values = [totals[str(year)] for year in range(1, 11)]
    labels = ["1yr" if year == 1 else f"{year}yrs" for year in range(1, 11)]
    axis = ax or plt.gca()
    if sum(values) == 0:
        axis.text(0.5, 0.5, "No experience flags", ha="center", va="center")
        axis.axis("off")
        return axis
    explode = tuple(0.08 if year in (3, 5) else 0 for year in range(1, 11))
    axis.pie(
        values,
        explode=explode,
        labels=labels,
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
        pctdistance=0.7,
    )
    axis.set_title("Jobs by years of experience")
    return axis


def plot_location_wordcloud(frame: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    from wordcloud import WordCloud

    series = frame["locations"] if "locations" in frame.columns else frame.get("location")
    if series is None:
        raise ValueError("Need a locations or location column")
    places = (
        series.fillna("")
        .astype(str)
        .str.replace(r",\s*[A-Z]{2}$", "", regex=True)
        .str.strip()
    )
    places = [place for place in places if place and place.lower() not in {"nan", "none", "remote"}]
    axis = ax or plt.gca()
    if not places:
        axis.text(0.5, 0.5, "No locations to plot", ha="center", va="center")
        axis.axis("off")
        return axis
    # Frequencies keep multi-word cities ("San Antonio") together.
    from collections import Counter

    cloud = WordCloud(width=900, height=500, background_color="white", max_words=80)
    image = cloud.generate_from_frequencies(Counter(places))
    axis.imshow(image, interpolation="bilinear")
    axis.axis("off")
    axis.set_title("Popular job locations")
    return axis


def save_figures(frame: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    """Write the original chart set to PNG files. Returns the paths written."""
    _require_columns(frame, ORIGINAL_SKILL_COLUMNS[:3])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_jobs_by_technology(frame, ax)
    fig.tight_layout()
    path = out / "jobs_by_technology.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_jobs_by_sector(frame, ax)
    fig.tight_layout()
    path = out / "jobs_by_sector.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    written.append(path)

    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    plot_jobs_by_education(frame, axs)
    fig.tight_layout()
    path = out / "jobs_by_education.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(7, 6))
    plot_jobs_by_experience(frame, ax)
    fig.tight_layout()
    path = out / "jobs_by_experience.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(10, 6))
    try:
        plot_location_wordcloud(frame, ax)
    except Exception:
        ax.text(0.5, 0.5, "Word cloud unavailable", ha="center", va="center")
        ax.axis("off")
    fig.tight_layout()
    path = out / "job_locations_wordcloud.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    written.append(path)
    return written
