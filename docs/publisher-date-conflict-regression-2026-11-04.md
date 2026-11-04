# Publisher vs PubMed date conflict: fail-closed regression (2026-11-04)

## Verified defect
In `scripts/verify_publishers.py`, the PubMed reconciliation branch previously overwrote `date_conflict` from an explicit publisher online date with `pubmed_date_match` whenever PubMed agreed with Crossref. This silently discarded contrary publisher evidence.

## Fix
`reconcile_status()` now preserves `date_conflict` whenever either publisher or PubMed electronic-date evidence conflicts with the expected Crossref date. Only unconflicted PubMed matches may promote an otherwise unverified result to `pubmed_date_match`. Five deterministic offline tests cover both conflict directions, promotion, lack of evidence, and explicit online-date classification.

Commits: [4830b333](https://github.com/mikkisixx/literaturmonitor-24-journale/commit/4830b333612b7d97c1442c62b2befdcc3a1f6ae5), [dd0d2f02](https://github.com/mikkisixx/literaturmonitor-24-journale/commit/dd0d2f02698e2585cb2927d294759771bf349f43), [24cda2f2](https://github.com/mikkisixx/literaturmonitor-24-journale/commit/24cda2f2301be451747c45ce739291ff05889a4a).

## Validation
GitHub fast regression run [41763918677](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41763918677) succeeded on the reconciliation refactor, before the new tests were added. Run [41763928160](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41763928160) validates the additional tests and was still in progress at documentation time. A new full monthly workflow is also queued/running; no scientific completeness claim follows from its success.

## Open work
Publisher-native exhaustive inventories for all 24 journals, particularly six original zero-hit journals, remain absent. Crossref/Europe PMC/NCBI metadata are not substitutes for publisher-native complete inventories. The eight known publisher omissions remain relevant; investigate them against the latest regenerated month data. Never mark a report editorially approved without explicit user approval.
