# Resource: Evidenz für die Makro-Gates R/P/B/F und den Zustand

Prüfung der Gate-Regeln aus dem Makro Fact Sheet (`fusion_lab/macro_agent`) gegen Forschung und
Praxis, Nutzerauftrag 11.11.2026 („Woher kommen die Gate-Annahmen? Mit eigener Research prüfen“).
Gehört zu [[makro-wirkketten-und-regeln]] (dort §3–§6 die Regeln) und [[quant-diskretionaer-fusion]].

Tags: Makro, Gate, Momentum, Zinsdifferenz, COT, Stress, Agent.

**Folge (11.11.):** Umbau zur Multi-Faktor-Scorecard mit Ersatzquellen, Backtest ohne Edge →
[[makro-scorecard-v2]].

## Herkunft

| Teil | Quelle |
|---|---|
| Fünf Gates M/R/P/B/F, Regel „≥ 4 von 5, kein dominantes FAIL“ | SMT-Reports (Dennis), notiert 21.10. in [[makro-wirkketten-und-regeln]] §4 |
| „≥ 75 % gepreist = bezahlt“, „Veränderung ist das Signal“ | SMT-Reports, §3 |
| TAIL-Schwellen (VIX 28, HY 350, Brent 120, OAT-Bund 180) | SMT-Report 21.10., §6 |
| Umsetzung in Zahlen: R = 2J-Spread über 1 Woche, P = SMA20 + Woche, F = COT 3 J ≥ 90 / ≤ 10, ALT-Zustand | eigene Annahmen 10.11., **ungetestet** |

Keine der Regeln ist bisher auf Daten geprüft. Die Richtungs-Calls der SMT-Reports selbst brachten im
Backtest ≈ 0 R ([[smh-makro-reports-backtest]]).

## Was Forschung und Praxis sagen

| Gate | Befund | Folge für uns |
|---|---|---|
| R (Zinsen) | Unerwartete Änderungen der Zinsdifferenz bewegen den Dollar, erwartete kaum (Fed-Note 2017). Zinsänderungen und Kurvensteigung sagen FX-Überrenditen bis 12 Monate voraus (Ang/Chen 2010; Chen/Tsang 2013) – auf Monatsbasis. | Stützt die 75-%-Regel. 1 Woche misst eher, was schon im Kurs ist; Prognose-Horizont 1–3 Monate prüfen. |
| P (Preis) | Time-Series-Momentum trägt in allen 58 Märkten inkl. FX mit 12-Monats-Rückblick, Monatswechsel (Moskowitz/Ooi/Pedersen 2012). | SMA20 + 1 Woche ist sehr kurz, dort ist FX-Momentum schwach und kostenanfällig. |
| B (G8) | Querschnitts-Momentum: bis 10 % p.a. Gewinner minus Verlierer, schwer ausnutzbar (Menkhoff et al. 2012). Eigener Test: G8-Nachbau kein Signal (Memory „G8-Stärke nachgebaut, kein Signal“). | **B und P messen beide Momentum**, R auf 1 Woche ebenfalls den gleichen Kursverlauf. „4/4“ zählt teils dasselbe dreimal. |
| F (COT) | Positionsänderungen erklären 30–45 % der Wechselkursbewegung derselben Woche, sagen die Folgewoche aber nicht voraus (NY Fed, Klitgaard/Weir 2004). COT-Index 3 J ist ein Praktiker-Werkzeug (Williams/Briese); Schwellen uneinheitlich (80/20, 75/25, 90/5, 95/5), kein begutachteter Beleg für Extreme. Eigener IS-Befund 10.11.: Crowding bester Zusatz zu Carry, als Veto ([[remy-king-trading-strategie-top1]]). | Nur als Veto behalten (so gebaut); Schwelle ist offen. |
| Zustand | Kein Standard. Gängige Stressmarken: VIX > 30, HY-Spread > 500–600 bp; VIX hoch ohne breitere HY-Spreads = Aktienstress, kein Kreditstress. | TAIL bei HY 350 bp ist streng (SMT). Ergänzung: amtlicher Stressindex (St. Louis Fed FSI auf FRED). |
| Fehlende Bausteine | Banken und Fonds bauen FX auf Carry, Value, Momentum und Dollar-Faktor (Lustig/Roussanov/Verdelhan 2011/2014; Menkhoff et al.). | Carry-Niveau und Value (Kaufkraftparität) fehlen im Fact Sheet. |

