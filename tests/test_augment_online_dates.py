"""Regression tests for conservative publisher date merging."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import augment_online_dates as module


class PublisherMergeTests(unittest.TestCase):
    def test_conflicting_fields_and_unknown_journal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "publisher-inventory").mkdir(parents=True)
            (root / "data" / "observed.json").write_text(json.dumps({
                "10.1234/conflict": {"title": "Conflict"},
                "10.1234/unknown": {"title": "Unknown"},
                "10.1234/valid": {"title": "Valid"}
            }))
            rows = [
                {"doi": "10.1234/conflict", "journal": "Dental Materials",
                 "status": "publisher_online_date_verified",
                 "publisher_online_date": "2026-10-01", "online_date": "2026-10-02"},
                {"doi": "10.1234/unknown", "journal": "Nonexistent Journal",
                 "status": "publisher_online_date_verified",
                 "publisher_online_date": "2026-10-03"},
                {"doi": "10.1234/valid", "journal": "Dental Materials",
                 "status": "publisher_online_date_verified",
                 "publisher_online_date": "2026-10-04", "online_date": "2026-10-04"}
            ]
            (root / "data" / "publisher-inventory" / "2026-10-verified.json").write_text(
                json.dumps({"records": rows}))
            with patch.object(module, "ROOT", root):
                self.assertEqual(module.merge_publisher("2026-10"), 1)
            observed = json.loads((root / "data" / "observed.json").read_text())
            self.assertNotIn("online_date", observed["10.1234/conflict"])
            self.assertNotIn("online_date", observed["10.1234/unknown"])
            self.assertEqual(observed["10.1234/valid"]["online_date"], "2026-10-04")


    def test_same_doi_with_two_journals_is_not_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "publisher-inventory").mkdir(parents=True)
            (root / "data" / "observed.json").write_text(json.dumps({
                "10.1234/ambiguous": {"title": "Ambiguous"}
            }))
            rows = [
                {"doi": "10.1234/ambiguous", "journal": "Dental Materials",
                 "status": "publisher_online_date_verified",
                 "publisher_online_date": "2026-10-04"},
                {"doi": "10.1234/ambiguous", "journal": "Journal of Dentistry",
                 "status": "publisher_online_date_verified",
                 "publisher_online_date": "2026-10-04"}
            ]
            (root / "data" / "publisher-inventory" / "2026-10-verified.json").write_text(
                json.dumps({"records": rows}))
            with patch.object(module, "ROOT", root):
                self.assertEqual(module.merge_publisher("2026-10"), 0)
            observed = json.loads((root / "data" / "observed.json").read_text())
            self.assertNotIn("online_date", observed["10.1234/ambiguous"])

if __name__ == "__main__":
    unittest.main()
