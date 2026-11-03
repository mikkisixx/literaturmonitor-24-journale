# Crossref cursor integrity — 2026-11-03

## Verified failure and status
GitHub Actions run [41713873677](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41713873677) failed at `validate_report.py` with `Crossref queries incomplete`. Backfill completed 21/24 journals; the title fallback exceeded its ten-page safety cap for American Journal of Dentistry, International Journal of Prosthodontics and Quintessence International. This is a real coverage failure, not a test flake. The diagnostic artifact was uploaded. No release approval is justified.

## Additional defect fixed
Previously both `fetch_pages` and `fetch_title_pages` silently stopped when a Crossref page contained exactly 200 items but the next cursor was absent or unchanged. A full page does **not** prove exhaustion, so this could incorrectly mark a truncated inventory as successful. Both paths now raise a descriptive `RuntimeError` in that situation. Two deterministic mocked regression tests cover the stalled cursor cases. Changes: `5e2ed6f`, `8b70a482`.

## Remaining work
- Investigate the three broad title fallbacks using **publisher-operated** article listings and DOI/date evidence; do not simply increase the page cap or mark the query complete.
- Establish independently enumerated publisher inventories for the six originally zero-hit journals and eventually all 24.
- Run the fast regression workflow and full monthly pipeline to verify these changes; a passing fast test does not establish coverage.
- Keep `publication_ready=false`, `release_status=review_required`, and `coverage.complete=false` until explicit editorial approval and defensible evidence.
