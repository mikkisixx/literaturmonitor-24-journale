#!/usr/bin/env python3
"""Generate provisional monthly views from explicit Crossref published-online dates."""
import datetime as dt
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
data=ROOT/"data"
observed=json.loads((data/"observed.json").read_text(encoding="utf-8"))
out=data/"months"
out.mkdir(parents=True,exist_ok=True)
months={}
for doi,item in observed.items():
    date=item.get("online_date") or item.get("published_date")
    if not date or len(date)!=10:continue
    month=date[:7]
    if month<"2026-01" or month>dt.date.today().strftime("%Y-%m"):continue
    months.setdefault(month,[]).append({"doi":doi,"title":item.get("title",""),"journal":item.get("journal",""),"category":item.get("category",""),"online_date":item.get("online_date"),"display_date":date,"date_basis":"crossref_online" if item.get("online_date") else "crossref_published_unverified","url":"https://doi.org/"+doi})
index=[]
for month,items in sorted(months.items()):
    items.sort(key=lambda x:(x["journal"],x["display_date"],x["title"]))
    report={"month":month,"classification":"Crossref online dates plus separate published-date candidates; none independently publisher verified","count":len(items),"verified_online_count":sum(bool(a["online_date"]) for a in items),"candidate_count":sum(not a["online_date"] for a in items),"articles":items}
    (out/(month+".json")).write_text(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    index.append({"month":month,"count":len(items)})
(out/"index.json").write_text(json.dumps({"months":index,"warning":"Vorläufige Crossref-Ansicht mit getrennt gekennzeichneten Online-Daten und unsicheren Publikationsdatum-Kandidaten. Nicht als vollständige Online-First-Ausgabe verwenden."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Monatsdateien:",len(index))
