# Crossref zero-hit fallback — 2026-11-03

## Problem
A single ISSN can omit eISSN/print-ISSN records. Even after querying registered ISSNs, a zero-hit month cannot be interpreted as no online-first publications. October 2026 contained six zero-hit journals, including two with independently publisher-dated missing Springer articles.

## Implemented
- Query all Crossref-listed ISSNs for each configured journal (previous change).
- If all ISSN-filtered queries return zero articles, run a second Crossref discovery path with `query.container-title`, publication-month filters and pagination.
- Only accept articles whose returned `container-title` **exactly matches** the normalized configured journal title or its explicitly registered alias. Similar titles are rejected.
- Deduplicate on DOI and preserve online/published dates separately.
- Regression tests reject similarly named journals and accept known aliases.

## Scientific limits
The fallback is **not independent publisher evidence**: it is a second query against Crossref. Its returned records are still subject to publisher first-online date checks. A zero-hit fallback remains unverified, not a verified empty month. `audit_coverage.py` continues to mark all 24 journals unverified and prevents automatic editorial approval.

## Next
1. Inspect the monthly GitHub Actions run, especially unit tests and timeouts.
2. Compare any newly discovered DOIs against publisher pages and `data/publisher-evidence/2026-10.json`.
3. Implement publisher-specific, paginated first-online inventories for all journals, beginning with the six zero-hit titles; validate date provenance, DOI identity, pagination exhaustion, and gaps with reproducible fixtures.
4. Do not release a report as scientifically complete without publisher-level evidence for every journal.
