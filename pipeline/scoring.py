"""Score each job against the user's resume.

Always: a free, explainable skill-overlap score (no API key needed).
Optional: if ANTHROPIC_API_KEY is set, Claude writes a short fit note for the top jobs.
"""
import json
import os
import re

import requests


def _norm(text):
    t = re.sub(r"[^a-z0-9+#.]+", " ", text.lower())
    t = re.sub(r"\.(?=\s|$)", " ", t)  # drop sentence full stops, keep "node.js"
    t = re.sub(r"\s+", " ", t)
    return f" {t} "


def find_skills(text, vocabulary):
    """Return the vocabulary skills that appear in text (aliases supported)."""
    t = _norm(text)
    found = []
    for skill, aliases in vocabulary.items():
        for term in [skill, *(aliases or [])]:
            if f" {_norm(term).strip()} " in t:
                found.append(skill)
                break
    return found


def keyword_score(job, resume_skills, vocabulary):
    job_skills = find_skills(f"{job['title']} {job['description']}", vocabulary)
    if not job_skills:
        return {"score": None, "matched": [], "missing": []}
    have = set(resume_skills)
    matched = [s for s in job_skills if s in have]
    missing = [s for s in job_skills if s not in have]
    return {"score": round(100 * len(matched) / len(job_skills)),
            "matched": matched, "missing": missing}


PROMPT = """You are helping a job seeker triage postings. Compare the resume and the job.
Reply with JSON only: {{"score": 0-100, "why": "<one sentence on the strongest fit>",
"gap": "<one sentence on the biggest gap, or 'none'>"}}. Be honest; do not inflate.

RESUME:
{resume}

JOB: {title} at {company} ({location})
{description}"""


def ai_note(job, resume, model):
    """Optional Claude fit note. Returns None if no key or on any error."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": model, "max_tokens": 300,
                  "messages": [{"role": "user", "content": PROMPT.format(
                      resume=resume[:6000], title=job["title"], company=job["company"],
                      location=job["location"], description=job["description"][:4000])}]},
            timeout=60)
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
        return {"score": int(data["score"]), "why": str(data["why"]), "gap": str(data["gap"])}
    except Exception as e:  # never let the optional AI step break the run
        print(f"WARN ai_note {job['company']}: {e}")
        return None
