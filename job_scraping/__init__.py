"""Collect and visualize public job listings for this portfolio project.

The 2018 notebooks used Careerjet plus HTML scraping. That path no longer
works without a publisher key. This package keeps the same analysis idea
(skill grouping + charts) and collects from documented public JSON APIs.
"""

from .jobs import JobPosting
from .skills import analyze_jobs, extract_keywords
from .sources import collect_jobs
from .visualize import save_figures

__all__ = [
    "JobPosting",
    "analyze_jobs",
    "collect_jobs",
    "extract_keywords",
    "save_figures",
]
__version__ = "1.0.0"
