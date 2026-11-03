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

    def test_title_fallback_fails_closed_on_unbounded_crossref_results(self):
        # A broad fuzzy title search can produce an arbitrarily long result set.
        # Do not silently accept a truncated subset as the journal inventory.
        records=[{"DOI":f"10.1234/{i}","container-title":["Unrelated Journal"]} for i in range(200)]
        calls={"count":0}
        def page(_url):
            calls["count"]+=1
            return {"items":records,"next-cursor":f"page-{calls['count']}"}
        with patch.object(backfill.collect,"get",side_effect=page), patch.object(backfill.time,"sleep"):
            with self.assertRaisesRegex(RuntimeError,"incomplete results"):
                list(backfill.fetch_title_pages("Clinical Oral Investigations","2026-10-01","2026-10-31","online"))
        self.assertEqual(calls["count"],10)


    def test_failed_journal_does_not_commit_partial_discoveries(self):
        import json
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            data=pathlib.Path(tmp)
            (data/"observed.json").write_text("{}")
            def pages(issn, *_):
                yield {"DOI":"10.1234/partial","title":["Partial"],"container-title":["Journal A"]}
                raise RuntimeError("page failed")
            with patch.object(backfill,"DATA",data), \
                 patch.object(backfill.collect,"JOURNALS",{"group":["Journal A"]}), \
                 patch.object(backfill.collect,"resolve",return_value="1234-5678"), \
                 patch.object(backfill,"journal_issns",return_value=["1234-5678"]), \
                 patch.object(backfill,"fetch_pages",side_effect=pages), \
                 patch.object(sys,"argv",["backfill.py","--month","2026-10"]):
                backfill.main()
            self.assertEqual(json.loads((data/"observed.json").read_text()),{})
            result=json.loads((data/"backfill-2026-10.json").read_text())
            self.assertEqual(result["checked"],0)
            self.assertIn("Journal A",result["errors"])

if __name__ == "__main__":
    unittest.main()
