"""Decide which postings are relevant, and tag work rights and job type."""
import re


def lower_filters(filters):
    return {k: [x.lower() for x in v] for k, v in filters.items()}


def matches(job, f):
    title = f" {job['title'].lower()} "
    loc = job["location"].lower()
    if not any(k in title for k in f["title_keywords"]):
        return False
    if any(re.search(k, title) for k in f["title_exclude"]):
        return False
    in_city = any(k in loc for k in f["locations"])
    remote_here = "remote" in loc and any(k in loc for k in f["remote_regions"])
    return in_city or remote_here


def _has(text, patterns):
    return any(re.search(p, text) for p in patterns)


def classify(job, f):
    """Work rights: open / restricted / unknown.  Track: summer / part_time / check."""
    text = f"{job['title']} {job['description']}".lower()
    if _has(text, f.get("open_to_visa_patterns", [])):
        rights = "open"
    elif _has(text, f.get("restricted_patterns", [])):
        rights = "restricted"
    else:
        rights = "unknown"
    if _has(text, f.get("part_time_patterns", [])):
        track = "part_time"
    elif _has(text, f.get("summer_patterns", [])):
        track = "summer"
    else:
        track = "check"
    return rights, track
