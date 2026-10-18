# Anleitung: SMH-Makro-Report → JSON (v2, 16.10.2026)

Gilt für jeden, der Reports extrahiert (Unteragent oder Session). Schema:
`fusion_lab/macro_reports/schema.py` (pydantic, `Report` / `Idea` / `Ranking`).

v2 ersetzt v1 nach der Nutzer-Stichprobe vom 16.10.: v1 übersah in
Generation 2 Trade-Tabellen mit Sternen (einmal sogar falsche Richtung) und
setzte „vorbereitet“, sobald nur eine technische Bestätigung fehlte. Das ist
falsch — siehe Status-Definition unten.

## Eingabe / Ausgabe

- Text: `fusion_lab/data/macro_reports/text/<msg_id>.txt`
  (Bild-PDFs: PNG-Seiten unter `fusion_lab/data/macro_reports/render/<msg_id>/`).
  Bei Tabellen, deren Spalten im Text durcheinander geraten (Sterne, Richtung),
  das PDF selbst prüfen: Seiten mit
  `python -c "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); d[int(sys.argv[2])].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(sys.argv[3])" <pdf> <seite0> <out.png>`
  rendern und mit dem Read-Tool ansehen. PDF-Pfad: Spalte `file` in
  inventory.csv, Ordner `fusion_lab/raw/telegram/SMH Daily Update__2552394198/media/`.
- `msg_id`, `posted_utc`, `generation` aus `fusion_lab/data/macro_reports/inventory.csv`
  übernehmen — NICHT aus dem PDF.
- Ausgabe: `fusion_lab/data/macro_reports/extracted_v2/<msg_id>.json`, UTF-8.
  Datei für Datei schreiben und sofort prüfen:
  `python -c "from fusion_lab.macro_reports.schema import load; load('fusion_lab/data/macro_reports/extracted_v2/<msg_id>.json')"`
  Existiert eine Datei schon und validiert, überspringen.

## Harte Regeln (Lookahead-Schutz)

1. **Wörtlich, nichts ergänzen.** Steht ein Stop/Ziel/Level nicht im Report → `null`
   bzw. leere Liste. Nicht schätzen.
2. **Keine Kursdaten, kein Web, keine anderen Reports ansehen.** Nur den einen Report.
   Kein Wissen darüber verwenden, wie es danach am Markt weiterging.
3. **Jede Idee braucht `quote`** (kurzes wörtliches Zitat für Richtung + Status) und,
   sobald eine Zahl gesetzt ist, `level_quote`.
4. Deutsche Dezimalkommas in Punkte (1,3865 → 1.3865; 4.449 bei Gold = 4449).

## Quellen-Priorität innerhalb eines Reports

1. **Trade-Tabelle / „Finales Buch“ / Setup-Liste mit Sternen oder Gates** — Hauptquelle.
   Jede Zeile dort mit Instrument + Richtung ist eine Idee. Richtung und Sterne genau
   aus der Tabelle lesen (bei Zweifel PDF-Seite ansehen).
2. Setup-Abschnitte („Setup / Entry-Idee“, „Der Trade“, „Trades – Status“).
3. Abschnitte je Währung / Fließtext — nur wenn dort ein konkretes Paar mit Richtung steht.
   Steht dieselbe Idee in Tabelle und Fließtext: eine Idee, Tabelle gewinnt.
- `section`: trade_tabelle | finales_buch | setup_abschnitt | waehrungsabschnitt | fliesstext.

## Was ist eine Idee?

Konkretes Instrument + Richtung, die ein Leser handeln könnte (Paar, Gold, Silber, Öl,
Index, BTC, DXY). Reine Währungs-Einschätzungen ohne Paar → `ranking`.
Ausdrücklich „kein Trade in beide Richtungen“ / keine Richtung → keine Idee, in `notes`.
Echte Zwei-Wege-Setups (long UND short je nach Event) → zwei Ideen, beide `status: event`.

## Status (Nutzerdefinition — wichtig)

Technische Bestätigung / Einstieg auf Rücksetzer ist IMMER Teil des Handelns und macht
eine Idee NICHT „wartend“. Der Nutzer kauft Longs bevorzugt etwas tiefer und verkauft
Shorts etwas höher als der aktuelle Markt.

- **aktiv** — Makro-Bild klar, Richtung steht; Einstieg nach technischer Validierung,
  auch wenn der Report „auf Rücksetzer/Rebound warten“, „technisch bestätigen“,
  „Long nur nach Konsolidierung“ sagt.
- **event** — wartet auf ein bestimmtes Makro-Ereignis oder eine Makro-Bedingung
  (CPI, NFP, Notenbank, Zollfrist, „erst nach Kanada-CPI“). Feld `event` setzen.
- **watch** — Makro-Bild noch unklar oder ausdrücklich nur beobachten („Watch“,
  „unter Beobachtung“, „wait“ ohne klares Ereignis).
- **bias** — nur Richtungseinschätzung ohne Trade-Charakter, oder ausdrücklich
  „mit Vorsicht / unter Vorbehalt“ ohne Setup.
- **inaktiv** — ausdrücklich nicht handeln / aus dem Buch genommen.
- „vorbereitet“ NICHT mehr verwenden.

## Rolle

main (Haupttrade, „Best Trade“, höchste Gewichtung) · secondary (weitere Trades) ·
event (Trade, dessen Kern ein Datenereignis ist) · **hedge** (ausdrücklich Absicherung,
z. B. „Gold als Hedge“) · bias (nur Richtung).

## Gewichtung

- `stars`: Anzahl Sterne genau wie im Report (1–6). Bei x/5-Dezimalwerten runden
  (3,5 → 4). Nur setzen, wenn der Report eine Gewichtung für GENAU diese Idee nennt.
- `gates_met` / `gates_total`: bei „4/5 Gates“ → 4 / 5.
- `confidence`: Wortlaut-Konfidenz („hoch“, „mittel-hoch“ …), sonst aus Sternen:
  5–6 hoch, 4 mittel-hoch, 3 mittel, 2 mittel-niedrig, 1 niedrig; sonst null.
- Sizing-Prozente oder A/B/C-Prioritäten in `notes` vermerken.

## Weitere Felder

- `entry_zone`, `stop`, `targets`, `activation_price`/`activation_side`,
  `invalidation_price`, `horizon_days`: nur wenn ausdrücklich genannt (wie v1).
- `activation_text`: Bedingung im Wortlaut, auch technische Bedingungen.
- `event`: kurzer Name des Ereignisses bei status event (oder wenn eine aktive Idee
  ausdrücklich an ein Ereignis gekoppelt ist).
- `regime`, `ranking`, `no_trade_rules`, `report_date`, `notes` wie v1.

## Beispiel (gekürzt)

```json
{"msg_id": 6057, "posted_utc": "...", "generation": 3, "regime": "...",
 "ideas": [
  {"instrument": "EURCHF", "direction": "long", "role": "main", "status": "aktiv",
   "stars": null, "gates_met": 4, "gates_total": 5, "section": "finales_buch",
   "activation_text": "Einstieg auf Rücksetzer nach technischer Bestätigung",
   "quote": "..."},
  {"instrument": "GOLD", "direction": "long", "role": "hedge", "status": "aktiv",
   "section": "finales_buch", "quote": "... als Absicherung ..."},
  {"instrument": "USDJPY", "direction": "short", "role": "event", "status": "event",
   "event": "BoJ-Sitzung", "section": "finales_buch", "quote": "..."}
 ]}
```