## Prüfung des Fact Sheets gegen öffentliche Quellen (11.11.)

- **Leitzinsen falsch:** BoE 4,00 % seit 05.11. (Fact Sheet 3,75), RBA 4,85 % seit 03.11. (4,60). Siehe
  Memory „BIS-Leitzins hinkt nach“.
- **Fed-Pfad stimmt:** Jan-Kontrakt +22 bp ≈ 88 % × 25 bp; CME FedWatch nach dem CPI 85–90 % für +25 bp
  im Dezember, vor einer Woche ~72 %, am Vortag ~84 %. Nach SMT-Regel war die Dezember-Anhebung schon
  vor dem CPI „bezahlt“. Das Fact Sheet zeigt aber keine Wahrscheinlichkeit je Sitzung, die Regel ist
  so nicht direkt prüfbar.
- **US-2J hinkt:** FRED-Wert 1–2 Tage alt; am CPI-Tag +18–20 bp auf ~4,75 %.
- **CPI 10.11.:** Gesamt +0,4 % (Konsens 0,3), Kern +0,3 % (0,2) – deckt sich mit dem Kalender-Ist.

## Erster Realitätscheck (CPI-Tag, n = 5, keine Evidenz)

Von 13:00 UTC 10.11. bis 11.11. 19:00 UTC: USDCAD long +0,54 %, AUDUSD short +0,29 %, GBPJPY long
±0, AUDJPY short −0,55 %, CADJPY short −0,32 % (Yen fiel mit dem Dollar-Anstieg). Die Yen-Kreuze
hingen am G8-Momentum (Yen stark), die Nachricht drehte es. Passt zur Leitlinie „Dollar-Stärke nur
gegen Rohstoffwährungen“ in [[makro-agent-report-pruefung]].

## Quellen

- [Menkhoff, Sarno, Schmeling, Schrimpf: Currency Momentum Strategies (BIS WP 366)](https://www.bis.org/publ/work366.pdf)
- [Moskowitz, Ooi, Pedersen: Time Series Momentum](https://papers.ssrn.com/abstract=2089463)
- [Fed IFDP-Note 2017: Sensitivity of the US dollar to monetary policy expectations](https://www.federalreserve.gov/econres/notes/ifdp-notes/the-sensitivity-of-the-us-dollar-exchange-rate-to-changes-in-monetary-policy-expectations-20170922.pdf)
- [Ang, Chen: Yield Curve Predictors of Foreign Exchange Returns](https://drupalgsb-test.paas.cc.columbia.edu/faculty/research/yield-curve-predictors-foreign-exchange-returns)
- [Chen, Tsang: What does the yield curve tell us about exchange rate predictability?](https://vtechworks.lib.vt.edu/handle/10919/25507)
- [Klitgaard, Weir (NY Fed 2004): Exchange rate changes and net positions of speculators](https://www.newyorkfed.org/research/epr/04v10n1/0405klit.html)
- [Lustig, Roussanov, Verdelhan: Common Risk Factors in Currency Markets](https://www.nber.org/papers/w14082.pdf)
- [Lustig, Roussanov, Verdelhan: Countercyclical Currency Risk Premia](https://www.nber.org/papers/w16427.pdf)
- [Williams x Briese COT-Index (Schwellen-Varianten)](https://www.tradingview.com/script/ztTU7B7o-Williams-x-Briese-Hybrid-CoT-Index)
- [Bank of England: Bank Rate](https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate)
- [Westpac: RBA hikes to 4.85 %](https://www.westpaciq.com.au/economics/2026/11/rba-decision-3-november-2026)
- [Investing.com: Fed hike odds 88 % after hot CPI](https://www.investing.com/news/economy-news/fed-rate-hike-odds-in-december-at-88-after-hot-cpi-cme-fedwatch-5017585)
- [CoinDesk: CPI +0,4 %, Kern +0,3 %](https://www.coindesk.com/markets/2026/11/10/u-s-cpi-rose-stronger-than-expected-0-4-in-october-core-rate-rose-0-3)
