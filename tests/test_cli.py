from pathlib import Path

from job_scraping.__main__ import main


def test_analyze_cli_writes_figures(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data" / "texas_jobs_2018.csv"
    figures = tmp_path / "figures"
    analyzed = tmp_path / "analyzed.csv"
    code = main(
        [
            "analyze",
            "--input",
            str(source),
            "--figures",
            str(figures),
            "--output",
            str(analyzed),
        ]
    )
    assert code == 0
    assert analyzed.exists()
    assert (figures / "jobs_by_technology.png").exists()


def test_collect_careerjet_exits_cleanly():
    assert main(["collect", "--source", "careerjet"]) == 2


def test_collect_uses_description_for_flags_then_drops_it(tmp_path, monkeypatch):
    from job_scraping import __main__ as cli
    from job_scraping.jobs import JobPosting

    def fake_collect(**kwargs):
        return [
            JobPosting(
                title="Data Analyst",
                company="Acme",
                location="Remote",
                url="https://example.test/job",
                source="jobicy",
                description="Python, SQL, Tableau and 3 years. Bachelor degree.",
            )
        ]

    monkeypatch.setattr(cli, "collect_jobs", fake_collect)
    out = tmp_path / "jobs.csv"
    assert main(["collect", "--output", str(out), "--limit", "1"]) == 0
    import pandas as pd

    frame = pd.read_csv(out)
    assert "description" not in frame.columns
    assert int(frame.loc[0, "python"]) == 1
    assert int(frame.loc[0, "sql"]) == 1
    assert int(frame.loc[0, "3"]) == 1
