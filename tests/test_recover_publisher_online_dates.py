"""Regression tests for publisher first-online date recovery (offline)."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from scripts import recover_publisher_online_dates as recovery


class RecoveryTests(unittest.TestCase):
    def test_explicit_online_date_is_accepted(self):
        with patch.object(recovery, "get_publisher", return_value=(
            "https://publisher.example/article", [
                ("citation_online_date", "2026-10-12"),
                ("citation_publication_date", "2027-01-01"),
            ])):
            doi, result = recovery.inspect({"doi": "10.1234/ABC"})
        self.assertEqual(doi, "10.1234/abc")
        self.assertEqual(result["online_date"], "2026-10-12")
        self.assertEqual(result["status"], "publisher_online_date_verified")

    def test_generic_publication_date_is_not_accepted(self):
        with patch.object(recovery, "get_publisher", return_value=(
            "https://publisher.example/article", [
                ("citation_publication_date", "2026-10-12"),
            ])):
            _, result = recovery.inspect({"doi": "10.1234/abc"})
        self.assertEqual(result["status"], "no_explicit_online_date")

    def test_conflicting_explicit_dates_are_rejected(self):
        with patch.object(recovery, "get_publisher", return_value=(
            "https://publisher.example/article", [
                ("citation_online_date", "2026-10-12"),
                ("citation_date_online", "2026-10-13"),
            ])):
            _, result = recovery.inspect({"doi": "10.1234/abc"})
        self.assertEqual(result["status"], "conflicting_online_dates")

    def test_recovery_does_not_overwrite_conflicting_existing_date(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "data/months").mkdir(parents=True)
            (root / "data/months/2026-10.json").write_text(json.dumps({
                "articles": [{"doi": "10.1234/abc", "journal": "Example",
                              "date_basis": "crossref_published_unverified"}]
            }))
            observed = {"10.1234/abc": {"online_date": "2026-09-30"}}
            (root / "data/observed.json").write_text(json.dumps(observed))
            with patch.object(recovery, "ROOT", root), patch.object(
                recovery, "inspect", return_value=("10.1234/abc", {
                    "status": "publisher_online_date_verified",
                    "online_date": "2026-10-12",
                    "publisher_url": "https://publisher.example/article",
                    "evidence": [{"field": "citation_online_date", "value": "2026-10-12"}],
                })
            ):
                recovery.recover("2026-10", workers=1)
            saved = json.loads((root / "data/observed.json").read_text())
            self.assertEqual(saved["10.1234/abc"]["online_date"], "2026-09-30")
            checks = json.loads((root / "data/publisher-candidate-checks/2026-10.json").read_text())
            self.assertEqual(checks["existing_date_conflicts"], 1)
            self.assertEqual(checks["publisher_dates_recovered"], 0)


if __name__ == "__main__":
    unittest.main()
