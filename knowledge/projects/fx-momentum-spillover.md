# Project: FX-only Momentum-Spillover-Nachbau (JPM-Paper)

**Ziel**: Workstream A aus dem 2026-09-09-Plan zu
[[cross-asset-momentum-spillover]] (JPM "Cross Asset Momentum Spillover",
Salopek/Tzotchev) -- vereinfachter Nachbau der Paper-These auf den 7
FX-Majors des Paper-Universums, mit eigenem Ersatz-Momentum-Signal (die
Original-Formel liegt in einem anderen, nicht verfügbaren Paper) und
eigener rollierender L1-Logit-Spillover-Regression.

**Status**: **abgeschlossen, negativer Befund.** Kein integrierbarer
Strategie-Kandidat. Kandidat für `archive/`, sobald der Nutzer das
bestätigt (siehe `knowledge/README.md`-Konvention: Projects wandern erst
nach expliziter Bestätigung, nicht automatisch).

**Warum als Project (nicht Area)**: hat ein klares Ende -- Go/No-Go-
Entscheidung steht (No-Go).

**Code**: `fx_momentum_spillover/` (`data.py`, `signals.py`, `spillover.py`,
`portfolio.py`), `scripts/research_fx_momentum_spillover.py`. `NZDUSD` neu
in `combined_strategy/data.py::INSTRUMENTS` registriert.

## Aufbau (Kurzfassung, Details im Code-Docstring)

- **Universum**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
  (7 der 42 Paper-Assets).
- **Ersatz-Momentum-Signal**: t-Test auf die mittlere tägliche Log-Rendite
  über 5 Lookbacks (32/64/126/252/504 Handelstage), durch die
  Standardnormal-CDF auf [-1,1] gemappt -- passend zur eigenen
  Paper-Beschreibung ("statistical hypothesis tests on the mean return"),
  aber NICHT die Original-JPM-Formel (die steht in einem anderen,
  referenzierten, hier nicht vorliegenden Paper).
- **Spillover-Modell**: rollierende L1-Logit-Regression (sklearn,
  `l1_ratio=1.0`, `solver="liblinear"`) je Rebalancing-Monat und
  Ziel-Paar, Feature = Momentum-Signale der 6 anderen Paare, Ziel =
  Vorzeichen der 1-Monats-Vorwärtsrendite, Trainingsfenster
  max(2×Lookback, 252 Tage), Regularisierungs-Grid {0.05,0.1,0.2} via
  `TimeSeriesSplit`.
- **Portfolio**: monatliches Rebalancing, Long/Short nach Signal-Vorzeichen,
  Positionsgröße invers zur realisierten Vol (20 Tage), auf Gross-Exposure=1
  normalisiert (siehe Bugfix unten), Portfolio-weite Skalierung auf 10%
  Ziel-Annualvol (rollierend 1 Jahr, Leverage gedeckelt bei 3x), 1-Tag
  Execution-Lag, 2.5bps Kosten.

## Datenlücke gefunden + Backtest-Fenster angepasst

Dukascopy's NZDUSD-D1-Serie ist 2003-2009 lückenhaft (verifiziert: ein
direkter Fetch in einem der Lücken-Fenster liefert 0 Zeilen -- echte
Datenlücke beim Anbieter, kein Fetch-Bug), USDJPY hat separat eine Lücke
2010-02..2010-09. Ein Inner-Join über alle 7 Paare ab 2003 hätte
Vor-Lücke- und Nach-Lücke-Daten stillschweigend als benachbarte
Handelstage verkettet -- fatal für ein rollierendes Momentum-Fenster.
`fx_momentum_spillover/data.py::check_no_gaps()` erkennt das jetzt aktiv
(wirft bei jeder Lücke >10 Kalendertage). Backtest-Fenster deshalb auf
**2010-11-01 -- 2026-08-31** eingegrenzt (190 Monats-Rebalancing-Termine)
statt der ursprünglich geplanten vollen 2003-2026-Historie -- zusätzlich
zur ohnehin schon eingeplanten 7-statt-42-Asset-Stichprobenschwäche.

## Bug gefunden + behoben: Turnover/Return-Skalen-Asymmetrie

