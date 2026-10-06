# Project: Faber GTAA -- 10-Monats-SMA-Timing (SSRN 962461)

**Status (2026-10-07): PAUSIERT -- Weiterarbeit vorerst verworfen (Nutzerentscheid).** Keine Live-Umsetzung. Alle Ergebnisse unten bleiben gültig. Bester Stand für einen späteren Neustart: EK, Cash only, SMA10, SL 20 %, 5 % Risiko je Position, ohne Öl, ~5,5 % p.a. bei −20 % MaxDD in beiden Zeitfenstern. Das Timing wirkt dabei als Versicherung, nicht als Renditetreiber. Offene, nicht getestete Idee: Rotation mit Deckel (siehe Ideen-Inbox).

**Ursprünglicher Status**: **Phase 1-4 + Basis-Phase-6 erledigt (2026-10-04). Befund: der
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

## Nachtrag 2026-10-05 -- Funded-/EK-Variante: SL, Positionsclose, Filter, Cross-Asset

**Auftrag (04.10.):** Die SMA-Regel mit SL und echtem Positionsclose für
**EK (Tickmill)** und **Funded TTP** handelbar machen, dazu Filter und
Modelle aus den 2013er-Befunden. Nutzerideen: SL aus dem maximalen
Rückgang innerhalb der durchschnittlichen Trade-Dauer, ausgewertet je
Jahr (A5), und ein Ersatz-Asset statt Cash (Gold/BTC, Variante D).

Plan: `~/.claude/plans/binary-enchanting-breeze.md`.

**Methodik:**
- Auswahl nur auf Daten bis 2012 (Portfolio-Fenster 2001-2012).
- Die Finalisten wurden geloggt, bevor 2013-01 bis 2026-09 einmal
  gerechnet wurde.
- Code: `faber_trend/` (`data`, `signals`, `engine`), Skript
  `scripts/research_faber_trend_funded.py` (`is` / `oos`).
- Tests: `tests/test_faber_trend_engine.py` (6 Tests). Abgedeckt sind:
  SL intraday, Gap zum Open, Monats-Close, Mindestlot, Wochenend-Swap,
  Instrumentwechsel.
- Rohzahlen: `Claude outputs/faber_trend_funded_is.json` und `_oos.json`.
- Regressionstest gegen den ^SP500TR-Lauf: exakt (9,31 % / −27,43 % /
  27 Einstiege).

**Engine-Regeln:**
- Ausführung zum Schluss des 1. Handelstags nach dem Monatsschluss; Exit
  bei Signal Cash ist ein echter Positionsclose.
- SL broker-seitig auf Tages-High/Low; Gap durch den SL → Fill zum Open.
- Nach SL: Re-Entry erst mit dem nächsten Monatssignal.
- Sizing = Risiko / SL-Abstand, auf 0,01 Lot abgerundet. Liegt das
  Ergebnis unter dem Mindestlot, wird **kein** Trade genommen (gezählt).
- **Monatliches Rebalancing aufs Risikobudget** (Faber-FAQ). Ohne
  Rebalancing wuchs das offene Risiko alter Gewinner (Kupfer 2003-06,
  5-facher Kurs) auf −6 %-Tage. Das bricht das TTP-Tageslimit.
- Spread 0,05 % je Ein-/Ausstieg, Swap 0 / 2,5 / 5 % p.a.
  (Ersatzwerte, bis die echten MT5-Swaps vorliegen).

**Daten:**
- Eingefroren in `scripts/frozen_data/*_ohlc_daily_20261004.csv`.
- SP500: ^SP500TR-Schluss + ^GSPC-Range.
- NASDAQ/US30: Preisindizes ohne Dividenden.
- DAX: Performance-Index.
- Rohstoffe/Bonds: yfinance-Frontmonat ab 2000, mit Roll-Sprüngen.
- FX ab 1996/2003; BTC ab 2014.

