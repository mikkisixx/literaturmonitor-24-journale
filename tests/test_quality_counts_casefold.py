"""Regression checks for DOI case normalization and stale verification records."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from quality_counts import online_corroboration_counts


class QualityCountsTests(unittest.TestCase):
    def test_case_insensitive_doi_and_unrelated_checks(self):
        articles = [
            {"doi": "10.1234/AbC", "date_basis": "crossref_online"},
            {"doi": "10.1234/OTHER", "date_basis": "crossref_online"},
            {"doi": "10.1234/EXCLUDED", "date_basis": "published_print"},
        ]
        checks = {
            " 10.1234/abc ": {"status": "publisher_date_match"},
            "10.1234/excluded": {"status": "publisher_date_match"},
            "10.1234/other": {"status": "needs_manual_review"},
        }
        self.assertEqual(online_corroboration_counts(articles, checks), (1, 1))

    def test_duplicate_doi_does_not_inflate_counts(self):
        articles = [
            {"doi": "10.1234/ABC", "date_basis": "crossref_online"},
            {"doi": "10.1234/abc", "date_basis": "crossref_online"},
        ]
        self.assertEqual(
            online_corroboration_counts(articles, {"10.1234/abc": {"status": "pubmed_date_match"}}),
            (1, 0),
        )


if __name__ == "__main__":
    unittest.main()
