"""Write today's results as a CSV and a Markdown report that renders on GitHub."""
import csv

RIGHTS = {"open": "✅ open", "unknown": "❔ check", "restricted": "⛔ restricted"}


def write_csv(path, jobs):
    cols = ["score", "ai_score", "company", "title", "location", "work_rights", "track",
            "matched", "missing", "ai_why", "ai_gap", "posted", "url"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for j in jobs:
            w.writerow({**j, "matched": "; ".join(j["matched"]),
                        "missing": "; ".join(j["missing"])})


def _cell(text):
    return str(text).replace("|", "/").replace("\n", " ")


def write_markdown(path, jobs, today, total_seen, errors):
    lines = [f"# Today's matches: {today}", "",
             f"**{len(jobs)} new matching jobs** (from {total_seen} postings checked). "
             "Sorted by fit score. Score = share of the job's listed skills found in your resume.", ""]
    if not jobs:
        lines.append("_No new matches today._")
    else:
        lines += ["| Fit | Role | Company | Location | Work rights | You have | Worth adding |",
                  "|---|---|---|---|---|---|---|"]
        for j in jobs:
            fit = "–" if j["score"] is None else f"{j['score']}%"
            if j.get("ai_score") is not None:
                fit += f" · AI {j['ai_score']}"
            lines.append("| " + " | ".join(_cell(x) for x in [
                fit, f"[{j['title']}]({j['url']})", j["company"], j["location"],
                RIGHTS.get(j["work_rights"], j["work_rights"]),
                ", ".join(j["matched"][:6]) or "–", ", ".join(j["missing"][:6]) or "–"]) + " |")
        notes = [j for j in jobs if j.get("ai_why")]
        if notes:
            lines += ["", "## AI notes", ""]
            for j in notes:
                lines.append(f"- **{_cell(j['title'])} · {_cell(j['company'])}**: "
                             f"{j['ai_why']} _Gap: {j['ai_gap']}_")
    if errors:
        lines += ["", "<details><summary>Feeds that failed today</summary>", ""]
        lines += [f"- {e}" for e in errors] + ["", "</details>"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
