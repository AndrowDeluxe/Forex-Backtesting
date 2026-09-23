# Project: EU-Open-Renditefenster (05:30-09:30 Berlin) -- Edge-Kandidat

**Status**: **ABGESCHLOSSEN, NEGATIV (2026-09-23).** Der Edge existiert in
unseren Jahren nicht mehr -- ohne 2020 liegt er auf allen drei Instrumenten
unter den Handelskosten. Nicht bauen. Vollstaendiges Ergebnis mit Zahlen und
Gegenchecks ganz unten; der Abschnitt darueber ist die Screening-Begruendung
vom 2026-09-22 und bleibt als Protokoll stehen, warum es einen Versuch wert war.
Entstanden aus der Paper-Sichtung in
[[24h-renditestruktur-und-informationskette]] (Nutzerauftrag 2026-09-22:
"schaue ob wir ... einen separaten Edge kreieren können").

**Die These in einem Satz**: Die gesamte durchschnittliche Rendite des
S&P 500 entsteht in vier Nachtstunden (23:30-03:30 ET = **05:30-09:30
Berlin**); long im Index-CFD genau über dieses Fenster, flat den Rest des
Tages.

## Warum das ernst zu nehmen ist

Aus Bondarenko/Muravyev (SSRN 3596245), ES-Futures 2004-2018 + OOS 2020:

- **+7,60 % p.a., t=6,35, Sharpe 1,67**, SD nur 4,55 %, **MaxDD 8 %**
  (vs. 66,4 % für den Rest des Tages).
- **In jedem einzelnen der 15 Jahre positiv.** Schwächstes Jahr 2017
  (+2,25 %), stärkstes 2009 (+16,24 %). 2008 immer noch +9,80 %, während
  der Rest des Tages -55,82 % machte.
- **Skew positiv (+1,64)** -- untypisch und angenehm; der Tagesrest hat
  -0,99.
- **Data-Snooping sauber ausgeschlossen**: White-(2000)-Reality-Check
  (99 %-Perzentil der Max-t-Verteilung über alle 4h-Fenster = 3,7; hier
  6,35) und Bonferroni über alle 4h-Fenster (p=5x10^-8).
- **Kausale Identifikation über Sommerzeit**: Asien kennt keine DST. Das
  Muster bleibt in europäischer Zeit stehen und wandert in asiatischer --
  also Europas Open, nicht Asiens Close. Das ist mehr als eine Korrelation.
- **Mechanismus vorhanden und separat belegt**: Unsicherheit akkumuliert
  nachts ohne kritische Investorenmasse und löst sich auf, wenn die
  Europäer kommen. Unabhängig bestätigt durch VIX-Futures (steigen davor
  +39,6 %, fallen darin -46,3 %, t=-5,2) und einen Varianz-Ratio-Test
  (Preise werden im Fenster 14 % effizienter).
- **Gilt auch für E-mini Nasdaq 100 und Dow** -- also für zwei unserer drei
  bestehenden Index-Beine.
- **Kollidiert zeitlich nicht mit dem ORB** (15:30-22:00 Berlin).

## Die Kostenfrage entscheidet alles -- und sie ist noch offen

Das Paper handelt **täglich zweimal** (rein/raus), also ~252 Round-Trips
pro Jahr. Damit ist es maximal kostenempfindlich:

| Version | Brutto p.a. | Nach Kosten | Sharpe nach Kosten |
|---|---|---|---|
| Naiv (jeden Tag) | 7,76 % | **2,58 %** | 0,55 |
| Konditional (~40 % der Tage) | 6,69 % | **4,61 %** (t=4,57) | **1,20** |

**Break-even gerechnet**: 7,76 % / 252 Round-Trips = **3,08 bps
Brutto-Edge je Round-Trip**. Darüber ist die naive Version tot.
Die konditionale Version hat mit ~101 Round-Trips und 6,69 % brutto
**~6,6 bps** Spielraum -- deutlich robuster.

