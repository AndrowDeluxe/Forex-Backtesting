# Project: Bond-Yield-Spread-Indikator

**Ziel**: Aus dem Spillover-Framework in [[monetary-policy-spillover]] einen
*stetigen* Indikator bauen, der Zins-Spreads zwischen den USA und den
Gegenländern der Haupt-FX-Paare laufend vergleicht -- statt nur binär in
3-Tage-Fenstern um Notenbanktermine wie im Paper -- und daraus ein FX-Signal
oder einen Filter für bestehende Strategien ableitet.

**Status**: Vollständig gebaut und rückgetestet (2026-08-10) -- Ergebnis:
**kein belastbarer Edge in V1**, kein Integrationskandidat in dieser Form.
Code lebt in `bond_yield_indicator/` (Layer 1-3 + Composite) und
`scripts/research_bond_yield_indicator.py` (Backtest, 6 Paare, 2016-2026,
IS/OOS-Split 2021-01-01, Vergleich ggü. Buy&Hold und 20-Tage-Momentum).
Datenentscheidung war [[monetary-policy-spillover|Hybrid]]: FRED jetzt
(US täglich, 6 Länder monatlich), Loader-Schnitt für spätere
Tagesquellen-Umstellung bewusst offengehalten.

## Backtest-Ergebnis (2026-08-10)

Equal-Weight-Portfolio über alle 6 Paare, Position = Vorzeichen des
Vortages-Indikators, ohne Transaktionskosten:

| | FULL | IS (bis 2021) | OOS (ab 2021) |
|---|---|---|---|
| Indikator | Sharpe +0.21, WinRate 49.9% | Sharpe +0.10 | Sharpe +0.30 |
| Buy&Hold | Sharpe +0.13 | Sharpe -0.16 | Sharpe +0.42 |
| Momentum20 | Sharpe -0.15 | Sharpe -0.49 | Sharpe +0.10 |

Einordnung: Trefferquote liegt bei praktisch allen 6 Einzelpaaren zwischen
48-51% -- ununterscheidbar von Zufall. IS/OOS ist instabil (z.B. CA kippt
von Sharpe +0.80 IS auf +0.08 OOS, DE von -0.21 IS auf +0.23 OOS) -- klassisches
Rauschmuster, keine stabile Kante. Der Indikator schlägt zwar den
Momentum20-Baseline, aber nicht konsistent Buy&Hold (OOS unterliegt ihm
sogar). Und das VOR Transaktionskosten, die bei ~50%-Trefferquote und
gelegentlichem Signalwechsel weiter belasten würden.

**Wahrscheinlichste Ursache**: die in der Datenlücke unten beschriebene
Monats-statt-Tages-Auflösung für 6 von 7 Ländern. Layer 1 (z-Score der
Rendite-Änderung) ist für diese Länder faktisch eine Stufenfunktion (nur an
~12 Tagen/Jahr echte Bewegung), und Layer 2 (Beta in FOMC-Fenstern) musste
deshalb in `beta.py` auf einen monatlichen Print-zu-Print-Schätzer
ausweichen, der die eigentliche Event-Fenster-Mechanik des Papers gar nicht
abbildet, s. `beta.py`-Docstring. Das ist kein Bug, sondern die direkte,
erwartete Konsequenz der Hybrid-Entscheidung -- der Test war fair, das
Ergebnis ist genau das, was die Datengrundlage hergibt.

## Architektur (drei Schichten)

**Layer 1 -- Spread-Core** (Herzstück, aktuell nicht baubar, siehe Datenlücke)
- `ΔS_i,t = ΔYield_US,t − ΔYield_i,t`, rollierend z-standardisiert je Land.
- Stetige Version von Baustein 2 aus dem Paper (dort nur in FOMC-Fenstern
  geschätzt).

**Layer 2 -- Event-Timing-Overlay** (Daten vorhanden: Appendix-Kalender)
- Rollierendes β_i (z.B. 2-Jahres-Fenster) statt Full-Sample-β als
  Sensitivitätsgewicht -- Pairs mit historisch hohem Spillover (CAD, EUR, GBP)
  bekommen mehr Gewicht auf US-Zinsüberraschungen als solche mit niedrigem
  (JPY, CHF, AUD).
