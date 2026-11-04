"""Offline regression tests for the on-demand HTML reader and evidence preservation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import export_neuerscheinungen, prepare_simple_report, backfill, audit_missing_journals, recover_publisher_online_dates

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for folder in ("months","quality","coverage"):
            (self.root/"data"/folder).mkdir(parents=True)
        self.month="2026-10"
        self.articles=[
            {"journal":"Journal A","title":"Confirmed <online>","doi":"10.1234/one","online_date":"2026-10-09","date_basis":"crossref_online"},
            {"journal":"Journal A","title":"Unconfirmed candidate","doi":"10.1234/two","date_basis":"crossref_published_unverified"},
            {"journal":"Journal B","title":"Wrong month","doi":"10.1234/three","online_date":"2026-09-30","date_basis":"crossref_online"},
            {"journal":"Journal A","title":"Publisher verified","doi":"10.1234/publisher","online_date":"2026-10-12","date_basis":"publisher_online","publisher_date_source":"https://example.org/publisher"},
            {"journal":"Journal B","title":"Malformed date","doi":"10.1234/four","online_date":"2026-10-99","date_basis":"crossref_online"}]
        self.write("months",{"month":self.month,"count":len(self.articles),"articles":self.articles})
        self.write("quality",{"publication_ready":False,"release_status":"review_required"})
        self.write("coverage",{"journals_expected":24,"journals_queried":24})
    def write(self,folder,obj):
        (self.root/"data"/folder/(self.month+".json")).write_text(json.dumps(obj))
    def test_only_explicit_month_matching_online_dates(self):
        with patch.object(export_neuerscheinungen,"ROOT",self.root):
            target=export_neuerscheinungen.export(self.month,self.root/"out")
        page=target.read_text()
        self.assertIn("Confirmed &lt;online&gt;",page)
        for excluded in ("Unconfirmed candidate","Wrong month","Malformed date",
                         "Rechercheentwurf:","Artikel oder Zeitschrift suchen"):
            self.assertNotIn(excluded,page)
        self.assertIn("2 Artikel mit ausgewiesenem Online-Veröffentlichungsdatum",page)
        self.assertIn("Publisher verified",page)
    def test_publisher_verified_date_survives_crossref_backfill(self):
        previous={"online_date":"2026-10-02","publisher_online_verified":True,"published_date":"2026-10-09"}
        result=backfill.preserve_known_dates(previous,"2026-10-09","2026-10-09",None)
        self.assertEqual(result["online_date"],"2026-10-02")
        self.assertEqual(result["published_date"],"2026-10-09")
    def test_missing_journal_query_blocks_export(self):
        self.write("coverage",{"journals_expected":24,"journals_queried":23})
        with patch.object(export_neuerscheinungen,"ROOT",self.root):
            with self.assertRaises(ValueError):
                export_neuerscheinungen.export(self.month,self.root/"out")
    def test_preparation_does_not_erase_review_or_publisher_evidence(self):
        quality_path=self.root/"data/quality"/(self.month+".json")
        coverage_path=self.root/"data/coverage"/(self.month+".json")
        old_quality=quality_path.read_bytes()
        old_coverage=coverage_path.read_bytes()
        (self.root/"data"/f"backfill-{self.month}.json").write_text(json.dumps({"checked":24,"errors":{}}))
        with patch.object(prepare_simple_report,"ROOT",self.root):
            prepare_simple_report.prepare(self.month)
        self.assertEqual(quality_path.read_bytes(),old_quality)
        self.assertEqual(coverage_path.read_bytes(),old_coverage)
    def test_missing_journals_are_not_silently_declared_inactive(self):
        with patch.object(audit_missing_journals,"ROOT",self.root):
            result=audit_missing_journals.audit(self.month)
        self.assertEqual(result["journals_expected"],24)
        self.assertEqual(result["journals_absent_from_html"],24)
        self.assertEqual(len(result["missing_journals"]),24)
        self.assertTrue(all("not_proof_of_inactivity" in j["status"] for j in result["missing_journals"]))

    def test_publisher_recovery_rejects_conflicting_online_dates(self):
        article={"doi":"10.1234/example"}
        with patch.object(recover_publisher_online_dates,"get_publisher",return_value=(
                "https://publisher.example/article",[
                    ("citation_online_date","2026-10-03"),
                    ("citation_online_date","2026-10-04")])):
            doi,record=recover_publisher_online_dates.inspect(article)
        self.assertEqual(doi,"10.1234/example")
        self.assertEqual(record["status"],"conflicting_online_dates")

    def test_publisher_recovery_rejects_generic_publication_date(self):
        with patch.object(recover_publisher_online_dates,"get_publisher",return_value=(
                "https://publisher.example/article",[
                    ("citation_publication_date","2026-10-03")])):
            _,record=recover_publisher_online_dates.inspect({"doi":"10.1234/example"})
        self.assertEqual(record["status"],"no_explicit_online_date")
if __name__=="__main__":
    unittest.main()