**Unsere Lage dazu ist unbekannt, aber gut messbar:**
- Gemessene Tages-Spreads unserer Index-CFDs: SP500 0,84 / US30 0,48 /
  NASDAQ 0,54 bps (`scripts/measure_broker_spreads.py`) -- das wäre
  **deutlich unter** den 2,03 bps, die das Paper annimmt (CME-Tick +
  Gebühren).
- **ABER**: diese Zahlen stammen aus dem NY-Open-Fenster. 05:30-09:30
  Berlin ist für einen Index-CFD das dünne Fenster; Broker weiten dort
  typischerweise. **Ungemessen.**
- **Swap dürfte entfallen**, weil das Fenster keinen Broker-Rollover
  kreuzt (typisch ~23:00-00:00 Serverzeit) -- zu verifizieren, nicht
  angenommen.

Genau dieser Punkt hat schon zweimal ein Ergebnis gedreht, in beide
Richtungen: bei CLS war der Edge ein Artefakt fehlender Kosten
([[cls-practical-kostenvalidierung]]), bei CTNL waren die angesetzten
Kosten 4-11x **zu hoch** ([[ctnl-kostenvalidierung]]). Deshalb gilt hier
[[realkosten-und-ausfuehrungs-probe]] **vor** jedem Backtest, nicht danach.

## Ehrliche Vorbehalte

1. **Das Sample endet Juli 2018** (+ ein OOS-Jahr 2020). Bis heute sind
   **acht Jahre unbekannter Decay** vergangen -- und das Paper ist seit
   2020 öffentlich und unter Praktikern bekannt (die Autoren erwähnen das
   selbst). Ein Edge, der 100 % der Marktrendite erklärt und trivial
   umzusetzen ist, ist ein naheliegendes Arbitrage-Ziel.
   **Das ist der größte Einzelvorbehalt**, und er ist mit unseren eigenen
   Daten (Dukascopy, 2018-2026) direkt prüfbar. Das ist der eigentliche
   erste Test, nicht die Replikation der Paper-Jahre.
2. **Die konditionale Version braucht Delta-VIX** -- Dukascopys
   VIX-Historie beginnt erst **2022-10-04** (in Stage 4b des ORB bereits
   verifiziert). Der zweite Prädiktor (Overnight-Realized-Vol, 18:00-23:30 ET)
   ist dagegen aus unseren eigenen Index-Bars über die volle Historie
   berechenbar. Möglicher Ausweg: erst nur mit dem Vol-Prädiktor, VIX später.
3. **Futures vs. CFD**: das Paper misst ES-Futures. Unsere CFDs bilden den
   Index ab, aber Finanzierung, Spread-Verhalten und Nacht-Liquidität sind
   andere. Die 1,71 bps CME-Spread sind nicht unsere Realität -- in keine
   Richtung.
4. **Kollisionsprüfung offen**: CLS Practical hat einen **09:00-Checkpoint**
   (siehe Memory `cls_practical_strategy_state`), also am Rand dieses
   Fensters. Vor jedem Live-Gedanken prüfen, ob sich Beine überlappen oder
   dasselbe Risiko doppelt tragen.
5. **Die zweite Hälfte trägt fast alles**: 07:30-09:30 Berlin = 5,90 der
   7,60 Punkte; 05:30-07:30 nur 1,70. Ein kürzeres Fenster halbiert
   womöglich die Kosten bei kaum weniger Ertrag -- eigene Testdimension.

## Vorgeschlagene Reihenfolge (nichts davon begonnen)