- Signal-Konfidenz hoch in den 3-Tage-Fenstern um Fed/ECB/BoE/BoJ/BoC/SNB/RBA,
  gedämpft außerhalb (laut Paper "transitorisch").
- Kalenderdaten ab 2024 über offizielle CB-Kalender fortzuschreiben.

**Layer 3 -- FX-Liquiditätsfilter** (sofort baubar, keine neue Datenquelle nötig)
- Corwin-Schultz Bid-Ask-Spread aus den vorhandenen FX-OHLC-Parquets in
  `data_cache/` (D1/H1 für alle 6 Paare vorhanden).
- Signal-Gate: hohe FXF -> Signal-Size reduzieren (Paper zeigt gedämpfte
  Transmission bei hoher Friktion).

**Composite**:
`Indicator_i,t = z_i,t × w_event(D_CB, decay) × β_i,rolling × (1 − FXF_i,t_norm)`

**Wichtige Einschränkung**: Das Vorzeichen für den eigentlichen FX-Trade
(long/short je Paar) ist NICHT aus dem Paper ableitbar -- es regressiert nur
Yield-auf-Yield, keine FX-Returns. Arbeitshypothese über den
Zins-Differential-Kanal: fallende US-Renditen relativ zum Gegenland ->
tendenziell USD-Schwäche -> long EURUSD/GBPUSD/AUDUSD, short USDJPY/USDCAD/
USDCHF. Das ist eigene Kalibrierung, kein Paper-Ergebnis, und muss im Backtest
zuerst validiert werden, bevor irgendetwas produktiv läuft.

## Datenlücke (Express-Blocker)

- FX-OHLC (Layer 3): vorhanden.
- Event-Kalender (Layer 2): aus Paper-Appendix extrahierbar.
- **10J-Staatsanleiherenditen (Layer 1): fehlen komplett im Repo.** Keine
  FRED-Anbindung vorhanden, nur `yfinance` (FX/Crypto/Futures/Equities).
  Benötigte Serien (FRED, kostenloser API-Key): `DGS10` (US), `IRLTLT01DEM156N`
  (DE), `IRLTLT01GBM156N` (UK), `IRLTLT01JPM156N` (JP), `IRLTLT01CAM156N` (CA),
  `IRLTLT01CHM156N` (CH), `IRLTLT01AUM156N` (AU).

## Architektur, wie tatsächlich gebaut

- `bond_yield_indicator/fred.py` -- FRED-CSV-Endpoint (kein API-Key nötig,
  `fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`), Cache als Parquet.
  `COUNTRIES`-Dict trägt pro Land Serie/Pair/USD-Basis-Flag; `FREQUENCY`-Dict
  macht die Auflösung explizit und ist der Hook für einen späteren
  Pro-Land-Wechsel auf eine Tagesquelle.
- `bond_yield_indicator/calendar.py` + `bond_yield_indicator/calendars/*.csv`
  -- ECB/BoE/BoJ/BoC/SNB/RBA (1997-2024, aus Paper-Appendix-Tabellen 4-9
  programmatisch geparst, nicht abgetippt, s. `_calendar_build/`) und FOMC
  (2016-2026, von federalreserve.gov gescraped, als statische CSV eingefroren
  für Reproduzierbarkeit). Bewusst NICHT in `data_cache/` (gitignored),
  sondern im Package selbst -- das sind mühsam gewonnene Referenzdaten, kein
  Wegwerf-Cache.
- `bond_yield_indicator/friction.py` -- Corwin-Schultz auf den bereits
  gecachten FX-D1-Daten aus `combined_strategy.data`, keine neue Datenquelle.
- `bond_yield_indicator/spread.py`, `beta.py`, `indicator.py` -- Layer 1/2/3
  + Composite, s. Docstrings dort für alle Formeln und Annahmen im Detail.
- `scripts/research_bond_yield_indicator.py` -- Backtest, s. oben.

## Cross-Check: abgeleitete Bausteine (2026-08-11)

Drei Bausteine aus diesem Bau sind unabhängig vom inkonklusiven Composite-
Ergebnis wiederverwendbar, weil sie nicht auf der schwachen Monatsauflösung
beruhen:

1. **Corwin-Schultz-Liquiditätsfilter** (`bond_yield_indicator/friction.py`)
   -- getestet gegen den vollen Gold-ASB-Produktions-Stack (ADX+Trend+
   Delay+Silver), s. `scripts/research_gold_liquidity_event_filters.py`.
   **Bestanden: Randomisierungstest p=0.000/0.001, Walk-Forward in 6/6
   Testjahren bestätigt** (Ø-PF 1.463 -> 2.267). **2026-08-11: als 5.
   Produktionsfilter in `app_pages/asian_range_breakout.py` verdrahtet**,
   mit kausaler (Lookahead-freier) rollierender Zweidrittel-Schwelle
   (`apply_gold_liquidity_filter_causal`, nicht die Full-Sample-Schwelle
   des Signifikanztests) -- Sidebar-Toggle Standard AN. Finaler Backtest
   (100k/1% Risiko, Walk-Forward-Sequenz Wick/Overlay): CAGR 3.40%, Sharpe
   0.71, PF 2.12, 116 Trades über 10,5 Jahre, Max-DD -5.5%, TTP-konform
   (0 Tages-Grenzbrüche). Wiederverwendbarer Baustein:
   `asian_range_breakout/filters.py::attach_gold_liquidity`/
   `apply_gold_liquidity_filter_causal`. Auch weiterhin als eigenständiger
   Baustein in Streamlit dokumentiert: `app_pages/fx_liquidity_filter.py`
   (Strategie Bestandteile -> Kategorie FILTER). **2026-08-11: läuft jetzt
   sogar LIVE** im externen `GoldASB-MT5-Bridge`-Bot (separates Projekt,
   `C:\Users\andre\GoldASB-MT5-Bridge`, eigenständig ohne Laufzeit-
   Abhängigkeit von diesem Repo nachgebaut, s. dortige `daily_filters.py`),
   zusammen mit Trend-Bias/Delay/Silber, auf einem neuen BeyondIQCapital-
   Evaluierungskonto (1% Risiko, Task Scheduler alle 15 Min. aktiv).
2. **CB-Event-Window-Dummy** (`bond_yield_indicator/calendar.py`) -- gegen
   denselben Produktions-Stack getestet (FOMC, beide Richtungen). **Nicht
   bestanden**: Randomisierungstest p=0.42-0.62 in beide Richtungen, kein
   integrierbarer Baustein für Gold ASB. Bleibt als generischer Baustein in
   Streamlit dokumentiert (`app_pages/cb_event_window_filter.py`) für
   andere, ggf. besser passende Strategien (z.B. reine FX-Breakouts).
3. **US-10J-Rendite als Gold-Filter** (Realzins-Kanal, `fred.py`'s
   DGS10-Serie) -- getestet gegen die ADX-gefilterte Gold-Asian-Range-
   Breakout-Config, s. `scripts/research_gold_yield_filter.py`. Ergebnis:
   **kein integrierbarer Baustein**, Fenster-Sweep und IS/OOS instabil
   (Details: [[fx-microstructure]], Eintrag "US-10J-Rendite als
   Cross-Asset-Filter für Gold Asian-Range-Breakout").

Vollständige Rigor-Details (Randomisierung + Walk-Forward) für 1. und 2.:
[[fx-microstructure]], Eintrag "Corwin-Schultz Gold-Liquiditätsfilter &
FOMC-Event-Window (validiert, 2026-08-11)".

## Nächste Schritte (falls weiterverfolgt)

1. **Tagesquellen pro Land nachrüsten** (Bundesbank-API, BoE IADB, MOF Japan
   CSV, BoC Valet API, SNB Data Portal, RBA F2-Tabellen) -- das ist der
   naheliegendste Hebel, da das V1-Ergebnis direkt auf die Monats-Auflösung
   zurückgeführt werden konnte, nicht auf ein grundsätzlich falsches Framework.
2. Falls das die Kante nicht bringt: FX-Signal-Hypothese selbst infrage
   stellen (Zins-Differential/UIP-Kanal ist eigene Annahme, nicht aus dem
   Paper) -- z.B. Momentum statt Level/Änderung des Spreads testen.
3. Transaktionskosten einbauen, bevor überhaupt weiter optimiert wird --
   aktuell ist das Ergebnis schon vor Kosten flach.

**Verknüpfung**: [[monetary-policy-spillover]] (Paper-Distillat, der Ursprung
dieses Designs), [[paper-verarbeitung]] (Area, allgemeiner Prozess).
