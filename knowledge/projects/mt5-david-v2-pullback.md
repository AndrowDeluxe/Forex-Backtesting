# Project: MT5 David-V2 (Trend+Pullback, Long+Short)

**Ziel**: Zweiten von drei "Neue Bots" (Community-Release-Paket,
`OneDrive/.../Bots/Neue Bots/2-David-V2/`) als backtestbare Basis
rekonstruieren und gegen den Standardprozess pruefen, BEVOR er live/Demo
geht (im Gegensatz zum Haupt-Bot ist dieser Bot auf dieser Maschine noch
NICHT deployed -- kein `David-*`-Ordner unter `C:\Users\andre\`, anders als
`TrendPullback-Bot/`).

**Status**: Phase 6 abgeschlossen. **Befund: NEGATIV -- kein validierter
Edge in diesem Backtest.** Vor Live-/Demo-Betrieb NICHT empfohlen ohne
weitere Ueberarbeitung. Neu gebaut (Paket existierte nicht im Repo), Code
Schritt 1/2/3 aus [[backtest-standard-process]] (eigenes Package, echte
Daten, Regeln 1:1 aus dem Bot uebernommen) vollstaendig durchlaufen, bevor
Phase 6 gezogen wurde.

**Prozess-Referenz**: `app_pages/education_gold_intraday.py`, Phase 6.
Code: `mt5_david_v2/pipeline.py`, `scripts/research_mt5_david_v2.py`,
`scripts/research_mt5_david_v2_phase6.py`.

## Strategie & Signal-Parität

Trend+Pullback, gespiegelt fuer Long UND Short: `close` ausserhalb einer
ATR-Neutralzone um EMA(200) (Puffer = 0.25 ATR) definiert die Richtung, RSI(14)
kreuzt aus der jeweiligen Zone zurueck (35 fuer Long, 65 fuer Short) loest aus.
Stop = ATR(14) x 1.5, Ziel = 2R. Maerkte/TF exakt wie `config.py`: EURUSD/
GBPUSD/USDJPY H1, Gold H4.

Vor jeder Ergebnis-Interpretation gegen die eigene `signals_vectorized()`-
Funktion des Live-Bots bit-exakt geprueft (EURUSD H1 2022, 6240 Balken, 0
Abweichungen bei 48 Signalen) -- die Rekonstruktion selbst ist korrekt, die
folgenden Befunde sind kein Implementierungsfehler.

## Phase 6 -- Robustheit: Befunde

**p6_1/p6_4 Walk-Forward (3 rollierende Sub-Perioden 2016-2026)**: Sharpe pro
Markt/Periode:

| Periode | EURUSD | GBPUSD | USDJPY | XAUUSD(H4) |
|---|---|---|---|---|
| 2016-2019 | -0.46 | -0.65 | -0.50 | -0.41 |
| 2019-2022 | -0.79 | -0.15 | -0.88 | -0.43 |
| 2022-2026 | -0.53 | -0.12 | -0.48 | **+0.20** |

Alle FX-Maerkte in ALLEN 3 Perioden negativ. Gold nur in der juengsten
Periode schwach positiv (Sharpe 0.20, PF 1.20, n=56). Winrate liegt
durchgehend nahe 30-36% -- fuer RR=2:1 liegt der rechnerische Breakeven-WR bei
33.3% (1/(1+RR)), die Strategie also strukturell auf/knapp unter der
Nulllinie, bevor ueberhaupt Kosten draufkommen.

**p6_2 Monte-Carlo-Bootstrap** (Portfolio aller 4 Maerkte, letzte Sub-Periode
2022-2026, block_size=20/n_sims=2000, RISK_PERCENT=0.5% Bot-Default, max. 3
gleichzeitige Positionen): realer Pfad verliert -31.5% des Kapitals
(final_equity $68.495 von $100.000). Bootstrap: **P(MaxDD>30%) = 79.8%**,
Median Sharpe = -0.51, Median Calmar = -0.14. Kein Szenario, in dem dieses
Ergebnis als "ungluecklicher Einzelpfad" relativiert werden koennte -- die
gesamte Bootstrap-Verteilung ist negativ zentriert.

**p6_3 Kosten-Sensitivitaet** (letzte Sub-Periode 2022-2026, je Markt):
EURUSD/GBPUSD/USDJPY sind bereits bei **unter 1bps** Spread (praktisch
kostenfrei) an der Verlustzone -- das ist KEIN Kostenproblem, sondern ein
strukturelles Edge-Problem (Sicherheitsfaktor <1.0x gegenueber der ohnehin
schon knappen Kostenannahme). Einzig Gold hat einen echten Puffer:
Breakeven zwischen 30-50bps gegen 10bps Annahme (5.0x Sicherheitsfaktor) --
aber Gold stellt nur 56 von insgesamt ueber 800 Trades in dieser Periode,
kann das FX-Uebergewicht im Portfolio nicht auffangen.

## Fazit

**Kein Blocker-freier Fund.** Die Strategie liegt bei WR nahe am
rechnerischen RR-Breakeven, verliert in FAST jeder Markt/Perioden-Kombination
Geld, und der Monte-Carlo-Bootstrap zeigt ein strukturell negatives
Portfolio-Ergebnis in der juengsten (und damit relevantesten) Periode, nicht
nur ein Sequenzrisiko-Randfall. Einzig Gold auf H4 zeigt in der juengsten
Periode einen schwachen, aber nicht kostenkritischen Vorteil -- zu duenn (56
Trades, ein Markt), um allein eine Live-Freigabe zu tragen.

**Empfehlung**: Bot NICHT wie konfiguriert live/Demo schalten. Falls
weiterverfolgt: entweder auf Gold-only H4 reduzieren und dort separat mit
laengerer Historie/mehr Sub-Perioden pruefen (aktuell nur n=56 in der
staerksten Periode -- zu duenn fuer eine eigenstaendige Entscheidung), oder
die Long/Short-Symmetrie und den Neutralzonen-Parameter (`TREND_BUFFER_ATR`)
grundlegend neu durchdenken -- beides wuerde eine neue Phase-4/5-Runde
brauchen, kein Nachbessern in Phase 6. NICHT in dieser Session verfolgt (das
waere ueber den Auftrag "rekonstruieren und pruefen" hinausgegangen, siehe
[[backtest-standard-process]]: erst pruefen, Optimierung ist ein bewusster
Folgeschritt mit dem Nutzer).

Die live-only Ueberlagerungen SECURE_PROFIT (Gewinn-Absicherung,
prozentkapitalbasiert) und die Tageslimits (-1.0%/+5.0%) sind in diesem
Backtest NICHT modelliert (passen nicht in `strategy.backtest.simulate_trades`'s
R-multiple-Engine) -- wuerden das obige Bild aber nicht grundlegend aendern:
Tageslimits kappen nur Verlust-/Gewinn-Serien, schaffen aber keinen
strukturellen Edge, wo keiner ist.

**Verknuepfung**: [[mt5-haupt-bot-trend-pullback]], [[mt5-gold-silber-divergenz]]
(die anderen beiden Bots desselben Pakets), [[backtest-standard-process]].

## Nachtrag 2026-08-25 -- Phase 5 (Optimierung), 9 Hebel getestet, NICHT integriert

Auf Nutzer-Wunsch ("gehe alle Optimierungsfaktoren durch") systematisch alle
Standard-Bausteine + strategie-eigenen Parameter durchgetestet, gleiche
Disziplin wie bei [[mt5-gold-silber-divergenz]] (nur auf IS 2016-2022
gewaehlt, unveraendert auf OOS 2023-2026 geprueft). Code:
`scripts/research_mt5_david_v2_optimization.py` (Pass 1-3),
`scripts/research_mt5_david_v2_final_phase6.py` (volle Phase-6-Runde auf der
finalen Kombi). Neuer optionaler `vol_window`/`vol_quantile`-Parameter in
`mt5_david_v2/pipeline.py` (Default `None`/aus -- Bot-Original-Signal-
Paritaet bleibt unveraendert erhalten).

**Bottleneck-Diagnose vorab** (gepoolt ueber alle 4 Maerkte, IS): ADX-Regime
zeigt KEINEN Unterschied (high_adx PF=0.85 == low_adx PF=0.85, anders als
beim Haupt-Bot). Long schlaegt Short in 3 von 4 Maerkten. Eine NORMIERTE
Volatilitaets-Zerlegung (ATR/Preis, nicht roher Dollar-ATR -- Lektion aus
dem verworfenen Bot-3-Artefakt) zeigt einen echten Effekt: Hoch-Vol-Tertile
PF~1.10-1.13 vs. Niedrig/Mittel-Vol PF~0.53-0.88.

**9 getestete Hebel**:

| # | Hebel | Ergebnis |
|---|---|---|
| 1 | ADX-Filter | kein Effekt -- nicht weiterverfolgt |
| 2 | Vol-Filter (`vol_window=1000, vol_quantile=0.7`, normiert) | **haelt IS->OOS** (Sharpe -0.19->+0.11 OOS, MaxDD -30.3%->-14.3%) |
| 3 | Stop/RR-Sweep (auf Vol-Filter-Config) | **Overfitting**: IS-Sharpe 0.59 (stop=1.5/rr=1.0), OOS faellt auf ~0.00 (PF<1.0) -- VERWORFEN |
| 4 | RSI_OVERSOLD x TREND_LEN-Sweep | Top-1 (rsi=45/trend_len=50) **Overfitting**: IS 0.58->OOS -0.90 -- VERWORFEN. Naechstbeste mit unveraendertem trend_len=200 (rsi_oversold=30 statt 35) **haelt IS->OOS** (0.43->0.29) -- UEBERNOMMEN |
| 5 | Session-/Zeitfenster-Filter (Entry-Stunde/Session-Bucket) | Beste IS-Session (Asien) **Overfitting**: IS-PF 1.10 -> OOS-PF 0.60 (schlechter als gar kein Filter) -- VERWORFEN |
| 6 | Kalman-Denoised-Slope-Bestaetigung (`strategy/kalman_filter.py`) | Stichprobe zu duenn (n=3-14 IS nach Kombination mit Vol-Filter) -- nicht beurteilbar, VERWORFEN |
| 7 | MTF-EMA-Ribbon-Filter (`strategy/mtf_ema_ribbon.py`, 4H/1D/1W/1D-Stack) | **Overfitting**: IS 0.41 (kaum Aenderung) -> OOS -0.89 -- VERWORFEN |
| 8 | CB-Event-Window-Filter (`bond_yield_indicator/calendar.py`, FOMC/ECB/BOE/BOJ +-1 Tag) | Scheitert schon auf IS selbst (Sharpe -0.11, schlechter als ohne Filter) -- VERWORFEN |
| 9 | Cross-Vote-Filter (`cls_cross_filter.py`) | Nicht getestet -- war fuer eine ANDERE Strategie (CLS Practical) bereits ohne Mehrwert getestet, niedrige Prioritaet |

**Finale gechainte Config** (Hebel 2 + 4): `trade_short=True` (unveraendert),
`vol_window=1000, vol_quantile=0.7, rsi_oversold=30.0, trend_len=200`
(unveraendert), Stop/RR unveraendert (1.5/2.0).

**Trade-Ebene** (gepoolt, Walk-Forward): **erstmals alle 3 Perioden
positiv** -- 2016-2019 Sharpe +0.55, 2019-2022 +0.61, 2022-2026 +0.22.

**Aber Portfolio-Ebene bleibt negativ** -- der entscheidende Befund dieser
gesamten Runde: Monte-Carlo-Simulation mit echten Positionsgroessen (0.5%
Risiko, max. 3 gleichzeitige Positionen ueber die 4 Maerkte, letzte
Sub-Periode 2022-2026): realer Pfad endet bei $90.857 (Verlust von
$100.000), **Median-Sharpe -0.39** (sogar schlechter als beim Vol-Filter
allein, -0.13), P(MaxDD>10%)=78%. Kosten-Sensitivitaet bestaetigt: GBPUSD/
USDJPY bereits unter der angenommenen Kostenannahme unprofitabel (Sicherheits-
faktor 0.5x/0.7x), nur EURUSD (0.7x, besser als vorher aber immer noch <1)
und Gold (n=12, zu duenn) zeigen ueberhaupt einen Puffer.

**Interpretation**: anders als bei [[mt5-gold-silber-divergenz]] (1 Markt, 1
Position, Trade-Ebene = Portfolio-Ebene) laufen bei David-V2 Trade-Ebene und
Portfolio-Ebene systematisch auseinander -- ein Hinweis, dass das Problem
weniger an der Entry-Signal-Qualitaet liegt als an der Portfolio-Konstruktion
selbst (4 korrelierte Maerkte teilen sich 3 Slots; welche Trades durch die
Concurrency-Kappe fallen, haengt von der Eintreffensreihenfolge ab, nicht
von der Signal-Qualitaet). Das waere eine andere Art Folgearbeit
(Portfolio-Konstruktion, nicht Signal-Sweep) -- auf Nutzer-Entscheidung
NICHT weiterverfolgt (2026-08-25: "Gut wir lassen das und integrieren nur
Bot 3").

**Endgueltiges Fazit**: David-V2 bleibt NICHT fuer Live-/Demo-Betrieb
empfohlen, auch nach erschoepfender Phase-5-Optimierung (9 Hebel, davon 2
mit echtem, validiertem Trade-Level-Edge). Kein Dashboard-Tab, keine
Aenderung an den Pipeline-Defaults -- `mt5_david_v2/pipeline.py`s neue
`vol_window`/`vol_quantile`-Parameter bleiben als dokumentierter, aber nicht
aktivierter Baustein im Code (Default `None`), fuer den Fall, dass der
Portfolio-Konstruktions-Winkel spaeter aufgegriffen wird.
