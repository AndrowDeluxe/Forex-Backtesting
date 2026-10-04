# Project: Faber GTAA -- 10-Monats-SMA-Timing (SSRN 962461)

**Status**: **Phase 1-4 + Basis-Phase-6 erledigt (2026-10-04). Befund: der
Risiko-Teil hält nach Veröffentlichung, der Rendite-Teil nicht. Kein
Kandidat für die Prop-/Intraday-Portfolios** (monatliche, long-only
Asset-Allokation, ~70 % investiert, kein Stop). Höchstens relevant als
langfristige ETF-Depot-Regel (Phase 8 nur auf Zuruf).
Skript: `scripts/research_faber_gtaa.py`, Rohzahlen:
`Claude outputs/faber_gtaa.json`. Thema: [[trend-following-momentum]].
Prozess: [[backtest-standard-process]], Edge Card nach [[edge-card-workflow]]
(Ausnahme: Paper-Ursprung, Edge Card auf ausdrücklichen Nutzerwunsch
zusätzlich zum 8-Phasen-Prozess).

## Phase 2 -- Paper

Mebane Faber, *A Quantitative Approach to Tactical Asset Allocation*,
Working Paper 2006, J. Wealth Mgmt. 2007, Updates Feb. 2009 + Feb. 2013.
Daten: Global Financial Data, Total-Return-Monatsreihen, S&P 500 ab 1901,
GTAA 1973-2012, Backtests in Excel.

- **These**: ein rein preisbasiertes, mechanisches Monats-Timing (Kurs
  über/unter 10-Monats-SMA, sonst T-Bills) senkt Vola und Drawdown einer
  Anlageklasse und eines Portfolios deutlich, „with no adverse impact on
  return" (Schluss S. 53): „equity-like returns with bond-like volatility".
- **Regel** (S. 21-22): Kauf bei Monatsschluss > SMA10, Verkauf in Cash bei
  Monatsschluss < SMA10; Fill zum Schlusskurs des Signaltags; nur am
  letzten Handelstag des Monats; Kosten/Steuern/Slippage nicht modelliert.
- **Behauptet**:
  - S&P 1901-2012: 10,18 % statt 9,32 %, Vola 12,0 statt 17,9, MaxDD −50
    statt −83 %.
  - GTAA-5 1973-2012: 10,48 % statt 9,92 %, Vola 7,0 statt 10,3, Sharpe
    0,73 statt 0,44, MaxDD −9,5 statt −46 %.
  - Eigenes OOS 2006-2012: 6,01 statt 3,94 %, MaxDD −9,4 statt −46 %.
  - SMA 3-12 Monate stabil (Fig. 15).
- **Mechanismus laut Paper**: Volatility Clustering (Fig. 18): unter dem
  SMA liegt die Rendite im Schnitt 60 % niedriger, die Vola 30 % höher.
  Ausnahme Rohstoffe: dort ist die Vola nicht höher. Dazu kommen
  Verhaltensverzerrungen (App. C).
- **Warnsignale schon im Paper**:
  - Das OOS 2006-2012 enthält 2008. Ohne dieses Jahr liegt GTAA 2009-2012
    jedes Jahr UNTER Buy & Hold (Fig. 14).
  - Excel-Backtest mit nicht teilbaren Daten.
  - Die „Extensions" (13 Klassen, Aggressive Top-6, 2x-Hebel) sind
    In-Sample-Erweiterungen derselben Periode, keine unabhängige Prüfung.

## Phase 3 -- Screening

Einfaches Signal, keine State-Machine, null freie Parameter außer der
SMA-Länge. Lässt sich 1:1 nachbauen, mit ETF-Total-Return-Proxys über
yfinance. **Pflichtcheck aus [[eu-open-renditefenster]]:** Sample-Ende 2012
→ 2013-03 bis heute ist echtes Post-Publikations-OOS (~13,5 Jahre). Dazu
eine Jahresreihe ohne das beste Jahr (2008).

## Edge Card

EDGE CARD

Faber GTAA -- 10-Monats-SMA-Timing, 5 Anlageklassen, monatlich (Paper SSRN 962461)

