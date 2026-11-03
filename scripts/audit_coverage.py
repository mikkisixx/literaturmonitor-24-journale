#!/usr/bin/env python3
"""Conservative journal coverage audit: successful queries are not proof of completeness."""
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect
month=sys.argv[1] if len(sys.argv)>1 else "2026-10"
data=ROOT/"data"
back=json.loads((data/("backfill-"+month+".json")).read_text())
report=json.loads((data/"months"/(month+".json")).read_text())
quality_path=data/"quality"/(month+".json")
quality=json.loads(quality_path.read_text())
observed={}
for a in report["articles"]:
    j=observed.setdefault(a["journal"],{"crossref_online":0,"other_candidates":0})
    j["crossref_online" if a["date_basis"]=="crossref_online" else "other_candidates"]+=1
rows=[]
for group,names in collect.JOURNALS.items():
    for name in names:
        count=back.get("counts",{}).get(name)
        err=back.get("errors",{}).get(name)
        entries=observed.get(name,{})
        issue="query_error" if err or count is None else ("zero_hits_requires_independent_check" if count==0 else "source_completeness_unverified")
        rows.append({"journal":name,"group":group,"crossref_query_count":count,"crossref_online":entries.get("crossref_online",0),"other_candidates":entries.get("other_candidates",0),"status":issue,"error":err,"publisher_coverage_verified":False})
evidence_path=data/"publisher-evidence"/(month+".json")
evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {"findings":[]}
existing_dois={a["doi"].lower() for a in report["articles"]}
missing=[{**a,"in_monthly_report":a["doi"].lower() in existing_dois} for a in evidence["findings"] if a["doi"].lower() not in existing_dois]
for row in rows:
    journal_missing=[a for a in missing if a["journal"]==row["journal"]]
    row["publisher_examples_missing"]=len(journal_missing)
    if journal_missing:row["status"]="confirmed_missing_publisher_articles"
coverage={"month":month,"journals_expected":sum(map(len,collect.JOURNALS.values())),"journals_queried":back.get("checked"),"query_errors":len(back.get("errors",{})),"zero_hit_journals":sum(r["crossref_query_count"]==0 for r in rows),"journals_independently_verified":0,"complete":False,"publisher_examples_checked":len(evidence["findings"]),"confirmed_missing_publisher_articles":len(missing),"missing_publisher_articles":missing,"reason":"No independent publisher-by-publisher exhaustive article enumeration has been performed.","journals":rows}
out=data/"coverage"/(month+".json");out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")
quality["coverage_summary"]={k:v for k,v in coverage.items() if k!="journals"}
quality["publication_ready"]=False
quality["release_status"]="review_required"
quality_path.write_text(json.dumps(quality,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(coverage["zero_hit_journals"]))
