# Gold-Bausteine für andere Edges (aus dem Gold-Confirmation-Test)

**Stand 15.11.2026, Nutzerentscheid: gespeichert.** Herkunft: [[gold-confirmation-score]]
(Nachbau von [[gold-confirmation-framework-pdf]]). Alles mit freien Daten, point-in-time.

## 1. Makro-Veto für Reversal-Einstiege (Filter)

`fusion_lab/filters/gold_macro_veto.py` → `GoldMacroVetoFilter().allows("long"|"short", tag)`

- MACRO-Block = Realzins 10J, USD, Breakeven 10J, EPU, je als 3-Jahres-Perzentil 0–100, Wert vom Vortag.
- Regel: kein Long bei ≤ 35, kein Short bei ≥ 65. `explain(tag)` liefert die Einzelteile fürs Log.
- Getragen von Realzins und USD; Inflation und EPU allein würden Gewinner sperren.

Gesperrte CTNL-Reversal-Trades, Ø R je Trade:

| Seite | IS 2010–19 | OOS 2020–05/26 | Tresor 05–10/26 |
|---|---|---|---|
| Long gegen Makro | −0,56 (n 77, p 0,009) | −0,85 (n 34, p 0,0003) | −1,16 (n 5) |
| Short gegen Makro | −1,02 (n 32, p 0,005) | −0,65 (n 35, p 0,08) | kein Fall |

- Short-Sperre: in 7 von 9 Jahren mit Fällen negativ. Ausnahmen 2013 (+0,32, n 6) und 2025 (+2,99, n 2).
- Gilt bisher nur für CTNL-Reversal auf Gold. Auf Gold ASB wirkungslos (Breakout, nicht Reversal).
- **Nicht live.** Auf andere Reversal-Edges nur als neue, gezählte Variante unter eigener Sperre übertragen.

## 2. Gold-Score als Filter-Werkzeug

`fusion_lab/gold_confirm/score.py` → `GoldScoreFilter(long_min, short_max, column)`. `column` = "score",
ein Block ("FLOW", "PHYSICAL", "PRICE", "MACRO") oder ein einzelner Baustein. Der Gesamtscore ist
ein Momentum-Sammelwert ohne eigenen Edge; brauchbar nur zum schnellen Durchprobieren von Blöcken
auf neuen Edges.

## 3. Lagebild „wer kauft Gold“ (Kontext, kein Signal)

`python -m fusion_lab.gold_confirm.context` → `gold_context(tag)`:
GLD-Bestand (t, Δ 5/20 T), China-Prämie (%), Zentralbanken netto 12 M (t, nur gemeldete Käufe,
2 Monate Lag), MACRO-Block mit Datum. Für das Fact-Sheet des Makro-Agenten.

- Daten aktualisieren: `python -m fusion_lab.gold_confirm.data`.
- **Achtung:** Der Score hängt am Dukascopy-D1-Cache (`data_cache/combined/GOLD_D1_*`), derzeit bis
  30.10.2026. Für Live-/Forward-Nutzung muss der Cache mitlaufen, sonst bleibt der MACRO-Wert stehen.

## Freie Quellen (für andere Projekte)

| Reihe | Quelle | Ab |
|---|---|---|
| GLD-Tonnen täglich | SPDR-API `historical-archive?product=gld` (xlsx) | 2004 |
| Shanghai-Benchmark | SGE `POST /graph/DayilyJzj` | 04/2016 |
| Goldreserven je Land | IMF IRFCL `IRFCLDT1_IRFCL56V_FTO` (Unzen) | 2000 |
| CFTC alle Händlergruppen | CFTC Disaggregated `72hh-3qpy` | 2006 |
| GVZ, Realzins, Breakeven, EPU | FRED | 2004–2008 |

Verworfen (15.11., Nutzerentscheid): Gold long am Limit-Rücksetzer, Gold ASB + Trendfilter als
Nebenbefunde. Verwandt: [[makro-wirkketten-katalog]], [[makro-scorecard-v2]].
