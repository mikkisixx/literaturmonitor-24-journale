#!/usr/bin/env python3
"""Verify independently discovered publisher DOI candidates against article-level online dates.

This is an audit, not proof of exhaustive publisher pagination. It does not modify
observed.json or silently add records to the published monthly report.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import pathlib
import sys
import urllib.parse


def canonical_doi(value):
    """Normalize DOI strings and doi.org links without changing DOI identity."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if value.lower().startswith(("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/")):
        value = urllib.parse.urlsplit(value).path.lstrip("/")
    elif value.lower().startswith("doi:"):
        value = value[4:].strip()
    value = urllib.parse.unquote(value).strip().lower()
    return value if value.startswith("10.") and "/" in value else ""

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_publishers import ONLINE_KEYS, get_publisher, normalize_date
import collect


def check_candidate(doi, month, fetch=get_publisher):
    try:
        url, dates = fetch(doi)
        explicit = [(key, normalize_date(value)) for key, value in dates if key in ONLINE_KEYS]
        valid = sorted({value for _, value in explicit if value})
        # A malformed explicit online date is not evidence that can be ignored.
        # Otherwise a valid date beside an unparseable conflicting date could
        # incorrectly pass the publication gate.
        if any(value is None for _, value in explicit):
            status = "unparseable_online_date"
        elif len(valid) > 1:
            status = "conflicting_online_dates"
        elif not valid:
            status = "no_explicit_online_date"
        elif valid[0].startswith(month + "-"):
            status = "verified_in_month"
        else:
            status = "verified_outside_month"
        return {"doi": doi, "status": status, "online_date": valid[0] if len(valid) == 1 else None,
                "publisher_url": url, "evidence": [{"field": k, "date": v} for k, v in explicit if v][:8]}
    except Exception as exc:
        return {"doi": doi, "status": "publisher_unavailable", "error": str(exc)[:200]}


def audit(month, inventory, report, workers=4, checker=check_candidate):
    in_report = {canonical_doi(a.get("doi")) for a in report.get("articles", [])} - {""}
    expected = {name for names in collect.JOURNALS.values() for name in names}
    listed = set(inventory.get("journals", {}))
    output = {"month": month, "coverage_complete": False,
              "expected_journal_count": len(expected),
              "journals_without_listing": sorted(expected - listed),
              "unexpected_journals": sorted(listed - expected),
              "journals": {}, "records": []}
    jobs = []
    for journal, listing in inventory.get("journals", {}).items():
        dois = sorted({canonical_doi(d) for d in listing.get("candidate_dois", [])} - {""})
        output["journals"][journal] = {"listing_status": listing.get("status", "unknown"),
            "publisher_listing_urls": [p.get("url") for p in listing.get("pages", [])],
            "coverage_verified": False, "candidate_count": len(dois), "records": []}
        jobs.extend((journal, doi) for doi in dois)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        checked = list(pool.map(lambda item: checker(item[1], month), jobs))
    for (journal, doi), result in zip(jobs, checked):
        result["in_monthly_report"] = doi in in_report
        result["journal"] = journal
        result["in_requested_month"] = result["status"] == "verified_in_month"
        if result["status"] == "verified_in_month":
            result["status"] = "publisher_online_date_verified"
        output["records"].append(result)
        output["journals"][journal]["records"].append(result)
    for row in output["journals"].values():
        row["verified_missing_from_report"] = sum(
            r["status"] == "publisher_online_date_verified" and not r["in_monthly_report"] for r in row["records"])
        row["warning"] = "Publisher listing is not proven exhaustive; candidate dates are article-level checks only."
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--fail-on-missing", action="store_true", help="Fail if publisher-verified articles are absent from the monthly report")
    args = p.parse_args()
    dt.date.fromisoformat(args.month + "-01")
    if not 1 <= args.workers <= 12:
        p.error("--workers must be 1..12")
    inventory_path = ROOT / "data/publisher-inventory" / (args.month + ".json")
    report_path = ROOT / "data/months" / (args.month + ".json")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = audit(args.month, inventory, report, args.workers)
    out = ROOT / "data/publisher-inventory" / (args.month + "-verified.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = sum(row["verified_missing_from_report"] for row in result["journals"].values())
    print(json.dumps({name: {"candidates": row["candidate_count"],
                             "verified_missing": row["verified_missing_from_report"]}
                      for name, row in result["journals"].items()}))
    if args.fail_on_missing and missing:
        raise SystemExit(f"Publication blocked: {missing} publisher-verified in-month DOI candidates are missing from the monthly report. See {out}")


if __name__ == "__main__":
    main()
