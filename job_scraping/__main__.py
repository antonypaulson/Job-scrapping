"""Command-line entry: collect public listings or analyze a saved CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .http import FetchError
from .skills import analyze_jobs
from .sources import SOURCE_NAMES, collect_jobs
from .visualize import save_figures

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HISTORICAL = ROOT / "data" / "texas_jobs_2018.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m job_scraping",
        description="Collect public job listings or analyze a saved CSV.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Fetch listings from a public JSON API")
    collect.add_argument(
        "--source",
        default="jobicy",
        help="jobicy (default), remoteok, arbeitnow, or all. careerjet is documented-only.",
    )
    collect.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Search term (repeatable). Defaults to data scientist and data analyst.",
    )
    collect.add_argument("--limit", type=int, default=50, help="Max rows to keep (default 50)")
    collect.add_argument("--location", default="", help="Optional geo filter (Jobicy only)")
    collect.add_argument(
        "--output",
        default=str(ROOT / "data" / "jobs.csv"),
        help="CSV path (default data/jobs.csv)",
    )
    collect.add_argument(
        "--include-description",
        action="store_true",
        help="Write public ad text. Do not commit that file; ads can contain emails.",
    )

    analyze = sub.add_parser("analyze", help="Rebuild skill flags and charts from a CSV")
    analyze.add_argument(
        "--input",
        default=str(DEFAULT_HISTORICAL),
        help="Jobs CSV (default data/texas_jobs_2018.csv)",
    )
    analyze.add_argument(
        "--figures",
        default=str(ROOT / "figures"),
        help="Directory for PNG charts (default figures/)",
    )
    analyze.add_argument(
        "--output",
        default="",
        help="Optional analyzed CSV path",
    )

    args = parser.parse_args(argv)
    if args.command == "collect":
        return _collect(args)
    return _analyze(args)


def _collect(args: argparse.Namespace) -> int:
    try:
        jobs = collect_jobs(
            source=args.source,
            queries=args.queries or ["data scientist", "data analyst"],
            limit=args.limit,
            location=args.location,
        )
    except FetchError as exc:
        print(f"Collect failed: {exc}", file=sys.stderr)
        print(
            "Analysis still works from saved data:\n"
            f"  python -m job_scraping analyze --input {DEFAULT_HISTORICAL}",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    if not jobs:
        print("No listings matched. Try --source all or a broader --query.", file=sys.stderr)
        return 1

    rows = []
    for job in jobs:
        row = job.to_public_row(include_description=False)
        # Analyze from the in-memory ad text, then drop it unless asked to keep it.
        row["description_text"] = job.description
        rows.append(row)
    frame = analyze_jobs(pd.DataFrame(rows))
    if args.include_description:
        frame["description"] = frame["description_text"]
    frame = frame.drop(columns=["description_text"], errors="ignore")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"Wrote {len(frame)} jobs to {output}")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.exists():
        print(f"No file at {path}. Run collect or use data/texas_jobs_2018.csv.", file=sys.stderr)
        return 1
    frame = pd.read_csv(path)
    analyzed = analyze_jobs(frame)
    written = save_figures(analyzed, args.figures)
    print(f"Analyzed {len(analyzed)} rows")
    for item in written:
        print(f"  {item}")
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        analyzed.to_csv(out, index=False)
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
