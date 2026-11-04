#!/usr/bin/env python3
"""Verify publisher-discovered Springer DOIs against publisher article pages.

A discovery listing is not an online-first date. Only exact article-level
citation_online_date metadata is accepted. All other records stay unresolved.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.request
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        data = dict(attrs)
        key = (data.get("name") or data.get("property") or "").lower()
        if key in ("citation_online_date", "citation_publication_date", "citation_doi"):
            self.values.setdefault(key, []).append(data.get("content", ""))

def publisher_online_date(html, expected_doi):
    parser = Meta()
    parser.feed(html)
    dois = parser.values.get("citation_doi", [])
    if not dois or not any(x.lower().strip() == expected_doi.lower() for x in dois):
        return None, "publisher_doi_mismatch_or_missing"
    dates = parser.values.get("citation_online_date", [])
    if not dates:
        return None, "publisher_online_date_missing"
    normalized = []
    for raw in dates:
        value = raw.strip()
        if re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", value):
            try:
                normalized.append(dt.date.fromisoformat(value.replace("/", "-")).isoformat())
            except ValueError:
                pass
    if len(set(normalized)) != 1 or len(normalized) != len(dates):
        return None, "publisher_online_date_invalid_or_conflicting"
    return normalized[0], "publisher_online_date_verified"

def verify(month, inventory, report_dois, fetch):
    rows = []
    for journal, entry in inventory["journals"].items():
        for doi in entry["candidate_dois"]:
            url = "https://link.springer.com/article/" + doi
            try:
                date, status = publisher_online_date(fetch(url), doi)
            except Exception as exc:
                date, status = None, "publisher_fetch_error: " + str(exc)[:150]
            rows.append({"journal": journal, "doi": doi, "source": url, "publisher_online_date": date,
                         "status": status, "in_requested_month": bool(date and date[:7] == month),
                         "in_monthly_report": doi.lower() in report_dois})
    missing = [r for r in rows if r["status"] == "publisher_online_date_verified"
               and r["in_requested_month"] and not r["in_monthly_report"]]
    return {"month": month, "coverage_complete": False, "articles_checked": len(rows),
            "verified_month_missing_from_report": missing, "records": rows,
            "warning": "Only DOI candidates found on bounded publisher listings were checked; absence does not establish completeness."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True)
    args = p.parse_args()
    dt.date.fromisoformat(args.month + "-01")
    inventory = json.loads((ROOT / "data/publisher-inventory" / (args.month + ".json")).read_text())
    report = json.loads((ROOT / "data/months" / (args.month + ".json")).read_text())
    dois = {r["doi"].lower() for r in report["articles"]}
    def fetch(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Literaturmonitor/0.2 (publisher date verification; https://github.com/mikkisixx/literaturmonitor-24-journale)"})
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    result = verify(args.month, inventory, dois, fetch)
    out = ROOT / "data/publisher-inventory" / (args.month + "-verified.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checked": result["articles_checked"], "verified_missing": len(result["verified_month_missing_from_report"])}))

if __name__ == "__main__":
    main()
