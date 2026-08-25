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
