# Crossref-Fehlerisolierung – 2026-11-03

## Befund
GitHub Actions 41705352517: Crossref-Backfill, HTML-Datenerzeugung, Verlagsabgleich, Qualitätsprüfung und Coverage-Audit erfolgreich; die Datenkonsistenzprüfung scheiterte, bevor die Leser-HTML erzeugt wurde. Der vorangehende Lauf dokumentierte drei nicht vollständig abfragbare Titel-Suchen (American Journal of Dentistry, International Journal of Prosthodontics, Quintessence International). Die Sperre bei unvollständiger Recherche ist korrekt und darf nicht umgangen werden.

## Nachweisbarer Defekt und Korrektur
`scripts/backfill.py` schrieb bislang gefundene DOI-Datensätze unmittelbar in `observed`, auch wenn eine spätere Seite derselben Zeitschriftenabfrage eine Ausnahme auslöste. Dadurch konnten partielle Treffer einer fehlgeschlagenen Abfrage dauerhaft in den Bestand gelangen. Jetzt werden pro Zeitschrift die neuen Datensätze in `staged` gehalten und erst nach vollständig erfolgreicher Abfrage mit `observed.update(staged)` übernommen. Der Regressionstest `test_failed_journal_does_not_commit_partial_discoveries` erzwingt eine Ausnahme nach einem ersten Treffer und prüft, dass keine DOI übernommen und die Zeitschrift als Fehler gemeldet wird.

## Verifikation und Grenzen
Der schnelle Regressionstest für Commit a00d272d war erfolgreich (GitHub Actions 41713873661). Für Commit 1546b2d6 mit dem zusätzlichen Regressionstest wurde der Lauf 41713931550 eingereiht; dessen Ergebnis muss nach Abschluss geprüft werden. Der vollständige Monatslauf 41713931124 wurde ebenfalls eingereiht. Keine redaktionelle Freigabe erteilt.

## Offene Aufgaben
1. Fehlerausgabe des Datenvalidators im jüngsten Monatslauf präzise auswerten; nicht allein aus einem fehlgeschlagenen Schritt auf die Ursache schließen.
2. Die drei überlaufenden Titel-Suchen durch eine nachweisbar vollständigere, engere Abfrage oder unabhängige Verlagsinventur ersetzen. Nicht stillschweigend abbrechen oder als vollständig markieren.
3. Alle sechs Null-Treffer-Zeitschriften anhand originaler Verlagslisten einschließlich Online-Erstveröffentlichungsdatum unabhängig inventarisieren.
4. Monatlichen HTML-Export und Freigabesperre im vollständigen Workflow verifizieren.

Die bisherige Evidenz beweist keine vollständige wissenschaftliche Erfassung der 24 Zeitschriften.