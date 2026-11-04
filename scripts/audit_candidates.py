#!/usr/bin/env python3
"""Audit every unresolved monthly candidate without inventing online-first dates."""
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
MONTH=sys.argv[1] if len(sys.argv)>1 else (dt.date.today().replace(day=1)-dt.timedelta(days=1)).strftime("%Y-%m")
DATA=ROOT/"data"
report=json.loads((DATA/"months"/(MONTH+".json")).read_text(encoding="utf-8"))
checks_path=DATA/"publisher-checks"/(MONTH+".json")
checks=json.loads(checks_path.read_text(encoding="utf-8")) if checks_path.exists() else {}
out=DATA/"quality"/(MONTH+".json")
out.parent.mkdir(parents=True,exist_ok=True)
candidates=[a for a in report["articles"] if a["date_basis"]!="crossref_online"]
records=[]
for i,a in enumerate(candidates,1):
    doi=a["doi"]
    entry={"doi":doi,"journal":a["journal"],"title":a["title"],"source":"Crossref DOI API",
           "status":"needs_manual_review","online_date":None,"reason":"No explicit online-first date in monthly data"}
    url="https://api.crossref.org/works/"+urllib.parse.quote(doi,safe="/")
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Literaturmonitor/1.0 (monthly academic metadata audit)","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=18) as response:
                item=json.load(response)["message"]
            online=item.get("published-online") or item.get("posted")
            if online:
                parts=online.get("date-parts",[[]])[0]
                if len(parts)>=3:
                    try:
                        date=dt.date(*map(int,parts[:3])).isoformat()
                        entry["online_date"]=date
                        entry["status"]="candidate_online_month_match" if date[:7]==MONTH else "candidate_online_other_month"
                        entry["reason"]="Explicit Crossref online date found; independent publisher confirmation still required"
                    except (ValueError,TypeError):pass
            break
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,KeyError,ValueError) as exc:
            entry["reason"]="Crossref recheck failed: "+str(exc)[:110]
            if isinstance(exc,urllib.error.HTTPError) and exc.code not in (429,500,502,503,504):break
            if attempt<2:time.sleep(2**attempt)
    # Europe PMC: match exact DOI; use electronicPublicationDate only.
    # firstPublicationDate can be inferred from incomplete dates and is not proof of online-first.
    query=urllib.parse.urlencode({"query":'EXT_ID:"'+doi+'" OR DOI:"'+doi+'"',"format":"json","resultType":"core","pageSize":"5"})
    epmc_url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?"+query
    try:
        req=urllib.request.Request(epmc_url,headers={"User-Agent":"Literaturmonitor/1.0 (research date audit)"})
        with urllib.request.urlopen(req,timeout=16) as response:
            hits=json.load(response).get("resultList",{}).get("result",[])
        exact=[hit for hit in hits if (hit.get("doi") or "").lower()==doi.lower()]
        if exact:
            hit=exact[0]
            entry["europe_pmc"]={"source":hit.get("source"),"id":hit.get("id"),
                "electronic_publication_date":hit.get("electronicPublicationDate"),
                "first_publication_date":hit.get("firstPublicationDate")}
            edate=hit.get("electronicPublicationDate")
            if edate and len(edate)==10 and edate[4]=="-" and edate[7]=="-":
                entry["europe_pmc"]["electronic_date_month_match"]=edate[:7]==MONTH
                if entry["status"]=="needs_manual_review":
                    entry["status"]="europe_pmc_electronic_month_match" if edate[:7]==MONTH else "europe_pmc_electronic_other_month"
                    entry["online_date"]=edate
                    entry["source"]="Europe PMC electronicPublicationDate"
                    entry["reason"]="Europe PMC electronic publication date; check publisher for original first-online event"
            elif entry["status"]=="needs_manual_review":
                entry["reason"]="Europe PMC indexed, but no exact electronic publication date"
        else:
            entry["europe_pmc"]={"status":"not_indexed_by_exact_doi"}
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as exc:
        entry["europe_pmc"]={"status":"lookup_failed","error":str(exc)[:110]}
    records.append(entry)
    if i%50==0:print("Kandidaten geprüft:",i,"/",len(candidates),flush=True)
    time.sleep(.18)
status_counts={}
by_journal={}
for entry in records:
    status_counts[entry["status"]]=status_counts.get(entry["status"],0)+1
    j=by_journal.setdefault(entry["journal"],{"total":0,"statuses":{}})
    j["total"]+=1
    j["statuses"][entry["status"]]=j["statuses"].get(entry["status"],0)+1
from quality_counts import online_corroboration_counts
verified,unresolved=online_corroboration_counts(report["articles"],checks)
quality={"month":MONTH,"publication_ready":False,"release_status":"review_required",
         "note":"Automatic checks cannot establish completeness across 24 journals. Editorial approval required.",
         "crossref_online_articles":report["verified_online_count"],
         "independently_corroborrated_online_dates":verified,
         "online_dates_not_corroborrated":unresolved,
         "candidate_count":len(candidates),"candidate_status_counts":status_counts,"candidate_journals":by_journal,
         "candidate_reviews":records}
out.write_text(json.dumps(quality,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in quality.items() if k!="candidate_reviews"},ensure_ascii=False))
