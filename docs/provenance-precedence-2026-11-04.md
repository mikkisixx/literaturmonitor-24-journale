# Publisher provenance precedence – 2026-11-04

## Verified defect and repair

In `scripts/verify_publishers.py`, `reconcile_status("publisher_date_match", "date_match")` previously returned `pubmed_date_match`. This erased the stronger independent publisher-page provenance when PubMed also agreed with the date.

The reconciliation now retains `publisher_date_match` when both sources agree. Any `date_conflict` from either source still overrides a match. PubMed can promote only otherwise unverified publisher evidence.

Regression cases added in `tests/test_verify_publishers.py` for publisher+PubMed agreement and publisher match with no PubMed record.

Commits: `5cffb97ce0acfb285c30420a3e2530efaa380edf` and `88c56e42d67d703d6fc597893bfd0496539eeb3f`.

## Execution verification

Prior to the change, the most recent completed monthly run and fast regression run were successful (GitHub Actions run IDs 41780294481 and 41780294545). Following the change, fast regression run 41788558525 was queued at inspection time. Passing execution of the new tests is **not yet confirmed**.

## Coverage and editorial status

October coverage reports 24/24 queried, zero query errors, four zero-count journals, and three title-fallback truncations. Independent exhaustive publisher inventories remain 0/24; `complete=false` and `publication_ready=false`. No editorial approval is implied by successful CI or Pages deployment.

## Next

Confirm fast tests and full monthly run. Expand reproducible publisher-by-publisher first-online inventories for zero-hit journals; treat publisher examples and Crossref title fallbacks as partial evidence only.
