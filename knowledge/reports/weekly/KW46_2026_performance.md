# Weekly Checkup - Performance - KW46/2026

**Abgedeckte Woche: Mo 2026-11-09 bis So 2026-11-15.** Erzeugt am So 15.11. durch den geplanten
`Forex-Weekly-Report`-Task.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W46.json` (09.11. 00:00 bis 16.11. 00:00
Serverzeit), Soll/Ist `scripts/reports/soll_ist_2026-W46.json`, die Logs der drei Portfolio-Bridges
(inkl. `gold_asb_filter_journal.jsonl`), `knowledge/CHANGELOG.md` und der Task Scheduler.

> **Zum Abzug - der erste war falsch, der zweite stimmt:**
> - Der erste Abzug um 18:00 meldete **TTP und IQ mit 0 Deals**, EK mit 4 und FK mit `IPC timeout`.
>   Grund: Am Sonntag lief kein Terminal. `mt5_pull.py` hat alle vier erst gestartet, die Deal-Historie war
>   noch nicht geladen (siehe Memory: `mt5_kaltes_terminal_leere_historie`), und FK startete ohne
>   `/portable` (siehe Memory: `fk_terminal_braucht_portable`).
> - FK-Terminal beendet, mit `/portable` neu gestartet, 90 s gewartet, zweiter Abzug: **EK 16, TTP 7,
>   IQ 8, FK 16 Deals**. Endstand minus Wochen-P&L trifft den KW45-Endstand jetzt **auf allen vier
>   Konten auf den Cent** (EK 2.750,19 EUR, TTP 99.675,45, IQ 97.666,89, FK 99.519,78 USD).
> - Soll/Ist wurde danach auf dem korrekten Abzug neu gerechnet. Die vier Terminals hat dieser Lauf
>   gestartet; alle vier wurden danach wieder geschlossen (kein Fenster offen).

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen mit echtem Geld: **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets 16054) und **FK Instant Funding**
(BeyondIQCapital 17764). Alle sechs Bridge-Tasks stehen auf `Bereit`, die Einzel-Bots bleiben
`Deaktiviert`. Keine neuen `*-Bridge`/`*-Bot`-Ordner.

**Live-Änderungen in der Woche:**

- **Di 10.11. ca. 01:49, FK:** Bein `gold_silver` hängt die laufende H4-Kerze als Platzhalter an
  (`ce42e5ef`). Vorher war jedes Signal ≥ 240 Min. alt und das Bein konnte seit 04.10. nie einsteigen
  (siehe Memory: `fk_gold_silver_strukturell_zu_alt`). In KW46 kam auf FK kein neues Signal; der Fix ist
  also live noch nicht erprobt.
- **Di 10.11. 02:19, alle drei Bridges:** Gold ASB schreibt je Tag ein Filter-Protokoll
  (`gold_asb_filter_journal.jsonl`); Soll/Ist übernimmt dort die Bot-Entscheidung (`4c0bcc53`). Die
  Handelslogik bleibt gleich. Die Ursache des KW45-Rätsels (Gold ASB 03.11.) ist damit belegt: Die
  Friktion des Vortags wird nach 01:00 NY überarbeitet.
- **Di 10.11.:** 37 verwaiste `placed`-Einträge (FK 24, IQ 6, TTP 7) per Broker-Abgleich auf `closed`
  gesetzt. Nur Buchführung.
- **So 15.11. (nach Handelsschluss), alle drei Bridges:** **CTNL-Makro-Sperre live** - kein
  CTNL-Reversal-Long bei Gold-MACRO ≤ 35, kein Short bei ≥ 65. Neuer Task `Forex-Gold-Makro-Gate-Refresh`
  (täglich 07:15). Wirkt erst ab Mo 16.11.; Stand 15.11.: MACRO 30, **CTNL-Longs gesperrt**.

**Störungen:** Zwei Tracebacks auf FK in der Nacht auf Di 10.11. (01:16 Verbindungsaufbau, 03:18
`.state.lock` existiert). Beides fällt in die nächtliche Arbeitssession an FK, danach lief FK normal
(89 Läufe Di bis Fr). Kein Neustart- oder Standby-Befund. Der Watchdog-Push läuft wieder:
`main` ist synchron mit `origin` (der KW45-Stau ist mit dem Commit vom 08.11. aufgelöst).

## 2. Risk-Management-Compliance

**Keine Regelverletzung der Bots. Kein Kill-Switch, kein Drawdown-Halt.** In den Logs aller drei Bridges
keine Kill-/Halt-Meldung. Einzige Kill-Switch-Zeile: FK-Fast Di 03:21 "Scan ohne Trades (Datenlücke?) -
kein Urteil, Zustand bleibt aus" (nachts, folgenlos).

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgelöst; Balance **2.520,44 EUR (−8,35 % in der Woche)**, davon −4,50 % aus einem Handtrade |
| EK-Portfolio | Gesamtrisiko-Deckel 30 % | Bot-Risiko eingehalten. **Offen über das Wochenende: manueller USD/JPY-Short 0,1 Lot, Stop 162,00 = ca. 116 EUR Risiko (4,6 %)** |
| EK-Portfolio | Einzeltrade-Deckel 5 % | Bot eingehalten (größter Bot-Verlust Gold-Silber −70,14 EUR = 2,6 %). **Handtrade Gold Long 11.11.: −123,85 EUR = 4,5 %** (gilt nicht als Bot-Regel, siehe Abschnitt 6) |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgelöst (CTNL hat nicht gehandelt) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Do 12.11. −85,50 USD; Balance 99.759,42 = −0,24 % seit Start |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag Do 12.11. −113,40 USD. Balance **97.621,51 USD = −2,38 % seit Start, ca. 3.622 USD Abstand** zur 6-%-Grenze (KW45: 3.667) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgelöst |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; schlechtester Tag Do 12.11. −272,52 USD (davon −145 aus Handtrades); Balance 99.661,71 USD (−0,34 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nicht ausgelöst |

**Zur Kenntnis:** Auf EK und FK liegen diese Woche **sieben Handtrades** (MT5 `reason` 1 = Mobile,
Magic 0) neben den Bots. Kein Bot-Limit wurde dadurch verletzt, aber auf EK haben zwei davon je ca. 4,5 %
Risiko, also mehr als jedes Bot-Bein. Details in Abschnitt 6, Punkt 1.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): −229,75 EUR (−8,35 %) bei 8 Trades, davon Bots −105,90 EUR (−3,85 %).**
  Die Bot-Verluste kommen aus Gold-Silber (Long 09.11. bei 4.123, am 10.11. ausgestoppt, −70,14),
  Trend-Pullback CHF/JPY (−52,47) und drei kleinen SP500-ORB-Stopps (je ca. −10). Gold ASB (+34,94) und OU
  QCOM (+10,96) dagegen. Der größte Einzelposten ist **kein Bot**: ein Gold-Long per Handy am 11.11.
  (−123,85).
- **Funded-Portfolio-Bridge (TTP + IQ): +38,59 USD (+0,02 %) bei 8 Trades.** Flach. Gold ASB (Short 13.11.,
  TTP +243, IQ +292) gleicht die SP500-ORB-Stopps aus (TTP 2 x ca. −83, IQ 3 x ca. −112). NASDAQ-ORB kam auf
  keinem Konto zum Zug (Abschnitt 5). OU: QCOM auf TTP per Modell geschlossen (+6,94).
- **FK Instant Funding: +141,93 USD (+0,14 %) bei 7 Trades, davon Bots −342,57 USD (−0,34 %).** Bots: drei
  SP500-ORB-Stopps (je ca. −128) und Gold ASB +40,82. Das Plus kommt aus **Handtrades**: EUR/USD-Short
  +631,42, zwei Gold-Longs −145,42.

**Muster der Woche:** **Die Bots verlieren leise, das Ergebnis machen die Handtrades.** Bot-Seite über
alle Konten: 19 Trades, 6 Gewinner, −304 USD und −106 EUR. Davon sind 9 Trades SP500-ORB-Stopps
(je ca. −1 R). Gold fiel in der Woche um 7 % (4.148 → 3.852); Gold ASB hat das am Freitag als Short
mitgenommen, CTNL hatte kein Signal.

## 4. Trades, Winrate, Gewinn - Summary

Gezählt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto inkl. Kommission und Swap.
Eine Teilschließung zählt nicht als eigener Trade. Die Prozentwerte beziehen sich auf den Kontostand zu
Wochenbeginn. Handtrades sind enthalten (wie in KW45), die Spalte "davon Bots" zeigt den Bot-Anteil.

| Bridge | Trades | Winrate | P&L | % | davon Bots |
|---|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 8 | 25,0 % | **−229,75 EUR** | **−8,35 %** | 7 Trades, −105,90 EUR (−3,85 %) |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 8 | 37,5 % | **+38,59 USD** | **+0,02 %** | alle 8 |
| FK Instant Funding (LIVE, echtes Geld) | 7 | 28,6 % | **+141,93 USD** | **+0,14 %** | 4 Trades, −342,57 USD (−0,34 %) |
| **Gesamt (alle 3, echtes Geld)** | **23** | **30,4 %** | **−229,75 EUR / +180,52 USD** | **ca. −0,02 %** | 19 Trades, −105,90 EUR / −303,98 USD |

- **Keine Summe über beide Währungen.** Für die Gesamt-Prozentzahl ist EK mit ca. 3.064 USD (Kurs 1,114
  zu Wochenbeginn) in ein Buch von ca. 299.900 USD eingerechnet, der EK-Verlust mit 1,10 (Wochenschluss).
- Je Konto: TTP 4 Trades **+83,97 USD (+0,08 %)**, IQ 4 Trades **−45,38 USD (−0,05 %)**.
- **Noch offen:** EK SYY/OXY (OU) + USD/JPY-Short (Hand); TTP STT (seit 16.10.), SYY, OXY (OU); FK USD/JPY-Short
  (Hand). IQ flach.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das IQ-Konto heißt "BeyondIQCapital
  **Demo** Challenge". Die Einordnung als "echtes Geld" übernehme ich unverändert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest über das Fenster 09.11. 00:00 bis 13.11. 21:00 (UTC) mit Sizing und
Kostenannahme der jeweiligen Bridge und der Konfiguration von HEUTE.

| Bridge | Soll | Ist (nur Bot) | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 10 Trades / **−0,33 %** | −105,90 EUR (−3,85 %) | - | - | - (**10 nicht_ermittelbar, +18,05 R**) |
| Funded-Portfolio | 10 Trades / **+1,19 %** | +38,59 USD (+0,02 %) | 0 | 1 (−1,04 R) | 9 (+21,55 R) |
| FK Instant Funding | 10 Trades / **+2,67 %** | −342,57 USD (−0,34 %) | 0 | 1 (−1,04 R) | 9 (+21,55 R) |

(Das Werkzeug weist für FK als Ist "+146,43 USD" aus, seine Bein-Summe ergibt aber −342,47 USD; die
Kopfzeile scheint einen Teil der Handtrades mitzuzählen. Ich nehme die Bein-Summe. Die EK-Kopfzeile
"−9,10 %" enthält den Handtrade und rechnet auf den heutigen Kontostand.)

**Hauptaussage: Ist liegt auf Funded ca. 1,2 und auf FK ca. 3 Prozentpunkte unter dem Soll. Die Lücke
besteht aus drei bekannten Posten: verpasste NASDAQ-Gewinner (Erste-Bar-Problem, ca. 12,9 R), ein zu
optimistisches SP500-Soll (Stop in der Fill-Kerze, ca. 7 R) und US30 im Soll trotz Pause (4,5 R).**

**Pflicht-Vorbehalte:**

1. **Konfiguration:** Soll rechnet mit dem Stand von heute. Die einzige Änderung mit Wirkung auf die
   Signale ist die CTNL-Makro-Sperre vom 15.11. Sie ändert hier nichts: CTNL hat weder im Soll noch im Ist
   einen Trade. Der FK-Fix für `gold_silver` (10.11.) gilt im Soll für die ganze Woche, live erst ab Dienstag;
   ein Signal gab es in keinem von beiden.
2. **EK lässt sich nur grob zerlegen** (SQLite statt Signal-Ledger). "10 nicht_ermittelbar" heißt genau das,
   nicht "nie gesehen".
3. **EKs Kostenannahme ist geschätzt** (0,50 Pips), Funded (2,05) und FK (1,30) sind gemessen. EK-Zahlen
   deshalb nicht gegen die anderen beiden stellen.

**Was hinter den Posten steckt:**

- **NASDAQ-ORB: Soll 4 Trades, +12,85 R (EK +10,39 R), live auf keinem Konto ein Fill.** Soll-Trades und
  Logs je Tag (TTP/IQ, FK gleich):
  - **Mo 09.11., Soll Long +6,42 R (Sessionende):** `breakout_passed (hoch=True)`. Der Kurs stand beim
    Platzierungslauf um 14:45 UTC schon über dem Auslöser. Auf TTP vorher einmal `10015 Invalid price`.
    **Verpasst.**
  - **Di 10.11. und Do 12.11., Soll je −1,01 R (Stop):** TTP platziert, beide Seiten nach 3 Min. storniert
    ("Kurs erreichte den geplanten SL vor dem Einstieg (wie im Backtest)"); IQ `breakout_passed`. **Gespart.**
    Widerspruch fürs Protokoll: Das Log sagt "wie im Backtest", das Soll zählt aber einen Stop.
  - **Mi 11.11.:** `filtered_out (Wednesday)`, im Soll nicht enthalten. Stimmig.
  - **Fr 13.11., Soll Short +8,46 R (Sessionende):** `breakout_passed (tief=True)`. **Verpasst.**
  - Das ist das Erste-Bar-Problem (siehe Memory: `orb_first_bar_and_polled_exits`): Der Backtest steigt in der
    ersten Kerze nach der Range ein, live kommt der Platzierungslauf zu spät. Verpasst sind **+14,88 R**,
    netto **+12,85 R**, grob **1.250-1.650 USD je Funded-/FK-Konto** (ca. 99 USD je R auf TTP, ca. 128 USD auf FK).
    **Größter Einzelposten der Woche.** Ob die beiden Gewinner live die Fill-Kerze überlebt hätten (siehe
    nächster Punkt), ist nicht prüfbar.
- **SP500-ORB: Soll 3 Trades +3,93 R, live je Konto bis zu 3 Stopps.** Am **Mo 09.11.** steigen Soll und
  live **denselben** Long ein (14:45 UTC, IQ/FK bei 7.491,3). Live wird er nach 69 Sekunden bei 7.482 gestoppt,
  danach läuft der Kurs bis zum Ziel. Das Soll zählt **+5,98 R**, weil der Backtest den Stop in der Fill-Kerze
  nicht prüft (siehe Memory: `orb_fill_bar_stop_and_live_order_gap`). Das ist hier also **ein zu
  optimistisches Soll, kein Ausführungsfehler**: ca. 7 R der Lücke. Di 10.11. und Do 12.11. (je ca. −1 R) sind
  in Soll und Ist gleich. TTP hatte am 09.11. wegen des `Invalid price`-Fehlversuchs keinen Fill und sparte
  den Verlierer. Das Werkzeug führt alle ORB-Trades als "nie gesehen", obwohl sie platziert wurden
  (Zuordnungslücke, bekannt).
- **`orb_us30` zählt mit +4,47 R im Soll**, obwohl US30 seit 04.10. pausiert ist. Werkzeugfehler, bekannt seit
  KW44, noch offen.
- **Gold ASB 13.11.: stimmig.** Short auf allen vier Konten, wie im Soll (+0,28 R, Zeitausstieg). Das neue Filter-Protokoll meldet **Filter-Drift an 2 von 3
  Tagen** (12.11., 13.11.): Die Nachrechnung hätte anders entschieden als der Bot. Seit dem 10.11. folgt das Soll
  dem Bot, deshalb erscheint das nicht mehr als Lücke. Wie oft das passiert, siehe Abschnitt 6, Punkt 4.
- **Trend-Pullback CHF/JPY 12.11.:** auf EK gehandelt und wie im Soll ausgestoppt (−1,04 R). Auf Funded/FK
  "nicht platziert": dort ist das Bein nicht live. Stimmig.

## 5b. Edge-Warnstufen je Live-Bein

**Zum vierten Mal in Folge NICHT frisch.** `research_live_legs.py tickmill --ampel` lief ab ca. 17:55, kam
bis zu einem Instrument bei **2018-02-28 14:30** und stand dort über 12 Minuten still (Dukascopy-Abruf ohne
Timeout, wie am 18.10., 01.11. und 08.11.). Ich habe den Lauf abgebrochen; `status.csv` wurde deshalb nicht neu
gerechnet. Die Liste `live_trades_tickmill_ampel.csv` stammt weiter vom **27.10., letzter Trade 25.10.**;
KW44 bis KW46 fehlen. Die Tabelle ist der Stand vom 08.11. (inhaltlich gleich wie 30.10.):

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** | **23,2** / 15,2 | alle fünf rot |
| orb_us30 | **ROT** (pausiert) | 24,5 / 13,2 | alle fünf rot |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_silver | GELB | 1,7 / 4,9 | roll_mean streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | grün | - | - |

- **orb_sp500 (ROT):** gegenüber KW45 unverändert (gleiche Liste). Live kamen in KW46 je Konto bis zu drei
  Stopps dazu, das Soll zählt dagegen +3,93 R (Fill-Kerze, Abschnitt 5). Die echte Lage ist also eher schlechter
  als die Tabelle. Entschieden ("ORB bleibt erstmal so", 16.10.), kein neuer Dashboard-Eintrag.
- **orb_us30 (ROT):** pausiert seit 04.10., unverändert.
- **btc_ema_cross, gold_silver (GELB):** unverändert, beobachten. gold_silver verlor live auf EK −70,14 EUR.
- **Werkzeug:** Vier Wochen ohne frische Ampel. Solange der Abruf kein Timeout hat, ist diese Tabelle für
  Wochenaussagen wertlos (Dashboard-Punkt "Report-Werkzeuge härten" besteht). Eine Warnung ist ein Grund
  hinzusehen, kein Grund, einen Bot zu ändern.

## 6. Auffälligkeiten / offene Punkte

**(1) Sieben Handtrades auf den Bot-Konten EK und FK, Ergebnis +360 USD / −124 EUR.**
Alle mit MT5 `reason` 1 (Mobile), Magic 0, ohne Bot-Kommentar:

| Konto | Trade | Eröffnet (Serverzeit) | Ergebnis |
|---|---|---|---|
| FK | EUR/USD Short 0,56 Lot bei 1,12268 | Di 10.11. 11:58 | Teil 0,25 bei 1,11388 (+220,72), Rest Ziel 1,10937 (+413,50) = **+631,42 USD** |
| FK | Gold Long 0,01 bei 4.029,70 | Di 10.11. 18:21 | Stop 3.980 → −54,80 USD |
| FK | Gold Long 0,01 bei 4.008,33 | Mi 11.11. 17:28 | Stop 3.921,60 → −90,62 USD |
| EK | Gold Long 0,01 bei 4.006,21 | Mi 11.11. 17:29 | Stop 3.870 → **−123,85 EUR (4,5 % des Kontos)** |
| FK | USD/JPY Short 0,3 Lot bei 159,844 | Mi 11.11. 23:24 | offen, Stop 162,00 (+22 USD) |
| EK | USD/JPY Short 0,1 Lot bei 159,837 | Mi 11.11. 23:23 | offen, Stop 162,00 (+6 EUR), **Risiko ca. 4,6 %** |

- Die Trades passen zu den Makro-Ideen der Woche (Education-Report 4c): EUR/USD-Short nach Dennis' Stop
  wieder eröffnet, Gold-Long genau am Alarm 4.030, USD/JPY-Short.
- **Kein Regelverstoß der Bots.** Aber: (a) Auf EK übersteigt das Risiko je Handtrade jedes Bot-Bein (Bot
  max. ca. 3 %), und EK hat in zwei Wochen ca. 10 % verloren (2.811 → 2.520 EUR). (b) Soll/Ist und Ampel
  kennen diese Trades nicht. (c) Offen ist, ob der EK-Gesamtrisiko-Deckel (30 %) offene Handpositionen
  mitzählt; nicht geprüft.
- Die NASDAQ-Teilschließung vom 05.11. hattest du am 10.11. als "händisch, emotional, Einzelfall"
  eingeordnet. Diese Woche ist es ein Muster. **Im Dashboard (Geparkt, Betrieb) zur Bestätigung
  eingetragen:** Sind Handtrades auf EK/FK gewollt, und mit welcher Größe?

**(2) ORB: Erste Kerze in beide Richtungen.** Siehe Abschnitt 5. NASDAQ verpasst zwei große Gewinner, weil
die Order zu spät kommt (+14,9 R); SP500 trifft denselben Einstieg wie der Backtest und wird in der Fill-Kerze
gestoppt, die der Backtest nicht prüft (ca. 7 R). Beides ist bekannt, die ORB-Entscheidung vom 16.10. ("bleibt
erstmal so") gilt. Neu ist nur das Ausmaß: ca. 20 R Soll-Differenz in einer Woche an der ersten Kerze. Keine
neue Dashboard-Frage, nur die Zahl fürs Protokoll.

**(3) TTP-OU: STT ist weiter offen, obwohl am 10.11. "bei US-Börsenöffnung schließen" entschieden wurde.**
Seit 16.10. in der Position (30 Tage, +9,09 USD, Stop 123,69). Laut CHANGELOG 10.11. ist die Schließung
"noch nicht ausgeführt"; FLEX und UAL waren schon zu. Die Entscheidung ist also da, nur die Ausführung fehlt.

**(4) Gold-ASB-Filter-Drift an 2 von 3 Protokolltagen.** Das neue Filter-Protokoll zeigt am 12. und 13.11.,
dass die Nachrechnung des Liquiditätsfilters anders ausfiele als die Live-Entscheidung (Friktion des Vortags
wird nachträglich überarbeitet, siehe Memory: `gold_asb_friktion_vorgriff`). Das Soll ist dagegen jetzt
geschützt. Für den Backtest heißt es: Die historischen Gold-ASB-Zahlen enthalten Tage, die live anders
entschieden worden wären. Beobachten, wie oft das in den nächsten Wochen vorkommt.

**(5) `mt5_pull.py` am Sonntag liefert still falsche Zahlen.** Zum dritten Mal (KW39, KW42, KW46) war der
erste Abzug unvollständig, weil die Terminals erst gestartet wurden. Diesmal ohne jeden Fehler bei TTP/IQ:
"0 Deals". Ohne den Saldenabgleich hätte der Report "Funded: 0 Trades" gemeldet. Vorschlag (nicht umgesetzt):
`mt5_pull.py` wartet nach dem Start eines Terminals, bis die Historie steht, und startet FK mit `/portable`.

**(6) Kleineres.**
- Soll/Ist-Werkzeug: FK-Kopfzeile passt nicht zur Bein-Summe (Abschnitt 5); `orb_us30` zählt weiter im Soll.
- FK warnt weiter in jedem Lauf "Kontostand weicht von STARTING_EQUITY=100.000 ab" (bekannt).
- Dieser Report committet nur `knowledge/reports/` und die Makro-Notiz (Pflicht aus 4c); Dashboard und
  CHANGELOG ebenfalls (Report-Pflichten).
