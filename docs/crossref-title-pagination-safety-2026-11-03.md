# Crossref-Titelsuche: begrenzte Pagination und explizite Fehlerbehandlung (2026-11-03)

## Befund

Der Monatsworkflow `41685896592` war bei der Kontrolle noch im Schritt „Monat bei Crossref nachrecherchieren“. Die Suche nach Zeitschriftentiteln ist eine unscharfe Crossref-Abfrage; ein exakter Abgleich des `container-title` findet erst **nach** dem Abruf statt. Die ursprüngliche Pagination hatte keine Obergrenze. Dadurch konnte eine breite Trefferliste den Monatslauf sehr lange beschäftigen.

## Änderung

`scripts/backfill.py::fetch_title_pages` bricht nach höchstens zehn vollständig gefüllten Crossref-Seiten mit einer expliziten Ausnahme ab. Die Ausnahme wird im Monats-Backfill als Zeitschriftenabfragefehler registriert. Dadurch wird eine abgeschnittene Treffermenge **nicht** als vollständig oder als bestätigter Null-Treffer behandelt. Ein Regressionstest simuliert eine unbegrenzte Folge unscharfer Treffer.

## Grenzen und nächste Schritte

Die Obergrenze ist ein Sicherheitsmechanismus, **keine Vollständigkeitsgarantie**. Eine Zeitschrift, deren relevante Artikel hinter der Obergrenze liegen, bleibt als nicht vollständig recherchiert markiert. Als nächstes ist ein gezielter, unabhängiger Verlagskatalog je Zeitschrift mit DOI, Online-Erstveröffentlichungsdatum, Quelle und reproduzierbarer Vollständigkeitsprüfung notwendig. Das gilt für alle 24 Zeitschriften, besonders für die sechs bisherigen Null-Treffer-Titel. Ohne diese Evidenz bleibt `publication_ready=false` und `release_status=review_required`.

Referenzen: [Monatslauf](https://github.com/mikkisixx/literaturmonitor-24-journale/actions/runs/41685896592), [Tests](https://github.com/mikkisixx/literaturmonitor-24-journale/blob/main/tests/test_backfill.py).