Erster Lauf zeigte absurde Ergebnisse (MaxDD nahe -100%, Volatilität
explodierte mit steigenden Kosten auf über 200%) -- kein echter
Strategie-Befund, sondern ein Konstruktionsfehler: die ursprüngliche
Gewichtung (`sign(signal)/vol`, unnormalisiert, typische Größenordnung
10-40) kombinierte Paare für die RENDITE per `.mean()`, aber für den
TURNOVER (und damit die Kosten) per `.sum()` -- diese Asymmetrie ließ die
Kosten eine völlig andere Größenordnung erreichen als die Rendite, gegen
die sie verrechnet wurden (Tagesrenditen bis -420% beobachtet).
**Behoben**: Gewichte werden jetzt so normalisiert, dass die
Brutto-Exposure (Summe der Beträge über alle 7 Paare) an jedem
Rebalancing-Termin exakt 1 ist (Standard-Risk-Parity-by-Inverse-Vol) --
sowohl Rendite- als auch Turnover-Berechnung arbeiten dadurch auf
derselben, gut beschränkten Skala. Nach dem Fix: keine Tagesrendite mehr
unter -10%, Volatilität bleibt bei jedem Kostenniveau stabil um ~8%.
Sauber dokumentiert im Docstring von `fx_momentum_spillover/portfolio.py`
für den Fall, dass dasselbe Muster (inverse-Vol-Gewichtung + getrennte
Rendite-/Turnover-Aggregation) anderswo im Repo wiederverwendet wird.

## Ergebnis (nach Bugfix, siehe volle Tabellen im Skript-Output)

| Strategie | Aggregierter Sharpe (diese Rebuild) | Paper-Behauptung (42 Assets) |
|---|---|---|
| Individual-Momentum | -0.37 | +0.66 |
| Spillover | -0.13 | +0.75 |
| Combination | -0.30 | +0.74 |

- **Kein Sharpe-Uplift durch Spillover reproduziert** -- im Gegenteil,
  alle drei Varianten sind auf dieser 7-Asset-FX-Teilmenge im Aggregat
  NEGATIV (Paper: alle drei deutlich positiv). Die QUALITATIVE Richtung
  "Spillover verbessert gegenüber reinem Individual-Momentum" zeigt sich
  schwach auch hier (Spillover -0.13 vs. Individual -0.37 -- weniger
  schlecht, nicht besser als Null), aber das ist bei durchweg negativen
  Werten kein belastbarer Fund.
- **IS/OOS (Split 2019-01-01)**: durchweg konsistent negativ in beiden
  Fenstern (Individual IS -0.36/OOS -0.39, Spillover IS 0.00/OOS -0.25,
  Combination IS -0.25/OOS -0.35) -- kein Regime-Bruch, sondern
  gleichmäßig schwach über die ganze Historie.
- **Monte-Carlo-Bootstrap** (2000 Resamples der Monatsrenditen,
  Aggregated Combination): P(Gesamtrendite < 0) = 93.3%, selbst das
  95.-Perzentil landet nur knapp über Sharpe 0.
- **Kosten-Sensitivität**: bereits bei 0bps Kosten ist der Sharpe negativ
  (-0.25) -- das Problem ist NICHT in erster Linie Handelskosten, sondern
  ein grundsätzlich zu schwaches/falsches Signal auf dieser Stichprobe.
- **Einzelner interessanter Ausreißer**: Spillover bei Lookback=504 zeigt
  als einziges Segment einen positiven Sharpe (+0.56, MaxDD nur -22%) --
  isoliert nicht vertrauenswürdig (1 von 15 getesteten Segmenten, keine
  eigene OOS-Bestätigung dieses einen Segments, klassisches
  Multiple-Comparisons-Risiko) -- kein Anlass, das gesondert zu verfolgen.

## Einordnung / warum das Ergebnis plausibel ist

Passt zur vor dem Backtest offen dokumentierten Erwartung (Plan dieser
Session): 7 statt 42 Assets und ~15,75 statt ~30 Jahre Monatsdaten (190
statt vermutlich >300 Beobachtungen im Original) sind eine deutlich
dünnere, instabilere Cross-Sektion -- die L1-Spillover-Regression hat pro
Ziel-Asset nur 6 potenzielle Prädiktoren (statt 41), was die Fähigkeit
des Modells, echte Cross-Asset-Beziehungen zu finden, strukturell
einschränkt. Zusätzlich ist das eigene Ersatz-Momentum-Signal nicht die
Original-JPM-Formel. Beide Abweichungen waren vorher als Kandidaten für
"warum es hier schwächer ausfallen könnte" benannt -- das Ergebnis
bestätigt das, ohne dass sich die beiden Faktoren einzeln sauber trennen
lassen.

## Verknüpfung

[[cross-asset-momentum-spillover]] (Paper-Distillation), [[paper-verarbeitung]]
(Area, allgemeiner Prozess).
