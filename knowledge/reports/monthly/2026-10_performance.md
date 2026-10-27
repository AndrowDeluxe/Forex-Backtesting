# Monthly Checkup - Performance - Oktober 2026

**Zeitraum: 01.10. bis 27.10.2026 abends (Stand des Abzugs).** Der Report
laeuft als Anschluss an den KW43-Weekly (letzter Sonntag vor dem
Monatswechsel war der 25.10.), hier verspaetet am Di 27.10. **Die letzten
vier Handelstage (28.-31.10.) fehlen.** Das ist ein Monatsstand, keine
Monatsbilanz; wenn diese Tage gross ausfallen, gehoert das als Nachtrag in
den November-Report.

**Datenbasis:** frischer, read-only Monatsabzug
`scripts/reports/mt5_2026-10_mtd.json` (01.10. 00:00 bis 28.10. 00:00
Serverzeit, alle vier Live-Konten), nicht die Summe der Weeklies. Dazu die
Weeklies KW40-KW43. Anders als im September sind diesmal **alle** Konten des
Monats enthalten (keine Konto-Wechsel im Oktober).

## 1. Monatsbogen

- **KW40 (28.09.-04.10.):** Die Woche der Schutzregeln: CTNL-Kill-Switch auf
  allen Bridges, Positionsdeckel 2, AIG-Drehtuer geschlossen, ORB US30
  pausiert (04.10.). Live: ORB **32 von 32** Trades ausgestoppt, FK nahm am
  01.10. sieben CTNL-Shorts in Folge. Alle drei Bridges im Minus.
- **KW41 (05.-11.10.):** Overfitting-Sperre eingefuehrt (05.10.), ORB-Tresor
  durchgefallen. Live ruhig: 9 von 9 neuen CTNL-Shorts und 6 von 6
  ORB-NASDAQ-Fills ausgestoppt; EK erstmals seit fuenf Wochen im Plus.
- **KW42 (12.-18.10.):** Reine Research-Woche (Edge-Ampel, NASDAQ-Storno als
  2026-Fit, Gold ASB verduennt). Live sehr wenig Handel; zwei Standbys in der
  Handelszeit, der erste Gold-ASB-Stop-Order-Fill seit der Umstellung
  verliert auf allen Konten.
- **KW43 (19.-25.10.):** OU-Fix (nur fertige Tageskerzen) und Akku-Fix am Mo,
  Altpositionen von Hand geraeumt, **ein CTNL-Gewinntag (21./22.10.) dreht
  den Monat auf Funded ins Plus**. Di 20.10. sieben Stunden Totalausfall.
- **KW44 bis 27.10.:** ORB auf TTP/IQ/FK zwei Tage ausgefallen
  (Serverzeit nach der Winterzeitumstellung, am 27.10. behoben).

## 2. Risk-Management-Compliance (Monat)

**Im ganzen Monat keine Regelverletzung und kein Drawdown-Halt auf
Kontoebene.** Die Risiko-Ereignisse des Monats:

| Wann | Wo | Was |
|---|---|---|
| 30.09./01.10. | alle Bridges | CTNL-Kill-Switch auf EK und Funded nachgeruestet (vorher nur FK); seitdem auf keinem Konto ausgeloest |
| 01.10. | FK | 7 CTNL-Shorts nacheinander, alle ausgestoppt (-245,55 USD); der Deckel griff nicht, weil die Trades nacheinander kamen |
| ab 04.10. | alle | ORB US30 pausiert (bewusst) |
| 12.-19.10. | Funded / TTP | CTNL-Deckel 2 durch drei Altpositionen dauerhaft belegt, kein neuer TTP-CTNL-Trade, bis du sie am 19./22.10. von Hand geschlossen hast |
| ganzer Monat | EK | Mindestlot: CTNL-Risiko je Order ein Vielfaches des Ziels (KW42: 26,9x), Gold ASB 2,4 % je Order. Bekannt, innerhalb der Konfiguration |

