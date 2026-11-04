import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import discover_springer as ds

class SpringerInventoryTests(unittest.TestCase):
    def test_only_article_links_and_correct_journal(self):
        html = '<a href="/article/10.1007/s00784-2026-07203-0">A</a><a href="/article/10.1007/s10856-2026-07117-z">B</a><p>10.1007/s00784-2026-99999-0</p>'
        self.assertEqual(ds.parse_dois(html, "Clinical Oral Investigations"), ["10.1007/s00784-2026-07203-0"])
    def test_bounded_listing_never_claims_complete(self):
        def fetch(url):
            return '<a href="/article/10.1007/s00784-2026-07203-0">A</a>' if "/784/" in url else '<a href="/article/10.1007/s10856-2026-07117-z">B</a>'
        result = ds.discover("2026-10", pages=1, fetch=fetch)
        self.assertFalse(result["coverage_complete"])
        for entry in result["journals"].values():
            self.assertEqual(entry["status"], "page_limit_reached")
            self.assertFalse(entry["online_first_month_verified"])
    def test_fetch_errors_remain_visible(self):
        def fetch(url):
            raise RuntimeError("publisher blocked")
        result = ds.discover("2026-10", fetch=fetch)
        self.assertTrue(all(e["status"] == "fetch_error" for e in result["journals"].values()))
        self.assertTrue(all(e["error"] for e in result["journals"].values()))

if __name__ == "__main__":
    unittest.main()
