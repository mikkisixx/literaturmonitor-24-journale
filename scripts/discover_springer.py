#!/usr/bin/env python3
"""Independent Springer journal-listing discovery (pilot, never completeness proof).

Reads Springer journal article listings, NOT Crossref. Fail closed on blocked,
unparseable, or truncated listings. Stores DOI candidates with source URLs;
article-level online dates require separate publisher verification.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNALS = {
    "Clinical Oral Investigations": "784",
    "Journal of Materials Science: Materials in Medicine": "10856",
}
DOI = re.compile(r"10\.1007/(?:s00784|s10856)-[0-9]{4}-[0-9a-z-]+", re.I)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if "/article/" in href:
            self.links.append(href)

def parse_dois(html, journal):
    parser = Links()
    parser.feed(html)
    if journal not in JOURNALS:
        raise ValueError(f"Unsupported Springer journal: {journal}")
    prefix = "s00784" if journal == "Clinical Oral Investigations" else "s10856"
    result = set()
    for href in parser.links:
        # Springer may percent-encode the DOI slash in article hrefs. Decode
        # URL escapes before matching, without accepting DOI text outside links.
        for match in DOI.findall(urllib.parse.unquote(href)):
            if match.lower().startswith("10.1007/" + prefix + "-"):
                result.add(match.lower().rstrip("/"))
    return sorted(result)

def discover(month, pages=5, fetch=None):
    if fetch is None:
        def fetch(url):
            req = urllib.request.Request(url, headers={"User-Agent": "Literaturmonitor/0.2 (research metadata; https://github.com/mikkisixx/literaturmonitor-24-journale)", "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=25) as response:
                return response.read().decode("utf-8", errors="replace")
    output = {"month": month, "source": "Springer Nature journal article listings (independent of Crossref)", "coverage_complete": False, "journals": {}}
    for name, jid in JOURNALS.items():
        found = set()
        status = "partial_listing"
        error = None
        visited = []
        for page in range(1, pages + 1):
            url = f"https://link.springer.com/journal/{jid}/articles?sort=PubDate&page={page}"
            try:
                html = fetch(url)
                dois = parse_dois(html, name)
                visited.append({"url": url, "doi_count": len(dois)})
                if not dois:
                    status = "unparseable_or_empty_listing"
                    break
                before = len(found)
                found.update(dois)
                if len(found) == before:
                    status = "repeated_listing_page"
                    break
            except Exception as exc:
                status = "fetch_error"
                error = str(exc)[:250]
                break
        else:
            status = "page_limit_reached"
        output["journals"][name] = {"status": status, "error": error, "pages": visited,
                                   "candidate_dois": sorted(found),
                                   "online_first_month_verified": False,
                                   "warning": "Listing may include other months; article-level first-online date must be checked."}
    return output

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True)
    p.add_argument("--pages", type=int, default=5)
    args = p.parse_args()
    dt.date.fromisoformat(args.month + "-01")
    if not 1 <= args.pages <= 30:
        p.error("--pages must be between 1 and 30")
    result = discover(args.month, args.pages)
    path = ROOT / "data" / "publisher-inventory" / (args.month + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"status": row["status"], "candidates": len(row["candidate_dois"])}
                      for name, row in result["journals"].items()}))

if __name__ == "__main__":
    main()
