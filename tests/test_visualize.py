from pathlib import Path

import pandas as pd

from job_scraping.skills import analyze_jobs
from job_scraping.visualize import save_figures


def test_save_figures_from_saved_style_table(tmp_path):
    frame = analyze_jobs(
        pd.DataFrame(
            [
                {
                    "title": "Data Analyst",
                    "company": "Acme",
                    "locations": "Austin, TX",
                    "description": "Python SQL Tableau 3 years Bachelor computer science finance",
                },
                {
                    "title": "Data Scientist",
                    "company": "Beta",
                    "locations": "Houston, TX",
                    "description": "Python R 5 years Master statistics healthcare",
                },
                {
                    "title": "Analyst",
                    "company": "Gamma",
                    "locations": "Dallas, TX",
                    "skills": "excel|word|bachelor|2",
                },
            ]
        )
    )
    written = save_figures(frame, tmp_path)
    names = {path.name for path in written}
    assert names == {
        "jobs_by_technology.png",
        "jobs_by_sector.png",
        "jobs_by_education.png",
        "jobs_by_experience.png",
        "job_locations_wordcloud.png",
    }
    assert all(path.exists() and path.stat().st_size > 0 for path in written)


def test_analyze_historical_csv_if_present():
    csv_path = Path(__file__).resolve().parents[1] / "data" / "texas_jobs_2018.csv"
    if not csv_path.exists():
        return
    frame = analyze_jobs(pd.read_csv(csv_path))
    assert len(frame) >= 50
    assert frame["sql"].sum() >= 1
    assert "Austin, TX" in set(frame["locations"].dropna())