Von Hand geprüft:
- EURUSD/USDJPY 08.12.2008 waren Phantom-Balken. Sie werden im
  Funded-Lauf durch den Vortagsschluss ersetzt (Liste `REPAIR` im
  Skript).
- T-Bond 23.03.2015: Roll-Sprung, belassen.
- Öl 2020: Roll-/Negativpreis-Monat, unzuverlässig.

### Ergebnisse auf den Daten bis 2012 (Auswahl)

**Machbarkeit EK** (~3.300 $, Mindestlot 0,01; Kontraktgrößen sind
Tickmill-Standard-Annahmen): Bei 1 % Risiko und 10 % SL passen nur
SP500 (Mindestlot-Nominal 77 $), DAX (252 $) und NASDAQ (308 $). US30
(512 $) passt erst ab 2 %. Gold (4.162 $), Silber, Öl, Kupfer, Bonds und
FX (~900-4.200 $) gehen auf EK nicht.

**Mechanismus je Instrument bis 2012 (C4):**
- Aktienindizes zeigen dort Rendite- und Vola-Asymmetrie, anders als
  nach 2013.
- Gold und Silber zeigen keine Rendite-Asymmetrie.
- Bonds zeigen nichts.
- Aufgenommen: SP500, NASDAQ, US30, DAX, GOLD, OIL, COPPER, EURUSD,
  USDJPY.

**SL-Wahl (Stufe 1)**, Median Rendite/MaxDD über 12 Instrumente, TTP,
0,5 % Risiko:
- Sieger: **A5 MAE-SL, 90-%-Quantil in ATR (0,073)**. Knapp dahinter
  A5 95 % (0,071), A0 ohne SL (0,067) und ATR6 (0,066).
- Alle engeren Stopps waren schlechter: 5 % (0,038), ATR2 (0,039),
  Trailing2 (0,018). Der SL taugt hier nur als Katastrophen-Stopp.
- Die A5-Abstände liegen bei Indizes bei 13-24 ATR bzw. 16-30 %, bei
  Gold bei 10 %.

**Bausteine (Portfolio 2001-2012, gegen Basis Ratio 0,40):**

| Baustein | Ratio | Urteil |
|---|---|---|
| C1 Ensemble SMA 8-12 | 0,475 | hilft |
| C3 Vola-Filter (halbes Risiko bei hoher Vola) | 0,409 | hilft knapp |
| D Gold statt Cash | 0,449 | hilft |
| C2 + 12M-Momentum | 0,336 | schadet |
| C5 Shorts | 0,285 | schadet |
| D Bonds statt Cash | 0,060 | schadet stark |
| B2 Deckel aufs offene Risiko | 0,308 | schadet |
| B3 Vol-Targeting | 0,403 | neutral |
| ohne Rebalancing | 0,254 | schadet (−7,7 % MaxDD) |
| Kontrolle immer long | 0,209 | -- |

**Finalisten** (Kombi = C1 + C3 + Gold statt Cash; MaxDD aus dem
Backtest, P aus Monte Carlo 2.000 Pfade):

| Finalist | CAGR | MaxDD | P(7 % trailing) |
|---|---|---|---|
| kombi_r0.5 | 1,77 % | −3,2 % | 0,05 % |
| kombi_r0.25 | 0,76 % | −1,6 % | 0 |
| kombi_alle_r0.5 | 1,97 % | −4,4 % | 0,25 % |

kombi_r1 (3,8 %, −6,8 %) fiel mit P(7 % trailing) = 10,1 % knapp
heraus.

### Ergebnisse 2013-01 bis 2026-09 (einmal, unverändert)

| Finalist | CAGR ohne / mittel / hoch | MaxDD (mittel) | Kontrolle immer long | Lag +1 Tag |
|---|---|---|---|---|
| **kombi_r0.5** | 1,08 / **0,50** / −0,04 % | −6,0 % | 0,17 % / −8,9 % | 0,59 % / −6,2 % |
| kombi_r0.25 | 0,50 / 0,29 / 0,12 % | −2,0 % | 0,06 % / −4,4 % | 0,25 % / −2,1 % |
| kombi_alle_r0.5 | 1,10 / 0,08 / −0,57 % | −6,9 % | −0,61 % / −13,0 % | 0,13 % / −8,3 % |

