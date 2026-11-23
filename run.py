"""Intern Pipeline: find new entry-level jobs every day and score them against your resume.

    python run.py           # live run: fetch every company in config.yaml
    python run.py --demo    # offline demo with bundled sample jobs and the demo resume
"""
import argparse
import datetime as dt
import os
import sqlite3
import sys
import time
from pathlib import Path

import yaml

from pipeline import fetchers, matching, report, scoring

ROOT = Path(__file__).parent
EXTRA_COLS = ("work_rights", "track", "ai_score", "ai_why", "ai_gap", "matched", "missing")


def load_yaml(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def open_db(path):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        key TEXT PRIMARY KEY, source TEXT, company TEXT, title TEXT, url TEXT,
        location TEXT, posted TEXT, description TEXT, found_on TEXT,
        score INTEGER, why TEXT, status TEXT DEFAULT 'new')""")
    have = {r[1] for r in con.execute("PRAGMA table_info(jobs)")}
    for c in EXTRA_COLS:  # upgrade databases made by older versions
        if c not in have:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {c} TEXT")
    return con


def load_resume(cfg, demo):
    if not demo and os.environ.get("RESUME_TEXT"):  # keep a real resume out of a public repo
        return os.environ["RESUME_TEXT"]
    return (ROOT / cfg["profile"]["resume_file"]).read_text(encoding="utf-8")


def collect(cfg, demo):
    if demo:
        return fetchers.demo_jobs(ROOT / "sample_data" / "demo_jobs.json"), []
    jobs, errors = [], []
    for c in cfg["companies"]:
        fetch = fetchers.FETCHERS.get(c["ats"])
        if not fetch:
            errors.append(f"{c['name']}: unknown ats '{c['ats']}'")
            continue
        try:
            jobs += fetch(c["name"], c["token"])
        except Exception as e:  # one bad board never stops the run
            errors.append(f"{c['name']}: {type(e).__name__}")
        time.sleep(0.5)  # be polite to the APIs
    return jobs, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--demo", action="store_true", help="offline demo with sample jobs")
    args = ap.parse_args(argv)

    cfg = load_yaml("config.yaml")
    vocab = load_yaml("skills.yaml")
    f = matching.lower_filters(cfg["filters"])
    resume = load_resume(cfg, args.demo)
    resume_skills = set(scoring.find_skills(resume, vocab)) | set(cfg["profile"].get("extra_skills") or [])

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    db_path = ":memory:" if args.demo else ROOT / "data" / "jobs.db"
    prefix = "demo" if args.demo else "latest"
    con = open_db(db_path)
    today = dt.date.today().isoformat()

    postings, errors = collect(cfg, args.demo)
    new = []
    for j in postings:
        if not matching.matches(j, f):
            continue
        j["work_rights"], j["track"] = matching.classify(j, f)
        status = "skipped_restricted" if j["work_rights"] == "restricted" else "new"
        cur = con.execute(
            "INSERT OR IGNORE INTO jobs (key, source, company, title, url, location, posted,"
            " description, found_on, status, work_rights, track) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (j["key"], j["source"], j["company"], j["title"], j["url"], j["location"],
             j["posted"], j["description"], today, status, j["work_rights"], j["track"]))
        if cur.rowcount and (status == "new" or cfg["profile"].get("show_restricted")):
            j.update(scoring.keyword_score(j, resume_skills, vocab))
            new.append(j)

    new.sort(key=lambda j: (j["work_rights"] == "restricted", -(j["score"] or -1)))

    ai = cfg.get("ai") or {}
    for j in new[: int(ai.get("max_jobs_per_run", 10))]:
        note = scoring.ai_note(j, resume, ai.get("model", "claude-haiku-5-5"))
        if note:
            j["ai_score"], j["ai_why"], j["ai_gap"] = note["score"], note["why"], note["gap"]

    for j in new:
        con.execute("UPDATE jobs SET score=?, matched=?, missing=?, ai_score=?, ai_why=?, ai_gap=?"
                    " WHERE key=?", (j["score"], "; ".join(j["matched"]), "; ".join(j["missing"]),
                                     j.get("ai_score"), j.get("ai_why"), j.get("ai_gap"), j["key"]))
    con.commit()

    report.write_csv(ROOT / "data" / f"{prefix}_jobs.csv", new)
    report.write_markdown(ROOT / "reports" / f"{prefix}.md", new, today, len(postings), errors)
    print(f"{len(new)} new matching jobs from {len(postings)} postings "
          f"-> reports/{prefix}.md")
    for e in errors:
        print("WARN", e, file=sys.stderr)
    return new


if __name__ == "__main__":
    main()
