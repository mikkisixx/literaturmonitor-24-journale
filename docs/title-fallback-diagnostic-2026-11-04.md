# Crossref-Titelfallback: Diagnose und konservative Behandlung (2026-11-04)

## Befund
GitHub Actions Lauf [41745812472](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41745812472) scheiterte in `validate_report.py` mit `Crossref queries incomplete`. Der Backfill meldete 21/24 abgeschlossene ISSN-Recherchen; die drei Fehler waren ausschließlich überlange, unscharfe Titelfallback-Suchen für American Journal of Dentistry, International Journal of Prosthodontics und Quintessence International. Jeweils zehn Seiten mit 200 Treffern waren kein belastbarer Nachweis für einen vollständigen Journalbestand.

## Änderung
Der auf zehn Seiten begrenzte Titelfallback bleibt bewusst begrenzt. Er wird nun als **unvollständige zusätzliche Entdeckung** mit `title_fallback_truncated` protokolliert, ohne eine ansonsten abgeschlossene ISSN-Abfrage als technischen Fehler zu zählen. `audit_coverage.py` weist die betroffenen Zeitschriften mit `title_fallback_truncated_requires_publisher_check` aus. Der Regressionstest kontrolliert diese Kennzeichnung. Echte ISSN-Abfragefehler und stagnierende Pagination bleiben fatal.

## Grenzen
Eine abgeschlossene ISSN-Abfrage ist **kein Beweis** für eine vollständige Online-First-Inventur. Die drei Titelfallbacks sind ausdrücklich nicht exhaustiv; Null-Treffer müssen unabhängig beim Verlag geprüft werden. `publication_ready=false`, `release_status=review_required` und `coverage.complete=false` bleiben unverändert. Es gibt keine redaktionelle Freigabe.

## Nächste Schritte
1. Den schnellen Regressionstest und den vollständigen Monatslauf auf GitHub überprüfen.
2. Verlagsseitige Inhaltsverzeichnisse/Online-First-Seiten für die sechs ursprünglichen Null-Treffer-Journale DOI-weise mit Veröffentlichungsdatum dokumentieren.
3. Publisher-Evidence unabhängig gegen die Monatsdatei abgleichen; keine 100%-Aussage ohne exhaustiven Beleg.
