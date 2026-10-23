#!/usr/bin/env python3
"""Conservative independent publisher-page check of Crossref online dates.
No publisher date -> no verified label. Metadata date alone is insufficient.
"""
import datetime as dt
import datetime
import email.utils
import html
import calendar
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
        super().__init__();self.meta=[];self.jsonld=False;self.jsontexts=[];self.jsonbuffer=[];self.title=False;self.titletext=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta":self.meta.append(a)
        if tag=="script" and a.get("type","").lower()=="application/ld+json":self.jsonld=True;self.jsonbuffer=[]
    def handle_endtag(self,tag):
        if tag=="script" and self.jsonld:
            self.jsontexts.append("".join(self.jsonbuffer));self.jsonld=False
    def handle_data(self,data):
        if self.jsonld:self.jsonbuffer.append(data)
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
    preferred=("citation_online_date","citation_publication_date","citation_date","article:published_time","dc.date.issued","dc.date","prism.publicationdate","dc.date.available","dc.date.created","dc.date.published","citation_firstpage","citation_date_online","datepublished","article:published","dc.date")
    for a in p.meta:
        name=(a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
        if name in preferred and a.get("content"):dates.append((name,a["content"]))
    for text in p.jsontexts:
        try:dates.extend(dates_in_json(json.loads(text)))
        except (ValueError,TypeError):pass
    return final,dates
def normalize_date(value):
    """Accept ISO, publisher dd Month yyyy, and common slash dates without guessing."""
    value=html.unescape(str(value)).strip()
    m=re.search(r"(?<![0-9])([12][0-9]{3})[-/]([01]?[0-9])[-/]([0-3]?[0-9])(?![0-9])",value)
    if m:
        try:return dt.date(*map(int,m.groups())).isoformat()
        except ValueError:return None
    for fmt in ("%d %B %Y","%d %b %Y","%B %d, %Y","%b %d, %Y","%d-%b-%Y"):
        try:return dt.datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    return None

ONLINE_KEYS={"citation_online_date","citation_date_online","article:published_time"}
GENERIC_KEYS={"citation_publication_date","citation_date","dc.date.issued","dc.date","prism.publicationdate","datepublished","article:published","datePublished"}

def classify(dates,expected):
    parsed=[(k,v,normalize_date(v)) for k,v in dates]
    # Only explicit online-date metadata is accepted as corroboration.
    online=[(k,v,d) for k,v,d in parsed if k in ONLINE_KEYS and d]
    if not online:return "needs_manual_review",[],parsed
    if any(d!=expected for _,_,d in online):return "date_conflict",[],parsed
    return "publisher_date_match",[(k,v) for k,v,d in online],parsed

def main():
    report=json.loads(SOURCE.read_text(encoding="utf-8"))
    existing=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    processed=0
    for a in report["articles"]:
        if a.get("date_basis")!="crossref_online":continue
        doi=a["doi"];date=a.get("online_date")
        if not date or len(date)!=10:continue
        try:
            url,dates=get_publisher(doi)
            status,evidence,parsed=classify(dates,date)
            existing[doi]={"status":status,"crossref_online_date":date,
                "publisher_url":url,"publisher_dates":dates[:20],
                "evidence":evidence[:3]}
        except Exception as exc:
            existing[doi]={"status":"unavailable","crossref_online_date":date,
                "reason":str(exc)[:160]}
        processed+=1
        if processed%20==0:
            OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        time.sleep(.25)
    OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    counts={status:sum(v.get("status")==status for v in existing.values()) for status in
        ("publisher_date_match","date_conflict","needs_manual_review","unavailable")}
    print(json.dumps({"month":MONTH,"checked":len(existing),"statuses":counts}))
if __name__=="__main__":main()
