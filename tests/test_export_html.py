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
        self.quality={"publication_ready":False,"release_status":"review_required"}
        self.coverage={"journals_independently_verified":0,"missing_publisher_articles":[]}
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
        self.assertIn("NICHT REDAKTIONELL FREIGEGEBEN",html)
        self.assertIn("Unsafe &lt;script&gt;",html)
        self.assertNotIn("Unsafe <script>",html)
        self.assertIn("https://doi.org/10.1234/test",html)
    def test_explicit_approval_never_auto_exported(self):
        self.quality={"publication_ready":True,"release_status":"approved"}
        self.save()
        with patch.object(export_html,"ROOT",self.root):
            with self.assertRaises(ValueError):
                export_html.export(self.month,self.root/"out")
if __name__=="__main__":
    unittest.main()