| Schritt | Was | Warum zuerst |
|---|---|---|
| 0 | **Nacht-Spread im Fenster messen** (`measure_broker_spreads.py` auf 05:30-09:30) | billigster Killer-Test; > ~3 bps RT und die naive Version ist tot |
| 1 | **Fenster auf 2018-2026 nachrechnen** (Dukascopy, SP500/US30/NASDAQ) | prüft die 8-Jahre-Decay-Frage, der größte Vorbehalt |
| 2 | Fenster-Varianten (voll vs. 07:30-09:30) | Kosten halbieren bei kaum Ertragsverlust? |
| 3 | Konditional: Overnight-Vol als Prädiktor (ohne VIX) | hebt Kostenspielraum von 3,1 auf ~6,6 bps |
| 4 | **Phase 6**: Walk-Forward + Monte-Carlo (Block über Kalendermonate) | Repo-Standard vor jeder Risiko-/Portfolio-Arbeit |

**Abbruchkriterium schon jetzt festhalten**: Wenn Schritt 1 für 2018-2026
keinen klar positiven Erwartungswert zeigt, ist das Thema erledigt --
unabhängig davon, wie gut die Paper-Jahre aussehen.

## Verweise

- [[24h-renditestruktur-und-informationskette]] -- Destillat der drei Papers
- [[ny-open-orb-sp500]] -- bestehendes Index-Bein, anderes Tagesfenster
- [[realkosten-und-ausfuehrungs-probe]] -- der Prozess für Schritt 0
- [[backtest-standard-process]] -- 8-Phasen-Prozess, Phase 6 vor Risiko-Arbeit

---

# ERGEBNIS 2026-09-23: Der Edge existiert in unseren Jahren nicht mehr

**Status: abgeschlossen, negativ. Nicht bauen.** Das vorab festgelegte
Abbruchkriterium ist erfuellt. Kein Bein, kein Bot, keine Weiterarbeit --
ausser dem, was unten unter "Was wir behalten" steht.

Skripte: `scripts/research_eu_open_window.py`,
`scripts/research_eu_open_decay.py`, `scripts/research_eu_open_windowscan.py`.
Daten: `knowledge/_data/eu_open_window.json`, `_decay.json`, `_windowscan.json`,
`broker_spreads_indices_euopen.json`. Alles rein lesend.

## Schritt 0 -- Kosten: bestanden, und zwar deutlich

Gemessen mit `measure_broker_spreads.py --window 5.5-9.5 --days 30` ueber
23 Handelstage (2026-08-24 bis 09-23), alle drei Broker:

| Konto | SP500 | US30 | NASDAQ |
|---|---|---|---|
| TTP | 0,831 | 0,486 | 0,525 |
| IQ Markets | 0,649 | 0,738 | 0,427 |
| **Tickmill (EK)** | **0,389** | **0,233** | **0,263** |

(bps, M1-Median; p90 praktisch identisch)

**Zwei Befunde, beide gut:** Die Spannen im Nachtfenster sind
**nicht weiter als tagsueber** -- die TTP-Werte treffen die im NY-Open-Fenster
gemessenen (0,84 / 0,48 / 0,54) fast auf die Nachkommastelle. Die befuerchtete
Nachtausweitung bei Index-CFDs gibt es auf diesen Brokern nicht. Und
Median = p75 = p90 = max deutet auf einen **fest quotierten Spread** hin.

Gegen die Break-even-Schwelle von 3,08 bps waere das ein Puffer von Faktor
4 bis 13 gewesen. **Die Kosten waren nie das Problem.**

## Schritt 1 -- Existiert das Fenster noch? Nein.

Dukascopy-Index-M15, Berliner Zeit, 2018-07 bis 2026-09 (davor hat der Feed
im Nachtfenster keine Bars). Gluecklicher Zufall: das Paper-Sample endet
Juli 2018, unsere Abdeckung beginnt dort -- der Test ist eine fast
lueckenlose **Out-of-Sample-Fortsetzung**, kein Nachbau der Paper-Jahre.

