"""Regression checks for the per-journal provenance ledger."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_provenance


class ProvenanceTests(unittest.TestCase):
    def test_all_24_journals_remain_unverified_without_independent_inventory(self):
        with patch.object(report_provenance, "load", return_value={}):
            result = report_provenance.make("2026-10")
        self.assertEqual(result["journal_count"], 24)
        self.assertEqual(len(result["journals"]), 24)
        self.assertEqual(len({row["journal"] for row in result["journals"]}), 24)
        self.assertFalse(result["independently_complete"])
        self.assertFalse(result["all_crossref_queries_succeeded"])
        self.assertTrue(all(not row["independently_exhaustive"] for row in result["journals"]))
        self.assertTrue(all(row["publisher_listing"]["status"] == "not_implemented"
                            for row in result["journals"]))

    def test_specific_publisher_coverage_failure_is_preserved(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        def fake_load(path):
            if path.name == "2026-10-coverage.json":
                return {"journals": [{"journal": journal,
                    "publisher_coverage_reason": "Publisher pagination stopped at page limit; remaining pages not checked"}]}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        row = next(row for row in result["journals"] if row["journal"] == journal)
        self.assertIn("page limit", row["reason"])
        self.assertFalse(row["independently_exhaustive"])

    def test_publication_queries_are_not_mistaken_for_online_first_queries(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        def fake_load(path):
            if path.name == "backfill-2026-10.json":
                return {"counts": {journal: 7}, "checked": 1, "errors": {}}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        row = next(row for row in result["journals"] if row["journal"] == journal)
        self.assertEqual(row["crossref_publication_query"]["status"], "queried")
        self.assertEqual(row["crossref_online_query"]["status"], "not_run")
        self.assertFalse(result["all_crossref_publication_queries_succeeded"])
        self.assertFalse(result["all_crossref_queries_succeeded"])

    def test_publication_query_success_requires_24_completed_checks(self):
        names = [name for group in report_provenance.collect.JOURNALS.values() for name in group]
        self.assertEqual(len(names), 24)
        def fake_load(path):
            if path.name == "backfill-2026-10.json":
                return {"counts": {name: 1 for name in names},
                        "checked": 23, "errors": {}}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        self.assertTrue(all(row["crossref_publication_query"]["status"] == "queried"
                            for row in result["journals"]))
        self.assertFalse(result["all_crossref_publication_queries_succeeded"])

    def test_publication_query_failure_is_explicit(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        def fake_load(path):
            if path.name == "backfill-2026-10.json":
                return {"counts": {}, "errors": {journal: "HTTP 503"}}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        row = next(row for row in result["journals"] if row["journal"] == journal)
        self.assertEqual(row["crossref_publication_query"]["status"], "failed")
        self.assertEqual(row["crossref_publication_query"]["error"], "HTTP 503")

    def test_confirmed_publisher_gaps_and_sources_are_preserved(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        def fake_load(path):
            if path.name == "2026-10-coverage.json":
                return {"journals": [{"journal": journal,
                    "confirmed_month_missing_dois": ["10.1007/missing"],
                    "confirmed_month_missing_from_report": 1,
                    "publisher_verified_date_source_urls": ["https://publisher.example/article"],
                    "publisher_conflicting_verified_date_dois": ["10.1007/conflict"],
                    "publisher_report_comparison_available": True,
                    "publisher_article_dates_with_https_source": 3,
                    "publisher_conflicting_verified_date_count": 1,
                    "publisher_report_online_date_conflict_count": 2,
                    "confirmed_month_missing_without_https_source_dois": ["10.1007/missing"]}]}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        row = next(row for row in result["journals"] if row["journal"] == journal)
        self.assertEqual(row["publisher_confirmed_month_missing_dois"], ["10.1007/missing"])
        self.assertEqual(row["publisher_confirmed_month_missing_count"], 1)
        self.assertEqual(row["publisher_verified_date_source_urls"], ["https://publisher.example/article"])
        self.assertEqual(row["publisher_conflicting_verified_date_dois"], ["10.1007/conflict"])
        self.assertTrue(row["publisher_report_comparison_available"])
        self.assertEqual(row["publisher_online_dates_with_https_source"], 3)
        self.assertEqual(row["publisher_online_date_conflicts"], 1)
        self.assertEqual(row["publisher_report_date_conflicts"], 2)
        self.assertEqual(row["publisher_missing_without_https_source_dois"], ["10.1007/missing"])
        self.assertFalse(result["independently_complete"])

    def test_inconsistent_publisher_gap_count_is_rejected(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        def fake_load(path):
            if path.name == "2026-10-coverage.json":
                return {"journals": [{"journal": journal,
                    "confirmed_month_missing_dois": ["10.1007/missing"],
                    "confirmed_month_missing_from_report": 2}]}
            return {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            with self.assertRaisesRegex(AssertionError, "Inconsistent publisher-confirmed gap ledger"):
                report_provenance.make("2026-10")

    def test_only_month_matching_dated_articles_are_counted(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        articles = [
            {"journal": journal, "online_date": "2026-10-03", "date_basis": "crossref_online"},
            {"journal": journal, "online_date": "2026-10-04", "date_basis": "publisher_online", "publisher_date_source": "https://publisher.example/article"},
            {"journal": journal, "online_date": "2026-09-30", "date_basis": "publisher_online"},
            {"journal": journal, "online_date": "2026-10-05", "date_basis": "print"},
            {"journal": journal, "online_date": "2026-10-99", "date_basis": "crossref_online"},
            {"journal": journal, "online_date": "2026-10", "date_basis": "publisher_online"},
            {"journal": journal, "online_date": "", "date_basis": "crossref_online"},
        ]
        def fake_load(path):
            return {"articles": articles} if path.parent.name == "months" else {}
        with patch.object(report_provenance, "load", side_effect=fake_load):
            result = report_provenance.make("2026-10")
        row = next(row for row in result["journals"] if row["journal"] == journal)
        self.assertEqual(row["included_articles"], 2)
        self.assertEqual(row["included_with_publisher_evidence"], 1)
        self.assertEqual(row["crossref_api_source"], "https://api.crossref.org/works")
        self.assertEqual(row["publisher_article_evidence_urls"], ["https://publisher.example/article"])
        self.assertFalse(row["independently_exhaustive"])


if __name__ == "__main__":
    unittest.main()
