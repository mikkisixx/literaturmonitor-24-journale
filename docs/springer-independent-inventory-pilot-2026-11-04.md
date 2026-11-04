# Unabhängige Springer-Verlagsinventur: Pilot (2026-11-04)

## Implementiert
- `scripts/discover_springer.py --month YYYY-MM` ruft direkt die Artikellisten von Springer Nature Link ab, ohne Crossref als Suchquelle zu verwenden.
- Pilotzeitschriften: Clinical Oral Investigations (Journal 784) und Journal of Materials Science: Materials in Medicine (Journal 10856).
- Verlagslinks werden nach DOI-Muster und Journalpräfix gefiltert und dedupliziert.
- Abruffehler, leere/unlesbare Listen, wiederholte Seiten und Seitenlimit werden explizit dokumentiert; kein Zustand bedeutet automatisch Vollständigkeit.
- Ergebnis: `data/publisher-inventory/YYYY-MM.json`; die Monats-GitHub-Action führt den Pilot aus und speichert die Daten.
- `tests/test_discover_springer.py` prüft DOI-Abgrenzung, Seitenlimit und Fehlerstatus.

## Wissenschaftliche Grenzen
**Nicht vollständig verifiziert.** Die Artikelübersichten können auch Artikel anderer Monate enthalten; das ursprüngliche Online-Erstveröffentlichungsdatum muss je DOI direkt auf der Verlagsartikelseite bestätigt werden. Seitenlimit, dynamisches HTML, Zugriffssperren und spätere Aktualisierungen können Ergebnisse unvollständig machen. Die Pilotinventur wird nicht als redaktionelle Freigabe oder Beleg für die Vollständigkeit aller 24 Zeitschriften verwendet.

## Nächste Schritte
1. GitHub-Actions-Ergebnis und tatsächliche Verlagsabrufe prüfen; bei Änderungen des Springer-HTML die Extraktion reparieren.
2. Für jeden Kandidaten den Original-Publisher-Online-Termin ermitteln und gegen den Berichtsmonat prüfen; fehlende DOIs mit überprüfbarer Quelle ergänzen.
3. Pagination/Abschlussbedingung unabhängig nachweisen, dann weitere Verlagssysteme implementieren und alle 24 Journale inventarisieren.
4. Freigabesperre beibehalten, bis vollständige unabhängige Inventuren pro Journal nachweisbar sind.