- **Kein TTP-Regelbruch:** P(7 % trailing) 0-0,2 %, schlechtester Tag
  −1,1 %. Wirtschaftlich ist das aber zu wenig: Die Ratio fällt von
  0,545 auf 0,083. Die Jahre schwanken zwischen −2,7 % und +4,9 %, das
  10-%-Ziel von TTP ist damit außer Reichweite.
- **Swap halbiert die Rendite** (1,08 → 0,50 %). Die echten Swap-Sätze
  entscheiden, ob überhaupt etwas übrig bleibt.
- **Signal gegen Kontrolle:** Das Trendsignal schlägt „immer long" mit
  denselben Stopps (Ratio 0,083 gegen 0,019) und 91 % der Zufallsläufe
  bei der Ratio (100 Läufe, Seed 42, nur Hauptfinalist). Beim MaxDD liegt
  es aber nicht vorne: 83 % der Zufallsläufe haben einen gleich kleinen
  oder kleineren.
- **EK: 0 Trades.** Alle 6.238 Einstiege liegen unter dem Mindestlot,
  weil die Ensemble-Teile mit 0,1 % von 3.300 $ und weiten MAE-Stopps
  zu klein sind. Selbst ein einzelnes SP500-Bein mit 1 % Risiko und
  ~15 % SL hätte nur ~220 $ Nominal, gerade über dem Mindestlot von 77 $.
- **Korrelation zu den bestehenden Beinen (täglich): 0,06-0,08.**
  Diversifizierend, aber zu klein, um etwas zu bewegen.

**A5 „hält er?"** SL-Quote je Jahr gegen die erwarteten 10 %
(kombi_r0.5):
- Erfüllt in 12 von 14 Jahren (0-11,6 %).
- **Ausnahme 2018 mit 27 %** (Februar-Vola-Schock und Q4-Abverkauf).
  2020 lag mit 10,8 % im Rahmen.
- Der MAE-SL ist damit über die Jahre stabil, versagt aber im
  Vola-Schock-Jahr.

**D mit BTC (nur Testfenster, keine saubere Auswahl möglich, BTC-SL =
Median-Faktor der anderen):**
- BTC statt Cash: 1,67 % p.a., MaxDD −4,75 %, Ratio 0,35. Das ist der
  beste Wert im Testfenster.
- Gold+BTC: 0,79 %, −6,6 %.
- Das ist Rückschau auf den BTC-Bullenmarkt 2014-2026 und kein Beleg.

### Urteil

- **Funded TTP:** regelkonform, aber nicht lohnend. Bei 0,5 % Risiko
  bleiben 0,5 % p.a. nach mittleren Kosten. Höheres Risiko (1 %) bricht
  schon im Lernfenster die 7-%-Schwelle mit ~10 %/Jahr. Die Strategie ist
  ein Risiko-Reduzierer und passt nicht zu einem Konto, das +10 %
  verdienen muss.
- **EK:** in dieser Form nicht handelbar (Mindestlot). Denkbar wäre
  höchstens ein einzelnes SP500-Bein, das aber ohne die Filter, die den
  Effekt tragen.
- **Was trägt:**
  - Monatliches Rebalancing ist Pflicht.
  - Der SL ist nur ein Katastrophen-SL (A5).
  - Ensemble 8-12, Vola-Filter und Gold statt Cash.
- **Was nicht trägt:** Shorts, Bonds statt Cash, enge oder trailing SLs,
  ein Deckel aufs offene Risiko.
- **Offene Hebel:** echte Swap-Werte (größter Einzeleffekt), echte
  Kontraktgrößen. Live erst nach Freigabe (Phase 8).

