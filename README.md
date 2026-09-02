# Scraping and visualization of job openings

Class / portfolio project by [Antony Paulson](https://github.com/antonypaulson): collect data-related job ads, group repeated skill wording, and chart what employers asked for.

The GitHub repo name (`Job-scrapping`) keeps the original spelling. This is still a local Jupyter / CLI project, not a hosted product.

## What was here in 2018

The notebooks on `master` were written in **Python 2.7**. They:

1. Called the Careerjet affiliate search client for *Data Analyst* jobs in Texas.
2. Followed each result URL and parsed `div.main_job` with BeautifulSoup.
3. Flagged skills, industries, degrees, and years of experience.
4. Plotted bars, pies, and a location word cloud.
5. Wrote `80JobsTexas.xlsx`, which was never committed.

That live path is broken:

- Careerjet’s current [publisher API](https://www.careerjet.com/partners/api) needs a key, HTTP basic auth, and an IP allowlist. The old `careerjet_api_client` / `affid` flow is not used here.
- Job-page HTML has changed, so the `main_job` scraper does not survive.
- The notebooks hardcoded an affiliate id and a residential IP. Those values are redacted.

The original assignment text is still in the notebook comments. The 2018 Texas analysis is runnable from `data/texas_jobs_2018.csv` (60 recoverable rows; see `data/README.md`).

## What works now

Live collection uses **documented public JSON feeds**, not HTML scraping of job boards:

| Source | Endpoint | Notes |
| --- | --- | --- |
| [Jobicy](https://jobicy.com/jobs-rss-feed) (default) | `https://jobicy.com/api/v2/remote-jobs` | No key. At most one poll per hour. |
| [Remote OK](https://remoteok.com) | `https://remoteok.com/api` | No key. Credit Remote OK; feed is delayed. |
| [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api) | `https://www.arbeitnow.com/api/job-board-api` | No key. Paginate slowly. |

Requests send a project User-Agent, a timeout, and a pause between calls. 429s honor `Retry-After` once and then stop.

Skill grouping is the same idea as 2018 (SQL / Python / degrees / years) plus a few newer data tools.

## Setup

Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For tests: `pip install -r requirements-dev.txt`

## Analyze the 2018 Texas snapshot (no network)

```bash
python -m job_scraping analyze --input data/texas_jobs_2018.csv --figures figures
```

Or open `notebooks/02_visualize_jobs.ipynb`.

That writes:

- `figures/jobs_by_technology.png`
- `figures/jobs_by_sector.png`
- `figures/jobs_by_education.png`
- `figures/jobs_by_experience.png`
- `figures/job_locations_wordcloud.png`

## Collect current public listings

```bash
python -m job_scraping collect --source jobicy --query "data scientist" --query "data analyst" --limit 50 --output data/jobs.csv
```

`--source all` tries Jobicy, then Remote OK, then Arbeitnow, with spacing between requests.

`--include-description` writes public ad text. Do not commit that file.

If a feed is down, analyze still runs from the saved CSV.

Careerjet is intentionally disabled (`--source careerjet` explains why).

## Notebooks

| File | Role |
| --- | --- |
| `notebooks/01_collect_jobs.ipynb` | Python 3 collect + skill flags |
| `notebooks/02_visualize_jobs.ipynb` | Charts from a CSV |
| `Data collection.ipynb` | Historical 2018 collector (do not run as-is) |
| `Data Visualisations.ipynb` | Historical 2018 charts (needs the missing xlsx; use the CSV instead) |

## Tests

```bash
pytest -q
```

Parser tests use fixtures. They do not hit the network.

## Respectful use

- Identify yourself (`User-Agent` in `job_scraping/http.py`).
- Do not loop these feeds. Jobicy asks for **at most one request per hour**.
- Link back to Jobicy / Remote OK / Arbeitnow if you republish listings.
- This repo stores titles, companies, locations, and skill flags only.

## Layout

```
job_scraping/     HTTP client, public-API collectors, skill flags, charts
notebooks/        Python 3 walkthrough
data/             Saved tables (see data/README.md)
tests/            Unit tests + JSON fixtures
figures/          PNG output from analyze
```
