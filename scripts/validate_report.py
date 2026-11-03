#!/usr/bin/env python3
"""Fail closed when a monthly report or its provenance is internally inconsistent."""
import datetime as dt
import json
import pathlib
import re
import sys

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
    reviews=quality["candidate_reviews"]
    statuses=quality["candidate_status_counts"]
    assert quality["candidate_count"]==len(reviews)==report["candidate_count"], "Candidate review count mismatch"
    assert sum(statuses.values())==len(reviews), "Candidate status totals inconsistent"
    assert set(statuses)=={r["status"] for r in reviews}, "Candidate status categories inconsistent"
    assert all(sum(r["status"]==status for r in reviews)==count for status,count in statuses.items()), "Candidate status counts differ from records"
    assert len({r["doi"].strip().lower() for r in reviews})==len(reviews), "Duplicate candidate reviews"
    assert quality["crossref_online_articles"]==report["verified_online_count"], "Crossref online count mismatch"
    assert quality["independently_corroborrated_online_dates"]+quality["online_dates_not_corroborrated"]==quality["crossref_online_articles"], "Online corroboration counts inconsistent"
    assert coverage["month"]==quality["month"]==report["month"]==month, "Month mismatch"
    assert coverage["journals_expected"]==24, "Expected 24 journals"
    assert len(coverage["journals"])==24, "Missing or duplicate journal audit rows"
    assert len({r["journal"] for r in coverage["journals"]})==24, "Duplicate journal coverage rows"
    assert coverage["journals_queried"]==24 and coverage["query_errors"]==0, "Crossref queries incomplete"
    assert coverage["zero_hit_journals"]==sum(r["crossref_query_count"]==0 for r in coverage["journals"]), "Zero-hit mismatch"
    assert coverage["confirmed_missing_publisher_articles"]==len(coverage["missing_publisher_articles"]), "Publisher evidence mismatch"
    for item in coverage["missing_publisher_articles"]:
        assert item["doi"].lower() not in dois, "Publisher article already in monthly report"
        assert item["journal"] in {r["journal"] for r in coverage["journals"]}, "Unknown evidence journal"
        assert item["publisher_online_date"].startswith(month+"-"), "Publisher evidence outside report month"
        dt.date.fromisoformat(item["publisher_online_date"])
        assert item["source"].startswith("https://"), "Publisher evidence has no HTTPS source"
    assert quality["publication_ready"] is False, "Unapproved report marked publication-ready"
    assert quality["release_status"]=="review_required", "Unapproved report release status changed"
    assert coverage["complete"] is False, "Completeness incorrectly claimed"
    print(f"PASS {month}: {len(articles)} articles, 24 journals, {len(coverage['missing_publisher_articles'])} missing publisher examples")

if __name__=="__main__":
    validate(sys.argv[1] if len(sys.argv)>1 else "2026-10")