| Instrument | 2018-2026 | t | OHNE 2020 | t | ab 2023 | t |
|---|---|---|---|---|---|---|
| SP500 | +3,52 % | 1,72 | **+0,67 %** | 0,49 | +0,28 % | 0,16 |
| US30 | +2,69 % | 1,29 | **−0,29 %** | −0,23 | −0,77 % | −0,50 |
| NASDAQ | +5,23 % | 2,13 | **+2,07 %** | 1,19 | +1,93 % | 0,86 |

Die Jahresreihe zeigt, warum die Vollsample-Zahl truegt:

| | 2018 | 2019 | **2020** | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| SP500 | +2,8 | +0,8 | **+24,3** | +0,9 | +0,7 | −2,5 | −0,2 | +2,0 | +2,5 |
| US30 | +1,3 | −0,3 | **+24,4** | −0,3 | +0,6 | −2,0 | −1,2 | −0,8 | +1,6 |
| NASDAQ | +3,8 | +0,8 | **+28,4** | +3,4 | +1,6 | −2,6 | −0,8 | +5,0 | +7,8 |

**Ein einziges Jahr traegt praktisch alles.**

### Warum das kein Messfehler ist

Unser 2020er Wert (+24,3 % SP500) trifft die **+24,5 %**, die das Paper
selbst fuer sein 2020-Out-of-Sample ausweist, fast exakt. Die Pipeline misst
also genau das, was die Autoren gemessen haben -- was den Befund fuer die
Jahre danach glaubwuerdig macht statt verdaechtig.

### Das entscheidende Verhaeltnis: Brutto-Edge gegen Kosten

Ohne 2020 betraegt der Brutto-Edge **0,26 / −0,12 / 0,82 bps je Trade**.
Der guenstigste gemessene Spread (Tickmill) betraegt **0,39 / 0,23 / 0,26 bps**.

- SP500: 0,26 brutto gegen 0,39 Kosten -> **netto negativ**
- US30: −0,12 brutto -> **negativ schon vor Kosten**
- NASDAQ: 0,82 gegen 0,26 -> +0,56 bps netto, aber bei t=1,19 statistisch
  nicht von null zu unterscheiden

Die Strategie handelt 252-mal im Jahr. Ein Edge, der kleiner ist als der
Spread, ist kein Edge.

## Schritt 2+3 -- Fenstervarianten und konditionale Version: retten nichts

**Haelften** (Paper: die zweite traegt 5,90 der 7,60 Punkte). Bei uns ist die
zweite Haelfte tatsaechlich die bessere (NASDAQ +3,71 vs. +1,52; US30 +2,01
vs. +0,66) -- die Struktur stimmt also qualitativ. Nur ist das Niveau zu
klein, um die Kosten zu tragen, und die erste Haelfte ist OOS auf allen drei
Instrumenten negativ.

**Konditionale Version.** Das Paper rettet die naive Variante ueber eine
Tagesauswahl (nur die ~40 % Tage mit hoher erwarteter Rendite). Nachgebaut
mit Overnight-Realized-Vol (M15-Bars 22:00-05:30, streng ex ante, Schwelle
aus einem expandierenden 60-%-Quantil -- kein Look-ahead). Delta-VIX ging
nicht, weil Dukascopys VIX erst ab 2022-10-04 liefert.

| Instrument | hohe Overnight-Vol | t | **davon ohne 2020** | t |
|---|---|---|---|---|
| SP500 | +8,02 % | 1,67 | **+0,89 %** | 0,31 |
| US30 | +8,57 % | 1,64 | **+1,07 %** | 0,39 |
| NASDAQ | +8,26 % | 1,43 | **+1,76 %** | 0,49 |

Der Filter sieht stark aus -- **bis man 2020 herausnimmt, dann bleibt nichts.**
Er selektiert im Wesentlichen 2020. Das ist der sauberste Einzelbefund
dieser Untersuchung: die vom Paper vorgesehene Rettung rettet bei uns nicht.

## Gegenchecks vor dem Abbruch