**Transparenz -- Engine-Fehler nach dem ersten Testfenster-Lauf
behoben:**
- Bei einem Wechsel in ein Instrument mit früherem Ausführungstag (BTC am
  Wochenende, Feiertage) wurde die alte Position zum Kurs des neuen
  Instruments geschlossen.
- Nach der Korrektur (Test ergänzt) wurden beide Phasen mit unveränderten
  Regeln neu gerechnet. Die Finalisten-Zahlen änderten sich nur in der
  Rundung, BTC von unmöglich (−100 %) auf plausibel.
- Die alten Dateien liegen als `*_vor_switchfix.json` vor.

### Edge Card -- Nachtrag „Funded-Variante"

02 REGEL (Ergänzung):
9. Je Instrument werden fünf Teilpositionen geführt (SMA 8/9/10/11/12),
   je 1/5 des Positionsrisikos.
10. Ist die 20-Tage-Vola über ihrem expandierenden Median, gilt beim
    Einstieg bzw. Rebalancing halbes Risiko.
11. SL = 90-%-Quantil des größten Rückgangs innerhalb der
    durchschnittlichen Haltedauer (in ATR20 beim Einstieg, je
    Instrument aus Daten bis 2012). Broker-seitig, Gap → Open.
12. Monatliches Rebalancing auf das Risikobudget (Stückzahl + SL neu).
13. Cash-Monate gehen in Gold, wenn Gold selbst über seinem SMA10 liegt.
14. Position < Mindestlot → kein Trade.

04 GEGENPROBE (neu):
- Hält der MAE-SL die erwartete Quote je Jahr? Befund: ja, außer 2018.
- Schlägt das Signal „immer long" mit denselben Stopps? Befund: ja.
- Schlägt es Zufall bei gleicher Zeit im Markt? Befund: bei der Ratio
  ja (91 %), beim MaxDD nein.
- Überlebt die Rendite den Swap? Befund: nur knapp bei 2,5 %, nicht
  bei 5 %.

## Nachtrag 2026-10-05 (2) -- Nachrechnung mit echten MT5-Werten

**Woher die Werte kommen:** am 05.10. nur lesend aus den bereits
laufenden Terminals (TTP 504072729, Tickmill-EK 55918977) gelesen, mit
`scripts/read_faber_symbol_specs.py`. Kein Login und kein neues
Terminal; ein Konto wird übersprungen, wenn sein Terminal nicht läuft.
Eingefroren als `scripts/frozen_data/faber_symbol_specs_20261005.json`.

Gelesen wurden:
- Swap je Instrument und Richtung,
- Spread,
- Kontraktgröße, Mindestlot, Lot-Schritt,
- Kontostand: TTP **99.134 $** (nicht 200k), EK **2.817 €** (≈ 3.156 $).

Finalisten und Regeln sind unverändert; es gibt keine neue Auswahl.
Skript `scripts/research_faber_trend_realkosten.py`, Rohzahlen
`Claude outputs/faber_trend_realkosten.json`.

**Echte Swap-Kosten long p.a.:**

| | TTP | Tickmill (EK) |
|---|---|---|
| US500 | 4,8 % | 6,4 % |
| USTEC | 6,8 % | 6,4 % |
| US30 | 8,1 % | 6,4 % |
| DE40 | 6,4 % | 4,6 % |
| XAUUSD | 7,7 % | 5,1 % |
| XAGUSD | 11,1 % | 6,4 % |
| Kupfer | 9,7 % | 9,2 % |
| Öl (XTIUSD) | Gutschrift 20,5 % | Gutschrift 8,7 % |
| EURUSD | 4,1 % | 1,9 % |
| USDJPY | Gutschrift 1,4 % | Gutschrift 1,6 % |
| BTCUSD | **29 %** | 0 |

**Weitere Befunde aus den Spezifikationen:**
- Die Spreads liegen bei 0,001-0,03 % je Seite und spielen keine Rolle.
- Bonds gibt es bei keinem der beiden Broker.
- Öl und Kupfer haben ein Mindestlot von 1,0; bei Kupfer sind das
  ~6.500 $ Nominal. DE40 hat bei TTP einen Lot-Schritt von 0,1.
