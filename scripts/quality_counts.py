"""Count only publisher checks belonging to the current month's online articles.

Historical checks can remain on disk after Crossref changes an article's date or
the monthly report is rebuilt. They must never inflate the corroboration rate.
"""
def online_corroboration_counts(articles, checks):
    online={a["doi"].strip().lower() for a in articles if a.get("date_basis")=="crossref_online"}
    accepted={"publisher_date_match","pubmed_date_match"}
    verified=sum(
        checks.get(doi,{}).get("status") in accepted
        for doi in online
    )
    return verified,len(online)-verified
