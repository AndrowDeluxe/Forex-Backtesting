# Project: MT5 Haupt-Bot (Trend+Pullback, Long-only)

**Ziel**: Den ersten von drei "Neue Bots" (Community-Release-Paket unter
`OneDrive/.../Institutial Mandate/Bots/Neue Bots/1-Haupt-Bot/`, siehe
`ANLEITUNG.md`/`CHANGELOG.md` dort) als backtestbare Basis unseres
Standardprozesses dokumentieren. Live-Quelle ist eine aeltere Instanz
desselben Bots unter `C:\Users\andre\OneDrive\...\Bots\Ideen1\
MT5-TrendPullback-Bot\` sowie die laufende Demo-Instanz
`C:\Users\andre\TrendPullback-Bot\` (siehe [[mt5-bot-deployment]]).

**Status**: Phase 6 (Robustheit) vollstaendig abgeschlossen. War bereits zu
~90% erledigt (mt5_trend_pullback/-Paket + 15 Research-Skripte existierten
schon), es fehlte nur p6_2 (Monte-Carlo) -- eine reine Second-Brain-
Nachholung, kein neuer Fund. Kein `knowledge/projects/*.md`-Eintrag existierte
vorher fuer dieses Paket, obwohl die Arbeit selbst schon gemacht war -- genau
die Luecke, die [[backtest-standard-process]] beschreibt.

**Prozess-Referenz**: `app_pages/education_gold_intraday.py`, Phase 6
"Robustheit" -- p6_1 Walk-Forward/echter OOS-Split, p6_2 Monte-Carlo-Bootstrap
(`ou_paper_backtest/monte_carlo.py`), p6_3 Kosten-Sensitivitaet, p6_4 mehrere
Jahre/Regime.

## Strategie & Code-Basis

Long-only Trend+Pullback: `close > EMA(150)` (Aufwaertstrend) UND RSI(14)
kreuzt von unten ueber 35 (Pullback endet). Stop = ATR(14) x 2.0, Ziel = 2R
(Fixed SL/TP bei Order-Eroeffnung, kein Trailing). Maerkte/Timeframes exakt
wie `config.py` des Live-Bots: XAUUSD/XAGUSD/XPTUSD auf H1, CHFJPY/USDJPY auf
H4. Max. 3 gleichzeitig offene Positionen ueber alle 5 Maerkte, 1% Risiko/Trade.

Repo-Code: `mt5_trend_pullback/pipeline.py` reproduziert die Bot-eigenen
Indikatorformeln WOERTLICH (`ewm(alpha=1/length)` ab der ersten Kerze, NICHT
`strategy.indicators.wilder_smooth`'s abweichend geseedete Wilder-Glaettung) --
bewusste Entscheidung, damit Backtest-Signale exakt mit dem decken, was der
Live-Bot auf denselben Kerzen ausgeloest haette. `mt5_trend_pullback/
account_simulation.py` bildet das dollar-denominierte Portfolio (sequenzielles
Replay, Equity-Update nur bei Trade-Close, siehe Docstring dort fuer die
offengelegten Vereinfachungen). `daily_risk_engine.py`/`open_risk_engine.py`
sind fuer Prop-Firm/FK-Kalibrierung vorbereitet, hier nicht gebraucht (Bot hat
kein FK-Mandat). `filters.py`/`execution_overlay.py` sind Forschungs-Extras,
NICHT Teil der Live-Logik.

## Phase 6 -- Robustheit: Befunde

**p6_1 Walk-Forward/OOS** (`research_mt5_trend_pullback_regime_shift.py`):
Ein zuerst gewaehltes "optimiertes" Filter/TP-SL/BE-Kombo ueberoptimierte
deutlich (neue-IS Sharpe 2.46 -> neue-OOS Sharpe 0.11, SCHLECHTER als gar
nichts zu tun). Die UNVERAENDERTE Bot-Default-Config (kein Filter, EMA150/
RSI14x35/ATR14x2.0/RR2.0) validiert dagegen robust: neue-OOS (2024-07 bis
2026-08) Sharpe 0.78, PF 1.37 gepoolt. Deshalb ist master_table.csv/diese Notiz
auf der DEFAULT-Config aufgebaut, nicht der optimierten.

Pro Markt (OOS 2024-07/2026-08, `mt5_trend_pullback/results/master_table.csv`):

| Markt | TF | n_oos | WR | PF | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|---|---|
| XAUUSD | H1 | 43 | 48.8% | 1.31 | 0.43 | +2.6% | -7.5% |
| XAGUSD | H1 | 41 | 43.9% | 1.35 | 0.47 | +5.2% | -11.6% |
| XPTUSD | H1 | 30 | 43.3% | 1.35 | 0.40 | +3.5% | -7.6% |
| CHFJPY | H4 | 18 | 50.0% | 2.13 | 0.81 | +2.3% | -2.1% |
| USDJPY | H4 | 13 | 46.2% | 1.19 | 0.17 | +0.4% | -1.6% |

CHFJPY/USDJPY haben kleines n (13-18 Trades OOS) -- Sharpe dort mit
entsprechend groesserer Unsicherheit lesen. Metalle liefern das breitere
Sample (30-43 Trades).

**p6_2 Monte-Carlo-Bootstrap** (neu, `scripts/
research_mt5_trend_pullback_monte_carlo.py`, block_size=20, n_sims=2000,
zirkulaerer Bootstrap, Portfolio mit max. 3 gleichzeitigen Positionen, OOS
2024-07/2026-08):

| Risiko/Trade | Median TotalReturn | Median MaxDD | P(MaxDD>10%) | P(MaxDD>20%) | Median Sharpe |
|---|---|---|---|---|---|
| 0.5% | +21.3% | -6.0% | 7.5% | 0.0% | 0.99 |
| 1.0% (Bot-Default) | +45.4% | -11.7% | 69.9% | 6.0% | 0.99 |
| 1.5% | +72.4% | -17.1% | 98.5% | 31.4% | 0.99 |
| 2.0% | +102.3% | -22.3% | 100.0% | 64.6% | 0.99 |

Der reale historische Pfad bei 1% Risiko (final_equity $146.819, MaxDD $11.002
~ -11.7% vom Startkapital $100.000) liegt nahe am P50-Bootstrap-Pfad -- kein
Warnsignal, dass der reale Pfad ungewoehnlich guenstig gelaufen ist. Bei
config.py's Default (RISK_PERCENT=1.0, MAX_OPEN_POSITIONS=3) sind aber knapp
70% der Bootstrap-Pfade mit einer Drawdown-Phase >10% zu rechnen -- kein
Blocker fuer einen Demo-Bot ohne hartes DD-Limit, aber relevant, falls dieser
Bot je fuer eine FK-Challenge (feste DD-Grenze) vorgesehen wird: dann eher
0.5% Risiko/Trade waehlen (P(MaxDD>10%) faellt auf 7.5%).

**p6_3 Kosten-Sensitivitaet** (`research_mt5_trend_pullback_spread_sensitivity.py`):
Breakeven-Spread je Markt OOS-only ermittelt (2023-2026, das einzige Fenster
mit echtem Edge -- ein IS-Breakeven waere fuer eine unprofitable Regime-Periode
irrefuehrend niedrig). Aktuelle Kostenannahme (10.0bps Metalle, 3.0bps CHFJPY,
1.5bps USDJPY) ist eine gelabelte Annahme, kein gemessener Spread (Repo hat
keinen historischen Bid/Ask-Feed) -- Sicherheitsfaktor gegenueber dem
Breakeven-Punkt im Skript-Output dokumentiert, nicht hier dupliziert (siehe
Skript direkt fuer die aktuellen Zahlen je Markt).

**p6_4 Mehrere Jahre/Regime**: Datenspanne 2016-2026 (10 Jahre) durchgehend.
`research_mt5_trend_pullback_small_timeframes.py` testet alle 5 Maerkte
zusaetzlich auf M3/M5/M15/M30 -- M3/M5 durchgehend NEGATIV (bis Sharpe -5.15),
M15/M30 gemischt/schwach -- bestaetigt die eigene H1/H4-Wahl des Live-Bots
gegenueber jeder schnelleren Intraday-Variante.
`research_mt5_trend_pullback_regime_shift.py`'s Timeframe-Vergleich
(`regime_shift_timeframe_comparison.csv`) bestaetigt zusaetzlich: H1 ist beim
Live-Timeframe der Metalle, H4 bei den JPY-Crosses tatsaechlich der jeweils
staerkere von mehreren getesteten Timeframes, nicht nur "das, was der Bot
zufaellig nutzt".

## Weitere Forschungslinien in diesem Paket (nicht Teil der Live-Config)

`research_mt5_trend_pullback_adx_filter.py`, `_proven_filters.py`,
`_market_dropout.py`, `_fx_majors.py`, `_tp_sl_be_sweep.py`,
`_risk_management.py`/`_v2.py`, `_execution_overlay.py`, `_market_metrics.py`,
`_account_sim.py` -- alles Sweeps/Varianten, die die Default-Config NICHT
geschlagen haben (sonst waere master_table.csv darauf aufgebaut). Nicht
einzeln nachvollzogen fuer diese Notiz; bei Bedarf dort nachlesen, bevor eine
"verbesserte" Config vorgeschlagen wird -- die meisten dieser Pfade wurden
bereits mit demselben IS/OOS-Ergebnis (ueberoptimiert) probiert wie der
`regime_shift`-Fund oben.

## Fazit

Kein Blocker gefunden. Bot-Default-Config ist die robustere Wahl gegenueber
jeder bisher versuchten "Optimierung" -- konsistent mit dem, was `config.py`
des Live-Bots selbst schon sagt ("die NEUTRALEN Werte aus dem
Robustheitstest, NICHT die pro Markt ueberoptimierten"). Live-Demo-Betrieb
(`TrendPullback-Bot/`) ist entsprechend bereits die richtige Config; keine
Aenderung an `config.py` empfohlen.

**Verknuepfung**: [[mt5-bot-deployment]] (Live-Aufsetzung), [[mt5-david-v2-pullback]],
[[mt5-gold-silber-divergenz]] (die beiden anderen Bots desselben
Community-Release-Pakets).
