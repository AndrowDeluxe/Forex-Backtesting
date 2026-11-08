# Handoff 2026-11-08 22:00 -- Renditen-Loader Makro-Datenschicht

## Learnings
- `python -m fusion_lab.macro_data --coverage` (Stand 08.11.): 2y nur US/EA, für GB/JP/CH/AU/CA/NZ
  FEHLT; 10y außer US/EA auf 26-09-01 stehen geblieben (OECD monatlich). Das blockiert das R-Gate
  und die Checklisten-Frage „steigt die 2J mit der Währung?“ aus
  [[makro-agent-report-pruefung]]. Speicher: `fusion_lab/data/macro_data/macro.parquet`
  (+ calendar/markets/positioning), Code `fusion_lab/macro_data/{sources,store}.py`.
- Quellen sind in [[filter-gold-zinskurve]] → „Datenquellen für die FX-Schicht“ schon getestet
  (EZB `YC/...SR_2Y`, MoF `jgbcme.csv`, BoC Valet `BD.CDN.2YR.DQ.YLD`, BoE IADB). Im Lake liegen
  zusätzlich `tradingview/US02Y_D1` und `DE02Y_D1` (bis 06.11. aktuell) – möglicher Abgleich.
- Telegram-Export lief nicht automatisch: neue SMT-Reports erst nach
  `python -m fusion_lab.ingest.telegram --chat -1002552394198 --skip-video` sichtbar.

## Fehlannahmen
- EUR/CHF-ATR aus EURUSD×USDCHF-Hochs/-Tiefs gerechnet → 0,0109 (Faktor ~2,5 zu hoch, Extremwerte
  nicht gleichzeitig). Kreuz-ATR nur aus echten Kreuzkursen.

## Offene Fäden
- BoE-Codes IUDSNPY/IUDMNPY/IUDLNPY: Laufzeit weiter unklar (siehe Handoff 02.11.); 2y ggf. aus
  Anderson-Sleath-Spotkurve (ZIP).
- AUD (RBA 403), CHF (SNB), NZD (RBNZ B2) ungeprüft; RBA nicht mit Browser-Kopf umgehen
  (Klassifizierer blockt zu Recht) → DBnomics `RBA/F2` oder manuell.
- Nach dem Loader laut Plan `~/.claude/plans/eventual-rolling-heron.md` Schritt 2 (Fact Sheet) –
  dafür Plan-Modus.

## Nächster Schritt
- Loader für EZB, MoF Japan, BoC, BoE (2y + 10y, täglich, mit Abrufzeit) in
  `fusion_lab/macro_data/sources.py` ergänzen, in den Task „Makro-Daten“ hängen, `--coverage` grün
  für EA/JP/CA/GB prüfen.
