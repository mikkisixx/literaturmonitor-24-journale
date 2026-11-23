import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import audit_publisher_inventory as audit

class AllJournalPublisherAuditTests(unittest.TestCase):
    def test_only_canonical_calendar_dates_are_valid_evidence(self):
        self.assertTrue(audit.is_valid_iso_date("2026-10-26"))
        self.assertTrue(audit.is_valid_month_date("2026-10-26", "2026-10"))
        for invalid in ("2026-W44-1", "20261026", "2026-10-32", "2026-10-1", "2026-10-26T00:00:00"):
            self.assertFalse(audit.is_valid_iso_date(invalid))
            self.assertFalse(audit.is_valid_month_date(invalid, "2026-10"))

    def test_iso_week_date_cannot_create_a_confirmed_missing_doi(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/weekdate",
            "status": "publisher_online_date_verified", "online_date": "2026-W44-1",
            "source": "https://link.springer.com/article/weekdate"}]}
        row = next(r for r in audit.build("2026-10", verification=verification,
                                          monthly_report={"articles": []})["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(row["publisher_article_dates_verified"], 0)

    def test_undated_candidate_does_not_hide_verified_publisher_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/candidate",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15",
            "source": "https://link.springer.com/article/candidate"}]}
        report = {"articles": [{"journal": "Clinical Oral Investigations",
                                "doi": "10.1007/candidate", "date_basis": "candidate"}]}
        row = next(r for r in audit.build("2026-10", verification=verification,
                                          monthly_report=report)["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/candidate"])

    def test_missing_month_dois_without_auditable_source_are_disclosed(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/sourced",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://link.springer.com/article/sourced"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/unsourced",
             "status": "publisher_online_date_verified", "online_date": "2026-10-16",
             "source": "https://"}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"],
                         ["10.1007/sourced", "10.1007/unsourced"])
        self.assertEqual(row["confirmed_month_missing_without_https_source_dois"],
                         ["10.1007/unsourced"])

    def test_malformed_https_evidence_is_not_counted_as_source(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/valid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://link.springer.com/article/valid"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/bad",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/credentials",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://user:pass@link.springer.com/article/credentials"}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_with_https_source"], 1)
        self.assertEqual(row["publisher_verified_date_source_urls"],
                         ["https://link.springer.com/article/valid"])

    def test_backslash_in_publisher_url_is_not_a_valid_source(self):
        self.assertFalse(audit.valid_https_source("https://publisher.example\\@other.example/article"))
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/backslash",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15",
            "source": "https://publisher.example\\@other.example/article"}]}
        row = next(r for r in audit.build("2026-10", verification=verification,
                                          monthly_report={"articles": []})["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_with_https_source"], 0)
        self.assertEqual(row["confirmed_month_missing_without_https_source_dois"],
                         ["10.1007/backslash"])

    def test_conflicting_doi_sources_are_not_presented_as_verified_evidence(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/conflict",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "source": "https://link.springer.com/article/10.1007/conflict"},
            {"journal": "Dental Materials", "doi": "10.1007/CONFLICT",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "source": "https://www.sciencedirect.com/science/article/pii/conflict"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/valid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://link.springer.com/article/10.1007/valid"}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        rows = {row["journal"]: row for row in result["journals"]}
        self.assertEqual(rows["Clinical Oral Investigations"]["publisher_verified_date_source_urls"],
                         ["https://link.springer.com/article/10.1007/valid"])
        self.assertEqual(rows["Dental Materials"]["publisher_verified_date_source_urls"], [])
        self.assertEqual(rows["Clinical Oral Investigations"]["confirmed_month_missing_dois"],
                         ["10.1007/valid"])

    def test_conflicting_dates_are_disclosed_per_journal_not_silently_ignored(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/CONFLICT",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "doi:10.1007/conflict",
             "status": "publisher_online_date_verified", "online_date": "2026-10-13",
             "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification, monthly_report={"articles": []})
        rows = {row["journal"]: row for row in result["journals"]}
        row = rows["Clinical Oral Investigations"]
        self.assertEqual(row["publisher_conflicting_verified_date_dois"], ["10.1007/conflict"])
        self.assertEqual(row["publisher_conflicting_verified_date_count"], 1)
        self.assertEqual(row["publisher_article_dates_verified"], 2)
        self.assertEqual(row["publisher_article_dates_verified_unambiguous"], 0)
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(rows["Dental Materials"]["publisher_conflicting_verified_date_count"], 0)
        self.assertFalse(result["complete"])

    def test_conflicting_dates_across_journal_assignments_are_not_confirmed(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/shared",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Dental Materials", "doi": "doi:10.1007/SHARED",
             "status": "publisher_online_date_verified", "online_date": "2026-10-13",
             "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        rows = {row["journal"]: row for row in result["journals"]}
        for name in ("Clinical Oral Investigations", "Dental Materials"):
            self.assertEqual(rows[name]["publisher_conflicting_verified_date_dois"],
                             ["10.1007/shared"])
            self.assertEqual(rows[name]["publisher_article_dates_verified_unambiguous"], 0)
            self.assertEqual(rows[name]["confirmed_month_missing_dois"], [])

    def test_same_doi_same_date_but_different_journals_is_ambiguous(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/shared",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "in_monthly_report": False},
            {"journal": "Dental Materials", "doi": "doi:10.1007/SHARED",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        rows = {row["journal"]: row for row in result["journals"]}
        for name in ("Clinical Oral Investigations", "Dental Materials"):
            self.assertEqual(rows[name]["publisher_conflicting_verified_date_dois"],
                             ["10.1007/shared"])
            self.assertEqual(rows[name]["confirmed_month_missing_dois"], [])
            self.assertEqual(rows[name]["publisher_article_dates_verified_unambiguous"], 0)

    def test_all_24_journals_have_platform_and_explicit_unverified_status(self):
        result = audit.build("2026-10")
        self.assertEqual(result["journal_count"], 24)
        self.assertEqual(len({r["journal"] for r in result["journals"]}), 24)
        self.assertFalse(result["complete"])
        self.assertTrue(all(r["publisher_platform"] != "unmapped" for r in result["journals"]))
        self.assertTrue(all(not r["publisher_coverage_verified"] for r in result["journals"]))
    def test_partial_listing_never_promoted_to_complete(self):
        inventory = {"journals": {"Clinical Oral Investigations": {"status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        verification = {"records": [{"journal": "Clinical Oral Investigations", "status": "publisher_online_date_verified", "online_date": "2026-10-15",
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
             "status": "publisher_online_date_verified", "online_date": "2026-10-15", "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/example",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15", "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/outside",
             "status": "publisher_online_date_verified", "online_date": "2026-09-15", "in_requested_month": False, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/unverified",
             "status": "unverified", "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", inventory, verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/example"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_verified_month_date_overrides_stale_false_month_flag(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/stale-month",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15",
            "in_requested_month": False, "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/stale-month"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)

    def test_stale_verification_gap_is_cleared_when_report_now_contains_doi(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached", "candidate_dois": ["10.1007/example"]}}}
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/EXAMPLE",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15", "in_requested_month": True,
            "in_monthly_report": False}]}
        report = {"articles": [{"journal": "Clinical Oral Investigations",
                               "doi": "10.1007/example", "date_basis": "publisher_online", "online_date": "2026-10-15"}]}
        result = audit.build("2026-10", inventory, verification, report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(row["confirmed_month_missing_from_report"], 0)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_reported_doi_with_conflicting_online_date_remains_a_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/date-mismatch",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15",
            "source": "https://link.springer.com/article/date-mismatch"}]}
        report = {"articles": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/date-mismatch",
            "date_basis": "crossref_online", "online_date": "2026-10-16"}]}
        row = next(r for r in audit.build("2026-10", verification=verification,
                                          monthly_report=report)["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(row["publisher_report_online_date_conflict_dois"], ["10.1007/date-mismatch"])
        self.assertEqual(row["publisher_report_online_date_conflict_count"], 1)

    def test_stale_snapshot_present_flag_does_not_hide_current_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/example",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15", "in_requested_month": True,
            "in_monthly_report": True}]}
        report = {"articles": []}
        result = audit.build("2026-10", verification=verification, monthly_report=report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/example"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)

    def test_publisher_url_doi_matches_bare_report_doi(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached",
            "candidate_dois": ["https://doi.org/10.1007/EXAMPLE", "doi:10.1007/example"]}}}
        verification = {"records": [{
            "journal": "Clinical Oral Investigations",
            "doi": "https://dx.doi.org/10.1007/EXAMPLE",
            "status": "publisher_online_date_verified", "online_date": "2026-10-15",
            "in_requested_month": True,
            "in_monthly_report": False}]}
        report = {"articles": [{"journal": "Clinical Oral Investigations",
                               "doi": "10.1007/example", "date_basis": "publisher_online", "online_date": "2026-10-15"}]}
        result = audit.build("2026-10", inventory, verification, report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_candidate_count"], 1)
        self.assertEqual(row["publisher_candidates_absent_count"], 0)
        self.assertEqual(row["confirmed_month_missing_dois"], [])

    def test_empty_normalized_doi_is_not_a_candidate_or_confirmed_gap(self):
        inventory = {"journals": {"Clinical Oral Investigations": {
            "status": "page_limit_reached",
            "candidate_dois": ["doi:", "https://doi.org/", "10.1007/real"]}}}
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "doi:",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", inventory, verification, {"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_candidate_count"], 1)
        self.assertEqual(row["publisher_candidates_not_found_anywhere"], ["10.1007/real"])
        self.assertEqual(row["confirmed_month_missing_dois"], [])

    def test_verified_doi_under_wrong_journal_remains_confirmed_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations",
            "doi": "10.1007/misattributed",
            "status": "publisher_online_date_verified",
            "online_date": "2026-10-15",
            "in_monthly_report": True}]}
        report = {"articles": [{
            "journal": "Dental Materials", "doi": "10.1007/misattributed"}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report=report)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"],
                         ["10.1007/misattributed"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_missing_online_date_is_not_verified_gap(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations", "doi": "10.1007/undated",
            "status": "publisher_online_date_verified", "in_requested_month": True,
            "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])

    def test_invalid_calendar_date_cannot_be_confirmed_gap(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/invalid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-99",
             "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/valid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-31",
             "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification, monthly_report={"articles": []})
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/valid"])

    def test_verified_date_contradicting_month_flag_is_not_a_confirmed_gap(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/outside",
             "status": "publisher_online_date_verified", "online_date": "2026-09-30",
             "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/inside",
             "status": "publisher_online_date_verified", "online_date": "2026-10-01",
             "in_requested_month": True, "in_monthly_report": False}]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/inside"])
        self.assertEqual(row["confirmed_month_missing_from_report"], 1)

    def test_verified_date_count_excludes_missing_and_impossible_calendar_dates(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "status": "publisher_online_date_verified",
             "doi": "10.1007/valid", "online_date": "2026-09-30"},
            {"journal": "Clinical Oral Investigations", "status": "publisher_online_date_verified",
             "doi": "10.1007/invalid", "online_date": "2026-02-30"},
            {"journal": "Clinical Oral Investigations", "status": "publisher_online_date_verified",
             "doi": "10.1007/missing"},
            {"journal": "Clinical Oral Investigations", "status": "unverified",
             "doi": "10.1007/unchecked", "online_date": "2026-10-15"}]}
        result = audit.build("2026-10", verification=verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_checked"], 4)
        self.assertEqual(row["publisher_article_dates_verified"], 1)
        self.assertFalse(row["publisher_coverage_verified"])

    def test_actual_springer_verifier_date_field_counts_verified_missing(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations",
            "doi": "10.1007/springer-verified",
            "status": "publisher_online_date_verified",
            "publisher_online_date": "2026-10-12",
            "in_requested_month": True,
            "in_monthly_report": False,
            "source": "https://link.springer.com/article/10.1007/springer-verified",
        }]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_verified"], 1)
        self.assertEqual(row["confirmed_month_missing_dois"], ["10.1007/springer-verified"])

    def test_conflicting_publisher_date_aliases_are_not_verified(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations",
            "doi": "10.1007/conflict",
            "status": "publisher_online_date_verified",
            "online_date": "2026-10-12",
            "publisher_online_date": "2026-09-12",
            "in_requested_month": True,
            "in_monthly_report": False,
        }]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_verified"], 0)
        self.assertEqual(row["confirmed_month_missing_dois"], [])

    def test_conflicting_verified_dates_for_same_doi_are_not_confirmed_gaps(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/conflict",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "in_requested_month": True, "in_monthly_report": False},
            {"journal": "Clinical Oral Investigations", "doi": "doi:10.1007/CONFLICT",
             "status": "publisher_online_date_verified", "online_date": "2026-09-30",
             "in_requested_month": False, "in_monthly_report": False},
        ]}
        result = audit.build("2026-10", verification=verification,
                             monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["confirmed_month_missing_dois"], [])
        self.assertEqual(row["confirmed_month_missing_from_report"], 0)

    def test_verified_publisher_date_sources_are_auditable_per_journal(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/one",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "source": "https://link.springer.com/article/10.1007/one"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/two",
             "status": "publisher_online_date_verified", "online_date": "2026-10-13",
             "source": "https://link.springer.com/article/10.1007/one"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/invalid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-99",
             "source": "https://link.springer.com/article/10.1007/invalid"},
            {"journal": "Dental Materials", "doi": "10.1016/example",
             "status": "unverified", "source": "https://example.org/not-verified"},
        ]}
        result = audit.build("2026-10", verification=verification)
        rows = {r["journal"]: r for r in result["journals"]}
        self.assertEqual(rows["Clinical Oral Investigations"]["publisher_verified_date_source_urls"],
                         ["https://link.springer.com/article/10.1007/one"])
        self.assertEqual(rows["Dental Materials"]["publisher_verified_date_source_urls"], [])

    def test_insecure_publisher_source_is_not_advertised_as_verified_link(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/insecure",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "source": "http://link.springer.com/article/10.1007/insecure"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/secure",
             "status": "publisher_online_date_verified", "online_date": "2026-10-13",
             "source": "https://link.springer.com/article/10.1007/secure"},
        ]}
        result = audit.build("2026-10", verification=verification)
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_verified_date_source_urls"],
                         ["https://link.springer.com/article/10.1007/secure"])

    def test_https_provenance_count_excludes_unsourced_and_conflicted_dates(self):
        verification = {"records": [
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/valid",
             "status": "publisher_online_date_verified", "online_date": "2026-10-12",
             "source": "https://link.springer.com/article/valid"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/unsourced",
             "status": "publisher_online_date_verified", "online_date": "2026-10-13"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/insecure",
             "status": "publisher_online_date_verified", "online_date": "2026-10-14",
             "source": "http://link.springer.com/article/insecure"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/conflict",
             "status": "publisher_online_date_verified", "online_date": "2026-10-15",
             "source": "https://link.springer.com/article/conflict"},
            {"journal": "Clinical Oral Investigations", "doi": "10.1007/conflict",
             "status": "publisher_online_date_verified", "online_date": "2026-10-16",
             "source": "https://link.springer.com/article/conflict"},
        ]}
        result = audit.build("2026-10", verification=verification)
        row = next(r for r in result["journals"] if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_verified"], 5)
        self.assertEqual(row["publisher_article_dates_verified_unambiguous"], 3)
        self.assertEqual(row["publisher_article_dates_with_https_source"], 1)

    def test_verified_date_without_doi_is_not_counted_or_sourced(self):
        verification = {"records": [{
            "journal": "Clinical Oral Investigations",
            "doi": "doi:",
            "status": "publisher_online_date_verified",
            "online_date": "2026-10-12",
            "source": "https://link.springer.com/article/unidentified",
        }]}
        result = audit.build("2026-10", verification=verification, monthly_report={"articles": []})
        row = next(r for r in result["journals"]
                   if r["journal"] == "Clinical Oral Investigations")
        self.assertEqual(row["publisher_article_dates_checked"], 1)
        self.assertEqual(row["publisher_article_dates_verified"], 0)
        self.assertEqual(row["publisher_article_dates_verified_unambiguous"], 0)
        self.assertEqual(row["publisher_verified_date_source_urls"], [])
        self.assertEqual(row["confirmed_month_missing_dois"], [])

if __name__ == "__main__":
    unittest.main()
