# Publisher evidence journal consistency — 2026-11-04

## Verified defect

The fail-closed monthly validator previously checked journal names only for publisher-evidence DOIs absent from the monthly report. For an already indexed DOI, a publisher-evidence record with a different (but configured) journal name could pass the consistency checks. This creates a risk of misattributing independent publisher evidence.

## Change

`validate_report.py` now requires every evidence journal to be one of the 24 configured journals and, whenever the DOI is already indexed, to match the article's journal. `test_validate_report.py` adds a regression test which changes an indexed DOI's evidence journal and expects validation to fail. The test skips if the fixture has no indexed publisher-evidence DOI.

## Verification and limits

The previous fast regression workflow succeeded (run 41777742216). The new change has been committed; the post-change GitHub Actions result must be checked before calling this fix verified. This check is internal consistency only: it does **not** independently enumerate publisher articles, establish correct online-first dates, or justify editorial approval. Keep `publication_ready=false`, `release_status=review_required` and `coverage.complete=false` without explicit approval and exhaustive evidence.
