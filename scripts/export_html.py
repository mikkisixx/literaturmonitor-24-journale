#!/usr/bin/env python3
"""Generate a self-contained reader-facing HTML report; no JSON or Markdown delivery."""
import argparse
import html
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def h(value):
    return html.escape(str(value if value is not None else ""), quote=True)
def export(month, output):
    report=json.loads((ROOT/"data/months"/(month+".json")).read_text())
    quality=json.loads((ROOT/"data/quality"/(month+".json")).read_text())
    coverage=json.loads((ROOT/"data/coverage"/(month+".json")).read_text())
    if report.get("count") != len(report.get("articles", [])):
        raise ValueError("Article count mismatch; refusing reader HTML export")
    if report.get("verified_online_count", 0) + report.get("candidate_count", 0) != report["count"]:
        raise ValueError("Article classification totals mismatch; refusing HTML export")
    if coverage.get("confirmed_missing_publisher_articles") != len(coverage.get("missing_publisher_articles", [])):
        raise ValueError("Publisher gap evidence inconsistent; refusing HTML export")
    if coverage.get("journals_expected") != 24 or coverage.get("journals_queried") != 24 or coverage.get("query_errors") != 0:
        raise ValueError("Incomplete journal queries; refusing HTML export")
    if quality.get("publication_ready") is not False or quality.get("release_status") != "review_required":
        raise ValueError("Editorial status inconsistent; refusing HTML export")
    approved=quality.get("publication_ready") is True and quality.get("release_status")=="approved"
    # Never infer approval from successful automation or article counts.
    if approved:
        raise ValueError("Reader release requires a separate explicit editorial approval workflow")
    journals={}
    for a in report["articles"]:
        journals.setdefault(a["journal"],[]).append(a)
    sections=[]
    for journal, articles in sorted(journals.items()):
        rows=[]
        for a in articles:
            basis=a.get("date_basis","")
            status="Online-Datum laut Crossref; Verlagsabdeckung ungeprüft" if basis=="crossref_online" else "Monatszuordnung nicht bestätigt"
            rows.append('<article class="entry"><h3>'+h(a.get("title") or "Ohne Titel")+'</h3><p>'+h(a.get("display_date") or a.get("online_date") or "Datum unbekannt")+' · '+h(status)+'</p><a href="https://doi.org/'+h(a["doi"])+'" target="_blank" rel="noopener noreferrer">DOI: '+h(a["doi"])+'</a></article>')
        sections.append('<section class="journal"><h2>'+h(journal)+' <small>('+str(len(articles))+')</small></h2>'+''.join(rows)+'</section>')
    missing=''.join('<li>'+h(a["journal"])+' · '+h(a["publisher_online_date"])+' · <a href="'+h(a["source"])+'" target="_blank" rel="noopener noreferrer">'+h(a["doi"])+'</a></li>' for a in coverage["missing_publisher_articles"])
    page='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Literaturbericht '''+h(month)+''' – Entwurf</title><style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#172436;background:#f4f7fa}*{box-sizing:border-box}body{margin:0}header{background:#152c47;color:white;padding:2.5rem max(1rem,calc((100vw - 1000px)/2))}main{max-width:1000px;margin:2rem auto;padding:0 1rem}.warning{background:#fff0d6;color:#653c00;border-left:5px solid #c77c00;padding:1.2rem;margin:1.5rem 0;font-weight:650}.stats{display:flex;flex-wrap:wrap;gap:.75rem}.stat{background:white;border:1px solid #d9e1e9;border-radius:10px;padding:1rem;min-width:170px;flex:1}.stat strong{display:block;font-size:1.7rem}.journal{background:white;border:1px solid #d9e1e9;border-radius:12px;margin:1.2rem 0;padding:1rem 1.4rem}.journal h2{border-bottom:1px solid #e1e6ed;padding-bottom:.8rem}.journal small{color:#60728a}.entry{padding:.8rem 0;border-bottom:1px solid #edf0f4}.entry:last-child{border:0}.entry h3{font-size:1rem;margin:0}.entry p{font-size:.9rem;color:#52657b;margin:.35rem 0}a{color:#1264a3;overflow-wrap:anywhere}input{width:100%;font:inherit;padding:.8rem;border:1px solid #9aabc0;border-radius:8px}button{font:inherit;padding:.65rem 1rem;border:0;border-radius:8px;background:#205f96;color:white;cursor:pointer}@media print{body{background:white}header{padding:1rem;color:black;background:white}button,input{display:none}.journal{break-inside:avoid}}
</style></head><body><header><h1>Literaturmonitor · '''+h(month)+'''</h1><p>Online-First-Recherche in 24 Fachzeitschriften</p></header><main><div class="warning" role="alert">NICHT REDAKTIONELL FREIGEGEBEN · Unvollständiger Rechercheentwurf. Nicht als vollständigen wissenschaftlichen Monatsbericht veröffentlichen.</div><div class="stats"><div class="stat"><strong>'''+str(report["count"])+'''</strong>Artikel und Kandidaten</div><div class="stat"><strong>'''+str(report["verified_online_count"])+'''</strong>Crossref-Online-Daten</div><div class="stat"><strong>'''+str(report["candidate_count"])+'''</strong>Unbestätigte Kandidaten</div><div class="stat"><strong>'''+str(coverage["journals_independently_verified"])+''' / 24</strong>Vollständig unabhängig geprüfte Journale</div></div><h2>Artikelübersicht</h2><label for="filter">Artikel oder Zeitschrift suchen</label><input id="filter" type="search" placeholder="Titel, DOI oder Zeitschrift"><div id="articles">'''+''.join(sections)+'''</div><section><h2>Nachweislich fehlende Verlagsartikel</h2><p>Diese Artikel sind durch Verlagsseiten belegt, fehlen jedoch in der erfassten Monatsliste.</p><ul>'''+missing+'''</ul></section><p><strong>Methodischer Hinweis:</strong> Erfolgreiche Crossref-Abfragen beweisen keine Vollständigkeit. Ein Ausgabenmonat ist nicht automatisch das erste Online-Veröffentlichungsdatum.</p><button type="button" onclick="window.print()">Drucken / als PDF speichern</button></main><script>document.getElementById('filter').addEventListener('input',function(){const q=this.value.toLocaleLowerCase('de');document.querySelectorAll('.journal').forEach(j=>{let any=false;j.querySelectorAll('.entry').forEach(e=>{const show=e.textContent.toLocaleLowerCase('de').includes(q)||j.querySelector('h2').textContent.toLocaleLowerCase('de').includes(q);e.hidden=!show;any=any||show});j.hidden=!any})})</script></body></html>'''
    output.mkdir(parents=True,exist_ok=True)
    target=output/("Literaturbericht-"+month+"-ENTWURF.html")
    target.write_text(page,encoding="utf-8")
    print("HTML created:",target)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("month")
    parser.add_argument("--output",type=Path,default=ROOT/"exports")
    args=parser.parse_args()
    export(args.month,args.output)