- Öl short zeigt bei TTP rechnerisch 88 % p.a. Kosten. Der Wert wurde
  bei geschlossenem Markt gelesen (Bid 0) und ist möglicherweise veraltet.
  Für den Finalisten ist das irrelevant, weil er keine Shorts hat.

**Zwei Swap-Modelle:**
- „heute": die heutigen Sätze über den ganzen Zeitraum (Stress).
- „zinsangepasst": Für in USD finanzierte Instrumente gilt der heutige
  Satz minus (IRX heute − IRX damals). FX und BTC bleiben unverändert.
- ^IRX ist eingefroren als `irx_daily_20261005.csv`.

**Ergebnis Hauptfinalist (kombi_r0.5):**

| Konto / Modell | 2001-2012 CAGR / MaxDD | 2013-2026 CAGR / MaxDD | P(7 % trailing) |
|---|---|---|---|
| TTP heute | 1,24 % / −3,4 % | **0,45 % / −4,1 %** | 0 |
| TTP zinsangepasst | 1,50 % / −3,3 % | **0,59 % / −4,2 %** | 0 |
| TTP Kontrolle immer long | -- | 0,20 % / −7,7 % | -- |
| EK (beide Modelle) | 19 Trades, −0,02 % | **0 Trades** | -- |

- Die anderen Finalisten liegen im Testfenster bei 0,06-0,52 % p.a.
- Gegenüber der Rechnung mit Ersatzkosten ändert sich am Urteil nichts.
  Die echten Spreads sind kleiner, die echten Swaps bei Indizes und
  Metallen höher. Durch das kleinere TTP-Konto (99k statt 200k) fallen
  mehr Teilpositionen unter das Mindestlot.
- **BTC statt Cash mit echtem TTP-Swap (29 %)**: 1,16 % / −4,2 %. Das
  bleibt der beste Wert, ist aber weiter nur Rückschau. Auf EK (Swap 0):
  0,35 % / −1,7 %, weil kaum etwas über das Mindestlot kommt.
- **EK explorativ** (nicht vorab ausgewählt, SMA10, A5-SL, nur
  Testfenster):

  | Variante | CAGR | MaxDD |
  |---|---|---|
  | SP500 + NASDAQ, 2 % Risiko | 1,30 % | −5,4 % |
  | SP500 + NASDAQ, 1 % Risiko | 0,40 % | −2,4 % |
  | 4 Indizes, 2 % Risiko | 1,74 % | **−11,7 %** |

  Auf 3.156 $ sind das ~40 $/Jahr.

**Urteil bestätigt:** Mit echten Kosten ist die Regel auf TTP
regelkonform, bringt aber ~0,5 % p.a. Auf EK ist sie nicht sinnvoll
handelbar. Keine Empfehlung für eine Live-Umsetzung.

## Nachtrag 2026-10-05 (3) -- Cash only + weiteste Stopps (Nutzerfrage, explorativ)

Nicht vorab ausgewählt, daher eine nachträgliche Erkundung und kein
sauberer Test. Hauptfinalist kombi_r0.5 (Ensemble 8-12, Vola-Filter,
0,5 % Risiko) mit echten MT5-Kosten (zinsangepasst). Skript
`scripts/research_faber_trend_cash_widestop.py`, Rohzahlen
`Claude outputs/faber_trend_cash_widestop.json`.

Median-Stoppweite der Instrumente des Finalisten:

| Stopp | Median-Weite |
|---|---|
| A5 %-Quantil 95 | **23 %** (weitester getesteter) |
| fester SL | 20 % |
| ohne SL (fiktiv fürs Sizing) | 20 % |
| A5 ATR-Quantil 95 | 16,8 % |
| A5 ATR-Quantil 90 (gewählt) | 12,6 % |

TTP 2013-2026 (2001-2012 in Klammern), CAGR / MaxDD:

