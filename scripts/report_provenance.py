#!/usr/bin/env python3
"""Per-journal provenance ledger; never equate a successful query with completeness."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect
from audit_publisher_inventory import verified_online_date, is_valid_month_date
def load(path):
    return json.loads(path.read_text()) if path.exists() else {}
def make(month):
    base=ROOT/"data"
    back=load(base/f"backfill-{month}.json")
    online=load(base/"online-audit"/f"{month}.json")
    inv=load(base/"publisher-inventory"/f"{month}.json")
    verified=load(base/"publisher-inventory"/f"{month}-verified.json")
    coverage=load(base/"publisher-inventory"/f"{month}-coverage.json")
    coverage_by_journal={row["journal"]:row for row in coverage.get("journals",[])}
    report=load(base/"months"/f"{month}.json")
    records=report.get("articles",[])
    rows=[]
    for group,names in collect.JOURNALS.items():
        for name in names:
            included=[a for a in records if a.get("journal")==name and is_valid_month_date(a.get("online_date"), month) and a.get("date_basis") in ("crossref_online","publisher_online")]
            publisher=[a for a in included if a.get("date_basis")=="publisher_online"]
            checks=[a for a in verified.get("records",[]) if a.get("journal")==name]
            audit=coverage_by_journal.get(name,{})
            rows.append({"journal":name,"group":group,
                "publisher_platform":audit.get("publisher_platform","unmapped"),
                "crossref_api_source":"https://api.crossref.org/works",
                "publisher_article_evidence_urls":sorted({a["publisher_date_source"] for a in publisher if isinstance(a.get("publisher_date_source"),str) and a["publisher_date_source"].startswith("https://")}),
                "publisher_listing_urls":audit.get("publisher_listing_urls",[]),
                "publisher_verified_date_source_urls":audit.get("publisher_verified_date_source_urls",[]),
                "publisher_confirmed_month_missing_dois":audit.get("confirmed_month_missing_dois",[]),
                "publisher_confirmed_month_missing_count":audit.get("confirmed_month_missing_from_report",0),
                "publisher_conflicting_verified_date_dois":audit.get("publisher_conflicting_verified_date_dois",[]),
                "publisher_report_comparison_available":audit.get("publisher_report_comparison_available",False),
                "publisher_coverage_reason":audit.get("publisher_coverage_reason","Publisher completeness not independently verified"),"crossref_publication_candidates":back.get("counts",{}).get(name,0),
                "crossref_publication_query":{"status":("failed" if name in back.get("errors",{}) else "queried" if name in back.get("counts",{}) else "not_run"),"error":back.get("errors",{}).get(name)},
                "crossref_online_query":online.get("journals",{}).get(name,{"status":"not_run"}),
                "publisher_listing":inv.get("journals",{}).get(name,{"status":"not_implemented"}),
                "publisher_article_pages_checked":len(checks),
                "publisher_online_dates_verified":sum(a.get("status")=="publisher_online_date_verified" and verified_online_date(a) is not None for a in checks),
                "included_articles":len(included),"included_with_publisher_evidence":len(publisher),
                "independently_exhaustive":False,
                "reason":audit.get("publisher_coverage_reason") or "No proven exhaustive publisher listing and article-level first-online date verification"})
    assert len(rows)==24 and len({row["journal"] for row in rows})==24
    for row in rows:
        missing=row["publisher_confirmed_month_missing_dois"]
        assert len(missing)==len(set(missing))==row["publisher_confirmed_month_missing_count"], "Inconsistent publisher-confirmed gap ledger"
    return {"month":month,"journal_count":24,"all_crossref_queries_succeeded":back.get("checked")==24 and not back.get("errors") and all(x["crossref_online_query"].get("status")=="queried" for x in rows),
        "all_crossref_publication_queries_succeeded":back.get("checked")==24 and not back.get("errors") and all(row["crossref_publication_query"]["status"]=="queried" for row in rows) and not back.get("title_fallback_truncated"),
        "independently_complete":False,"journals":rows}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--month",required=True)
    args=p.parse_args()
    obj=make(args.month)
    target=ROOT/"data"/"online-audit"/f"{args.month}-provenance.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"journal_count":24,"queries_succeeded":obj["all_crossref_queries_succeeded"],"publisher_exhaustive":False}))
