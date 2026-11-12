"""Count corroborated online dates for the current month's Crossref-online articles.

Historical checks and unrelated DOI keys must not inflate the corroboration rate.
DOIs are case-insensitive, including keys in publisher-checks JSON.
"""
def online_corroboration_counts(articles, checks):
    online = {
        a["doi"].strip().casefold()
        for a in articles
        if a.get("date_basis") == "crossref_online" and a.get("doi", "").strip()
    }
    accepted = {"publisher_date_match", "pubmed_date_match"}
    normalized_checks = {
        doi.strip().casefold(): check
        for doi, check in checks.items()
        if isinstance(doi, str) and isinstance(check, dict)
    }
    verified = sum(
        normalized_checks.get(doi, {}).get("status") in accepted
        for doi in online
    )
    return verified, len(online) - verified
