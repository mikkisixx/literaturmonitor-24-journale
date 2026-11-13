import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import audit_publisher_inventory as audit

class AllJournalPublisherAuditTests(unittest.TestCase):
    def test_all_24_journals_have_platform_and_explicit_unverified_status(self):
        result = audit.build("2026-10")
        self.assertEqual(result["journal_count"], 24)
        self.assertEqual(len({r["journal"] for r in result["journals"]}), 24)
        self.assertFalse(result["complete"])
        self.assertTrue(all(r["publisher_platform"] != "unmapped" for r in result["journals"]))
        self.assertTrue(all(not r["publisher_coverage_verified"] for r in result["journals"]))
    def test_partial_listing_never_promoted_to_complete(self):
        inventory = {"journals": {"Clinical Oral Investigations": {"status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        verification = {"records": [{"journal": "Clinical Oral Investigations", "status": "publisher_online_date_verified",
                                     "doi": "10.1007/example", "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", inventory, verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)
        self.assertFalse(row["publisher_coverage_verified"])
        self.assertEqual(row["publisher_candidate_count"], 1)

    def test_page_limit_is_reported_as_incomplete_pagination(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        result = audit.build("2026-10", inventory)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertIn("page limit", row["publisher_coverage_reason"])
        self.assertFalse(row["publisher_coverage_verified"])

    def test_listing_failures_and_sources_are_explicit(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "unparseable_or_empty_listing",
            "pages": [{"url": "https://link.springer.com/journal/784/articles?page=1", "doi_count": 0}],
            "candidate_dois": []}}}
        result = audit.build("2026-10", inventory)
        rows = {row["journal"]: row for row in result["journals"]}
        attempted = rows["Clinical Oral Investigations"]
        absent = rows["Dental Materials"]
        self.assertEqual(attempted["publisher_listing_urls"], ["https://link.springer.com/journal/784/articles?page=1"])
        self.assertIn("no DOI could be extracted", attempted["publisher_coverage_reason"])
        self.assertEqual(absent["publisher_listing_urls"], [])
        self.assertIn("No independent publisher listing attempted", absent["publisher_coverage_reason"])
        self.assertFalse(attempted["publisher_coverage_verified"])
        self.assertFalse(absent["publisher_coverage_verified"])


    def test_publisher_doi_assigned_to_wrong_journal_is_not_counted_as_covered(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached",
            "candidate_dois": ["10.1007/EXAMPLE", "10.1007/example", "10.1007/other"]}}}
        report = {"articles": [
            {"journal": "Dental Materials", "doi": "10.1007/example"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/other"}]}
        result = audit.build("2026-10", inventory, monthly_report=report)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_candidate_count"], 2)
        self.assertEqual(row["publisher_candidates_absent_from_monthly_report"], ["10.1007/example"])
        self.assertEqual(row["publisher_candidates_absent_count"], 1)
        self.assertEqual(row["publisher_candidates_present_under_other_journal"], ["10.1007/example"])
        self.assertEqual(row["publisher_candidates_not_found_anywhere"], [])
        self.assertEqual(row["publisher_candidates_not_found_anywhere_count"], 0)
        self.assertTrue(row["publisher_report_comparison_available"])
        self.assertFalse(row["publisher_coverage_verified"])

    def test_global_absence_distinguished_from_wrong_journal(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached",
            "candidate_dois": ["10.1007/absent", "10.1007/misplaced", "10.1007/present"]}}}
        report = {"articles": [
            {"journal": "Dental Materials", "doi": "10.1007/misplaced"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/present"}]}
        result = audit.build("2026-10", inventory, monthly_report=report)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_candidates_absent_from_monthly_report"],
                         ["10.1007/absent", "10.1007/misplaced"])
        self.assertEqual(row["publisher_candidates_not_found_anywhere"], ["10.1007/absent"])
        self.assertEqual(row["publisher_candidates_not_found_anywhere_count"], 1)
        self.assertEqual(row["publisher_candidates_present_under_other_journal"], ["10.1007/misplaced"])
        self.assertFalse(row["publisher_coverage_verified"])

    def test_missing_monthly_report_does_not_claim_zero_missing_dois(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        result = audit.build("2026-10", inventory)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertFalse(row["publisher_report_comparison_available"])
        self.assertEqual(row["publisher_candidate_count"], 1)
        self.assertEqual(row["publisher_candidates_not_found_anywhere"], [])
        self.assertFalse(row["publisher_coverage_verified"])

    def test_existing_empty_monthly_report_is_comparable(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        result = audit.build("2026-10", inventory, monthly_report={"articles": []})
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertTrue(row["publisher_report_comparison_available"])
        self.assertEqual(row["publisher_candidates_not_found_anywhere"], ["10.1007/example"])
        self.assertEqual(row["publisher_candidates_absent_count"], 1)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_verified_missing_doi_evidence_is_deduplicated(self):
        inventory = {"journals": {"Clinical Oral Investigations": {"status": "page_limit_reached"}}}
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/EXAMPLE",
             "status": "publisher_online_date_verified", "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/example",
             "status": "publisher_online_date_verified", "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/outside",
             "status": "publisher_online_date_verified", "in_requested_month": False, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/unverified",
             "status": "unverified", "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", inventory, verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/example"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_stale_verification_gap_is_cleared_when_report_now_contains_doi(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/EXAMPLE",
            "status": "publisher_online_date_verified", "in_requested_month": True,
            "in_monthly_report": False}]}
        report = {"articles": [{"journal": "Clinical Oral Investigations",
                               "doi": "10.1007/example"}]}
        result = audit.build("2026-10", inventory, verification, report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(row["confirmed_month_missing_from_report"], 0)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_stale_snapshot_present_flag_does_not_hide_current_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/example",
            "status": "publisher_online_date_verified", "in_requested_month": True,
            "in_monthly_report": True}]}
        report = {"articles": []}
        result = audit.build("2026-10", verification=verification, monthly_report=report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/example"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)

if __name__ == "__main__":
    unittest.main()