**Falsch verankert?** Nein. Ich hatte in Berliner Zeit gerechnet (Paper-
DST-Test), das Paper definiert in ET. Beide Verankerungen liefern praktisch
dasselbe (SP500 +3,52 vs. +3,32; NASDAQ +5,23 vs. +4,90; ohne 2020 beide
nahe null). Die Wahl war egal.

**Nur verschoben statt tot?** Nein. Scan ueber **alle 42 Vier-Stunden-Fenster**
im 30-Minuten-Raster, je Instrument, fuer 2018-2026 und fuer ab 2021:
**kein einziges Fenster erreicht die White-(2000)-Schwelle von |t| >= 3,7**,
die das Paper selbst als Messlatte gegen genau dieses Mehrfachtesten setzt.
Und das EU-Open-Fenster rangiert ab 2021 auf **Rang 38/42 (SP500)** bzw.
**40/42 (US30)** -- es ist nicht verschoben, es ist eines der schlechtesten
Fenster des Tages geworden. Die besten Kandidaten ab 2021 (17:00-21:00,
12:00-16:00, also US-Session) erreichen t = 1,6-2,3 und sind gegen die
3,7er-Schwelle Rauschen.

Zwischenfall dabei, der Erwaehnung wert: der erste Lauf des Scans wies
ET-verankerte Fenster mit **−13 bis −19 % p.a.** aus. Ursache war ein
stiller Vorzeichenfehler -- Fenster ueber Mitternacht wurden mit dem
Endzeitpunkt DESSELBEN Kalendertags gepaart, also minus 20 Stunden statt
plus 4. Behoben durch Paarung ueber Bar-Zeitstempel
(`searchsorted`, `max_hold_h`). **Waere das unbemerkt geblieben, haette es
als spektakulaerer Short-Edge ausgesehen.**

## Schritt 4 -- Phase 6: bewusst NICHT gerechnet

Walk-Forward und Monte Carlo pruefen, ob ein **positiver** Edge robust ist.
Hier ist nach Kosten keiner da, den man stresstesten koennte. Eine
Monte-Carlo-Simulation auf einem Erwartungswert von ~0 waere Theater und
wuerde dem Ergebnis eine Serioritaet verleihen, die es nicht hat.

## Verbleibender Vorbehalt

Unsere Preise sind **Dukascopy-Index-CFD-Mid**, das Paper misst
**E-mini-Futures**. Sollte Dukascopys Nachtquote gegenueber dem echten
Futures-Tape gedaempft sein, wuerde das den Effekt kleinrechnen. Dagegen
spricht deutlich, dass 2020 fast exakt reproduziert -- eine gedaempfte
Quote haette auch 2020 gedaempft. Ich halte den Vorbehalt fuer klein, aber
nicht fuer null.

## Was wir behalten

1. **Die Nacht-Spread-Messung.** Erstmals belegt, dass unsere Index-CFDs
   zwischen 05:30 und 09:30 Berlin **nicht teurer** sind als tagsueber
   (Tickmill 0,23-0,39 bps). Das ist eine wiederverwendbare Zahl fuer jede
   kuenftige Idee in diesem Fenster -- und sie war vorher nicht bekannt.
2. **Der Scan als Werkzeug.** `research_eu_open_windowscan.py` beantwortet
   fuer jedes Instrument die Frage "liegt irgendwo im Tag eine
   Renditekonzentration?" gegen eine korrekte Multiple-Testing-Schwelle.
   Wiederverwendbar.
3. **Ein sauber dokumentierter Nullbefund.** Ein publizierter Edge mit
   Sharpe 1,67, der jedes Jahr seines Samples positiv war, ist in den acht
   Jahren nach Sample-Ende verschwunden. Das ist die beste Illustration des
   Decay-Risikos, die wir im Second Brain haben -- und der Grund, warum der
   Nachrechnen-Schritt vor dem Bau kommt.
