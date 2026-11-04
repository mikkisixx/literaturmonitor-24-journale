# Publisher first-online date cross-check (2026-11-04)

The October coverage audit now compares the publisher's independently recorded first-online date with the corresponding DOI's reported online date. DOI presence alone is not sufficient date corroboration. Differences are recorded as `publisher_date_conflicts` and `publisher_date_conflict_count` in coverage and quality summaries.

Current upstream observations before rerun: 24/24 journals queried, 4 zero-hit journals, 3 truncated title fallbacks, 563 Crossref online articles, 8 publisher examples, 0 journals exhaustively publisher-verified. The release remains `review_required` and `publication_ready=false`.

**Limitations:** Eight article-level examples are not an exhaustive publisher inventory. The new comparison does not establish completeness. Next steps: verify report date field semantics, add targeted regression fixtures for a matching and a mismatching DOI, inspect resulting GitHub Actions, then independently enumerate the six historically zero-hit journals using publisher issue/online-first archives. Never set publication-ready without explicit editorial approval.
