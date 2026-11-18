#!/usr/bin/env python3
"""Conservative 24-journal publisher discovery coverage ledger.

A provider adapter must independently enumerate publisher records, confirm the
first-online date per DOI and prove pagination exhaustion before it can claim
full coverage. Unsupported journals remain explicitly unverified.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect

SPRINGER = {"Clinical Oral Investigations", "Journal of Materials Science: Materials in Medicine"}
BMC = {"BMC Oral Health"}
WILEY = {"European Journal of Oral Sciences", "The Journal of Esthetic and Restorative Dentistry",
         "International Endodontic Journal", "Dental Traumatology",
         "International Journal of Paediatric Dentistry", "Journal of Oral Rehabilitation",
         "Journal of the American Ceramic Society"}
ELSEVIER = {"Dental Materials", "Journal of Dentistry", "Journal of Prosthetic Dentistry",
            "Journal of Endodontics", "Journal of the Mechanical Behavior of Biomedical Materials",
            "Acta Biomaterialia", "Journal of the European Ceramic Society", "Journal of Biomechanics"}
QUINTESSENCE = {"Journal of Adhesive Dentistry", "International Journal of Prosthodontics", "Quintessence International"}

def platform(name):
    if name in SPRINGER: return "springer_link"
    if name in BMC: return "bmc_springer_nature"
    if name in WILEY: return "wiley_online_library"
    if name in ELSEVIER: return "elsevier_sciencedirect"
    if name in QUINTESSENCE: return "quintessence_publishing"
    if name == "Journal of Dental Research": return "sage"
    if name == "American Journal of Dentistry": return "american_journal_of_dentistry"
    if name == "Operative Dentistry": return "operative_dentistry"
    return "unmapped"

def normalize_doi(value):
    """Canonicalize DOI identifiers from publisher URLs and bare DOI strings."""
    doi = str(value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.strip().lower()

def is_valid_iso_date(value):
    """Count only publisher dates that represent real ISO calendar days."""
    if not isinstance(value, str):
        return False
    try:
        return dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False

def is_valid_month_date(value, month):
    """Require a real ISO calendar date, not just a matching YYYY-MM prefix."""
    if not isinstance(value, str):
        return False
    try:
        return dt.date.fromisoformat(value).strftime("%Y-%m") == month
    except ValueError:
        return False

def verified_online_date(row):
    """Accept both publisher-verifier date field names, rejecting conflicts."""
    dates = [row[key] for key in ("online_date", "publisher_online_date") if row.get(key)]
    if not dates or len(set(dates)) != 1 or not is_valid_iso_date(dates[0]):
        return None
    return dates[0]

def build(month, inventory=None, verification=None, monthly_report=None):
    inventory = inventory or {}
    verification = verification or {}
    report_available = monthly_report is not None
    monthly_report = monthly_report if report_available else {}
    reported_dois = {doi for a in monthly_report.get("articles", []) if (doi := normalize_doi(a.get("doi")))}
    reported_by_journal = {}
    for article in monthly_report.get("articles", []):
        doi = normalize_doi(article.get("doi"))
        journal = str(article.get("journal", "")).strip()
        if doi and journal:
            reported_by_journal.setdefault(journal, set()).add(doi)
    verified_rows = verification.get("records", [])
    by_journal = {}
    for row in verified_rows:
        by_journal.setdefault(row["journal"], []).append(row)
    # A DOI with contradictory verified publisher dates is not reliable evidence.
    # Suppress it from confirmed-gap reporting until the conflict is resolved.
    dates_by_doi = {}
    for record in verified_rows:
        doi = normalize_doi(record.get("doi"))
        date = verified_online_date(record)
        if doi and record.get("status") == "publisher_online_date_verified" and date:
            dates_by_doi.setdefault(doi, set()).add(date)
    # A DOI assigned to two journals is contradictory even when dates agree.
    journals_by_doi = {}
    for record in verified_rows:
        doi = normalize_doi(record.get("doi"))
        if doi and record.get("status") == "publisher_online_date_verified" and verified_online_date(record):
            journals_by_doi.setdefault(doi, set()).add(record.get("journal"))
    conflicting_dois = {
        doi for doi in dates_by_doi
        if len(dates_by_doi[doi]) > 1 or len(journals_by_doi.get(doi, ())) > 1
    }
    rows = []
    for group, names in collect.JOURNALS.items():
        for name in names:
            listing = inventory.get("journals", {}).get(name)
            checks = by_journal.get(name, [])
            publisher_dois = {normalized for doi in (listing or {}).get("candidate_dois", []) if isinstance(doi, str) and (normalized := normalize_doi(doi))}
            missing_dois = sorted(publisher_dois - reported_by_journal.get(name, set())) if report_available else []
            misplaced_dois = sorted(publisher_dois & (reported_dois - reported_by_journal.get(name, set()))) if report_available else []
            globally_absent_dois = sorted(publisher_dois - reported_dois) if report_available else []
            status = "not_implemented" if listing is None else listing.get("status", "unknown")
            # Report the actual listing attempt, rather than a generic coverage warning.
            pages = listing.get("pages", []) if listing else []
            urls = [p["url"] for p in pages if isinstance(p, dict) and p.get("url")]
            if listing is None:
                reason = "No independent publisher listing attempted for this journal"
            elif status == "unparseable_or_empty_listing":
                reason = "Publisher listing attempted but no DOI could be extracted; coverage unverified"
            elif status == "page_limit_reached":
                reason = "Publisher pagination stopped at page limit; remaining pages not checked"
            elif status == "request_failed":
                reason = "Publisher listing request failed; coverage unverified"
            else:
                reason = "Publisher listing not proven exhaustive and first-online dates not fully inventoried"
            conflicting_journal_dois = sorted({normalize_doi(record.get("doi")) for record in checks
                                               if normalize_doi(record.get("doi")) in conflicting_dois})
            confirmed_missing = [
                x for x in checks
                if x.get("status") == "publisher_online_date_verified"
                # Derive month membership from the verified date, not a potentially stale flag.
                # A verified date is mandatory; the month flag alone is not evidence.
                and verified_online_date(x)
                and is_valid_month_date(verified_online_date(x), month)
                and normalize_doi(x.get("doi")) not in conflicting_dois
                # Prefer the actual current report over the verification
                # snapshot, which can be stale in either direction.
                and ((normalize_doi(x.get("doi"))
                      not in reported_by_journal.get(name, set()))
                     if report_available else not x.get("in_monthly_report"))
            ]
            confirmed_missing_dois = sorted({
                normalize_doi(x["doi"]) for x in confirmed_missing
                if x.get("doi") and normalize_doi(x["doi"])
            })
            verified_sources = sorted({str(x.get("source") or x.get("publisher_url") or x.get("url")).strip()
                                       for x in checks
                                       if x.get("status") == "publisher_online_date_verified"
                                       and normalize_doi(x.get("doi"))
                                       and normalize_doi(x.get("doi")) not in conflicting_dois
                                       and verified_online_date(x)
                                       and str(x.get("source") or x.get("publisher_url") or x.get("url") or "").startswith(("https://", "http://"))})
            rows.append({"journal": name, "group": group, "publisher_platform": platform(name),
                         "publisher_listing_status": status,
                         "publisher_listing_urls": urls,
                         "publisher_verified_date_source_urls": verified_sources,
                         "publisher_candidate_count": len(publisher_dois),
                         "publisher_candidates_absent_from_monthly_report": missing_dois,
                         "publisher_candidates_absent_count": len(missing_dois),
                         "publisher_candidates_present_under_other_journal": misplaced_dois,
                         "publisher_candidates_not_found_anywhere": globally_absent_dois,
                         "publisher_candidates_not_found_anywhere_count": len(globally_absent_dois),
                         "publisher_report_comparison_available": report_available,
                         "publisher_conflicting_verified_date_dois": conflicting_journal_dois,
                         "publisher_conflicting_verified_date_count": len(conflicting_journal_dois),
                         "publisher_article_dates_checked": len(checks),
                         "publisher_article_dates_verified": sum(x.get("status") == "publisher_online_date_verified" and bool(normalize_doi(x.get("doi"))) and verified_online_date(x) is not None for x in checks),
                         "publisher_article_dates_verified_unambiguous": sum(
                             x.get("status") == "publisher_online_date_verified"
                             and verified_online_date(x) is not None
                             and bool(normalize_doi(x.get("doi")))
                             and normalize_doi(x.get("doi")) not in conflicting_dois
                             for x in checks),
                         "confirmed_month_missing_from_report": len(confirmed_missing_dois),
                         "confirmed_month_missing_dois": confirmed_missing_dois,
                         "publisher_coverage_verified": False,
                         "publisher_coverage_reason": reason})
    assert len(rows) == 24
    return {"month": month, "journal_count": 24, "journals_independently_verified": 0,
            "complete": False, "journals": rows}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    dt.date.fromisoformat(args.month + "-01")
    folder = ROOT / "data/publisher-inventory"
    listing_path = folder / (args.month + ".json")
    verified_path = folder / (args.month + "-verified.json")
    listing = json.loads(listing_path.read_text()) if listing_path.exists() else {}
    verified = json.loads(verified_path.read_text()) if verified_path.exists() else {}
    report_path = ROOT / "data/months" / (args.month + ".json")
    monthly_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    result = build(args.month, listing, verified, monthly_report)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (args.month + "-coverage.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"journals": 24, "implemented_listings": sum(r["publisher_listing_status"] != "not_implemented" for r in result["journals"]),
                      "independently_verified": 0}))

if __name__ == "__main__":
    main()
