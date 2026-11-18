# Auftrag: Wöchentliche Tiefen-Analyse {NAME} ({SCHLUESSEL}, Future {TICKER})

Du läufst unbeaufsichtigt (geplanter Task `Forex-Rohstoff-Tiefenanalyse`, Datum {DATUM}). Niemand kann Rückfragen
beantworten. Keine Orders, keine Broker, keine Bridges, keine Commits. Deutsch, einfache Sprache, keine Anlageberatung.
Vorbild ist die Kupfer-Analyse vom 18.11.2026 (`fusion_lab/screener/archive/kupfer_analyse_2026-11-18.md`).
Lies sie kurz, um Aufbau und Tiefe zu übernehmen.

## Regeln
- Nur Zahlen nennen, die in Quellen stehen, jeweils mit Datum und Domain. Nichts schätzen oder interpolieren.
- Widersprüche zwischen Quellen offen mit ⚠️ ausweisen statt einen Wert zu wählen.
- Fehlendes ehrlich als „fehlt“ markieren.
- Technik **selbst rechnen**: `python scripts/reports/stock_technicals.py {TICKER}` (Bash). Keine Indikatorwerte von
  Webseiten übernehmen. Schlägt das fehl, schreibe es offen hin.
- Positionierung zuerst aus dem Tageslauf lesen: neueste Datei `fusion_lab/data/screener/*_rohstoffe.json`, Eintrag
  `{SCHLUESSEL}` in `tief` (Score, Szenarien A/B/C, COT Managed Money, Schlagzeilen). Ergänze sie per Web.

## Schritte (je Block per WebSearch, Ergebnisse kompakt halten)
1. **News** der letzten ~4 Wochen: Kurs und Auslöser großer Bewegungen, Politik/Zölle/Sanktionen, Bankprognosen mit
   Kurszielen, Termine der nächsten 2–4 Wochen.
2. **Sentiment und Positionierung:** CFTC COT (Managed Money, Trend, Extrem?), ETF-Flüsse, Optionsmarkt falls
   auffindbar, Medien-Tenor. Urteil: überdehnt (Contrarian-Risiko) oder Platz in die Trendrichtung?
3. **Makro:** Fed/Zinsen/Realzinsen, Dollar (DXY), China-Daten, Konjunktur (PMI), Geopolitik. Für jeden Faktor
   Rückenwind 🟢, Gegenwind 🔴 oder neutral ⚪.
4. **Branche: Angebot und Nachfrage** (der wichtigste Teil, gründlich):
{CHECKLISTE}
5. **Technik und Preisbereiche** aus den gerechneten Marken (Swing-Hochs/-Tiefs, SMAs, Volumenprofil, ATR):
   - A Rücksetzer-Zone, Stopp ~1 ATR darunter
   - B Bestätigungs-Marke mit Stopp
   - C Abwarten
   - Ziele und Chance-Risiko. A/B nur als Einstieg, wenn Chance-Risiko ≥ 2.
   - Vergleich mit den Szenarien des Tageslaufs.

## Ausgabe
Schreibe **genau eine Datei** `fusion_lab/screener/archive/rohstoffe_tief/{DATUM}_{SCHLUESSEL}.md`
(Ordner bei Bedarf anlegen). Aufbau:

1. Erste Zeile: ein JSON-Kommentar
   `<!-- {"schluessel": "{SCHLUESSEL}", "datum": "{DATUM}", "kurs": <Zahl oder null>, "urteil_kurz": "bullisch|neutral|bärisch", "urteil_struktur": "bullisch|neutral|bärisch", "szenario": "A|B|C", "treiber": ["...", "...", "..."], "termine": ["TT.MM. ...", "..."], "fazit": "1-2 Sätze"} -->`
2. Danach Markdown mit diesen Abschnitten:
   - 📊 Lage auf einen Blick
   - 🗞️ News
   - 😶‍🌫️ Sentiment & Positionierung
   - 🌍 Makrolage (Tabelle)
   - ⛏️ Angebot & Nachfrage
   - 📈 Technik
   - 🎯 Szenarien
   - ⚖️ Fazit (inkl. „Was die Lage dreht“)
   - ⚠️ Widersprüche/Datenlücken
   - Quellen (Domains)
   - „Analyse, keine Anlageberatung.“

Höchstens ~1.200 Wörter. Antworte am Ende mit einer Zeile: Dateipfad und Urteil kurz/strukturell.
