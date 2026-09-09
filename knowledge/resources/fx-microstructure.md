# Resource: FX-Microstructure (Execution, Gaps, Settlement-Flow)

Destillate der Papers, die auf Mikrostruktur-Effekte in FX abzielen --
gesammelt an einem Ort, damit Muster über Papers hinweg sichtbar werden
(z.B.: mehrere dieser Effekte zeigten sich in echten Daten deutlich
schwächer/inexistent gegenüber der Paper-Behauptung -- s. Distill unten).
Verwandt: [[crypto-etf-flows]] (gleiche Methoden-Familie -- Kyle's Lambda /
Preiswirkung von Order-Flow --, dort Crypto statt FX), [[crypto-volume-profile-mean-reversion]]
(Paper-Edges, die auf echten Daten schwächer/inexistent sind -- gleiches
Muster wie hier, dort Crypto statt FX).

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

---

## US-10J-Rendite als Cross-Asset-Filter für Gold Asian-Range-Breakout

**Capture** -- eigene Ableitung aus [[monetary-policy-spillover]] (Yildirim SSRN 6353258), nicht aus einem eigenen Paper -- Cross-Check-Schritt des [[bond-yield-spread-indikator]]-Projekts; erfasst 2026-08-11.

**Organize** -- Tags: real-rate-channel, cross-asset-filter, gold. Verwandt: DXY-Alignment/VIX-Change-Filter (gleiche Gold-ADX-Config getestet, `scripts/research_gold_dxy_vix_change_filters.py`, 2026-08-06).

**Distill** -- Hypothese über den Realzins-Kanal (Gold zahlt keinen Zins, Opportunitätskosten steigen mit dem Zinsniveau): Long-Trades bei fallender US-10J-Rendite, Short-Trades bei steigender Rendite sollten besser laufen ("aligned") als das Gegenteil. Gleiche Aligned/Misaligned-Logik wie der bestehende DXY-Filter, DGS10 (FRED, echt täglich) statt DXY als Signal.

**Express** -- Getestet gegen die ADX-gefilterte Gold-ASB-Config (`scripts/research_gold_yield_filter.py`), Fenster-Sweep [3,5,10,20]. Uneinheitlich: Fenster 3/10/20 leicht zugunsten "aligned" (PF 1.14-1.20 vs. 1.02-1.13), Fenster 5 (Referenzfenster des DXY-Tests) dreht sich um (aligned PF 1.128 < misaligned PF 1.158). IS/OOS-Split bei Fenster 5 kippt komplett: IS aligned besser (PF 1.168 vs 0.966), OOS misaligned besser (PF 1.104 vs 1.289). Klassisches Rauschmuster -- kein integrierbarer Baustein, trotz theoretisch plausiblem Kanal.

