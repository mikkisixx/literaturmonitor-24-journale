#!/usr/bin/env python3
"""Offline regression tests for independent publication-date provenance."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from verify_publishers import classify, reconcile_status, get_publisher, normalize_date

class PublisherDateConflictTests(unittest.TestCase):
    def test_publisher_conflict_cannot_be_overridden_by_matching_pubmed(self):
        self.assertEqual(reconcile_status("date_conflict", "date_match"), "date_conflict")

    def test_pubmed_conflict_cannot_be_overridden_by_matching_publisher(self):
        self.assertEqual(reconcile_status("publisher_date_match", "date_conflict"), "date_conflict")

    def test_matching_pubmed_does_not_demote_publisher_provenance(self):
        self.assertEqual(reconcile_status("publisher_date_match", "date_match"), "publisher_date_match")

    def test_publisher_match_preserved_without_pubmed_record(self):
        self.assertEqual(reconcile_status("publisher_date_match", "not_indexed"), "publisher_date_match")

    def test_pubmed_match_only_promotes_unverified_publisher(self):
        self.assertEqual(reconcile_status("needs_manual_review", "date_match"), "pubmed_date_match")

    def test_unverified_remains_unverified_without_evidence(self):
        self.assertEqual(reconcile_status("needs_manual_review", "not_indexed"), "needs_manual_review")

    def test_explicit_online_publisher_date_conflict(self):
        status, _, _ = classify([("citation_online_date", "2026-10-02")], "2026-10-03")
        self.assertEqual(status, "date_conflict")


class PublisherVisibleOnlineDateTests(unittest.TestCase):
    def _extract(self, hostname, visible_text):
        class FakeResponse:
            url = "https://" + hostname + "/article"
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return ("<html><body><p>" + visible_text + "</p></body></html>").encode()
        with patch("verify_publishers.urllib.request.urlopen", return_value=FakeResponse()):
            return get_publisher("10.1234/example")[1]

    def test_springer_visible_online_date(self):
        dates = self._extract("link.springer.com", "Published online: 12 October 2026")
        self.assertIn(("springer_visible_published", "12 October 2026"), dates)
        self.assertEqual(normalize_date(dates[0][1]), "2026-10-12")

    def test_elsevier_visible_online_date(self):
        dates = self._extract("www.sciencedirect.com", "Available online 3 November 2026")
        self.assertIn(("elsevier_available_online", "3 November 2026"), dates)
        self.assertEqual(normalize_date(dates[0][1]), "2026-11-03")

if __name__ == "__main__":
    unittest.main()
