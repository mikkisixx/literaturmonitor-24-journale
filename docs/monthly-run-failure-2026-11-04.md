# Monatslauf 2026-10 – reproduzierbare Fehlerdiagnose (2026-11-04)

## Belegter Zustand

- GitHub Actions Monatslauf [41722247631](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41722247631), Job 126219439119, **failure**.
- Schnelle Regressionstests [41722247278](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41722247278), **success**.
- Backfill-Ausgabe im Joblog: `checked=21`, Fehler in genau drei Zeitschriften: **American Journal of Dentistry**, **International Journal of Prosthodontics**, **Quintessence International**. Für jede: `Crossref title search ... exceeded 10 pages`.
- Nachfolgende HTML-Daten- und Verlagsdatums-Abgleichschritte liefen durch; `scripts/validate_report.py` stoppte beim Assert `coverage["journals_queried"]==24 and coverage["query_errors"]==0` mit `AssertionError: Crossref queries incomplete`.
- Diagnoseartefakt: [Recherche-Diagnose-2026-10-41722247631](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41722247631/artifacts/13275536136). Es enthält die temporären Recherche-/Qualitätsdaten, die **nicht** als geprüfte Monatsdaten übernommen werden dürfen.

## Interpretation und Schutzmaßnahme

Die Titelsuche `query.container-title` ist eine **unscharfe Crossref-Suche**. Ein Treffer mit exakt passendem `container-title` ist zwar verwertbar, aber das Durchsuchen nur der ersten zehn unscharfen Ergebnis-Seiten beweist nicht, dass alle passenden Artikel gefunden wurden. Das Limit ist deshalb eine korrekte **Fail-closed**-Sicherung, kein Fehler der Datenvalidierung. **Nicht** das Seitenlimit entfernen oder `query_errors` ignorieren, um einen grünen Workflow zu erzwingen.

## Nächste nachprüfbare Arbeit

1. Die konkreten Print-/Online-ISSNs und Verlagsarchive dieser drei Zeitschriften verifizieren. Eine leere ISSN-Suche darf nicht mit einem belegten Null-Publikationsmonat verwechselt werden.
2. Eine wirklich begrenzte, testbare Suchstrategie entwickeln (z. B. datumssegmentierte Crossref-Titelsuche mit harter Abbruchbedingung **pro Segment** und exakter Titelprüfung). Vor produktivem Einsatz Requestzahl, Paging-Vollständigkeit und DOI-Deduplikation mit Fixture-Tests nachweisen. Bei überlaufendem Segment weiter fail-closed.
3. Parallel unabhängige **Verlagsinventuren** für alle sechs Null-Treffer-Zeitschriften mit DOI und originalem Online-Datum erfassen; DOI gegen den Monatsbericht abgleichen. Crossref/Europe PMC allein gelten nicht als unabhängige Verlagsbelege.
4. Danach erneut Monatslauf und Regressionstests ausführen, Artefakt und Sperrstatus prüfen. Freigabe nur nach ausdrücklicher Nutzerentscheidung.

**Redaktioneller Status: gesperrt.** Weder ein erfolgreicher Workflow noch 24 fehlerfreie Crossref-Abfragen beweisen wissenschaftliche Vollständigkeit.
