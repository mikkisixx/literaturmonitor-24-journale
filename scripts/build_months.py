#!/usr/bin/env python3
"""Produce transparently labeled monthly candidate reports from Crossref."""
import datetime as dt
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
data=ROOT/"data"
observed=json.loads((data/"observed.json").read_text(encoding="utf-8"))
out=data/"months"
out.mkdir(parents=True,exist_ok=True)
months={}
current=dt.date.today().strftime("%Y-%m")
for doi,item in observed.items():
    online=item.get("online_date")
    published=item.get("published_date")
    matched=item.get("matched_months") or []
    eligible=set(m for m in matched if "2026-01"<=m<=current)
    # An explicit online month takes precedence over a general publication month.
    if online and len(online)==10:
        eligible={online[:7]} if "2026-01"<=online[:7]<=current else set()
    if online and "2026-01"<=online[:7]<=current:eligible.add(online[:7])
    if not online and published and "2026-01"<=published[:7]<=current:eligible.add(published[:7])
    for month in eligible:
        explicit=bool(online and online.startswith(month))
        basis="crossref_online" if explicit else "crossref_published_unverified"
        record={"doi":doi,"title":item.get("title",""),"journal":item.get("journal",""),
            "category":item.get("category",""),"online_date":online if explicit else None,
            "display_date":online if explicit else (published if published and published.startswith(month) else month+" (Filtertreffer)"),
            "date_basis":basis,"url":"https://doi.org/"+doi}
        months.setdefault(month,[]).append(record)
index=[]
for month,items in sorted(months.items()):
    items.sort(key=lambda x:(x["journal"],x["display_date"],x["title"]))
    report={"month":month,"classification":"Crossref online dates and unverified publication-month candidates; not publisher validated",
        "count":len(items),"verified_online_count":sum(a["date_basis"]=="crossref_online" for a in items),
        "candidate_count":sum(a["date_basis"]!="crossref_online" for a in items),"articles":items}
    (out/(month+".json")).write_text(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    index.append({"month":month,"count":len(items)})
(out/"index.json").write_text(json.dumps({"months":index,"warning":"Ungeprüfte Crossref-Kandidaten werden getrennt angezeigt. Der Filtertreffer allein bestätigt kein Online-First-Datum."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Monatsdateien:",len(index))
