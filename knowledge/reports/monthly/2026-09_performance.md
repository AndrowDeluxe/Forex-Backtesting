# Monthly Checkup - Performance - September 2026

**Zeitraum: 01.09. bis 28.09.2026 frueh (Stand des Abzugs).** Der Report
laeuft als Anschluss an den KW39-Weekly am letzten Sonntag vor dem
Monatswechsel, hier verspaetet am Mo 28.09. **Die letzten drei Handelstage
(28.-30.09.) fehlen deshalb.** Das ist keine Monatsbilanz, sondern ein
Monatsstand. Wenn diese Tage gross ausfallen, gehoert das in den
Oktober-Report als Nachtrag.

**Datenbasis:** frischer, read-only Monatsabzug
`scripts/reports/mt5_2026-09_month.json` (01.09. bis 29.09. Serverzeit, alle
vier aktuellen Live-Konten), nicht die Summe der Weeklies. Dazu die vier
September-Weeklies KW36-KW39.

> **Luecke im Monatsabzug:** Er erfasst nur die Konten, die **heute** in den
> Bridge-Configs stehen. **Nicht enthalten** sind TTP Konto 1 (504069845,
> live 01.-19.09., am 23.09. endgueltig ausgebaut, Zugangsdaten entfernt)
> und IQ 15514 (bis 07.09.). Fuer diese beiden Konten gelten nur die Zahlen
> aus KW36-KW38. Die Funded-Zeile unten ist deshalb **"Funded, heutige
> Konten"** und nicht "Funded, alle Konten des Monats".

## 1. Monatsbogen

- **KW36 (31.08.-06.09.):** Funded mit 4 Konten live; FK noch Paper.
  Ruhiger Start: Funded +0,09 %, EK -0,2 %.
- **KW37 (07.-13.09.):** FK geht am 08.09. live, handelt aber 5 Tage lang
  keine einzige Order. IQ 15514 faellt raus. Funded -1,01 % (0/9 Gewinner).
- **KW38 (14.-20.09.):** Bei TTP stauen sich 32 offene XAUUSD-Positionen,
  weil der Sim-Filter kein Live-Gate ist; 24 Risikodeckel-Ereignisse. ttp1
  faellt am 19.09. raus. Der Weekly-Report selbst fiel aus (Standby) und
  wurde nachgebaut.
- **KW39 (21.-27.09.):** Die Woche der grossen Umbauten: OU Logik D, ORB
  Variante C, EK-Hebel 1,2x, E5-c, Handaufraeumen. Der CTNL-Kill-Switch
  greift nur auf FK.

## 2. Risk-Management-Compliance (Monat)

**Im ganzen Monat keine Regelverletzung und kein Drawdown-Halt auf
Kontoebene.** Die Risiko-Ereignisse des Monats:

| Wann | Wo | Was |
|---|---|---|
| 17./18.09. | Funded TTP + IQ | 24x Offenes-Risiko-Deckel (Gold-Stau), korrekt gegriffen |
| 21.09. | Funded TTP | 31x Offenes-Risiko-Deckel bis zum Handaufraeumen |
| 21.-28.09. | FK | **CTNL-Standalone-Kill-Switch aktiv**; nur auf FK vorhanden (siehe KW39) |
| ab 24.09. | EK | E5-c-Deckel (`ctnl_reversal` max. 1) greift |

**Die Konten sind weit von ihren harten Grenzen entfernt:** TTP -1,20 %
(7%-Cap), IQ -1,99 % (6%-Cap), FK -0,43 % (5%-Trailing), EK -19,4 %
(45%-Trailing). **EK ist der einzige Fall mit Tempo:** -0,2 / -3,1 / -6,6 /
-11,6 % pro Woche, jede Woche groesser. Formal ist das innerhalb der Regeln.
Von der Tendenz her ist es das Wichtigste in dieser Tabelle.

## 3. Was hat gut / nicht gut funktioniert (Trend je Bridge)

- **EK-Portfolio-Bridge: stetig schlechter, Woche fuer Woche.** Der Verlust
  ist gold-lastig: XAUUSD -549,49 EUR von -687,94 realisiert. `ctnl_reversal`
  mit Mindestlot ist ueber den Monat der groesste Einzeltreiber. Die
  Aktien- und Indexbeine sind zusammen leicht negativ. **Trend: verschlechtert.**
- **Funded-Portfolio-Bridge: pendelt um Null mit negativer Drift, beherrscht
  von Gold.** Die Weeklies: +359 / -2.999 / +501 / -1.696 USD. IQ verliert
  auf XAUUSD.gbe -2.703,70 USD im Monat. EURUSD (`cls_practical`) ist auf
  beiden Konten der Lichtblick (+478,52 IQ, +29,35 TTP; der grosse Treffer
  vom 22.09. kam nach TTP-Verlusten frueher im Monat). Die Ausfuehrung ist
  seit KW38 sichtbar stabiler: keine Fehlermeldungen und korrekte ORB-OCOs,
  so das CHANGELOG vom 22.09. **Trend: flach bis leicht negativ, Qualitaet
  der Ausfuehrung verbessert.**
