#!/usr/bin/env python3
"""Recover missing first-online dates from DOI-resolved publisher pages.

Only explicit online-date metadata is eligible; issue dates, generic publication
dates, Crossref's 'published' and guessed dates are never promoted. The DOI
redirect is followed to the publisher. Ambiguous/conflicting dates are rejected.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from verify_publishers import get_publisher, normalize_date, ONLINE_KEYS
ROOT=pathlib.Path(__file__).resolve().parents[1]

def inspect(item):
    doi=(item.get("doi") or "").lower()
    try:
        url,dates=get_publisher(doi)
        explicit=[(k,v,normalize_date(v)) for k,v in dates if k in ONLINE_KEYS]
        # An invalid explicit date invalidates otherwise parseable evidence.
        if any(parsed is None for _,_,parsed in explicit):
            return doi,{"status":"invalid_online_date_metadata","publisher_url":url,
                        "evidence":[{"field":k,"value":v} for k,v,_ in explicit][:5]}
        values=sorted({parsed for _,_,parsed in explicit})
        if len(values)==1:
            return doi,{"status":"publisher_online_date_verified","online_date":values[0],
                "publisher_url":url,"evidence":[{"field":k,"value":v} for k,v in dates if k in ONLINE_KEYS and normalize_date(v)==values[0]][:5]}
        return doi,{"status":"conflicting_online_dates" if values else "no_explicit_online_date",
                    "publisher_url":url,"dates":values}
    except Exception as exc:
        return doi,{"status":"publisher_unavailable","error":str(exc)[:180]}

def recover(month,workers=6):
    report=json.loads((ROOT/"data/months"/(month+".json")).read_text())
    candidates=[a for a in report["articles"] if a.get("date_basis") not in ("crossref_online","publisher_online") and a.get("doi")]
    candidates=list({a["doi"].lower():a for a in candidates}.values())
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for doi,record in pool.map(inspect,candidates):
            results[doi]=record
    observed_path=ROOT/"data/observed.json"
    observed=json.loads(observed_path.read_text())
    updated=0
    conflicts=0
    for doi,record in results.items():
        if record["status"]!="publisher_online_date_verified":continue
        existing=observed.get(doi)
        if not existing or existing.get("publisher_online_verified"):continue
        online=record["online_date"]
        previous_online=existing.get("online_date")
        if previous_online and previous_online != online:
            record["status"]="conflict_with_existing_online_date"
            record["existing_online_date"]=previous_online
            conflicts+=1
            continue
        existing.update({"online_date":online,"publisher_online_verified":True,
                         "publisher_date_source":record["publisher_url"],
                         "publisher_date_evidence":record["evidence"]})
        updated+=1
    observed_path.write_text(json.dumps(observed,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    output=ROOT/"data/publisher-candidate-checks"/(month+".json")
    output.parent.mkdir(parents=True,exist_ok=True)
    journal_statuses={}
    for candidate in candidates:
        journal=candidate.get("journal") or "Unbekannt"
        status=results[candidate["doi"].lower()]["status"]
        bucket=journal_statuses.setdefault(journal,{"candidates":0,"statuses":{}})
        bucket["candidates"]+=1
        bucket["statuses"][status]=bucket["statuses"].get(status,0)+1
    output.write_text(json.dumps({"month":month,"candidates_checked":len(candidates),
        "journal_statuses":journal_statuses,
        "publisher_dates_recovered":updated,"existing_date_conflicts":conflicts,"statuses":{k:sum(v["status"]==k for v in results.values()) for k in sorted({v["status"] for v in results.values()})},
        "records":results},ensure_ascii=False,indent=2)+"\n")
    print("Publisher candidate audit:",len(candidates),"checked;",updated,"dates recovered")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--month",required=True)
    p.add_argument("--workers",type=int,default=6)
    a=p.parse_args()
    recover(a.month,max(1,min(a.workers,12)))
