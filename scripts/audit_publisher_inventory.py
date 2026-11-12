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

def build(month, inventory=None, verification=None):
    inventory = inventory or {}
    verification = verification or {}
    verified_rows = verification.get("records", [])
    by_journal = {}
    for row in verified_rows:
        by_journal.setdefault(row["journal"], []).append(row)
    rows = []
    for group, names in collect.JOURNALS.items():
        for name in names:
            listing = inventory.get("journals", {}).get(name)
            checks = by_journal.get(name, [])
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
            rows.append({"journal": name, "group": group, "publisher_platform": platform(name),
                         "publisher_listing_status": status,
                         "publisher_listing_urls": urls,
                         "publisher_candidate_count": len(listing.get("candidate_dois", [])) if listing else 0,
                         "publisher_article_dates_checked": len(checks),
                         "publisher_article_dates_verified": sum(x.get("status") == "publisher_online_date_verified" for x in checks),
                         "confirmed_month_missing_from_report": sum(x.get("in_requested_month") and not x.get("in_monthly_report")
                                                                      and x.get("status") == "publisher_online_date_verified" for x in checks),
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
    result = build(args.month, listing, verified)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (args.month + "-coverage.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"journals": 24, "implemented_listings": sum(r["publisher_listing_status"] != "not_implemented" for r in result["journals"]),
                      "independently_verified": 0}))

if __name__ == "__main__":
    main()
