#!/usr/bin/env python3
"""Conservative independent publisher-page check of Crossref online dates.
No publisher date -> no verified label. Metadata date alone is insufficient.
"""
import datetime as dt
import html.parser
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
MONTH=sys.argv[1] if len(sys.argv)>1 else (dt.date.today().replace(day=1)-dt.timedelta(days=1)).strftime("%Y-%m")
SOURCE=DATA/"months"/(MONTH+".json")
OUT=DATA/"publisher-checks"/(MONTH+".json")
OUT.parent.mkdir(exist_ok=True,parents=True)
class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__();self.meta=[];self.jsonld=False;self.jsontexts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta":self.meta.append(a)
        if tag=="script" and a.get("type","").lower()=="application/ld+json":self.jsonld=True
    def handle_endtag(self,tag):
        if tag=="script":self.jsonld=False
    def handle_data(self,data):
        if self.jsonld:self.jsontexts.append(data)
def dates_in_json(obj):
    if isinstance(obj,list):
        for x in obj:yield from dates_in_json(x)
    elif isinstance(obj,dict):
        typ=obj.get("@type",[])
        if isinstance(typ,str):typ=[typ]
        if any(t in ("ScholarlyArticle","Article","MedicalScholarlyArticle") for t in typ):
            for k in ("datePublished","dateCreated"):
                if obj.get(k):yield (k,str(obj[k]))
        for v in obj.values():
            if isinstance(v,(dict,list)):yield from dates_in_json(v)
def get_publisher(doi):
    url="https://doi.org/"+urllib.parse.quote(doi,safe="/")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; academic-literature-verification/1.0)","Accept":"text/html"})
    with urllib.request.urlopen(req,timeout=22) as response:
        final=response.url
        if urllib.parse.urlsplit(final).hostname in ("doi.org","dx.doi.org"):raise ValueError("No publisher redirect")
        data=response.read(1600000).decode("utf-8","replace")
    p=Parser();p.feed(data)
    dates=[]
    preferred=("citation_online_date","citation_publication_date","citation_date","article:published_time","dc.date.issued","dc.date","prism.publicationdate")
    for a in p.meta:
        name=(a.get("name") or a.get("property") or "").lower()
        if name in preferred and a.get("content"):dates.append((name,a["content"]))
    for text in p.jsontexts:
        try:dates.extend(dates_in_json(json.loads(text)))
        except (ValueError,TypeError):pass
    return final,dates
def main():
    report=json.loads(SOURCE.read_text())
    existing=json.loads(OUT.read_text()) if OUT.exists() else {}
    count=0
    for a in report["articles"]:
        if a.get("date_basis")!="crossref_online":continue
        doi=a["doi"];date=a.get("online_date")
        if not date or len(date)!=10:continue
        if doi in existing and existing[doi].get("status")=="publisher_date_match":continue
        try:
            url,dates=get_publisher(doi)
            exact=[(k,v) for k,v in dates if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}",v) and v[:10]==date]
            conflicting=[(k,v) for k,v in dates if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}",v) and v[:10]!=date]
            # Generic publication dates may represent an issue, not the first online date.
            online=[(k,v) for k,v in exact if k in ("citation_online_date","article:published_time")]
            status="publisher_date_match" if online and not conflicting else "needs_manual_review"
            existing[doi]={"status":status,"crossref_online_date":date,"publisher_url":url,"publisher_dates":dates[:12],"evidence":online[:2]}
        except Exception as exc:
            existing[doi]={"status":"unavailable","crossref_online_date":date,"reason":str(exc)[:120]}
        count+=1
        if count%20==0:
            OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n")
        time.sleep(.35)
    OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"checked":len(existing),"publisher_matches":sum(v.get("status")=="publisher_date_match" for v in existing.values()),"manual_or_unavailable":sum(v.get("status")!="publisher_date_match" for v in existing.values())}))
if __name__=="__main__":main()
