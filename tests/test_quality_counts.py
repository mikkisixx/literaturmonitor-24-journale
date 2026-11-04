"""Regression tests for monthly corroboration counts."""
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from quality_counts import online_corroboration_counts

class OnlineCountTests(unittest.TestCase):
    def test_stale_and_candidate_checks_are_not_counted(self):
        articles=[
            {"doi":"10.1234/A","date_basis":"crossref_online"},
            {"doi":"10.1234/B","date_basis":"crossref_online"},
            {"doi":"10.1234/C","date_basis":"candidate"},
        ]
        checks={
            "10.1234/a":{"status":"publisher_date_match"},
            "10.1234/c":{"status":"publisher_date_match"},
            "10.1234/stale":{"status":"publisher_date_match"},
        }
        self.assertEqual(online_corroboration_counts(articles,checks),(1,1))
    def test_missing_and_conflicting_checks_remain_unverified(self):
        articles=[{"doi":"10.1/x","date_basis":"crossref_online"},
                  {"doi":"10.1/y","date_basis":"crossref_online"}]
        self.assertEqual(online_corroboration_counts(articles,{"10.1/x":{"status":"date_conflict"}}),(0,2))
    def test_no_online_articles(self):
        self.assertEqual(online_corroboration_counts([],{"old":{"status":"publisher_date_match"}}),(0,0))
if __name__=="__main__":unittest.main()
