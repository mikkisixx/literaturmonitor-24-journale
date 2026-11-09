import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from verify_discovered_candidates import audit, check_candidate


class IndependentPublisherAuditTests(unittest.TestCase):
    def test_explicit_online_date_only(self):
        def fetch(_):
            return "https://publisher.example/article", [("citation_publication_date", "2026-08-03")]
        self.assertEqual(check_candidate("10.1000/example", "2026-08", fetch)["status"],
                         "no_explicit_online_date")

    def test_conflicting_dates_rejected(self):
        def fetch(_):
            return "https://publisher.example/article", [
                ("citation_online_date", "2026-08-03"),
                ("citation_date_online", "2026-09-03")]
        self.assertEqual(check_candidate("10.1000/example", "2026-08", fetch)["status"],
                         "conflicting_online_dates")

    def test_missing_from_report_is_reported_not_inserted(self):
        inventory = {"journals": {"Example": {"status": "page_limit_reached",
            "candidate_dois": ["10.1000/A", "10.1000/B"], "pages": [{"url": "https://example.org"}]}}}
        report = {"articles": [{"doi": "10.1000/a"}]}
        def checker(doi, month):
            return {"doi": doi, "status": "verified_in_month", "online_date": "2026-08-01"}
        result = audit("2026-08", inventory, report, workers=1, checker=checker)
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["journals"]["Example"]["verified_missing_from_report"], 1)
        self.assertEqual(len(report["articles"]), 1)
        self.assertEqual(len(result["records"]), 2)


if __name__ == "__main__":
    unittest.main()
