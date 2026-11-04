#!/usr/bin/env python3
"""Offline regression tests for independent publication-date provenance."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from verify_publishers import classify, reconcile_status

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

if __name__ == "__main__":
    unittest.main()
