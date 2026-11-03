# Publisher evidence integrity — 2026-11-04

## Failure reviewed
GitHub Actions run [41722247631](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41722247631) completed with failure at **Datenkonsistenz und redaktionelle Sperre prüfen**. The assertion was `Crossref queries incomplete`. The upstream collection, publisher checking and coverage auditing steps completed, and the diagnostic artifact was saved. Fast regression tests on the corresponding commit succeeded. This is a genuine *coverage failure*, not a reason to bypass validation.

Previous diagnostics identify title-fallback pagination limits for American Journal of Dentistry, International Journal of Prosthodontics and Quintessence International. The fuzzy Crossref title search cannot be considered exhaustive after a fixed page cap. Keep these journals marked incomplete until independently inventoried; do not turn a cap into a false success.

## Change in this run
`scripts/audit_coverage.py` now validates publisher evidence entries before counting them. DOI must be DOI-shaped, journal must be one of the configured 24, online publication date must be a valid date in the audited month, and a HTTPS source URL must be provided. Repeated identical DOI evidence counts once; conflicting records for one DOI fail the audit. These are *input integrity checks*, not publisher authenticity verification. They do not establish that the linked page actually supports the date.

## Remaining work
1. Implement a bounded **publisher-native** article inventory for each journal, with source URL, DOI, first-online date, pagination completeness and retrieval timestamp; use publisher APIs/TOCs where appropriate, not broad Crossref title search as a substitute.
2. Add deterministic offline tests for malformed/duplicate/conflicting evidence and for coverage gating.
3. Re-run full workflow and confirm quality gate and standalone HTML export; never remove the editorial release lock without explicit user approval.
4. Review all 24 journal inventories, especially the six zero-hit journals; the eight documented publisher examples do not prove completeness.

**Editorial status: NOT APPROVED.**