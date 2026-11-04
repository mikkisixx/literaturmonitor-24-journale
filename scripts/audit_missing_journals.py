#!/usr/bin/env python3
"""Explicitly account for every journal absent from the reader-facing report.

A journal with zero verified articles is NOT silently treated as a journal with
no publications. Keep unresolved candidates separate from confirmed zero hits.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from collect import JOURNALS

def audit(month):
    report=json.loads((ROOT/"data/months"/(month+".json")).read_text())
    by_journal={}
    for group,names in JOURNALS.items():
        for name in names:
            by_journal[name]={"group":group,"verified":0,"unresolved":0,"status":"no_records_found"}
    for a in report["articles"]:
        name=a.get("journal")
        if name not in by_journal:continue
        row=by_journal[name]
        if a.get("date_basis") in ("crossref_online","publisher_online") and (a.get("online_date") or "")[:7]==month:
            row["verified"]+=1
        else:
            row["unresolved"]+=1
    for row in by_journal.values():
        row["status"]="dated_articles_found" if row["verified"] else ("undated_candidates_need_publisher_check" if row["unresolved"] else "no_records_found_not_proof_of_inactivity")
    missing=[{"journal":name,**row} for name,row in by_journal.items() if not row["verified"]]
    return {"month":month,"journals_expected":24,"journals_in_html":24-len(missing),
        "journals_absent_from_html":len(missing),
        "undated_candidates_in_absent_journals":sum(x["unresolved"] for x in missing),
        "missing_journals":missing,
        "warning":"Absence from HTML does not establish that a journal published no articles."}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--month",required=True)
    args=p.parse_args()
    result=audit(args.month)
    out=ROOT/"data"/"missing-journals"/(args.month+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="missing_journals"},ensure_ascii=False))
if __name__=="__main__":main()