Vollständige Ausgangsthese

01 IDEE

Risikoanlagen (Aktien, Auslandsaktien, Rohstoffe, REITs) erleiden selten,
aber dann tiefe und lange Drawdowns (50-80 %). Faber beobachtet, dass
diese Phasen nicht schlagartig an einem Tag passieren, sondern sich über
mehrere Monate hinziehen. In dieser Zeit liegt der Preis unter seinem
langfristigen Durchschnitt. Laut Paper ist in diesem Zustand (unter dem
10-Monats-Durchschnitt) die Volatilität im Folgezeitraum höher und die
Rendite niedriger als über dem Durchschnitt. Die Rendite liegt dort im
Schnitt 60 % niedriger, die Vola 30 % höher. Bei Rohstoffen ist nur die
Rendite niedriger, nicht die Vola. Wer in diesem Zustand in T-Bills
wechselt, verpasst wenig Rendite, schneidet aber den linken Rand der
Verteilung ab.

Was weiterhin passieren darf, ohne die Idee zu invalidieren:
- Schnelle Einbrüche innerhalb eines Monats. Sie werden bewusst ignoriert.
- Underperformance in starken Bullenmärkten (z.B. 1990er).
- Underperformance in etwa der Hälfte aller Jahre.
- Whipsaws in Seitwärtsmärkten.
- Kein Nutzen beim Timing von Staatsanleihen. Das sagt das Paper im FAQ
  selbst.

Was NICHT passieren darf: dass Monate unter dem Durchschnitt im Mittel
genauso viel Rendite liefern wie Monate darüber. Dann wäre der Filter
nur eine teure Art, weniger investiert zu sein. Ebenso wenig darf ein
beliebiges Rein/Raus mit gleicher Investitionsquote dasselbe leisten.

Ebene: ausschließlich Monatsschlüsse von Total-Return-Reihen. Keine Tages-
oder Intraday-Ebene. Das Paper nennt Tages-/Wochendaten nur „ähnlich",
ohne Zahlen.

02 REGEL

1. Universum: fünf Anlageklassen als Total-Return-Reihen (inkl. Dividenden
   und Kupons), je 20 % Zielgewicht. Das Paper verwendet:
   - S&P 500 (US Large Cap)
   - MSCI EAFE (entwickelte Märkte ex USA/Kanada)
   - US-Staatsanleihen 10 Jahre
   - GSCI (Rohstoffe, long-only, ungehebelt)
   - NAREIT (US-REITs)

   Unser Nachbau: SPY, EFA, IEF, DBC, VNQ (ab 2006-02). Längere
   Fonds-Proxys: VFINX, VGTSX, VUSTX, PCRIX, FRESX (ab 2002-07).
2. Beobachtungszeitpunkt: nur der Schlusskurs am letzten Handelstag jedes
   Monats. Kursbewegungen während des Monats werden nicht betrachtet.
3. Indikator je Klasse: SMA10 = arithmetisches Mittel der letzten zehn
   Monatsschlüsse der Total-Return-Reihe, einschließlich des aktuellen
   Monatsschlusses.
4. Signal je Klasse, unabhängig von den anderen Klassen:
   - Monatsschluss > SMA10: Klasse für den Folgemonat halten bzw. kaufen.
   - Monatsschluss < SMA10: den 20-%-Anteil der Klasse in 90-Tage-T-Bills
     legen.

   Den Fall „genau gleich" lässt das Paper offen; wir werten ihn als Cash.
5. Ausführung: Laut Paper zum Schlusskurs desselben Tages. Real ist frühestens
   der nächste Handelstag erreichbar. Das ist eine Lag-Variante und wird
   getrennt geprüft.
