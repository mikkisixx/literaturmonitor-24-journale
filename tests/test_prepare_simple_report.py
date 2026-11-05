"""Regression tests for month-specific coverage metadata."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_simple_report


class PrepareSimpleReportTests(unittest.TestCase):
    def test_refreshes_counters_and_preserves_reviewed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("data/months", "data/coverage", "data/quality"):
                (root / folder).mkdir(parents=True)
            month = "2026-08"
            (root / f"data/backfill-{month}.json").write_text(
                json.dumps({"checked": 24, "errors": {"one": "timeout"}}))
            (root / f"data/months/{month}.json").write_text(
                json.dumps({"verified_online_count": 12, "candidate_count": 19}))
            (root / f"data/coverage/{month}.json").write_text(
                json.dumps({"journals_queried": 1, "complete": False,
                            "journals_independently_verified": 3,
                            "missing_publisher_articles": ["10.1234/example"]}))
            (root / f"data/quality/{month}.json").write_text(
                json.dumps({"crossref_online_articles": 2,
                            "publication_ready": False,
                            "release_status": "review_required"}))
            with patch.object(prepare_simple_report, "ROOT", root):
                prepare_simple_report.prepare(month)
            coverage = json.loads((root / f"data/coverage/{month}.json").read_text())
            quality = json.loads((root / f"data/quality/{month}.json").read_text())
            self.assertEqual(coverage["journals_queried"], 24)
            self.assertEqual(coverage["query_errors"], 1)
            self.assertEqual(coverage["journals_independently_verified"], 3)
            self.assertEqual(coverage["missing_publisher_articles"], ["10.1234/example"])
            self.assertFalse(coverage["complete"])
            self.assertEqual(quality["crossref_online_articles"], 12)
            self.assertEqual(quality["candidate_count"], 19)
            self.assertFalse(quality["publication_ready"])
            self.assertEqual(quality["release_status"], "review_required")


if __name__ == "__main__":
    unittest.main()
