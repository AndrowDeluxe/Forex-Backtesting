# Gesamtportfolio-Backtest je Konto (2016–10/2026, reale Kosten, Live-Risiko)

**Stand 16.11.2026, Nutzerauftrag.** Skript `scripts/research_portfolio_live_2016.py ek|fk|ttp|iq|alle`,
Ergebnisse `portfolio_construction/results/live_2016/` (Trades je Konto, Beine, Jahre, Korrelation,
`alle_konten.csv`). Gleiche Kennzahlen wie der CTNL-Backtest ([[gold-confirmation-score]]).

## Grundlagen
- Beine und Risiko je Trade exakt wie am 16.11. in den Bridges (EK 1/8-Gewichte inkl. Hebel 1,2,
  FK `CAPITAL_WEIGHT × LEG_RISK_PCT` mit $500-Deckel, TTP `leg_risk_pct`-Overrides, IQ 1/3; CLS auf
  TTP/IQ mit Zinsfaktor). Startkapital = heutige Equity. ORB-US30 pausiert, CTNL-Continuation stillgelegt.
- Kosten gemessen je Broker (Gold TTP 2,08 / IQ 0,86 / FK 0,79 / Tickmill 1,07 bps ganztägig bzw. 0,38
  im ASB-Fenster; EURUSD- und Index-Spreads aus `research_live_legs`). Einstiegsverzögerung und
  R-Detektor wie live. CTNL mit Ribbon, Spike, Makro-Sperre, Kill-Switch.
- **Swap** 1,5 bps je Nacht (Annahme) auf CTNL, Gold-Silber, Trend Pullback; OU gemessen, BTC Annahme.
- Kontogrenzen werden ausgewiesen, nicht als Stopp simuliert.

## Ergebnis

| | EK (€) | FK | TTP | IQ |
|---|---|---|---|---|
| Trades/Jahr | 279 | 195 | 270 | 207 |
| Ø R · PF | +0,29 · 1,50 | +0,38 · 1,52 | +0,25 · 1,42 | +0,35 · 1,47 |
| Rendite p. a. (Zinseszins) | 147 % | 8,3 % | 10,0 % | 15,8 % |
| Rendite p. a. ohne Zinseszins | 113 % | 8,4 % | 9,9 % | 15,2 % |
| Sharpe · Sortino | 1,52 · 4,41 | 1,44 · 4,26 | 1,50 · 3,51 | 1,78 · 4,36 |
| Max DD · Calmar | −58,8 % · 2,5 | −10,6 % · 0,8 | −6,2 % · 1,6 | −7,3 % · 2,2 |
| Schlechtester Tag / Monat | −16,7 / −37,2 % | −0,9 / −2,4 % | −1,0 / −2,8 % | −1,4 / −3,4 % |
| Positive Monate · Jahre | 72 % · 9/11 | 58 % · 8/11 | 68 % · 11/11 | 71 % · 11/11 |
| MC-DD Median / 95 % | 46 / 63 % | 6,0 / 9,4 % | 6,7 / 10,4 % | 7,8 / 12,0 % |
| Kontogrenze | 45 % | 5 % | 7 % (+3 % Tag) | 6 % |
| **P(Bruch binnen 12 Monaten)** | 5 % | 9 % | **3 %** | **15 %** |
| Historisch erster Bruch | 10/2018 | 01/2017 | nie | 05/2017 |

- **TTP** ist das einzige Konto, das seine Grenze historisch nie gerissen hat.
- **IQ** hat die beste Sharpe (1,78), aber mit 15 % das höchste 12-Monats-Bruchrisiko (6 % Grenze,
  ~0,67 % auf Gold ASB). Live steht IQ bei −3,3 %.
- **FK** verliert 2016–18 (ORB und CLS schwach, beide hoch gewichtet), 894 Tage längste DD.
- **EK** handelt 3,5 % je Trade auf Gold ASB, Gold-Silber, BTC (2,2 % Trend Pullback). Die Zinseszins-
  Zahlen sind unrealistisch (Lotgrößen), aussagekräftig sind Max DD −59 % und schlechtester Monat
  −37 %. Die 45-%-Grenze wurde 2018 gerissen. Live liegt EK 24,8 % unter dem Hoch. Bekannte Lehre:
  Simulationen liefen bisher besser als live.

Größter Beitrag je Konto: EK Trend Pullback (34 %), FK ORB NASDAQ (29 %), TTP Gold ASB (30 %),
IQ CTNL (24 %). Beine sind untereinander kaum korreliert (Tages-PnL meist |ρ| < 0,15).

## Lücken
CLS-Zinsfaktor erst ab 12/2018 (US-Bond-Daten bei Dukascopy), Gold-ASB-Daten bis 01.10.2026 und ab
11/2016, ORB ab 07/2016, OU ab 06/2018, BTC ab 10/2017, Platin (Trend Pullback TTP/IQ) fehlt wegen
Datenfehler. Prüfung gegen die TTP-Listen 2019+: CLS/OU identisch, Abweichungen bei ASB (Live-Friktion),
NASDAQ (SL-Storno), CTNL (Sperren), Trend Pullback (ohne Platin) erklärt.
