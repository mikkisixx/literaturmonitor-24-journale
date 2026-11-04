# Quality audit: stale publisher checks (2026-11-04)

## Confirmed defect
`scripts/audit_candidates.py` previously counted all entries in `data/publisher-checks/YYYY-MM.json` as corroborated or unresolved, regardless of whether their DOI still belonged to the current month's `crossref_online` articles. After rebuilding a month or changing date assignments, historical checks could inflate the independently corroborated count and break the validation identity against current Crossref online records.

## Fix
`scripts/quality_counts.py` derives the DOI set from the current monthly report, normalizes case and counts only `publisher_date_match` or `pubmed_date_match` as corroborated. Missing checks and conflicts count as unresolved; stale checks and non-online candidates do not contribute. `scripts/audit_candidates.py` uses this helper. Three deterministic offline regression tests in `tests/test_quality_counts.py` cover stale/candidate records, conflicts/missing checks, and an empty month.

## Remaining scientific limitations
A matched DOI date does **not** demonstrate exhaustive publisher issue/online-first coverage. No journal can be marked independently exhaustive based on article-by-article checks alone. Keep `publication_ready=false`, `release_status=review_required`, and the HTML draft warning until explicit editorial approval and evidence of full journal-level enumeration.

## Verification
Run `python -m unittest discover -s tests -p 'test_*.py' -v` (offline) and check the GitHub Actions **Schnelle Regressionstests** workflow. The monthly pipeline must still finish successfully before its regenerated quality counts can be treated as verified.
