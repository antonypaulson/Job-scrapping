import pandas as pd

from job_scraping.skills import (
    analyze_jobs,
    extract_experience_years,
    extract_keywords,
    flags_from_skills,
    parse_skill_list,
)


def test_extract_keywords_finds_skills_and_years():
    text = (
        "Looking for a Data Analyst with Python, SQL and Tableau. "
        "3-5 years of experience. Bachelor degree in computer science."
    )
    found = extract_keywords(text)
    assert "python" in found
    assert "sql" in found
    assert "tableau" in found
    assert "computer science" in found
    assert "bachelor" in found
    assert "5" in found


def test_r_does_not_match_inside_other_words():
    found = extract_keywords("Senior analyst for our marketing department")
    assert "r" not in found
    assert "marketing" in found


def test_experience_word_numbers():
    assert extract_experience_years("at least five years of experience") == 5
    assert extract_experience_years("no mention") is None


def test_education_grouping_matches_2018_notebook():
    flags = flags_from_skills(["bachelor", "bs", "master", "mba", "degree", "5"])
    assert flags["Bachelor"] == 0
    assert flags["Master"] == 0
    assert flags["Master_pref"] == 1
    assert flags["5"] == 1
    assert flags["degree"] == 0


def test_parse_skill_list_from_notebook_cell():
    parsed = parse_skill_list("[excel, accounting, food, operation, degree, ms, 5]")
    assert "excel" in parsed
    assert "5" in parsed or "5" in [str(x) for x in parsed]


def test_analyze_jobs_adds_flag_columns():
    frame = pd.DataFrame(
        [
            {
                "title": "Data Analyst",
                "company": "Acme",
                "location": "Austin, TX",
                "description": "Python SQL 2 years Bachelor",
            },
            {
                "title": "Chef",
                "company": "",
                "location": "Houston, TX",
                "skills": "excel|food|3",
            },
        ]
    )
    out = analyze_jobs(frame)
    assert out.loc[0, "python"] == 1
    assert out.loc[0, "sql"] == 1
    assert out.loc[0, "2"] == 1
    assert out.loc[1, "company"] == "Unknown"
    assert out.loc[1, "food"] == 1
    assert "locations" in out.columns
