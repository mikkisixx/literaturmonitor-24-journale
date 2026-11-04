#!/usr/bin/env python3
"""Per-journal provenance ledger; never equate a successful query with completeness."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect
def load(path):
    return json.loads(path.read_text()) if path.exists() else {}
def make(month):
    base=ROOT/"data"
    back=load(base/f"backfill-{month}.json")
    online=load(base/"online-audit"/f"{month}.json")
    inv=load(base/"publisher-inventory"/f"{month}.json")
    verified=load(base/"publisher-inventory"/f"{month}-verified.json")
    report=load(base/"months"/f"{month}.json")
    records=report.get("articles",[])
    rows=[]
    for group,names in collect.JOURNALS.items():
        for name in names:
            included=[a for a in records if a.get("journal")==name and (a.get("online_date") or "").startswith(month) and a.get("date_basis") in ("crossref_online","publisher_online")]
            publisher=[a for a in included if a.get("date_basis")=="publisher_online"]
            checks=[a for a in verified.get("records",[]) if a.get("journal")==name]
            rows.append({"journal":name,"group":group,"crossref_publication_candidates":back.get("counts",{}).get(name,0),
                "crossref_online_query":online.get("journals",{}).get(name,{"status":"not_run"}),
                "publisher_listing":inv.get("journals",{}).get(name,{"status":"not_implemented"}),
                "publisher_article_pages_checked":len(checks),
                "publisher_online_dates_verified":sum(a.get("status")=="publisher_online_date_verified" for a in checks),
                "included_articles":len(included),"included_with_publisher_evidence":len(publisher),
                "independently_exhaustive":False,
                "reason":"No proven exhaustive publisher listing and article-level first-online date verification"})
    assert len(rows)==24
    return {"month":month,"journal_count":24,"all_crossref_queries_succeeded":back.get("checked")==24 and not back.get("errors") and all(x["crossref_online_query"].get("status")=="queried" for x in rows),
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
