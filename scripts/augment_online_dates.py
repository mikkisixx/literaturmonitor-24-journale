#!/usr/bin/env python3
"""Supplement month with explicitly dated Crossref online records and independently checked Springer dates.

No issue/print/published date is interpreted as an online-first date.
Publisher records are accepted only when the DOI and citation_online_date match.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import collect
import backfill
ROOT=pathlib.Path(__file__).resolve().parents[1]
def augment(month):
    start=dt.date.fromisoformat(month+"-01")
    end=(dt.date(start.year+1,1,1) if start.month==12 else dt.date(start.year,start.month+1,1))-dt.timedelta(days=1)
    path=ROOT/"data"/"observed.json"
    observed=json.loads(path.read_text())
    journal_results={}
    for group,names in collect.JOURNALS.items():
        for name in names:
            added=0
            try:
                issn=collect.resolve(name)
                ids=backfill.journal_issns(issn)
                seen=set()
                for ident in ids:
                    for item in backfill.fetch_pages(ident,start.isoformat(),end.isoformat(),"online"):
                        doi=(item.get("DOI") or "").strip().lower()
                        online=collect.date_field(item,"published-online")
                        if not doi or not online or online[:7]!=month or doi in seen:
                            continue
                        seen.add(doi)
                        old=observed.get(doi,{})
                        if old.get("journal") and old["journal"]!=name:
                            continue
                        old.update({"doi":doi,"journal":name,"category":group,
                            "title":(item.get("title") or [""])[0] or old.get("title",""),
                            "authors":[(a.get("family","")+" "+a.get("given","")).strip() for a in item.get("author",[])][:8] or old.get("authors",[]),
                            "online_date":online,"url":"https://doi.org/"+doi})
                        old.setdefault("matched_months",[])
                        if month not in old["matched_months"]:old["matched_months"].append(month)
                        observed[doi]=old
                        added+=1
                journal_results[name]={"crossref_online_records":len(seen),"status":"queried"}
            except Exception as exc:
                journal_results[name]={"status":"error","error":str(exc)[:200]}
            print("Online-Monatsabfrage:",name,journal_results[name],flush=True)
            time.sleep(.1)
    path.write_text(json.dumps(observed,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    return journal_results
def merge_publisher(month):
    p=ROOT/"data"/"publisher-inventory"/(month+"-verified.json")
    if not p.exists():return 0
    observed_path=ROOT/"data"/"observed.json"
    observed=json.loads(observed_path.read_text())
    n=0
    for row in json.loads(p.read_text()).get("records",[]):
        if row.get("status")!="publisher_online_date_verified":continue
        online=row.get("publisher_online_date")
        doi=(row.get("doi") or "").lower()
        if not doi or not online or online[:7]!=month:continue
        previous=observed.get(doi,{})
        if previous.get("journal") and previous["journal"]!=row["journal"]:continue
        previous.update({"doi":doi,"journal":row["journal"],"online_date":online,
            "publisher_online_verified":True,"publisher_date_source":row.get("source"),
            "url":"https://doi.org/"+doi})
        if not previous.get("title"):
            continue
        previous.setdefault("matched_months",[])
        if month not in previous["matched_months"]:previous["matched_months"].append(month)
        observed[doi]=previous
        n+=1
    observed_path.write_text(json.dumps(observed,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    return n
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--month",required=True)
    a=p.parse_args()
    rows=augment(a.month)
    target=ROOT/"data"/"online-audit"/(a.month+".json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({"month":a.month,"journals":rows,"publisher_verified_merged":merge_publisher(a.month)},ensure_ascii=False,indent=2)+"\n")
    if any(x["status"]=="error" for x in rows.values()):
        raise SystemExit("Mindestens eine der 24 Online-Monatsabfragen ist fehlgeschlagen")
