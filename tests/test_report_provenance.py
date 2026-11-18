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

    def test_only_month_matching_dated_articles_are_counted(self):
        journal = next(iter(next(iter(report_provenance.collect.JOURNALS.values()))))
        articles = [
            {"journal": journal, "online_date": "2026-10-03", "date_basis": "crossref_online"},
            {"journal": journal, "online_date": "2026-10-04", "date_basis": "publisher_online", "publisher_date_source": "https://publisher.example/article"},
            {"journal": journal, "online_date": "2026-09-30", "date_basis": "publisher_online"},
            {"journal": journal, "online_date": "2026-10-05", "date_basis": "print"},
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
