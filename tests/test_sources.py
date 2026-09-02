import json
from pathlib import Path

import pytest

from job_scraping.http import RespectfulClient
from job_scraping.sources import collect_jobs, looks_like_data_role

FIXTURES = Path(__file__).parent / "fixtures"


class ScriptedClient(RespectfulClient):
    def __init__(self, payload_by_url):
        super().__init__(min_interval=0, sleeper=lambda _: None)
        self.payload_by_url = payload_by_url
        self.urls = []

    def get_json(self, url, params=None, extra_headers=None):
        self.urls.append((url, dict(params or {})))
        for prefix, payload in self.payload_by_url.items():
            if prefix in url:
                return payload
        raise AssertionError(f"unexpected url {url}")


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def test_jobicy_parser():
    client = ScriptedClient({"jobicy.com": _load("jobicy_sample.json")})
    jobs = collect_jobs("jobicy", queries=["data scientist"], limit=10, client=client)
    assert len(jobs) == 1
    assert jobs[0].title == "Data Scientist"
    assert jobs[0].company == "Open Data Lab"
    assert jobs[0].source == "jobicy"
    assert "Python" in jobs[0].description or "python" in jobs[0].description.lower()


def test_remoteok_filters_to_query():
    client = ScriptedClient({"remoteok.com": _load("remoteok_sample.json")})
    jobs = collect_jobs("remoteok", queries=["data analyst"], limit=10, client=client)
    assert [job.title for job in jobs] == ["Senior Data Analyst"]
    assert jobs[0].salary == "90000 - 120000"


def test_arbeitnow_skips_non_data_roles():
    client = ScriptedClient({"arbeitnow.com": _load("arbeitnow_sample.json")})
    jobs = collect_jobs("arbeitnow", queries=["data analyst"], limit=10, client=client)
    assert [job.title for job in jobs] == ["Data Analyst (m/w/d)"]
    assert jobs[0].location == "Berlin"


def test_careerjet_is_explicitly_disabled():
    with pytest.raises(RuntimeError, match="Careerjet"):
        collect_jobs("careerjet")


def test_unknown_source():
    with pytest.raises(ValueError, match="Unknown source"):
        collect_jobs("indeed")


def test_looks_like_data_role():
    assert looks_like_data_role("Junior Data Scientist")
    assert not looks_like_data_role("Line Cook", ["kitchen"])
