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
    date=item.get("online_date")
    if not date or len(date)!=10:continue
    month=date[:7]
    if month<"2026-01" or month>dt.date.today().strftime("%Y-%m"):continue
    months.setdefault(month,[]).append({"doi":doi,"title":item.get("title",""),"journal":item.get("journal",""),"category":item.get("category",""),"online_date":date,"url":"https://doi.org/"+doi})
index=[]
for month,items in sorted(months.items()):
    items.sort(key=lambda x:(x["journal"],x["online_date"],x["title"]))
    report={"month":month,"classification":"Crossref published-online; not independently verified as first online publication","count":len(items),"articles":items}
    (out/(month+".json")).write_text(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    index.append({"month":month,"count":len(items)})
(out/"index.json").write_text(json.dumps({"months":index,"warning":"Vorläufige Crossref-Ansicht. Ungeklärte Veröffentlichungen fehlen; nicht als vollständige Online-First-Ausgabe verwenden."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Monatsdateien:",len(index))