| Stopp | Gold statt Cash | Cash only |
|---|---|---|
| A5 ATR q90 (gewählt) | 0,59 % / −4,2 % (1,50 / −3,3) | 0,47 % / −3,6 % (0,85 / −1,8) |
| **A5 % q95, weitester** | 0,25 % / −1,8 % | **0,25 % / −1,8 %** (0,61 / −1,3) |
| A5 ATR q95 | 0,39 % / −2,9 % | 0,32 % / −2,5 % (0,69 / −1,5) |
| fester 20 % | 0,56 % / −1,8 % | **0,56 % / −1,8 %** (0,54 / −1,7) |
| ohne SL | 0,56 % / −1,75 % | 0,56 % / −1,75 % (0,57 / −1,5) |

Was die Zahlen zeigen:
- **Der Gold-Switch wirkt bei weiten Stopps nicht mehr.** Ein
  Gold-Teilstück (0,1 % Risiko / 20-23 % SL ≈ 500 $ Nominal) liegt
  unter dem Mindestlot (0,01 Lot ≈ 4.160 $) und wird nie gehandelt.
  Deshalb sind die Gold- und Cash-Spalten dort identisch.
- **Cash only + 20 % SL** bringt im Testfenster dieselbe Rendite wie der
  gewählte Finalist (0,56 % gegen 0,59 %), bei weniger als halbem MaxDD
  (−1,8 % gegen −4,2 %). Bis 2012 war sie schlechter (Ratio 0,33 gegen
  0,47) und wurde deshalb nicht gewählt. Das ist ein Hinweis, dass der
  Gold-Switch eher Glück im Lernfenster war (Gold-Hausse 2001-2011).
- **Der weiteste A5-Stopp (q95, 23 %)** halbiert die Rendite (0,25 %).
  Je weiter der SL, desto mehr Ensemble-Teile fallen unter das
  Mindestlot.
- **EK:** in allen Varianten 0 Trades.

Am Urteil ändert sich nichts: Auch die beste Variante bringt ~0,5 % p.a.
auf TTP.

## Nachtrag 2026-10-06 -- Ganzes Edge auf EK mit 5-10 % Risiko je Position (Nutzerfrage, explorativ)

Nicht vorab ausgewählt, daher eine Erkundung. EK-Konto 2.817 € (als
3.156 $ gerechnet, EUR/USD-Effekt ignoriert), echte Tickmill-Kosten,
Kontrakte und Mindestlots. Skript
`scripts/research_faber_trend_ek_hochrisiko.py`, Rohzahlen
`Claude outputs/faber_trend_ek_hochrisiko.json`. Neu in der Engine: der
Bruttohebel (Nominal/Equity) je Tag.

CAGR / MaxDD, Swap zinsangepasst (in Klammern: heutige Swaps,
2013-2026):

| Variante | Risiko | 2001-2012 | 2013-2026 | P(−45 %)/Jahr | Hebel Median/Max |
|---|---|---|---|---|---|
| **Cash only, SMA10, SL 20 %, 9 Instr.** | 5 % | 9,1 % / −25,9 % | **7,8 % / −27,1 %** (5,3 / −28,3) | 0 | 1,2 / 1,9 |
| | 7,5 % | 14,4 % / −40,8 % | **12,5 % / −38,0 %** (8,8 / −37,0) | 0,2 % | 2,0 / 3,2 |
| | 10 % | 18,4 % / −55,0 % | **15,9 % / −52,1 %** (12,1 / −52,3) | 2,3 % | 2,8 / 4,7 |
| nur 4 Indizes, Cash, SL 20 % | 5 % | 2,8 % / −18,5 % | 5,1 % / −21,6 % | 0 | 0,9 / 1,0 |
| | 10 % | 4,7 % / −36,0 % | 10,0 % / −39,9 % | 0,5 % | 1,9 / 2,3 |
| Finalist (Ensemble + Vola + Gold, A5 q90) | 5 % | 7,5 % / −22,2 % | 2,6 % / −34,1 % (0,2 / −27,6) | 0 | 0,6 / 3,1 |
| | 10 % | 31,5 % / −48,2 % | 7,5 % / **−62,7 %** (−0,3 / −67,2) | 6,9 % | 2,8 / 11,8 |
| Ensemble + Vola, Cash | 10 % | 16,9 % / −31,8 % | 4,6 % / **−66,1 %** | 3,8 % | 2,4 / 8,5 |

