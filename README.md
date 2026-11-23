# Intern Pipeline: your daily job radar

![tests](https://github.com/dsolankiwork-oss/intern-pipeline-public/actions/workflows/tests.yml/badge.svg)

**Stop scrolling job boards.** Every morning this tool checks the careers pages of the companies you care about, keeps the entry-level roles in your city, and **scores each one against your resume**. You also see which skills you already have and which are worth adding.

It's free and runs on GitHub Actions, so your laptop doesn't need to be on. Fork it, edit one file, and you're done.

👉 **[See a sample report](reports/demo.md)** (generated from the demo resume and sample jobs)

| Fit | Role | Company | Work rights | You have | Worth adding |
|---|---|---|---|---|---|
| 100% | Data Analyst Intern | Northwind Analytics | ✅ open | python, sql, power bi … | – |
| 67% | AI Automation Intern | Bluegum Software | ❔ check | python, apis, generative ai … | javascript, crm |
| 50% | Junior BI Analyst | Coastline Health | ❔ check | sql, power bi, git … | etl, dbt, snowflake |

<sub>Demo data. The companies are fictional.</sub>

## Try it in 30 seconds (no setup, no internet)

```bash
git clone https://github.com/dsolankiwork-oss/intern-pipeline-public.git
cd intern-pipeline-public
pip install -r requirements.txt
python run.py --demo        # writes reports/demo.md
```

## Make it yours (about 10 minutes)

1. **Fork** this repo. Click **Fork** at the top right.
2. **Add your resume.** Pick one option:
   - **Private (recommended):** go to *Settings → Secrets and variables → Actions → New repository secret*, name it `RESUME_TEXT`, and paste your resume as plain text. It never appears in the repo.
   - **Simple:** replace `profile/resume.md` with your own. Note that it becomes public if your fork is public.
3. **Edit `config.yaml`:**
   - change `locations` to your city
   - adjust `title_keywords` to the roles you want
   - add the companies you're watching (the file explains how to find each company's token in 10 seconds)
4. **Turn it on.** Open the *Actions* tab, enable workflows, open **daily-job-run** and click **Run workflow**.
5. **Read your report** at `reports/latest.md` every morning. A CSV version is saved at `data/latest_jobs.csv`.

**Optional AI notes.** Add an `ANTHROPIC_API_KEY` secret and Claude writes a one-line "why you fit" and "biggest gap" note for your top 10 jobs each day. The number of jobs is capped in `config.yaml` to keep costs small. Without a key, everything else still works.

## How it works

```
companies.yaml ─► fetch (Greenhouse · Lever · Ashby · SmartRecruiters APIs)
               ─► filter (title keywords, seniority, city / remote region)
               ─► tag    (work rights: open / check / restricted · summer / part-time)
               ─► dedupe (SQLite: a job is never shown twice)
               ─► score  (skill overlap with your resume  [+ optional Claude note])
               ─► report (reports/latest.md + CSV, committed back by GitHub Actions)
```

**Design choices**

- **Official public APIs only.** Most companies list jobs through an applicant tracking system (ATS) with a public API, so nothing is scraped from LinkedIn or Seek.
- **Explainable scoring.** The fit score is the share of a job's listed skills that appear in your resume, using a vocabulary with aliases in `skills.yaml`. That makes the "worth adding" column something you can act on.
- **Fault tolerant.** One broken company feed, or a failed AI call, never stops the run.
- **Config, not code.** Cities, keywords, companies and skills all live in YAML.
- **Upgrades in place.** New versions add columns to your existing database instead of breaking it.
- **Tested.** 12 offline unit tests, including an end-to-end demo run, on every push.

## Project layout

```
run.py                    # entry point (python run.py [--demo])
config.yaml               # your city, keywords, companies, AI settings
skills.yaml               # skill vocabulary + aliases for scoring
profile/resume.md         # demo resume (replace, or use the RESUME_TEXT secret)
pipeline/fetchers.py      # one function per ATS, normalised to one schema
pipeline/matching.py      # filters + work-rights / job-type tagging
pipeline/scoring.py       # skill-overlap score + optional Claude note
pipeline/report.py        # Markdown + CSV output
sample_data/demo_jobs.json
tests/test_pipeline.py
.github/workflows/        # daily run + tests
```

## Notes

- Work-rights tags are a hint based on wording in the job ad. Always read the ad.
- Companies on Workday or custom careers sites can't be read this way yet. Contributions are welcome.

## Roadmap

- [ ] Email or Telegram digest of the top 5 jobs
- [ ] Workday support
- [ ] One-click "draft cover letter" for a chosen job

---

Built by **Dhruv Solanki**, Master of Data Science student at Monash University, to automate his own job search. Built with help from AI coding assistants. MIT licensed: fork it, use it, improve it.
