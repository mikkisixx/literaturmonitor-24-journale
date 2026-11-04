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
        truncated=name in back.get("title_fallback_truncated",[])
        issue="query_error" if err or count is None else ("zero_hits_requires_independent_check" if count==0 else "source_completeness_unverified")
        if truncated and not err: issue="title_fallback_truncated_requires_publisher_check"
        rows.append({"journal":name,"group":group,"crossref_query_count":count,"crossref_online":entries.get("crossref_online",0),"other_candidates":entries.get("other_candidates",0),"status":issue,"error":err,"title_fallback_truncated":truncated,"publisher_coverage_verified":False})
evidence_path=data/"publisher-evidence"/(month+".json")
evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {"findings":[]}
existing_dois={a["doi"].lower() for a in report["articles"]}
report_by_doi={a["doi"].lower():a for a in report["articles"]}
# Publisher evidence is independent input: validate before counting and deduplicate DOI.
# Malformed or contradictory records must never inflate corroboration counts.
evidence_by_doi={}
for finding in evidence.get("findings",[]):
    doi=str(finding.get("doi","")).strip().lower()
    journal=finding.get("journal")
    date=finding.get("publisher_online_date")
    source=finding.get("source","")
    if not doi.startswith("10.") or journal not in {r["journal"] for r in rows}:
        raise ValueError("Invalid publisher evidence DOI or journal")
    if not isinstance(date,str) or not date.startswith(month+"-"):
        raise ValueError("Publisher evidence date does not match audit month")
    import datetime
    try: datetime.date.fromisoformat(date)
    except ValueError as exc: raise ValueError("Invalid publisher evidence date") from exc
    if not isinstance(source,str) or not source.startswith("https://"):
        raise ValueError("Publisher evidence requires HTTPS source URL")
    if doi in evidence_by_doi and evidence_by_doi[doi]!=finding:
        raise ValueError("Conflicting publisher evidence for DOI "+doi)
    evidence_by_doi[doi]=finding
missing=[{**a,"in_monthly_report":False} for doi,a in evidence_by_doi.items() if doi not in existing_dois]
# A present DOI does not corroborate the date: compare publisher first-online dates.
date_conflicts=[]
for doi,finding in evidence_by_doi.items():
    if doi not in report_by_doi:
        continue
    article=report_by_doi[doi]
    reported=article.get("online_date") or article.get("date")
    if reported != finding["publisher_online_date"]:
        date_conflicts.append({"doi":doi,"journal":finding["journal"],
            "publisher_online_date":finding["publisher_online_date"],
            "reported_online_date":reported,"source":finding["source"]})
for row in rows:
    journal_missing=[a for a in missing if a["journal"]==row["journal"]]
    row["publisher_examples_missing"]=len(journal_missing)
    if journal_missing:row["status"]="confirmed_missing_publisher_articles"
coverage={"month":month,"journals_expected":sum(map(len,collect.JOURNALS.values())),"journals_queried":back.get("checked"),"query_errors":len(back.get("errors",{})),"title_fallback_truncated":back.get("title_fallback_truncated",[]),"zero_hit_journals":sum(r["crossref_query_count"]==0 for r in rows),"journals_independently_verified":0,"complete":False,"publisher_examples_checked":len(evidence_by_doi),"confirmed_missing_publisher_articles":len(missing),"missing_publisher_articles":missing,"publisher_date_conflicts":date_conflicts,"publisher_date_conflict_count":len(date_conflicts),"reason":"No independent publisher-by-publisher exhaustive article enumeration has been performed.","journals":rows}
out=data/"coverage"/(month+".json");out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")
quality["coverage_summary"]={k:v for k,v in coverage.items() if k!="journals"}
quality["publication_ready"]=False
quality["release_status"]="review_required"
quality_path.write_text(json.dumps(quality,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(coverage["zero_hit_journals"]))