Was die Zahlen zeigen:
- **Bei hohem Risiko kehrt sich die Rangfolge um.** Die einfache
  Variante (Cash only, SMA10, 20 % SL) ist in beiden Zeitfenstern
  ähnlich: 9,1 → 7,8 % bei 5 %. Der „optimierte" Finalist bricht im
  Testfenster ein (MaxDD −34 bis −63 %).
- Der enge A5-SL (q90) mit Ensemble-Teilen erzeugt bei großem Risiko
  viele Ausstopper und hohe Spitzenhebel (bis 11,8x).
- **Hebel:** Die einfache Variante bleibt bei max. 1,9x (5 %) bis 4,7x
  (10 %), also klar unter den EU-Retail-Grenzen (Indizes 20:1, Gold
  20:1, Rohstoffe 10:1). Der Finalist erreicht bei 10 % bis 11,8x und
  verletzt damit die Rohstoff-Grenze potenziell.
- **Einordnung:** 5 % Risiko bei 20 % SL heißt 25 % Nominal je
  Position. Das ist im Kern ein ~1,2-fach gehebeltes, trendgefiltertes
  Multi-Asset-Portfolio. Ein großer Teil der Rendite ist Marktrendite
  (Beta), kein reiner Timing-Edge. Eine Kontrolle „immer long mit
  gleichem Hebel" fehlt in diesem Lauf noch.
- **Kosten:** Die heutigen Swaps kosten die einfache Variante bei 5 %
  ~2,5 Pp. p.a. (7,8 → 5,3 %).
- **Kill-Switch EK (−45 % trailing):** Die Auslösewahrscheinlichkeit
  liegt bei 5 % bei 0 und bei 10 % bei ~2 %/Jahr. −20 % erreicht man bei
  7,5 % Risiko in ~24 % der Jahre.
- **Gold statt Cash** ist auf EK auch bei 5 % praktisch wirkungslos
  (Mindestlot). Die Finalist- und Cash-Zeilen sind dort identisch.

**Kontrolle „immer long, gleicher SL und gleiches Risiko"** (EK, Cash
only, SL 20 %, Swap zinsangepasst; Skript
`scripts/research_faber_trend_ek_kontrolle.py`, Rohzahlen
`faber_trend_ek_kontrolle_immer_long*.json`):
- Mit Öl hat „immer long" im Testfenster schlechteste Tage von −39 bis
  −71 %. Das ist der Negativpreis-Monat April 2020 der
  Öl-Futures-Reihe, ein Daten-Artefakt. Deshalb ist die Kontrolle auch
  **ohne Öl** gerechnet.
- **Ohne Öl** sinkt auch die SMA-Variante deutlich. Öl hat einen großen
  Teil beigetragen (Futures-Roll in der Reihe plus Swap-Gutschrift long)
  und ist nicht verlässlich.

| ohne Öl, CAGR / MaxDD | Risiko | 2001-2012 | 2013-2026 |
|---|---|---|---|
| SMA10-Timing | 5 % | 5,6 % / −19,3 % | 5,5 % / −21,6 % |
| immer long | 5 % | −0,9 % / −58,9 % | 11,0 % / −27,1 % |
| SMA10-Timing | 7,5 % | 8,0 % / −29,5 % | 9,9 % / −30,5 % |
| immer long | 7,5 % | −2,5 % / −76,2 % | 14,6 % / −47,6 % |
| SMA10-Timing | 10 % | 11,0 % / −44,2 % | 10,7 % / −45,1 % |
| immer long | 10 % | −6,1 % / −88,7 % | 18,9 % / −59,5 % |