- **FK Instant Funding: von "handelt nicht" zu "handelt und verdient".**
  KW37: 0 Orders. KW38: keine Daten (IPC-Timeout beim Abzug). KW39: +586 USD
  aus Bot-Trades. Das Kontoergebnis ist trotzdem negativ, wegen der
  Handtrades (siehe Abschnitt 6). **Trend: verbessert (Bot), verschlechtert
  (Konto).**

## 4. Trades, Winrate, Gewinn - Summary (frischer Monatsabzug)

Geschlossene Positionen, netto inkl. Kommission/Swap. % bezogen auf den
Kontostand am 01.09. (aktueller Balance minus Monats-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill) | 77 | 22,1 % | **-673,59 EUR** (inkl. +14,35 Gutschriften) | **-19,4 %** |
| Funded-Portfolio, heutige Konten (TTP 2 + IQ 16054) | 180 | 43,9 % | **-3.192,09 USD** | **-1,59 %** |
| &nbsp;&nbsp;davon TTP Konto 2 | 94 | 40,4 % | -1.204,87 USD | -1,20 % |
| &nbsp;&nbsp;davon IQ Markets 16054 | 86 | 47,7 % | -1.987,22 USD | -1,99 % |
| FK Instant Funding (live ab 08.09.) | 33 | 42,4 % | **-434,43 USD** (Bot +798,39 / Hand -1.232,82) | **-0,43 %** |
| **Gesamt (echtes Geld, heutige Konten)** | **290** | **37,9 %** | **-673,59 EUR / -3.626,52 USD** | **ca. -1,4 %** |

Wie immer keine Summe ueber beide Waehrungen. EK ist ca. 1 % des Buchs, und
die Gesamtprozentzahl bewegt sich zwischen EUR/USD 1,05 und 1,25 kaum
(-1,43 % bis -1,46 %). ttp1 und IQ 15514 fehlen (siehe Kasten oben).

## 5. Portfolio vs. Einzelkonten

**Erstmals gibt es mit FK Instant Funding echte Portfolio-Historie:** 29
geschlossene Bot-Trades, der erste echte Entry am 14.09. **Fuer eine
risikobereinigte Aussage ist das zu wenig.** Zwei Wochen mit Handel ergeben
keinen Sharpe und keinen belastbaren MaxDD. Als Referenzpunkt bleibt der
Backtest `portfolio_construction/results/fk_instant_funding_final.json`
(2024-08 bis 2026-07):

| | CAGR | Sharpe | Max DD |
|---|---|---|---|
| **6-Strategien-Portfolio (Backtest)** | 24,81 % | 2,72 | **-2,27 %** |
| bestes Einzelbein ORB-Portfolio | 34,72 % | 1,66 | -9,26 % |
| CTNL Edge einzeln | 21,69 % | 1,82 | -7,95 % |

**Was sich live schon sagen laesst:** Der Backtest erwartet im Mittel etwa
+1,9 % pro Monat bei sehr flacher Kurve. Die Bots auf FK lieferten
**+0,80 %** in knapp drei Wochen mit Handel; der schlechteste Tag war der
24.09. mit -0,70 % (inkl. Handtrades). Das liegt im Rahmen. **Der
Diversifikationseffekt war diese Woche direkt zu sehen:** FK setzte CTNL per
Kill-Switch aus, und die uebrigen Beine (`cls_practical`, `orb_us30`) trugen
das Konto. Auf den Einzelbein-Konten (IQ, EK), wo CTNL durchlief, dominierte
Gold den Monat. Das ist eine Anekdote und kein Beweis. Sie zeigt aber in die
Richtung, die der Backtest behauptet.

## 6. Auffaelligkeiten / offene Punkte (Monatsrollup)

1. **Der CTNL-Kill-Switch fehlt auf Funded und EK.** Das ist der teuerste
   offene Punkt des Monats (siehe KW39).
2. **EK: -19,4 % im September, mit beschleunigender Tendenz**, waehrend der
   Hebel auf 1,2x erhoeht wurde. Das Mindestlot-Problem (Memory
   `ek_mindestlot_kehrt_hierarchie_um`) ist nur fuer `ctnl_reversal`
   gedeckelt, nicht fuer `ctnl_continuation` und nicht fuer die uebrigen
   Beine.
3. **Handtrades auf dem FK-Bot-Konto: -1.232,82 USD aus 4 Positionen.** Das
   ist mehr, als die Bots im Monat verdient haben. Die Frage aus KW37 ist
   weiter offen.
4. **Gold dominiert das Ergebnis aller drei Bridges.** EK -549 EUR, IQ
   -2.704 USD, TTP -452 USD auf XAUUSD. Drei der sechs Beine (gold_asb,
   ctnl_continuation, ctnl_reversal) handeln dasselbe Instrument. Die
   Diversifikation ist damit kleiner, als die Beinzahl vermuten laesst.
5. **Die Datenkette hatte im September vier stille Fehlermodi:** das
   abgeschnittene Tagesende, IPC-Timeout (KW38), die Standby-Luecke beim
   Report und die leere Historie auf kaltem Terminal (KW39). Jeder wurde
   gefunden. Das eigentliche Muster ist, dass keiner von ihnen sich selbst
   gemeldet hat.
6. **Monatsende nicht abgedeckt** (28.-30.09.), und ttp1/IQ 15514 fehlen im
   Monatsabzug.
