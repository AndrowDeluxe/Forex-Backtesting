# Resource: FX-Microstructure (Execution, Gaps, Settlement-Flow)

Destillate der Papers, die auf Mikrostruktur-Effekte in FX abzielen --
gesammelt an einem Ort, damit Muster über Papers hinweg sichtbar werden
(z.B.: mehrere dieser Effekte zeigten sich in echten Daten deutlich
schwächer/inexistent gegenüber der Paper-Behauptung -- s. Distill unten).

---

## Execution-Overlay (Fast Alpha als Timing-Filter)

**Capture** -- Zarattini & Pagani (2026), "Improving Performance with Fast Alphas"; erfasst 2026-08-09, manuell im Chat.

**Organize** -- Tags: execution, timing-filter, mean-reversion. Verwandt: [[gap-fade]] (unten, gleiche Datei).

**Distill** -- 5-Min-Mean-Reversion-Signal als Solo-Strategie stirbt an Kosten, soll aber als reiner Timing-Filter für eine ATR-Breakout-Trendstrategie den Einstiegspreis verbessern, ohne das Signal zu verändern.

**Express** -- Getestet auf SPY (H1, 730 Tage) und EUR/USD (2016-2026). SPY: Baseline positiv (PF 1.10, n.s.), Overlay macht es schlechter (PF 0.89). EUR/USD: kein Edge, weder mit noch ohne Overlay. Kein integrierbarer Baustein -- Wirkung ist auflösungsabhängig, keine neutrale Verfeinerung. Seite: `app_pages/execution_overlay_writeup.py`.

---

## Gap-Fade EUR/USD & GBP/USD

**Capture** -- Caporale & Plastun (2016); erfasst 2026-08-09, manuell im Chat.

**Organize** -- Tags: gap-anomaly, mean-reversion, EOD-exit. Verwandt: [[execution-overlay]] (oben, gleiche Datei).

**Distill** -- Positive Montags-Gaps in EUR/USD und GBP/USD faden, EOD glattstellen -- im Paper der einzige von sechs getesteten Gap-Hypothesen mit signifikantem Effekt.

**Express** -- Eigener OOS-Test 2016-2026: EUR/USD brutto nicht von Null unterscheidbar (p=0.42), GBP/USD signifikant NEGATIV (p=0.995). Trefferquote fällt von ~60-65% (Paper) auf ~44% -- Regimebruch, kein integrierbarer Baustein. Seite: `app_pages/gap_fade_writeup.py`.