- **Das Timing ist eine Versicherung, kein Renditetreiber.** 2001-2012
  (zwei Bärenmärkte) rettet es das Konto: +5,6 % statt −0,9 % und
  −19 % statt −59 %. Im Bullenmarkt 2013-2026 kostet es die Hälfte der
  Rendite (5,5 % statt 11,0 %), bei ähnlichem Drawdown bei 5 % Risiko.
- **Ehrliche EK-Zahl (ohne Öl, 5 % Risiko):** ~5,5 % p.a. bei
  −20 bis −22 % MaxDD, über beide Zeitfenster stabil. Mit Öl sind es
  7,8-9,1 %; das ist optimistisch.

## Nachtrag 2026-10-06 (2) -- Rotation in Öl statt Cash auf EK (Nutzerfrage, explorativ)

Einfache Variante: SMA10, SL 20 %, 8 Instrumente; Öl nur als
Rotationsziel. Cash-Monate gehen in OIL, wenn OIL über seinem SMA10
liegt. Gold-Rotation zum Vergleich. Swap zinsangepasst (Tickmill: Öl
long ist eine Gutschrift). Skript
`scripts/research_faber_trend_ek_oelrotation.py`, Rohzahlen
`faber_trend_ek_oelrotation.json`.

CAGR / MaxDD:

| Variante | Risiko | 2001-2012 | 2013-2026 | 2013-26 ohne 2020 | schlechtester Tag (OOS) |
|---|---|---|---|---|---|
| Cash | 5 % | 5,6 % / −19 % | **5,5 % / −22 %** | 5,3 % / −22 % | −4,3 % |
| **Öl-Rotation** | 5 % | 16,3 % / −53 % | **4,4 % / −56 %** | 4,4 % / −56 % | **−19,7 %** |
| Gold-Rotation | 5 % | 7,6 % / −34 % | 5,5 % / −22 % (= Cash) | -- | −4,3 % |
| Cash | 10 % | 11,0 % / −44 % | 10,7 % / −45 % | 9,9 % / −42 % | −11,8 % |
| **Öl-Rotation** | 10 % | 23,5 % / −84 % | **5,0 % / −83 %** | 4,8 % / −83 % | **−34,6 %** |
| Gold-Rotation | 10 % | 13,9 % / −74 % | 14,0 % / −41 % | 10,8 % / −38 % | −11,0 % |

- **Öl-Rotation schadet.** Bis 2012 ergibt sie mehr Rendite, aber mit
  −53 % MaxDD schon bei 5 %. Ab 2013 verliert der Öl-Anteil Geld:
  −117 % des Gesamt-P&L, d.h. Öl-Trades verlieren mehr, als die
  restlichen Trades verdienen. Der MaxDD liegt bei −56 bis −83 %.
- Ohne 2020 bleibt das Bild gleich. Es ist also kein Artefakt des
  Negativpreis-Monats, sondern strukturell (Öl-Trendbrüche 2014/15,
  2018, 2022).
- **Ursache Konzentration:** Mehrere Instrumente können gleichzeitig auf
  Cash springen. Dann rotieren alle ihre Slots gleichzeitig in dasselbe
  Öl: bei 8 Instrumenten bis 8 × 5 % = 40 % Risiko in einem Markt.
  Daraus kommen die Tage mit −20 bis −35 %.
- **Gold-Rotation:** Bei 5 % Risiko ist sie identisch mit Cash (Gold
  unter dem Mindestlot). Ab 7,5 % ist sie im Testfenster besser
  (11,7 % / −34 %), bis 2012 aber deutlich schlechter (−59 bis −74 %
  MaxDD). Auch sie leidet unter derselben Konzentration.
- Würde man Rotation weiterverfolgen, bräuchte es einen Deckel: Höchstens
  ein Slot (oder X % Risiko) darf in das Ersatz-Asset. Das ist nicht
  getestet.
