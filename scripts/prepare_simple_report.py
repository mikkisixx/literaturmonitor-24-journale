#!/usr/bin/env python3
"""Prepare explicitly provisional coverage metadata for an on-demand month."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prepare(month):
    data=ROOT/"data"
    back=json.loads((data/f"backfill-{month}.json").read_text())
    report=json.loads((data/"months"/f"{month}.json").read_text())
    expected=24
    coverage={"month":month,"journals_expected":expected,"journals_queried":back["checked"],
              "query_errors":len(back.get("errors",{})),
              "journals_independently_verified":0,"complete":False,
              "missing_publisher_articles":[],"confirmed_missing_publisher_articles":0,
              "reason":"Crossref search is not exhaustive independent publisher verification."}
    quality={"month":month,"publication_ready":False,"release_status":"review_required",
             "crossref_online_articles":report.get("verified_online_count", sum(1 for a in report.get("articles", []) if a.get("date_basis") == "crossref_online")),
             "candidate_count":report.get("candidate_count", len(report.get("articles", [])))}
    for folder,obj in (("coverage",coverage),("quality",quality)):
        target=data/folder/f"{month}.json"
        target.parent.mkdir(parents=True,exist_ok=True)
        # Never overwrite prior independent publisher evidence or editorial review. 
        # This helper supplies missing provisional metadata only. 
        previous=json.loads(target.read_text()) if target.exists() else {}
        if not isinstance(previous,dict):
            raise ValueError(f"Invalid metadata object: {target}")
        preserve=("missing_publisher_articles","confirmed_missing_publisher_articles",
                  "journals_independently_verified","complete") if folder=="coverage" else ("publication_ready","release_status")
        for key in preserve:
            if key in previous:
                obj[key]=previous[key]
        previous.update(obj)
        target.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+"\\n")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("month")
    a=p.parse_args()
    prepare(a.month)
