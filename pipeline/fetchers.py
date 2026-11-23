"""Fetch postings from public ATS job-board APIs and normalise them into one shape."""
import datetime as dt
import json
import re
from pathlib import Path

import requests

HEADERS = {"User-Agent": "intern-pipeline/2.0 (open-source job search tool)"}
TIMEOUT = 20


def _job(source, company, jid, title, url, location, posted, description=""):
    text = re.sub(r"<[^>]+>", " ", description or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return {
        "key": f"{source}:{company}:{jid}",
        "source": source,
        "company": company,
        "title": (title or "").strip(),
        "url": url or "",
        "location": (location or "").strip(),
        "posted": (posted or "")[:10],
        "description": re.sub(r"\s+", " ", text).strip()[:8000],
    }


def greenhouse(company, token):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                     params={"content": "true"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return [_job("greenhouse", company, j["id"], j.get("title"), j.get("absolute_url"),
                 (j.get("location") or {}).get("name"), j.get("updated_at"), j.get("content"))
            for j in r.json().get("jobs", [])]


def lever(company, token):
    r = requests.get(f"https://api.lever.co/v0/postings/{token}",
                     params={"mode": "json"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json():
        ts = j.get("createdAt")
        posted = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).isoformat() if ts else ""
        cat = j.get("categories") or {}
        loc = cat.get("location") or ", ".join(cat.get("allLocations") or [])
        out.append(_job("lever", company, j["id"], j.get("text"), j.get("hostedUrl"),
                        loc, posted, j.get("descriptionPlain")))
    return out


def ashby(company, token):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        loc = j.get("location") or ""
        if j.get("isRemote"):
            loc = f"{loc} (Remote)".strip()
        out.append(_job("ashby", company, j["id"], j.get("title"), j.get("jobUrl"),
                        loc, j.get("publishedAt"), j.get("descriptionPlain")))
    return out


def smartrecruiters(company, token):
    r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
                     params={"limit": 100}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json().get("content", []):
        loc = j.get("location") or {}
        loc_s = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
        if loc.get("remote"):
            loc_s += " (Remote)"
        out.append(_job("smartrecruiters", company, j["id"], j.get("name"),
                        f"https://jobs.smartrecruiters.com/{token}/{j['id']}",
                        loc_s, j.get("releasedDate")))
    return out


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
            "smartrecruiters": smartrecruiters}


def demo_jobs(path):
    """Bundled sample postings so anyone can try the tool offline."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_job("demo", j["company"], i, j["title"], j["url"], j["location"],
                 j.get("posted", ""), j["description"]) for i, j in enumerate(raw)]