**Nachtrag 2026-09-09 -- Risk-SCALING-Variante getestet (statt Alignment-Gate), ebenfalls verworfen** (`scripts/research_gold_rate_risk_scaling.py`, Cross-Check aus [[cross-asset-momentum-spillover]], JPM-Spillover-Paper). Andere Mechanik als oben: nicht Long/Short-Aligned-Gate auf US-10J, sondern die bei `cls_practical` (EUR/USD) VALIDIERTE kontinuierliche Risk-Scaling-Multiplikator-Kette (`cls_practical.rates.compute_combined_rate_risk_multiplier` -- BUND/USTBOND-CFD long-end x DE02Y/US02Y front-end, exakte Produktions-Config lag=2/1, z>=0.5, 1.75x je Bein), zum ersten Mal auf Gold-ASB statt EUR/USD angewendet. Naiv (kein Walk-Forward) sieht es leicht positiv aus (EndEquity $166.804 -> $185.711 über 2016-2026 bei Voll-Scaling), aber PF selbst verschlechtert sich leicht (Full 1.091->1.078, IS 1.033->1.026, OOS 1.131->1.105) -- der höhere Endwert kommt vom reinen "öfter hebeln" auf einer im Schnitt leicht positiven Strategie, nicht von echtem Timing. **Walk-Forward (2021-2026, gleiche Expanding-Window-Disziplin wie die 4 Produktionsfilter)**: 4 von 6 Testjahren bestätigten Scaling auf Train-Only-Daten, aber real gemischt -- 2022/2023 leicht besser (+$10.6k/+$13.8k), 2024/2025 schlechter (-$14.2k/-$11.3k). **Randomisierung (structure-preserving, 1000 Shuffles je Methode, gleiche Rigor-Stufe wie der validierte Liquiditätsfilter)**: klar NICHT bestanden -- p=0.665 (Rotation) / p=0.670 (Run-Permutation), der echte Befund liegt sogar UNTER dem Null-Mittelwert (actual PF 1.079 vs. null_mean 1.088-1.089). Ein zufälliges Scaling-Muster mit demselben Duty-Cycle (931/2190 Tage, gleiche Lauflängen-Struktur) performt im Schnitt genauso gut oder besser -- der scheinbare Vorteil ist reines Leverage-Artefakt, kein Timing-Signal. **Fazit**: Anders als bei `cls_practical` (5/5 IS/OOS-Splits, alle Jahre positiv) trägt dasselbe Rate-Momentum-Signal auf Gold ASB nicht -- kein integrierbarer Baustein, nicht verdrahtet. Wiederverwendbare Infrastruktur bleibt trotzdem im Repo: `asian_range_breakout/sizing.py::simulate_equity(risk_multiplier=...)` (Muster aus `cls_practical/engine.py` übernommen) und `asian_range_breakout/walkforward.py::run_rate_scaling_walk_forward` (neuer Walk-Forward-Helfer für kontinuierliche Scaling-Multiplikatoren statt Bucket-Gates) -- für eine zukünftige, tatsächlich Gold-spezifische Scaling-Idee direkt nutzbar, ohne diesen Test zu wiederholen.

---

## Corwin-Schultz Gold-Liquiditätsfilter & FOMC-Event-Window (validiert, 2026-08-11)

**Capture** -- eigene Ableitung aus [[monetary-policy-spillover]] (Corwin & Schultz 2012, Yildirim SSRN 6353258 als Vermittler); erfasst 2026-08-11, Cross-Check-Schritt des [[bond-yield-spread-indikator]]-Projekts.

**Organize** -- Tags: liquidity-filter, statistical-rigor, gold. Verwandt: DXY/VIX/US-Yield-Filter (oben, gleiche Datei), `asian_range_breakout/randomization.py` + `walkforward.py` (Methodik).

**Distill** -- Zwei Kandidaten gegen den VOLLEN Produktions-Stack (ADX+Trend+Delay+Silver) getestet, mit dem gleichen zweistufigen Rigor wie die 4 bestehenden Produktionsfilter (Structure-Preserving-Randomisierung + Walk-Forward, nicht nur PF/WR):
1. Corwin-Schultz-Liquiditätsgate auf Golds eigenen Daily-OHLC (unteres Zweidrittel = normale/gute Liquidität behalten).
2. FOMC-3-Tage-Fenster, beide Richtungen (meiden/bevorzugen).

**Express** -- `scripts/research_gold_liquidity_event_filters.py`. **Liquiditätsfilter: klar bestanden.** Randomisierung p=0.000 unter Rotation UND Run-Permutation (n=1000 Shuffles je Methode) -- stärker als 2 der 4 bestehenden Produktionsfilter (Trend-Bias/Delay lagen bei p≈0.16-0.23). Walk-Forward: in 6/6 Testjahren (2021-2026) auf Train-Only-Daten bestätigt, Ø-PF/Jahr von 1.463 (ungefiltert) auf 2.267 (walk-forward) angehoben. **FOMC-Fenster: klar nicht bestanden**, beide Richtungen (p=0.42-0.62) -- bestätigt den informellen Befund aus dem US-Yield-Test oben. Wiederverwendbarer Baustein liegt bereits in `asian_range_breakout/filters.py::attach_gold_liquidity`/`apply_gold_liquidity_filter`, aber noch NICHT in den angezeigten Produktions-Stack (`app_pages/asian_range_breakout.py`) verdrahtet -- das ist eine bewusste, noch offene Entscheidung, kein technisches Blocker.
