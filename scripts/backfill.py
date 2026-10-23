#!/usr/bin/env python3
"""Backfill a calendar month using publication-date filters, not indexing dates.
Crossref 'published' is a candidate date, NOT evidence of first online publication.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import collect
DATA=collect.DATA
def fetch_pages(issn, start, end, mode):
    filters=f"from-{mode}-pub-date:{start},until-{mode}-pub-date:{end},type:journal-article"
    cursor="*"
    while True:
        msg=collect.get(collect.url("journals/"+issn+"/works",{
            "filter":filters,"rows":200,"cursor":cursor,
            "select":"DOI,title,published-online,published-print,published,created,indexed,container-title,ISSN,URL,author,type"}))
        items=msg.get("items",[])
        yield from items
        nxt=msg.get("next-cursor")
        if len(items)<200 or not nxt or nxt==cursor:break
        cursor=nxt
        time.sleep(.12)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--month",required=True,help="YYYY-MM")
    args=p.parse_args()
    start=dt.date.fromisoformat(args.month+"-01")
    end=(dt.date(start.year+1,1,1) if start.month==12 else dt.date(start.year,start.month+1,1))-dt.timedelta(days=1)
    oldfile=DATA/"observed.json"
    observed=json.loads(oldfile.read_text(encoding="utf-8")) if oldfile.exists() else {}
    counts={};errors={}
    for group,names in collect.JOURNALS.items():
        for name in names:
            try:
                issn=collect.resolve(name)
                if not issn:raise ValueError("ISSN unbekannt")
                found=set()
                for mode in ("online","",):
                    # Crossref supports from-online-pub-date and from-pub-date.
                    for item in fetch_pages(issn,start.isoformat(),end.isoformat(),mode):
                        doi=(item.get("DOI") or "").lower().strip()
                        if not doi:continue
                        found.add(doi)
                        previous=observed.get(doi,{})
                        online=collect.date_field(item,"published-online")
                        published=collect.date_field(item,"published")
                        previous.update({
                            "doi":doi,"title":(item.get("title") or [""])[0],
                            "journal":name,"category":group,
                            "online_date":online,"published_date":published,
                            "print_date":collect.date_field(item,"published-print"),
                            "url":item.get("URL") or "https://doi.org/"+doi,
                            "last_seen":dt.date.today().isoformat()})
                        previous.setdefault("first_seen",dt.date.today().isoformat())
                        observed[doi]=previous
                counts[name]=len(found)
            except Exception as exc:
                errors[name]=str(exc)[:200]
            print(name,counts.get(name,"ERROR"),flush=True)
    oldfile.write_text(json.dumps(observed,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    report={"month":args.month,"source":"Crossref journal-article queries using publication/online-publication month filters",
            "checked":len(counts),"errors":errors,"counts":counts,"distinct_doi_in_register":len(observed),
            "warning":"Published date alone is NOT confirmed online-first; publication dates can be updated."}
    (DATA/("backfill-"+args.month+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"month":args.month,"checked":len(counts),"errors":errors}),flush=True)
if __name__=="__main__":main()
