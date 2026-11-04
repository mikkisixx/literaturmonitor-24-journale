# CI-Regression und Korrektur – 2026-11-04

## Nachgewiesener Fehler

GitHub Actions „Schnelle Regressionstests“, Lauf 41807770972, scheiterte an zwei Tests in `tests/test_discover_springer.py`:

- `test_only_article_links_and_correct_journal`
- `test_bounded_listing_never_claims_complete`

Die Test-Fixtures enthielten Springer-DOIs mit dreistelliger Jahresangabe (`-026-`). Die produktive DOI-Erkennung akzeptiert korrekt vierstellige Jahresangaben (`-2026-`). Daher erkannte sie die künstlichen Artikel nicht, und die Discovery meldete `unparseable_or_empty_listing` statt `page_limit_reached`.

## Korrektur

Commit `4de8b3eadf1dd73e43e31841f3bf7f2987c2df46` korrigiert ausschließlich die Test-Fixtures auf `-2026-`. Der produktive DOI-Parser wurde bewusst **nicht** gelockert, um fehlerhafte DOI-Muster weiterhin abzulehnen.

## Reproduzierbarkeit

```bash
python -m unittest discover -s tests -p 'test_discover_springer.py' -v
python -m unittest discover -s tests -v
```

Die CI-Ausführung für diesen Commit wurde automatisch angestoßen (Lauf 41810647199); bei Dokumentation noch nicht abgeschlossen.

## Qualitätsgrenzen

- Springer-Inventur ist ein Pilot für zwei Zeitschriften und kein Nachweis einer lückenlosen Online-First-Recherche.
- Die sechs Null-Treffer-Zeitschriften bleiben ohne unabhängig bestätigte vollständige Verlagsinventur offen.
- Redaktionelle Freigabe und Vollständigkeitsbehauptungen sind nicht durch diese Korrektur legitimiert.
- Die neue Monatsauswahl erzeugt einen **Rechercheentwurf** und ist nicht gleichbedeutend mit redaktionell geprüfter Veröffentlichung.
