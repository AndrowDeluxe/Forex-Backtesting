# Project: EU-Open-Renditefenster (05:30-09:30 Berlin) -- Edge-Kandidat

**Status**: **Kandidat, nicht begonnen.** Phase 3 (Screening) abgeschlossen
am 2026-09-22, Phase 4+ steht aus und braucht eine Nutzerentscheidung.
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
