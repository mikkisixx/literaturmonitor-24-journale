"""Offline regression checks for the single-file reader HTML export."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import export_html

class HtmlExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for part in ("data/months","data/quality","data/coverage"):
            (self.root/part).mkdir(parents=True,exist_ok=True)
        self.month="2026-10"
        self.report={"month":self.month,"count":1,"verified_online_count":0,"candidate_count":1,
                     "articles":[{"journal":"Journal <A>","title":"Unsafe <script>alert(1)</script>","doi":"10.1234/test",
                                  "date_basis":"crossref_published_unverified","display_date":"2026-10"}]}
        self.quality={"month":self.month,"publication_ready":False,"release_status":"review_required"}
        self.coverage={"month":self.month,"journals_expected":24,"journals_queried":24,"query_errors":0,"confirmed_missing_publisher_articles":0,"journals_independently_verified":0,"missing_publisher_articles":[], "journals":[{"journal":"Journal <A>" if i == 0 else f"Journal {i+1}", "publisher_platform":"Example Publisher", "publisher_listing_status":"not_implemented", "publisher_coverage_verified":False} for i in range(24)]}
        self.save()
    def save(self):
        for folder,obj in (("months",self.report),("quality",self.quality),("coverage",self.coverage)):
            (self.root/"data"/folder/(self.month+".json")).write_text(json.dumps(obj),encoding="utf-8")
    def test_standalone_html_and_escaping(self):
        with patch.object(export_html,"ROOT",self.root):
            export_html.export(self.month,self.root/"out")
        paths=list((self.root/"out").iterdir())
        self.assertEqual(len(paths),1)
        self.assertEqual(paths[0].suffix,".html")
        html=paths[0].read_text()
        self.assertIn("<!doctype html>",html)
        self.assertIn("Die unabhängige Vollständigkeit aller 24 Zeitschriften ist nicht nachgewiesen",html)
        self.assertNotIn("Unsafe &lt;script&gt;",html)
        self.assertNotIn("Unsafe <script>",html)
        self.assertNotIn("https://doi.org/10.1234/test",html)
        self.assertNotIn("Rechercheentwurf",html)
        self.assertNotIn("<input",html)
        self.assertIn("Quellen- und Vollständigkeitsprüfung aller 24 Zeitschriften",html)
        self.assertIn("Journal &lt;A&gt;",html)
        self.assertEqual(html.count("<tr>"),25)
    def test_only_verified_online_dates_in_selected_month_are_exported(self):
        self.report={"month":self.month,"count":3,"verified_online_count":1,"candidate_count":2,
                     "articles":[
                         {"journal":"Journal <A>","title":"Included online","doi":"10.1234/included",
                          "date_basis":"publisher_online","online_date":"2026-10-12"},
                         {"journal":"Journal <A>","title":"Wrong month","doi":"10.1234/wrong-month",
                          "date_basis":"crossref_online","online_date":"2026-09-30"},
                         {"journal":"Journal <A>","title":"Unverified","doi":"10.1234/unverified",
                          "date_basis":"crossref_published_unverified","online_date":"2026-10-15"}]}
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            export_html.export(self.month,self.root/"out")
        html=(self.root/"out"/"Literaturbericht-2026-10.html").read_text()
        self.assertIn("10.1234/included",html)
        self.assertNotIn("10.1234/wrong-month",html)
        self.assertNotIn("10.1234/unverified",html)

    def test_invalid_online_date_blocks_export(self):
        self.report={"month":self.month,"count":1,"verified_online_count":1,"candidate_count":0,
                     "articles":[{"journal":"Journal <A>","title":"Invalid date",
                                  "doi":"10.1234/invalid","date_basis":"publisher_online",
                                  "online_date":"2026-10-99"}]}
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaises(ValueError):
                export_html.export(self.month,self.root/"out")

    def test_duplicate_verified_doi_blocks_export(self):
        self.report={"month":self.month,"count":2,"verified_online_count":2,"candidate_count":0,
                     "articles":[{"journal":"Journal <A>","title":"First","doi":"10.1234/SAME",
                                  "date_basis":"publisher_online","online_date":"2026-10-12"},
                                 {"journal":"Journal <A>","title":"Duplicate","doi":"10.1234/same",
                                  "date_basis":"crossref_online","online_date":"2026-10-13"}]}
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Duplicate verified DOI"):
                export_html.export(self.month,self.root/"out")

    def test_mismatched_month_blocks_export(self):
        self.coverage["month"]="2026-09"
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"months must match"):
                export_html.export(self.month,self.root/"out")

    def test_inconsistent_verified_count_blocks_export(self):
        self.report["verified_online_count"]=1
        self.report["candidate_count"]=0
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Verified online article count"):
                export_html.export(self.month,self.root/"out")

    def test_missing_journal_audit_blocks_export(self):
        self.coverage["journals"].pop()
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Expected 24 distinct journal audit records"):
                export_html.export(self.month,self.root/"out")
    def test_missing_journal_query_blocks_export(self):
        self.coverage["journals_queried"]=23
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Incomplete journal queries"):
                export_html.export(self.month,self.root/"out")
    def test_inconsistent_publisher_evidence_blocks_export(self):
        self.coverage["confirmed_missing_publisher_articles"]=1
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Publisher gap evidence inconsistent"):
                export_html.export(self.month,self.root/"out")
    def test_inconsistent_publisher_date_conflicts_block_export(self):
        self.coverage["publisher_date_conflict_count"]=2
        self.coverage["publisher_date_conflicts"]=[{"doi":"10.1234/conflict"}]
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Publisher date conflict evidence inconsistent"):
                export_html.export(self.month,self.root/"out")

    def test_consistent_publisher_date_conflicts_are_disclosed(self):
        self.coverage["publisher_date_conflict_count"]=1
        self.coverage["publisher_date_conflicts"]=[{"doi":"10.1234/conflict"}]
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            export_html.export(self.month,self.root/"out")
        page=(self.root/"out"/"Literaturbericht-2026-10.html").read_text()
        self.assertIn("1 dokumentierte Datumsabweichungen",page)

    def test_unsafe_publisher_evidence_url_blocks_export(self):
        self.coverage["confirmed_missing_publisher_articles"]=1
        self.coverage["missing_publisher_articles"]=[{
            "journal":"Journal <A>", "publisher_online_date":"2026-10-12",
            "doi":"10.1234/missing", "source":"javascript:alert(1)"}]
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaisesRegex(ValueError,"Unsafe publisher evidence URL"):
                export_html.export(self.month,self.root/"out")

    def test_explicit_approval_never_auto_exported(self):
        self.quality={"month":self.month,"publication_ready":True,"release_status":"approved"}
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaises(ValueError):
                export_html.export(self.month,self.root/"out")
if __name__=="__main__":
    unittest.main()
