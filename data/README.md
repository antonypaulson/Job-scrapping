# Saved job tables

These files are public job-ad metadata (title, company, location, salary range, listing URL). They are not applicant records.

| File | What it is |
| --- | --- |
| `texas_jobs_2018.csv` | 60 of the ~80 Texas Data Analyst rows from the original 2018 Careerjet run. Recovered from the committed notebook output. Twenty rows were lost because pandas truncated the displayed table. `skills` is the keyword list the 2018 notebook extracted, not the full job description. |

Do not commit live collect output if you used `--include-description`. Public ads sometimes contain recruiter emails.
