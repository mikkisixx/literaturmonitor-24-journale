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
                                     "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", inventory, verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)
        self.assertFalse(row["publisher_coverage_verified"])
        self.assertEqual(row["publisher_candidate_count"], 1)

if __name__ == "__main__":
    unittest.main()
