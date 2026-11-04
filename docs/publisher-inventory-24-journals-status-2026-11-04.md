# Status unabhängige Verlagsinventur aller 24 Journale – 2026-11-04

## Tatsächlich implementiert
- Springer-Link-Listen-Pilot für Clinical Oral Investigations und Journal of Materials Science: Materials in Medicine.
- Direktes Abrufen von Verlagsartikelseiten und Prüfung von DOI und explizitem `citation_online_date`.
- Unabhängige 24-Journal-Abdeckungsmatrix `scripts/audit_publisher_inventory.py` mit Zuordnung zu Springer Link, BMC, Wiley, Elsevier, Quintessence, SAGE, American Journal of Dentistry und Operative Dentistry.
- Das bestehende Coverage-Audit zeigt Verlagsplattform, Listingstatus, Anzahl Kandidaten und unabhängig bestätigte Datumswerte. Tests sind ergänzt.
- Erkannte Fehler bei doppelt maskierten regulären Ausdrücken nach Auswertung realer GitHub-Testlogs in Commits `42bf230a` und `ba9175c0` korrigiert.

## Explizit NICHT erreicht
- Keine erschöpfende Verlagslisten-Pagination nachgewiesen; der Springer-Pilot ist seitenbegrenzt.
- Für 22 Zeitschriften ist noch kein unabhängiger Verlagslisten-Adapter implementiert.
- Kein bestätigter vollständiger Live-Abgleich der 24 Journale. Ein GitHub-Lauf, der noch wartet oder läuft, ist kein erfolgreicher Live-Nachweis.
- Keine redaktionelle Freigabe und keine Vollständigkeitsbehauptung.

## Technisch nächster zwingender Schritt
- GitHub-Action bis zum Abschluss verfolgen, Fehler anhand Logs reparieren.
- Publisher-Adapter je Plattform mit belastbarer Monatsgrenze, vollständiger Pagination und DOI-Artikelprüfung implementieren.
- DOI-Differenzen mit verifizierten Online-Erstveröffentlichungsdaten in die Monatskandidaten integrieren und gegen Crossref-Bericht abgleichen.
- Erst bei nachgewiesener Vollständigkeit jeder einzelnen Verlagsinventur die Coverage-Sperre neu bewerten.
