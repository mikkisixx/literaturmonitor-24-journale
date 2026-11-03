"""Regression tests for print/electronic ISSN expansion."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import backfill


class JournalIssnTests(unittest.TestCase):
    def test_uses_both_issns_and_deduplicates(self):
        with patch.object(backfill.collect, "get", return_value={"ISSN": ["1234-5678", "9876-5432", "1234-5678"]}):
            self.assertEqual(backfill.journal_issns("1234-5678"), ["1234-5678", "9876-5432"])

    def test_falls_back_if_crossref_journal_lookup_fails(self):
        with patch.object(backfill.collect, "get", side_effect=TimeoutError("unavailable")):
            self.assertEqual(backfill.journal_issns("1234-5678"), ["1234-5678"])

    def test_empty_metadata_preserves_primary(self):
        with patch.object(backfill.collect, "get", return_value={}):
            self.assertEqual(backfill.journal_issns("1234-5678"), ["1234-5678"])


    def test_title_fallback_rejects_similarly_named_journals(self):
        records=[
            {"DOI":"10.1/exact","container-title":["Clinical Oral Investigations"]},
            {"DOI":"10.1/wrong","container-title":["Clinical Oral Investigations Reports"]},
            {"DOI":"10.1/other","container-title":["Unrelated Journal"]},
        ]
        with patch.object(backfill.collect,"get",return_value={"items":records}):
            found=list(backfill.fetch_title_pages("Clinical Oral Investigations","2026-10-01","2026-10-31","online"))
        self.assertEqual([x["DOI"] for x in found],["10.1/exact"])

    def test_title_fallback_accepts_known_alias(self):
        with patch.object(backfill.collect,"get",return_value={"items":[
            {"DOI":"10.1/alias","container-title":["Journal of Esthetic and Restorative Dentistry"]}
        ]}):
            found=list(backfill.fetch_title_pages("The Journal of Esthetic and Restorative Dentistry","2026-10-01","2026-10-31","online"))
        self.assertEqual(len(found),1)

if __name__ == "__main__":
    unittest.main()
