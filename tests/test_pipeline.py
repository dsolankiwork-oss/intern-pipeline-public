"""Offline tests: filtering, work-rights tagging, skill scoring and the full demo run."""
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run  # noqa: E402
from pipeline import matching, scoring  # noqa: E402

CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
F = matching.lower_filters(CFG["filters"])
VOCAB = yaml.safe_load((ROOT / "skills.yaml").read_text(encoding="utf-8"))


def job(title, location="Melbourne, VIC", description=""):
    return {"title": title, "location": location, "description": description}


class Matching(unittest.TestCase):
    def test_keeps_local_entry_level(self):
        self.assertTrue(matching.matches(job("Data Analyst Intern"), F))

    def test_drops_senior_titles(self):
        self.assertFalse(matching.matches(job("Senior Data Analyst"), F))
        self.assertFalse(matching.matches(job("Data Engineer II"), F))

    def test_drops_other_cities(self):
        self.assertFalse(matching.matches(job("Graduate Analyst", "Sydney, NSW"), F))

    def test_remote_only_counts_in_region(self):
        self.assertTrue(matching.matches(job("Junior Analyst", "Remote - Australia"), F))
        self.assertFalse(matching.matches(job("Junior Analyst", "Remote - USA"), F))


class Classify(unittest.TestCase):
    def test_open_beats_restricted(self):
        text = "Open to international students as well as Australian citizens"
        self.assertEqual(matching.classify(job("Intern", description=text), F)[0], "open")

    def test_restricted(self):
        text = "Must be an Australian citizen"
        self.assertEqual(matching.classify(job("Intern", description=text), F)[0], "restricted")

    def test_tracks(self):
        tracks = [matching.classify(job(t), F)[1]
                  for t in ("Summer Vacation Program", "Casual Data Assistant", "Graduate Analyst")]
        self.assertEqual(tracks, ["summer", "part_time", "check"])


class Scoring(unittest.TestCase):
    def test_aliases_and_punctuation(self):
        found = scoring.find_skills("We use PostgreSQL, REST APIs. Also node.js and PowerBI.", VOCAB)
        for s in ("sql", "apis", "javascript", "power bi"):
            self.assertIn(s, found)

    def test_no_partial_word_matches(self):
        self.assertNotIn("java", scoring.find_skills("We love JavaScript", VOCAB))

    def test_score_and_gaps(self):
        j = job("Data Intern", description="Python, SQL and Tableau")
        out = scoring.keyword_score(j, {"python", "sql"}, VOCAB)
        self.assertEqual(out["score"], 67)
        self.assertEqual(out["missing"], ["tableau"])

    def test_ai_note_skipped_without_key(self):
        self.assertIsNone(scoring.ai_note(job("x"), "resume", "model"))


class DemoRun(unittest.TestCase):
    def test_demo_end_to_end(self):
        jobs = run.main(["--demo"])
        titles = [j["title"] for j in jobs]
        self.assertEqual(len(jobs), 5)
        self.assertNotIn("Senior Data Scientist", titles)
        self.assertNotIn("Graduate Data Analyst", titles)  # citizens-only is hidden
        self.assertEqual(jobs[0]["score"], max(j["score"] for j in jobs))
        self.assertTrue((ROOT / "reports" / "demo.md").exists())


if __name__ == "__main__":
    unittest.main()
