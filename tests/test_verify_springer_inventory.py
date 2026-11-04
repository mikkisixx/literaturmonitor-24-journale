import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import verify_springer_inventory as v

DOI = "10.1007/s00784-026-07203-0"
def html(date="2026-10-17", doi=DOI):
    return f'<meta name="citation_doi" content="{doi}"><meta name="citation_online_date" content="{date}">'

class PublisherDates(unittest.TestCase):
    def test_verified_online_date(self):
        self.assertEqual(v.publisher_online_date(html(), DOI), ("2026-10-17", "publisher_online_date_verified"))
    def test_doi_mismatch_fails_closed(self):
        self.assertIsNone(v.publisher_online_date(html(doi="10.1007/other"), DOI)[0])
    def test_publication_date_not_substituted(self):
        self.assertIsNone(v.publisher_online_date('<meta name="citation_doi" content="'+DOI+'"><meta name="citation_publication_date" content="2026-10-17">', DOI)[0])
    def test_month_and_missing_report(self):
        inv = {"journals": {"Clinical Oral Investigations": {"candidate_dois": [DOI]}}}
        result = v.verify("2026-10", inv, set(), lambda url: html())
        self.assertEqual(len(result["verified_month_missing_from_report"]), 1)
        self.assertFalse(result["coverage_complete"])
    def test_bad_date_fails_closed(self):
        self.assertIsNone(v.publisher_online_date(html(date="2026-02-31"), DOI)[0])

if __name__ == "__main__":
    unittest.main()