6. Rebalancing: monatlich auf 20 % je Klasse (Paper-FAQ). Cash-Anteile
   werden nicht auf die investierten Klassen umverteilt (kein „All-in").
7. Kein Stop, kein Target, kein Short, kein Hebel. Ausstieg erfolgt
   ausschließlich über den Signalwechsel an einem Monatsende.
8. Keine weiteren No-Trade-Bedingungen.

Merksatz: Einmal im Monat, je Anlageklasse: über dem 10-Monats-Schnitt
halten, darunter T-Bills -- sonst nichts.

03 MECHANISMUS

Das Paper nennt zwei Ursachen, ohne sie zu trennen. Wir trennen sie, weil
sie unterschiedliche Vorhersagen machen:

(A) Trend-Persistenz (Rendite-Prognose):
1. Ein Abschwung beginnt (fundamentaler Schock, Bewertungskorrektur), und
   der Kurs fällt unter seinen langfristigen Durchschnitt.
2. Hypothese: Anleger passen ihre Positionen verzögert an. Sie halten
   Verlierer bis „break even" (Prospect Theory/Disposition-Effekt), ankern
   an alten Kursen und folgen der Herde mit Verspätung. Dadurch wird
   Information nicht sofort, sondern über Monate eingepreist.
3. Folge (Hypothese): Monatsrenditen sind positiv autokorreliert. Der
   Zustand „unter SMA10" sagt eine unterdurchschnittliche Rendite der
   Folgemonate voraus.
4. Der träge SMA-Filter erkennt den Zustand zu spät für den Anfang, aber
   früh genug für den Großteil einer mehrmonatigen Abwärtsphase.

(B) Volatilitäts-Clustering (Risiko-Prognose):
1. In fallenden Märkten steigt die Volatilität, etwa durch den
   Leverage-Effekt oder Zwangsverkäufe. Hohe Vola bleibt über Monate
   bestehen.
2. Der Zustand „unter SMA10" ist deshalb ein Indikator für ein
   Hochvola-Regime.
3. Den Hochvola-Regimen auszuweichen senkt Portfolio-Vola und Drawdown.
   Wegen des Volatilitätsabschlags (geometrisches < arithmetisches Mittel,
   „volatility gremlins") kann das die Compound-Rendite sogar bei gleicher
   Durchschnittsrendite heben.

Portfolio-Ebene: Die fünf Klassen sind schwach korreliert. Ihre
Abwärtsphasen fallen selten gleichzeitig. Das Portfolio bleibt deshalb im
Schnitt ~70 % investiert, und der Cash-Anteil steigt genau dann, wenn
mehrere Klassen gleichzeitig fallen (2008).

Vorhersage-Unterschied: Wenn nur (B) gilt, sinken Vola und Drawdown
deutlich, die Rendite liegt aber unter Buy & Hold (Kosten der Cash-Quote
in normalen Phasen). Wenn (A) gilt, kann die Rendite gleich oder höher
sein. Faber behauptet beides („no adverse impact on return").

Wichtig: Das ist eine Mechanismus-Hypothese. Wir behaupten noch nicht,
dass sie bewiesen ist.

04 GEGENPROBE

- Rendite-Asymmetrie fehlt: Liegt die Folgemonatsrendite unter SMA10 nicht
  niedriger als darüber, ist (A) für diese Klasse falsch. Der Nutzen wäre
  dann reine Risiko-Reduktion, und der Rendite-Anspruch des Papers fällt.
- Vola-Asymmetrie fehlt: Wirkt das Timing gerade bei Klassen ohne
  höhere Vola unter SMA10 (laut Paper: Rohstoffe, Bonds), ist (B) als
  Hauptursache falsch.
- Zufall mit gleicher Investitionsquote: Liefert ein zufälliges
  Rein/Raus mit ~70 % Investitionsquote dieselbe Sharpe und denselben
  MaxDD, trägt das Signal keine Information. Der Effekt wäre dann nur
  geringeres Exposure.
- Allgemeineres Trendsignal: Funktioniert 12-Monats-Absolute-Momentum
  genauso gut, ist der Effekt kein SMA-Effekt, sondern ein allgemeiner
  Trend-Effekt. Das schwächt nicht die Idee, wohl aber jede Behauptung,
  SMA10 sei besonders.
- Einzelereignis: Hängt der Vorteil an einem Jahr (2008), ist es kein
  wiederkehrender Mechanismus, sondern ein Einzelfall mit großer Wirkung.
- Parameter: Liefern SMA-Längen 3-12 stark unterschiedliche Ergebnisse,
  ist 10 ein Fit und kein Plateau.
- Post-Publikation: Verschwindet der Vorteil nach 2013 (Paper-Ende 2012),
  war er Data-Mining oder ist arbitragiert.
- Verzögerung: Zerstört ein Monat Ausführungsverzögerung den Vorteil
  vollständig, ist der Zustand nicht persistent genug für die behauptete
  „langsame" Ursache.

Kern: Eine gute Gegenprobe greift nicht nur die Performance an. Sie
greift die angenommene Ursache an.

05 TEST

Datenquelle:
- Monatsschlüsse adjustierter (Total-Return-)Kurse über yfinance.
- ETF-Universum: SPY/EFA/IEF/DBC/VNQ. Fonds-Proxy: VFINX/VGTSX/VUSTX/PCRIX/FRESX.
- Cash: ^IRX (13-Wochen-T-Bill) / 12.
- Unbekannt bzw. abweichend: GFD-Originaldaten (nicht teilbar); GSCI und
  NAREIT nur über Proxys. DBC ist anders gewichtet als der GSCI, VUSTX
  sind lange Treasuries statt 10-jährige.

Zeitraum:
- Pflichtfenster ist 2013-03 bis heute, also echtes OOS nach dem letzten
  Paper-Update.
- Zusätzlich 2006-2012 (vom Paper selbst als OOS markiert, enthält 2008)
  und die Gesamtreihe mit und ohne 2008.
- Vor Testbeginn fixiert: SMA10, 1/N, Monatsende, Cash = T-Bills.

Fallzahl:
- Statistische Einheit sind Monate (2013-03 bis 2026-10: 164), nicht
  Trades.
- Es gibt nur ~0,9 Signalwechsel je Klasse und Jahr. Eine Trade-Statistik
  ist damit zu dünn.
- Alle Monate gehen ein, keine Auswahl.

Vergleich (aus den Gegenproben):
- Buy & Hold 1/N.
- Zufalls-Timing mit 71 % Investitionsquote (200 Läufe).
- 12M-Absolute-Momentum statt SMA.
- SMA 3/6/8/9/11/12.
- Ein Monat Lag.
- Kosten 10/25/50 bps je Wechsel.
- Ohne 2008.
- Rendite und Vola je Klasse ober- und unterhalb SMA10 im Folgemonat
  (Fig.-18-Nachbau).
- Block-Bootstrap (12-Monats-Blöcke) der Sharpe-Differenz zu Buy & Hold.

Heute noch nicht:
- Tages-/Wochen-Varianten.
- 13-Klassen-, Top-6- und Hebel-Erweiterungen.
- Steuern.
- Live-Ausführung.

Ergebnis: Eine vollständige, falsifizierbare und testbare Ausgangsthese.

## Phase 4 + Phase 6 (Basis) -- Befund gegen die Edge Card

Monatsdaten bis 02.10.2026 (der Oktober 2026 ist ein Teilmonat). Kein
Kostenabzug, sofern nicht anders angegeben.

**ETF-Universum (SPY/EFA/IEF/DBC/VNQ)**, im Schnitt 67,5 % investiert,
~4,6 Wechsel/Jahr portfolioweit:

| Fenster | | CAGR | Vola | Sharpe | MaxDD |
|---|---|---|---|---|---|
| 2006-12 bis 2026 | Timing | 5,41 % | 6,6 | 0,59 | −11,2 % |
| | B&H | 5,89 % | 12,2 | 0,41 | −43,5 % |
| 2006-2012 (Paper-OOS) | Timing | 4,18 % | 8,0 | 0,41 | −11,2 % |
| | B&H | 3,76 % | 16,0 | 0,24 | −43,5 % |
| **2013-03 bis heute (echtes OOS)** | **Timing** | **5,88 %** | **5,9** | **0,69** | **−5,5 %** |
| | B&H | 6,76 % | 10,1 | 0,52 | −17,7 % |
| ohne 2008 | Timing | 5,86 % | 6,5 | 0,66 | −11,2 % |
| | B&H | 7,96 % | 11,2 | 0,60 | −20,9 % |

**Fonds-Proxy (ab 2003)** zeigt dasselbe Bild:
- OOS: 5,60 % gegen 6,46 % CAGR, Sharpe 0,61 gegen 0,47, MaxDD −7,4 % gegen −20,8 %.
- Gesamt: 7,32 % gegen 7,79 % CAGR, MaxDD −7,5 % gegen −45,3 %.

Gegenproben (alle OOS 2013+, ETF; Fonds-Werte in Klammern):

1. **Post-Publikation: Der Risiko-Vorteil hält, der Rendite-Vorteil nicht.**
   - Die CAGR liegt ~0,9 Pp. UNTER Buy & Hold.
   - Vola und MaxDD sind ungefähr halbiert bzw. gedrittelt.
   - Timing liegt nur in 5 von 14 OOS-Jahren vorn: 2013, 2014, 2015, 2018
     und 2022. Das sind fast nur flache oder negative Jahre.
   - Fabers „no adverse impact on return" ist widerlegt, „bond-like
     drawdown" bestätigt.
2. **Zufall mit 71 % Investitionsquote**:
   - Median-Sharpe 0,50 (0,46), Median-MaxDD −14,7 % (−16,0 %).
   - Timing schlägt 95,5 % (92 %) der Zufallsläufe bei der Sharpe und
     100 % beim MaxDD.
   - Das Signal trägt also Information über reine Exposure-Reduktion
     hinaus, vor allem für den Drawdown.
3. **Block-Bootstrap der Sharpe-Differenz** (Timing − B&H):
   - Median +0,28 (+0,24), 5-%-Quantil +0,07 (+0,02).
   - Nur 1,1 % (4 %) der Ziehungen liegen ≤ 0.
   - Die Risiko-Verbesserung ist damit statistisch belastbar.
4. **12M-Absolute-Momentum**: Sharpe 0,54 (0,55), MaxDD −10,7 % (−8,4 %).
   Etwas schwächer als SMA10, aber gleiche Richtung. Es ist ein allgemeiner
   Trend-Effekt, nichts SMA-Spezifisches.
5. **Ohne 2008** schrumpft der Sharpe-Vorsprung über die Gesamtreihe von
   0,18 auf 0,06. 2008 trägt einen großen Teil des Paper-Effekts. Im OOS
   2013+ (ohne 2008) bleibt der Vorsprung trotzdem bei +0,17.
6. **Parameter-Plateau**:
   - SMA 8-12 liefert eine Sharpe von 0,63-0,69 bei einem MaxDD zwischen
     −5,5 und −8 %. Das ist ein Plateau.
   - SMA 3 und 6 sind schwächer (0,53-0,58, MaxDD −9 bis −13 %).
   - Fabers „3-12 alle ähnlich" gilt nur grob.
7. **Ein Monat Lag**: Sharpe 0,57 (0,59), MaxDD −13,7 % (−12,1 %). Das
   schwächt den Effekt deutlich, liegt aber noch über Buy & Hold. Der real
   relevante Lag ist ein Tag, das wurde nicht separat gerechnet
   (Tagesdaten wären nötig). Ein Monat ist eine grobe Obergrenze.
8. **Kosten**: Bei 50 bps je Wechsel kostet das ~1 Pp. CAGR. Realistische
   ETF-Spreads (1-5 bps) sind irrelevant. Steuern: nicht modelliert (Paper:
   ~70 % Turnover).

**Mechanismus-Check (Fig.-18-Nachbau, Folgemonat nach Zustand, OOS 2013+):**
- **Vola unter SMA höher**: SPY 22,8 gegen 11,9; EFA 18,8 gegen 12,2;
  VNQ 20,8 gegen 14,9; IEF 7,4 gegen 5,5; DBC nur 17,3 gegen 16,4. Damit
  ist (B) für Aktien und REITs bestätigt.
- **Rendite unter SMA niedriger**: nur bei DBC (−4,4 % gegen +12,2 % p.a.),
  EFA (5,3 gegen 9,4) und IEF (−0,1 gegen 1,9). **Bei SPY ist es
  umgekehrt (+37 % p.a. unter SMA, n=24 Monate, V-Erholungen 2018/2020/
  2022-23), ebenso bei VNQ (11,9 gegen 5,1).** (A) gilt also für
  Rohstoffe, nicht für US-Aktien.
- Für den S&P 500 ist der Filter seit 2013 also ein reiner Vola-Filter,
  der Rendite kostet. Der Return-Beitrag kommt fast nur aus der
  Rohstoff-Klasse.

**Gesamturteil:**
- Die Edge Card überlebt in der Form „(B) Risiko-Reduktion, (A) nur bei
  Rohstoffen". In der Original-Form „gleiche Rendite, halbes Risiko"
  überlebt sie nicht.
- Für einen Anleger, der Drawdown höher gewichtet als ~1 Pp. Rendite, ist
  das eine robuste, extrem einfache Regel.
- Für unsere Prop-Konten mit R-basiertem Sizing ist das nicht relevant:
  monatlich, long-only, ohne definiertes Risiko je Trade, ~1
  Wechsel/Klasse/Jahr.

## Paper-Verarbeitung Schritt 3 -- Cross-Check auf bestehende Beine

Frage: Trennt der Monats-SMA10-Zustand des Basiswerts (Vormonatsende) die
R-Ergebnisse unserer Beine? Datenbasis:
`portfolio_construction/results/fk_trades_2019_2026_live.csv`
(live-getreue Trades 2019-2026, R je Trade).

| Bein (Proxy) | unter SMA10: n / Ø R / t | über SMA10: n / Ø R / t |
|---|---|---|
| orb_sp500 (SPY) | 82 / +0,63 / 1,9 | 280 / +0,48 / 2,8 |
| orb_us30 (DIA) | 86 / **+0,67** / 2,6 | 306 / +0,10 / 0,8 |
| orb_nasdaq (QQQ) | 320 / **+0,35** / 2,3 | 1276 / +0,11 / 1,6 |
| gold_asb (GLD) | 26 / +0,47 / 1,5 | 109 / +0,44 / 2,6 |
| ctnl_reversal (GLD) | 40 / +1,06 / 2,2 | 126 / +1,05 / 3,9 |

**Ein Faber-Filter („nur über SMA10 handeln") würde nirgends helfen.** Bei
den Index-ORBs würde er sogar die besseren Trades abschneiden: Unter SMA10
liegt der Ø R je Trade 1,3-6,7x höher. Das passt zu Mechanismus (B): Ein
Hochvola-Regime liefert für eine Ausbruchsstrategie mit festem R größere
Intraday-Ranges, also mehr Bewegung relativ zum Stop. Gold ASB und CTNL
sind gegenüber dem Zustand neutral.

Explorativ, ohne Mehrfachtest-Korrektur. Kein Filter wird eingebaut.
Höchstens eine Notiz für eine spätere ORB-Regime-Analyse: Ein
Hochvola-Monat ist dort eher Rücken- als Gegenwind.

## Nicht gemacht (bewusst)

- **Phase 5** (Kalman/ADX/VWAP/Session-Filter): passt nicht zu einer
  monatlichen Allokationsregel.
- **p6_7/p6_8** (Sizing-Nenner, Stop gegen Kosten): kein Stop, kein
  R-Sizing, daher nicht anwendbar.
- **13-Klassen-, Top-6- und Hebel-Extensions des Papers**: nicht
  nachgebaut. Sie optimieren auf derselben Periode, und vorher müsste
  feststehen, ob GTAA überhaupt einen Einsatzzweck hier hat.

## Nachtrag 2026-10-04 -- S&P 500 TR, Tagesdaten, Nutzer-Spezifikation

Die Spezifikation hat der Nutzer festgelegt; sie ersetzt für diesen Test
meine Proxy-Annahmen von oben.
- **Daten:** ^SP500TR ab 1988, Tagesdaten, eingefroren in
  `scripts/frozen_data/sp500tr_daily_20261004.csv`.
- **Signal und Ausführung:**
  - Monatsschluss = letzter Handelstag; ein laufender Monat zählt nicht.
  - Bei Gleichstand bleibt der alte Zustand.
  - Die neue Position gilt ab dem Schluss des ersten Handelstags danach.
- **Renditen und Kosten:**
  - Cash bringt 0 %.
  - Spread 0,05 % je Ein- und Ausstieg.
  - Swap mittel 2,5 % p.a., hoch 5 % p.a. je Kalendertag investiert.
  - Max Drawdown vor Kosten.
- **Split:** vor und ab 01.06.2006.
- **Zufallstest:** 2000 Läufe, Seed 42, Monats-Positionen gemischt.

Skript `scripts/research_faber_sp500tr.py`, Rohzahlen
`Claude outputs/faber_sp500tr.json`.

Die Bewertung endet am letzten abgeschlossenen Monatsschluss, dem
30.09.2026. Die Tage 01.-02.10. sind nicht enthalten.

Tagesrenditen über ±10 %: 13.10.2008 (+11,58 %), 28.10.2008 (+10,79 %),
16.03.2020 (−11,98 %). Alle drei sind echte, bekannte Indextage und bleiben
drin.

**SMA10:**

| Fenster | | CAGR ohne / mittel / hoch | MaxDD vor Kosten | im Markt | Einstiege |
|---|---|---|---|---|---|
| 1988-11 bis 2026-09 | Strategie | 9,31 / 7,10 / 5,00 % | −27,4 % | 79 % | 27 |
| | B&H | 11,39 % | −55,3 % | | |
| 1988-11 bis 2006-05 | Strategie | 10,58 / 8,39 / 6,30 % | −23,3 % | 78 % | 11 |
| | B&H | 11,46 % | −47,4 % | | |
| 2006-06 bis 2026-09 | Strategie | 8,15 / 5,93 / 3,83 % | −27,4 % | 80 % | 17 |
| | B&H | 11,26 % | −55,3 % | | |

**Varianten** (gesamt, CAGR ohne Kosten / MaxDD; Teil ab 2006-06 in
Klammern):
- SMA8: 9,59 % / −27,4 % (9,15 / −27,4)
- SMA9: 9,67 / −27,4 (8,76 / −27,4)
- SMA10: 9,31 / −27,4 (8,15 / −27,4)
- SMA11: 9,82 / −27,4 (8,15 / −27,4)
- SMA12: 10,20 / −21,0 (8,86 / −21,0)

**Zufall** (456 Monate, 78,9 % long): Keiner der 2000 Läufe erreicht
einen ebenso kleinen Max Drawdown (Anteil 0,0). Der Median liegt bei
−50,4 %, das 5-%- bis 95-%-Band bei −59,8 bis −40,7 %.

**Gegencheck letzter Monat:**
- Monat 2026-09, Monatsschluss 30.09.2026
- Schluss 17.160,41, Durchschnitt (10 M.) 16.148,79
- Signal **long**, gilt ab Schluss 01.10.2026

**Einordnung:**
- Der Drawdown halbiert sich in beiden Teilen. Das ist nicht durch die
  geringere Zeit im Markt erklärbar, denn kein Zufallslauf schafft es.
- Die Rendite liegt aber in jedem Teil und jeder Variante unter Buy & Hold,
  ab 2006 um ~3 Pp. Das liegt auch daran, dass Cash hier 0 % bringt.
- Mit Swap 2,5 % wächst der Abstand ab 2006 von 3,1 auf 5,3 Pp.
  (5,9 % gegen 11,3 %). Gehalten über einen CFD mit
  Finanzierungskosten ist die Regel deshalb deutlich unattraktiv. Das ist
  ein Argument für ein ETF-Depot statt CFD.
- Der größte Verlust der Strategie (SMA8-11) ist nicht 2008, sondern
  01/2022 bis 03/2023: Whipsaw mit Ein- und Ausstiegen 03/22, 04/22,
  05/22, 12/22, 01/23 und 02/23.
- SMA12 hätte diese Phase ruhiger überstanden (MaxDD −21,0 %, aus
  2010). Das ist aber ein Einzelfall-Unterschied und kein Grund, auf 12
  umzustellen.
