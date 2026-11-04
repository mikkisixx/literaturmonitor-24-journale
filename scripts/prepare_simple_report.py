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
    from sys import path
    path.insert(0,str(ROOT/"scripts"))
    import collect
    expected=sum(map(len,collect.JOURNALS.values()))
    coverage={"month":month,"journals_expected":expected,"journals_queried":back["checked"],
              "query_errors":len(back.get("errors",{})),
              "journals_independently_verified":0,"complete":False,
              "missing_publisher_articles":[],"confirmed_missing_publisher_articles":0,
              "reason":"Crossref search is not exhaustive independent publisher verification."}
    quality={"month":month,"publication_ready":False,"release_status":"review_required",
             "crossref_online_articles":report["verified_online_count"],
             "candidate_count":report["candidate_count"]}
    for folder,obj in (("coverage",coverage),("quality",quality)):
        target=data/folder/f"{month}.json"
        target.parent.mkdir(parents=True,exist_ok=True)
        # Never overwrite prior independent publisher evidence or editorial review. 
        # This helper supplies missing provisional metadata only. 
        if not target.exists(): 
            target.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("month")
    a=p.parse_args()
    prepare(a.month)
