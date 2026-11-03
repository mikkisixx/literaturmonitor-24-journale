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


if __name__ == "__main__":
    unittest.main()
