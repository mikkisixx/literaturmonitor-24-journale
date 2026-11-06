# Literaturmonitor – 24 Fachzeitschriften

Monatliche DOI-Recherche mit Crossref, ergänzenden Verlagsprüfungen und einem **eigenständigen HTML-Bericht**. Die Erfassung aller erschienenen Artikel ist **nicht** als vollständig verifiziert. Ein erfolgreicher GitHub-Actions-Lauf bestätigt die technische Verarbeitung, nicht die bibliografische Vollständigkeit.

## Monat auswählen und HTML herunterladen

1. In GitHub **Actions → Monatsrecherche und Bericht → Run workflow** öffnen.
2. Branch `main` und den gewünschten Monat im Format `YYYY-MM` eingeben (z. B. `2026-09`), dann **Run workflow** wählen. Ohne Eingabe wird der vorherige Kalendermonat verwendet. Zukünftige Monate werden abgewiesen.
3. Nach Abschluss den Workflow-Lauf öffnen und unter **Artifacts** `Literaturbericht-YYYY-MM-HTML` herunterladen. Das ZIP entpacken und `Literaturbericht-YYYY-MM.html` im Browser öffnen. Das HTML benötigt keinen Webserver.
4. Ein grüner Workflow-Lauf ist **keine** redaktionelle Freigabe: die Quellen- und Vollständigkeitstabelle im Bericht prüfen.

Der Workflow ist unter [monthly-report.yml](.github/workflows/monthly-report.yml) definiert. Die Ausgabe wird von [export_html.py](scripts/export_html.py) erstellt. Die unabhängige Prüfung eines explizit ausgewählten anderen Monats ist als End-to-End-Nachweis noch offen; die bloße Existenz des Eingabefelds reicht dafür nicht.

## Datenherkunft und Einschränkungen

- **Crossref** liefert DOI und Online-Publikationsmetadaten; nur Einträge mit zum gewählten Monat passendem `online_date` und ausgewiesener Datumsbasis (`crossref_online` oder `publisher_online`) werden im Leser-HTML ausgegeben. Ein Print-/Heftdatum ist kein Ersatz.
- Ergänzende Verlagsdaten und Datumsabweichungen werden gesondert geprüft. Das bedeutet **nicht**, dass jede Verlagsartikelliste vollständig durchsucht wurde.
- Für **alle 24 Journale** stehen Quellen- und Abdeckungsinformationen in `data/coverage/YYYY-MM.json` und `data/publisher-inventory/YYYY-MM.json`; Prüfinformationen stehen in `data/quality/YYYY-MM.json` und `data/publisher-checks/`.
- **Null Treffer** bedeutet nur, dass keine entsprechend datierten und bestätigten Artikel erfasst wurden. Es beweist nicht, dass keine Artikel erschienen sind.
- Bekannte, anhand von Verlagsdaten belegte, aber im Monatsbestand fehlende Artikel werden als Lücken ausgewiesen, **nicht** stillschweigend als vollständig recherchiert deklariert.
- `publication_ready: false` und `release_status: review_required` sind absichtliche redaktionelle Sperren, solange die Vollständigkeit nicht unabhängig nachgewiesen ist.

## Technische Prüfungen

Lokal mit Python 3.12 im Repository:

```sh
python -m unittest discover -s tests -v
python scripts/validate_report.py 2026-10
python scripts/export_html.py 2026-10 --output exports
```

Der letzte Befehl erzeugt `exports/Literaturbericht-2026-10.html` aus den bereits gespeicherten Monatsdaten; **er recherchiert nicht erneut**. Eine vollständige Recherche benötigt den oben beschriebenen GitHub-Actions-Workflow und Netzwerkzugang. Die Datenvalidierung und HTML-Erzeugung ersetzen keine stichprobenweise DOI-/Verlagskontrolle.

## Reproduzierbarkeit

Für jede Ausgabe sollten der gewählte Monat, die Workflow-Run-ID, der Commit, die Artefakt-ID sowie die Anzahl bestätigter Artikel, Null-Treffer-Journale und nicht verifizierter Verlagsinventuren festgehalten werden. Bis eine unabhängige Inventur aller 24 Zeitschriften abgeschlossen ist, darf aus einem grünen Workflow-Status keine vollständige Monatsbibliografie abgeleitet werden.
