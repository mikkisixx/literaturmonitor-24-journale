#!/usr/bin/env python3
"""Reader-friendly self-contained HTML, styled after Neuerscheinungen_2026-08.html."""
import argparse
import html
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MONTHS=["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
def esc(s): return html.escape(str(s or ""),quote=True)
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
def human_date(value):
    try:
        d=date.fromisoformat(value)
        return f"{d.day}. {MONTHS[d.month-1]} {d.year}"
    except (ValueError,TypeError): return "Online-Datum nicht bestätigt"
def export(month, output):
    root=ROOT/"data/months"/(month+".json")
    report=json.loads(root.read_text(encoding="utf-8"))
    quality=json.loads((ROOT/"data/quality"/(month+".json")).read_text(encoding="utf-8"))
    coverage=json.loads((ROOT/"data/coverage"/(month+".json")).read_text(encoding="utf-8"))
    if report["count"]!=len(report["articles"]): raise ValueError("Artikelanzahl inkonsistent")
    if coverage["journals_expected"]!=24 or coverage["journals_queried"]!=24: raise ValueError("Nicht alle Journale abgefragt")
    year,number=map(int,month.split("-"))
    heading=f"Neuerscheinungen {MONTHS[number-1]} {year}"
    groups=defaultdict(list)
    for item in report["articles"]:
        online=item.get("online_date")
        if item.get("date_basis") not in ("crossref_online","publisher_online") or not online:
            continue
        try:
            if date.fromisoformat(online).strftime("%Y-%m") != month:
                continue
        except (ValueError, TypeError):
            continue
        groups[item["journal"]].append(item)
    selected_count=sum(map(len,groups.values()))
    nav=[]
    sections=[]
    for journal,items in sorted(groups.items()):
        ident=slug(journal)
        nav.append(f'<a href="#{esc(ident)}">{esc(journal)} <span>{len(items)}</span></a>')
        articles=[]
        for item in sorted(items,key=lambda x:(x.get("online_date") or "",x.get("title") or ""),reverse=True):
            doi=item.get("doi") or ""
            url=item.get("url") or ("https://doi.org/"+doi if doi else "")
            if not url.startswith(("https://","http://")): url=""
            authors=item.get("authors") or []
            if isinstance(authors,list): authors=", ".join(authors[:3])+(", et al." if len(authors)>3 else "")
            date_label=human_date(item.get("online_date")) if item.get("date_basis") in ("crossref_online","publisher_online") else "Online-Erstveröffentlichung nicht bestätigt"
            doi_html=f'<span class="doi">DOI: {esc(doi)}</span>' if doi else ""
            link=f'<a class="open" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Artikel öffnen ↗</a>' if url else ""
            title=f'<a class="title" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(item.get("title") or "Ohne Titel")}</a>' if url else f'<span class="title">{esc(item.get("title") or "Ohne Titel")}</span>'
            articles.append(f'<article>{title}<div class="authors">{esc(authors)}</div><div class="meta"><span>{esc(date_label)}</span>{doi_html}</div>{link}</article>')
        sections.append(f'<section id="{esc(ident)}"><div class="journal-head"><h2>{esc(journal)}</h2><span>{len(items)} Artikel</span></div>{"".join(articles)}</section>')
    css="""
:root{--bg:#f4f6f8;--paper:#fff;--ink:#17202a;--muted:#667085;--line:#e4e7ec;--accent:#2457a7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif;line-height:1.5}
header{background:#17202a;color:white;padding:36px 24px}.wrap{max-width:980px;margin:auto}
h1{margin:.15rem 0 .4rem;font-size:2rem}.eyebrow{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;opacity:.7}
main{max-width:980px;margin:28px auto 60px;padding:0 20px}
.panel,.summary,section{background:var(--paper);border:1px solid var(--line);border-radius:14px}
.panel{padding:22px;margin-bottom:24px}.controls{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
label{display:block;font-weight:650;font-size:.9rem;margin-bottom:5px}
input{padding:9px;border:1px solid #cfd4dc;border-radius:8px;background:white;width:100%}
button{border:0;border-radius:8px;padding:10px 14px;font-weight:700;cursor:pointer;background:var(--accent);color:white}
.note{color:var(--muted);font-size:.86rem;margin-top:12px}.summary{padding:20px 22px;margin-bottom:24px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}nav a{text-decoration:none;color:var(--accent);background:#f7f9fc;border:1px solid var(--line);padding:7px 10px;border-radius:8px;font-size:.9rem}nav span{color:var(--muted);margin-left:5px}
section{margin:20px 0;overflow:hidden}.journal-head{display:flex;justify-content:space-between;gap:16px;align-items:baseline;padding:20px 24px;background:#fafafa;border-bottom:1px solid var(--line)}
h2{font-size:1.3rem;margin:0}.journal-head span{font-size:.85rem;color:var(--muted);white-space:nowrap}
article{position:relative;padding:22px 24px;border-bottom:1px solid var(--line)}article:last-child{border-bottom:0}
.title{display:block;color:#173f78;text-decoration:none;font-weight:700;font-size:1.08rem;line-height:1.38;padding-right:135px}.title:hover{text-decoration:underline}
.authors{margin-top:7px;color:#344054;font-size:.93rem}.meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:7px;color:var(--muted);font-size:.86rem}
.doi{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.8rem}.open{position:absolute;right:24px;top:22px;text-decoration:none;color:var(--accent);font-size:.88rem;font-weight:650}
.warning{border-left:4px solid #b7791f;background:#fff9ed;padding:12px 16px;border-radius:7px;margin-bottom:20px;font-size:.9rem}
@media(max-width:650px){header{padding:28px 20px}h1{font-size:1.65rem}.title{padding-right:0}.open{position:static;display:inline-block;margin-top:10px}article{padding:19px}.journal-head{padding:17px 19px}}
@media print{body{background:white}.panel{display:none}header{background:white;color:black;padding:15px 0}main{margin-top:0}section,.summary{break-inside:avoid;border-color:#bbb}.open{display:none}}
"""

    page=f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{esc(heading)}</title><style>{css}</style></head><body>
<header><div class="wrap"><div class="eyebrow">Wissenschaftlicher Literaturmonitor · Online First</div><h1>{esc(heading)}</h1><div>Monatliche Neuerscheinungen aus 24 Fachzeitschriften</div></div></header>
<main>
<div class="summary"><div class="note">{selected_count} Artikel mit ausgewiesenem Online-Veröffentlichungsdatum im ausgewählten Monat · {len(groups)} Zeitschriften mit Treffern</div><nav id="nav">{"".join(nav)}</nav></div>
<div id="sections">{"".join(sections)}</div></main>

</body></html>'''
    if "Rechercheentwurf:" in page or "Artikel oder Zeitschrift suchen" in page:
        raise AssertionError("Unerwünschte Berichtselemente")
    output.mkdir(parents=True,exist_ok=True)
    target=output/("Neuerscheinungen_"+month+".html")
    target.write_text(page,encoding="utf-8")
    print("HTML created:",target)
    return target
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("month")
    p.add_argument("--output",type=Path,default=ROOT/"exports")
    a=p.parse_args()
    export(a.month,a.output)
