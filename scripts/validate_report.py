#!/usr/bin/env python3
"""Fail closed when a monthly report or its provenance is internally inconsistent."""
import datetime as dt
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit


def valid_https_source(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and not any(c.isspace() for c in value))
    except ValueError:
        return False

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def validate(month, data=DATA):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",month):
        raise ValueError("Invalid report month")
    report=json.loads((data/"months"/(month+".json")).read_text())
    quality=json.loads((data/"quality"/(month+".json")).read_text())
    coverage=json.loads((data/"coverage"/(month+".json")).read_text())
    articles=report["articles"]
    dois=[str(a["doi"]).strip().lower() for a in articles]
    assert all(dois) and len(dois)==len(set(dois)), "Missing or duplicate article DOI"
    assert report["count"]==len(articles), "Report count differs from article count"
    assert report["verified_online_count"]+report["candidate_count"]==len(articles), "Online/candidate totals inconsistent"
    # Validate each article, not only the aggregate verified/candidate totals.
    eligible_bases={"crossref_online","publisher_online"}
    eligible=[]
    candidates=[]
    for article in articles:
        basis=article.get("date_basis")
        online=article.get("online_date")
        if basis in eligible_bases:
            assert isinstance(online,str), "Verified article has no online date"
            parsed=dt.date.fromisoformat(online)
            assert parsed.strftime("%Y-%m")==month, "Verified article outside selected month"
            eligible.append(article)
        else:
            candidates.append(article)
    assert len(eligible)==report["verified_online_count"], "Verified article classification mismatch"
    assert len(candidates)==report["candidate_count"], "Candidate classification mismatch"
    reviews=quality["candidate_reviews"]
    statuses=quality["candidate_status_counts"]
    assert quality["candidate_count"]==len(reviews)==report["candidate_count"], "Candidate review count mismatch"
    assert sum(statuses.values())==len(reviews), "Candidate status totals inconsistent"
    assert set(statuses)=={r["status"] for r in reviews}, "Candidate status categories inconsistent"
    assert all(sum(r["status"]==status for r in reviews)==count for status,count in statuses.items()), "Candidate status counts differ from records"
    assert len({r["doi"].strip().lower() for r in reviews})==len(reviews), "Duplicate candidate reviews"
    candidate_dois={str(a["doi"]).strip().lower() for a in candidates}
    reviewed_dois={str(r["doi"]).strip().lower() for r in reviews}
    assert reviewed_dois==candidate_dois, "Candidate review DOIs do not match candidate article DOIs"
    assert quality["crossref_online_articles"]==report["verified_online_count"], "Crossref online count mismatch"
    assert quality["independently_corroborrated_online_dates"]+quality["online_dates_not_corroborrated"]==quality["crossref_online_articles"], "Online corroboration counts inconsistent"
    assert coverage["month"]==quality["month"]==report["month"]==month, "Month mismatch"
    assert coverage["journals_expected"]==24, "Expected 24 journals"
    assert len(coverage["journals"])==24, "Missing or duplicate journal audit rows"
    assert len({r["journal"] for r in coverage["journals"]})==24, "Duplicate journal coverage rows"
    assert coverage["journals_queried"]==24 and coverage["query_errors"]==0, "Crossref queries incomplete"
    assert coverage["zero_hit_journals"]==sum(r["crossref_query_count"]==0 for r in coverage["journals"]), "Zero-hit mismatch"
    assert coverage["confirmed_missing_publisher_articles"]==len(coverage["missing_publisher_articles"]), "Publisher evidence mismatch"
    truncated=coverage.get("title_fallback_truncated",[])
    assert isinstance(truncated,list) and len(truncated)==len(set(truncated)), "Duplicate title fallback truncation"
    known_rows={row["journal"]:row for row in coverage["journals"]}
    assert set(truncated)=={name for name,row in known_rows.items() if row.get("title_fallback_truncated") is True}, "Title fallback truncation summary differs from journal rows"
    for name in truncated:
        assert name in known_rows, "Unknown truncated journal"
        assert known_rows[name]["status"] in ("title_fallback_truncated_requires_publisher_check","confirmed_missing_publisher_articles"), "Truncated title search incorrectly marked complete"
    conflicts=coverage.get("publisher_date_conflicts",[])
    assert coverage.get("publisher_date_conflict_count",0)==len(conflicts), "Publisher date conflict count mismatch"
    assert len({str(c["doi"]).strip().lower() for c in conflicts})==len(conflicts), "Duplicate publisher date conflict"

    for item in coverage["missing_publisher_articles"]:
        assert item["doi"].lower() not in dois, "Publisher article already in monthly report"
        assert item["journal"] in {r["journal"] for r in coverage["journals"]}, "Unknown evidence journal"
        assert item["publisher_online_date"].startswith(month+"-"), "Publisher evidence outside report month"
        dt.date.fromisoformat(item["publisher_online_date"])
        assert valid_https_source(item.get("source")), "Publisher evidence has no valid HTTPS source"
    evidence_path=data/"publisher-evidence"/(month+".json")
    evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {"findings":[]}
    findings=evidence["findings"]
    assert evidence.get("month",month)==month, "Publisher evidence month mismatch"
    evidence_dois=[str(item["doi"]).strip().lower() for item in findings]
    assert len(evidence_dois)==len(set(evidence_dois)), "Duplicate publisher evidence DOI"
    # Evidence for an already indexed DOI must identify the same journal.
    # Otherwise a wrong publisher attribution could silently pass validation.
    article_journals={a["doi"].strip().lower():a["journal"] for a in articles}
    known_journals={r["journal"] for r in coverage["journals"]}
    for item in findings:
        doi=item["doi"].strip().lower()
        assert item["journal"] in known_journals, "Unknown publisher evidence journal"
        assert isinstance(item.get("publisher_online_date"), str), "Publisher evidence missing online date"
        assert dt.date.fromisoformat(item["publisher_online_date"]).strftime("%Y-%m")==month, "Publisher evidence outside report month"
        assert valid_https_source(item.get("source")), "Publisher evidence missing valid HTTPS source"
        assert doi not in article_journals or item["journal"]==article_journals[doi], (
            f"Publisher evidence journal mismatch for {doi}")
    expected_missing=[item for item in findings if item["doi"].strip().lower() not in dois]
    assert coverage["publisher_examples_checked"]==len(findings), "Publisher evidence count mismatch"
    assert coverage["confirmed_missing_publisher_articles"]==len(expected_missing), "Missing publisher evidence count mismatch"
    expected_by_doi={item["doi"].strip().lower():item for item in expected_missing}
    actual_by_doi={item["doi"].strip().lower():item for item in coverage["missing_publisher_articles"]}
    assert len(actual_by_doi)==len(coverage["missing_publisher_articles"]), "Duplicate missing publisher DOI"
    assert set(actual_by_doi)==set(expected_by_doi), "Missing publisher evidence DOI set mismatch"
    for doi,original in expected_by_doi.items():
        actual=actual_by_doi[doi]
        for field in ("journal","publisher_online_date","source"):
            assert actual[field]==original[field], f"Publisher evidence {field} altered for {doi}"
        assert actual.get("in_monthly_report") is False, "Missing publisher DOI marked present"
    expected_conflicts={}
    for item in findings:
        doi=item["doi"].strip().lower()
        article=next((a for a in articles if a["doi"].strip().lower()==doi),None)
        if article is not None:
            reported=article.get("online_date") or article.get("date")
            if reported!=item["publisher_online_date"]:
                expected_conflicts[doi]=(item["journal"],item["publisher_online_date"],reported,item["source"])
    actual_conflicts={}
    for item in conflicts:
        doi=item["doi"].strip().lower()
        actual_conflicts[doi]=(item["journal"],item["publisher_online_date"],item["reported_online_date"],item["source"])
    assert actual_conflicts==expected_conflicts, "Publisher date conflicts do not match evidence"
    for row in coverage["journals"]:
        expected=sum(item["journal"]==row["journal"] for item in expected_missing)
        assert row["publisher_examples_missing"]==expected, "Per-journal publisher gap count mismatch"
        assert row["publisher_coverage_verified"] is False, "Exhaustive publisher coverage claimed without audit"
    assert coverage["journals_independently_verified"]==0, "Unverified journals counted as complete"
    assert quality["publication_ready"] is False, "Unapproved report marked publication-ready"
    assert quality["release_status"]=="review_required", "Unapproved report release status changed"
    assert coverage["complete"] is False, "Completeness incorrectly claimed"
    print(f"PASS {month}: {len(articles)} articles, 24 journals, {len(coverage['missing_publisher_articles'])} missing publisher examples")

if __name__=="__main__":
    validate(sys.argv[1] if len(sys.argv)>1 else "2026-10")
