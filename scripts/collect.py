#!/usr/bin/env python3
"""Daily Crossref collection. Technical monitoring, not proof of complete Online First coverage."""
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
JOURNALS = {
"Zahnmedizin": ["Journal of Dental Research","Dental Materials","Journal of Dentistry","American Journal of Dentistry","Journal of Adhesive Dentistry","Journal of Prosthetic Dentistry","International Journal of Prosthodontics","Quintessence International","Operative Dentistry","Clinical Oral Investigations","European Journal of Oral Sciences","The Journal of Esthetic and Restorative Dentistry","International Endodontic Journal","Journal of Endodontics","Dental Traumatology","International Journal of Paediatric Dentistry","BMC Oral Health"],
"Biomaterialien": ["Journal of the Mechanical Behavior of Biomedical Materials","Journal of Materials Science: Materials in Medicine","Acta Biomaterialia","Journal of Oral Rehabilitation"],
"Engineering": ["Journal of the American Ceramic Society","Journal of the European Ceramic Society","Journal of Biomechanics"]}
ISSN = {"American Journal of Dentistry":"0894-8275","Journal of Adhesive Dentistry":"1461-5185","International Journal of Prosthodontics":"1942-4426","Quintessence International":"0033-6572"}
ALIASES = {"International Journal of Prosthodontics":"The International Journal of Prosthodontics","The Journal of Esthetic and Restorative Dentistry":"Journal of Esthetic and Restorative Dentistry"}
AGENT = "Literaturmonitor/0.1 (public research metadata; https://github.com/mikkisixx/literaturmonitor-24-journale)"
def get(url):
    for n in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=45) as r:
                return json.load(r)["message"]
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
            if isinstance(exc,urllib.error.HTTPError) and exc.code not in (429,500,502,503,504):
                raise
            if n==3: raise
            time.sleep(2**n*2)
def url(path,params):
    return "https://api.crossref.org/"+path+"?"+urllib.parse.urlencode(params)
def norm(s):
    return "".join(c for c in s.casefold() if c.isalnum())
def resolve(name):
    if name in ISSN:return ISSN[name]
    data=get(url("journals",{"query":ALIASES.get(name,name),"rows":20}))
    for j in data.get("items",[]):
        if norm(j.get("title","")) in (norm(name),norm(ALIASES.get(name,name))):
            return (j.get("ISSN") or [None])[0]
    raise ValueError("Keine exakte Zeitschriftenzuordnung")
def date_field(item,key):
    parts=(item.get(key) or {}).get("date-parts",[])
    if not parts or len(parts[0])!=3:return None
    try:return dt.date(*parts[0]).isoformat()
    except (TypeError,ValueError):return None
def main():
    today=dt.date.today()
    since=(today-dt.timedelta(days=45)).isoformat()
    oldfile=DATA/"observed.json"
    old=json.loads(oldfile.read_text()) if oldfile.exists() else {}
    errors={};counts={};candidates={}
    for group,names in JOURNALS.items():
        for name in names:
            try:
                issn=resolve(name)
                if not issn:raise ValueError("Keine ISSN")
                cursor="*";seen=0
                while True:
                    message=get(url("works",{"filter":f"from-index-date:{since},until-index-date:{today.isoformat()},issn:{issn}","rows":200,"cursor":cursor,"select":"DOI,title,published-online,published-print,published,created,indexed,container-title,ISSN,URL"}))
                    items=message.get("items",[])
                    for a in items:
                        doi=a.get("DOI","").strip().lower()
                        if not doi:continue
                        seen+=1
                        online=date_field(a,"published-online")
                        entry=old.get(doi,{})
                        entry.update({"doi":doi,"title":(a.get("title") or [""])[0],"journal":name,"category":group,"online_date":online,"published_date":date_field(a,"published"),"print_date":date_field(a,"published-print"),"url":a.get("URL") or "https://doi.org/"+doi,"last_seen":today.isoformat()})
                        entry.setdefault("first_seen",today.isoformat())
                        old[doi]=entry
                        if not online:candidates[doi]=name
                    next_cursor=message.get("next-cursor")
                    if len(items)<200 or not next_cursor or next_cursor==cursor:break
                    cursor=next_cursor
                    time.sleep(.15)
                counts[name]={"indexed_records":seen,"issn":issn}
            except Exception as exc:
                errors[name]=str(exc)[:180]
            time.sleep(.2)
    oldfile.write_text(json.dumps(old,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    report={"updated":dt.datetime.now(dt.timezone.utc).isoformat(),"source":"Crossref indexed records (last 45 days)","journal_count":sum(map(len,JOURNALS.values())),"checked":len(counts),"errors":errors,"counts":counts,"unique_observed_doi":len(old),"undated_in_latest_window":len(candidates),"warning":"Technische Datensammlung; kein Nachweis vollständiger Online-First-Erfassung. Datumsfelder und Verlagsquellen sind noch nicht validiert."}
    (DATA/"status.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"checked":len(counts),"errors":len(errors),"observed":len(old)}))
if __name__=="__main__":main()