**Abstand zu den harten Grenzen (Stand 27.10.):** TTP Balance 99.313 USD,
**IQ 97.205 USD = -2,80 % (Grenze 6 %)**, FK 98.314 USD = -1,69 % (5-%-
Trailing), EK 2.822,95 EUR (45-%-Trailing, weit entfernt). **IQ ist das Konto
mit der kleinsten Reserve.** Tiefster IQ-Stand im Monat 96.127 USD (-3,87 %,
nach KW42); der CTNL-Tag vom 21./22.10. hat davon 1.335 USD zurueckgeholt.

## 3. Was hat gut / nicht gut funktioniert (Trend je Bridge)

Monats-P&L je Bein aus dem Abzug (Zuordnung ueber den Kommentar des
Einstiegs; "vor Okt." = Positionen aus dem September, die im Oktober
schlossen):

- **EK-Portfolio-Bridge: flach.** Wochen: -43 / +13 / -33 / +93 / -33 EUR.
  CTNL +92,95, OU +22,24, ORB -68,96, Gold ASB -29,15, September-Positionen
  -19,70. **Trend: stabilisiert** nach dem September (-19,4 %), aber ohne
  Richtung. Der Monat haengt an einem CTNL-Trade.
- **Funded-Portfolio-Bridge: knapp Null, aber nur dank der Handschliessungen.**
  Wochen: -915 / -470 / -794 / **+2.665** / -433 USD. Je Bein (beide Konten):
  **ORB -1.048,66**, **CTNL +1.035,24** (fast alles aus dem 21./22.10.),
  **Gold ASB -667,68** (ein einziger Fill am 15.10.), OU +28,25,
  September-Positionen -273,05, **Handschliessungen +979,24**. Ohne die
  Handschliessungen ca. -930 USD (-0,47 %). **Trend: drei Verlustwochen,
  dann eine Gewinnwoche; ORB ist das Dauerminus.**
- **FK Instant Funding: der einzige klare Monatsverlust.** Wochen: -704 /
  -283 / -100 / +54 / -82 USD. **ORB -922,92** (FK riskiert dort am meisten
  je Trade), CTNL -146,62 (die 7er-Serie vom 01.10. ist nicht aufgeholt, weil
  FK kleine CTNL-Positionen faehrt), Gold ASB -63,51, Hand +18,50. **Trend:
  verbessert von Woche zu Woche** (der Verlust kam fast ganz in KW40/41).

**Ueber alle Bridges:** ORB ist im Oktober das teuerste Bein (ca. **-2.040
USD + -69 EUR**), passend zur roten Ampel bei orb_sp500 und zum
durchgefallenen ORB-Tresor (siehe Memory: `orb_is_only_tresor_durchgefallen`).
Live bleibt ORB auf deinen Entscheid vom 16.10. unveraendert.

## 4. Trades, Winrate, Gewinn - Summary (frischer Monatsabzug)

Geschlossene Positionen, netto inkl. Kommission/Swap. % bezogen auf den
Kontostand am 01.10. (aktueller Balance minus Monats-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill) | 42 | 42,9 % | **-2,31 EUR** (inkl. +0,31 Gutschrift) | **-0,08 %** |
| Funded-Portfolio (TTP 2 + IQ 16054) | 48 | 39,6 % | **+52,26 USD** | **+0,03 %** |
| &nbsp;&nbsp;davon TTP Konto 2 | 26 | 53,8 % | +372,25 USD | +0,38 % |
| &nbsp;&nbsp;davon IQ Markets 16054 | 22 | 22,7 % | -319,99 USD | -0,33 % |
| &nbsp;&nbsp;davon Handschliessungen (beide) | 6 | 100 % | +979,24 USD | +0,50 % |
| FK Instant Funding | 29 | 17,2 % | **-1.114,70 USD** | **-1,12 %** |
| **Gesamt (echtes Geld)** | **119** | **35,3 %** | **-2,31 EUR / -1.062,44 USD** | **ca. -0,36 %** |

