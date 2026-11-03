#!/usr/bin/env python3
"""Export a readable, explicitly unapproved monthly literature report."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def export(month, destination):
    report = json.loads((ROOT / "data/months" / (month + ".json")).read_text(encoding="utf-8"))
    quality = json.loads((ROOT / "data/quality" / (month + ".json")).read_text(encoding="utf-8"))
    coverage = json.loads((ROOT / "data/coverage" / (month + ".json")).read_text(encoding="utf-8"))
    if quality.get("publication_ready") is not False or quality.get("release_status") != "review_required":
        raise ValueError("Unexpected editorial release status: refusing automated export")
    destination.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Literaturbericht " + month,
        "",
        "> **NICHT REDAKTIONELL FREIGEGEBEN – UNVOLLSTÄNDIGER RECHERCHEENTWURF.**",
        "> Online-First-Daten sind nicht für alle 24 Zeitschriften unabhängig vollständig geprüft.",
        "",
        "## Qualitätsübersicht",
        "",
        "- Artikel und Prüfkandidaten: " + str(report["count"]),
        "- Crossref-Online-Datumsangaben: " + str(report["verified_online_count"]),
        "- Nicht bestätigte Monatskandidaten: " + str(report["candidate_count"]),
        "- Zeitschriften mit null Crossref-Treffern: " + str(coverage["zero_hit_journals"]),
        "- Durch Verlagsquellen belegte fehlende Artikel: " + str(coverage["confirmed_missing_publisher_articles"]),
        "- Unabhängig vollständig überprüfte Zeitschriften: " + str(coverage["journals_independently_verified"]) + "/24",
        "",
        "## Artikel nach Zeitschrift",
        "",
    ]
    journals = {}
    for a in report["articles"]:
        journals.setdefault(a["journal"], []).append(a)
    for journal in sorted(journals):
        lines.extend(["### " + journal, ""])
        for a in journals[journal]:
            title = str(a.get("title") or "Ohne Titel").replace("\n", " ")
            date = a.get("online_date") or a.get("display_date") or "unbekannt"
            basis = "Crossref-Online-Datum; Verlag nicht vollständig geprüft" if a["date_basis"] == "crossref_online" else "UNBESTÄTIGTER MONATSKANDIDAT"
            lines.append("- **" + title + "** — " + str(date) + " (" + basis + "). DOI: https://doi.org/" + str(a["doi"]))
        lines.append("")
    lines.extend(["## Nachweislich fehlende Verlagsartikel", ""])
    for a in coverage["missing_publisher_articles"]:
        lines.append("- " + a["journal"] + " — " + a["publisher_online_date"] + " — " + a["doi"] + " — " + a["source"])
    lines.extend(["", "## Redaktionelle Freigabe", "", "**Nicht freigegeben.** Automatisierung ersetzt keine nachgewiesene vollständige Verlagsinventur.", ""])
    (destination / ("Literaturbericht-" + month + "-ENTWURF.md")).write_text("\n".join(lines), encoding="utf-8")
    for name, obj in [("Monatsdaten", report), ("Qualitaet", quality), ("Abdeckung", coverage)]:
        (destination / (name + "-" + month + ".json")).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported", month, "to", destination)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("month")
    p.add_argument("--output", type=Path, default=ROOT / "exports")
    args = p.parse_args()
    export(args.month, args.output)