Wie immer keine Summe ueber beide Waehrungen. EK ist ca. 1 % des Buchs
(2.825 EUR, angenommen 1,17, nicht abgefragt); die Gesamtprozentzahl bezieht
sich auf ca. 299.200 USD. Zum Vergleich September (bis 28.09.): -1,4 %.

## 5. Portfolio vs. Einzelkonten

**FK Instant Funding hat jetzt sieben Wochen echte Portfolio-Historie**
(erster Entry 14.09.). Fuer eine risikobereinigte Aussage ist das immer noch
zu wenig: 29 Trades im Oktober, Sharpe und MaxDD sind daraus nicht
belastbar. Referenz bleibt der Backtest
`portfolio_construction/results/fk_instant_funding_final.json`
(2024-08 bis 2026-07):

| | CAGR | Sharpe | Max DD |
|---|---|---|---|
| **6-Strategien-Portfolio (Backtest)** | 24,81 % | 2,72 | **-2,27 %** |
| bestes Einzelbein ORB-Portfolio | 34,72 % | 1,66 | -9,26 % |
| CTNL Edge einzeln | 21,69 % | 1,82 | -7,95 % |

**Was sich live sagen laesst:** Der Backtest erwartet im Mittel ca. +1,9 %
pro Monat bei sehr flacher Kurve. Live lieferte FK im Oktober **-1,12 %**,
und der Kontostand fiel im Monat praktisch monoton von 99.429 auf 98.314 USD
(der Hoechststand war der 01.10.). **Die Diversifikation hat diesen Monat
nicht getragen, weil das groesste Bein (ORB, 37 % Kapitalanteil im Backtest)
gleichzeitig mit dem Edge-Kipp 2026 verliert** und die Gold-Beine keinen
Ausgleich lieferten (Gold ASB nur ein Fill, CTNL mit kleinen Positionen).
Das ist eine Beobachtung, kein Beweis gegen den Backtest; sie passt aber zu
"Simulation optimistischer als live" (siehe Memory: `sim_optimistischer_als_live`)
und zum Tresor-Check aller Live-Beine (KW42).

## 6. Auffaelligkeiten / offene Punkte (Monatsrollup)

1. **Verfuegbarkeit des Rechners ist der teuerste operative Punkt des
   Monats.** Standbys/Ausfaelle in der Handelszeit am 12.10. (7 h), 15.10.
   (1 h, ORB-Fenster), 20.10. (7 h, Akku leer, ORB-Gewinner +5,97 R
   verpasst). Der Akku-Fix vom 19.10. hat das Problem verschoben; der VPS ist
   auf November gelegt.
2. **ORB laeuft live auf schwachem Grund weiter** (Ampel ROT bei SP500,
   Tresor durchgefallen, NASDAQ-Storno als 2026-Fit), bewusst so entschieden
   (16.10.). Im Oktober das teuerste Bein auf allen Bridges.
3. **Serverzeit-Fehler nach der Umstellung** (26./27.10., ORB auf drei Konten
   aus), behoben. Die naechste kritische Phase ist Mitte Maerz 2027.
4. **Soll/Ist ist fuer ORB weiter nicht lesbar** (Storno nicht modelliert,
   Fills nicht zugeordnet) und zeigt CTNL-Signale zeitversetzt (KW42, KW43).
5. **TTP-OU: STT weiter offen** (verwaist), FLEX/UAL ungeprueft; DD/EOG am
   22.10. von Hand geschlossen.
6. **IQ hat die kleinste Reserve** (-2,80 %, Grenze 6 %). Ein Monat wie
   KW40-42 (-1.400 USD) ist verkraftbar, zwei nicht.
7. **Research-Arbeit der zweiten Monatshaelfte grossteils nicht committet**
   (siehe Education-Teil).
