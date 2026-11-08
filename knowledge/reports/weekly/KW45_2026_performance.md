# Weekly Checkup - Performance - KW45/2026

**Abgedeckte Woche: Mo 2026-11-02 bis So 2026-11-08.** Erzeugt am So 08.11.
durch den geplanten `Forex-Weekly-Report`-Task.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W45.json`
(02.11. 00:00 bis 09.11. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W45.json`, die Logs der drei Portfolio-Bridges und
des Bridge-Watchdogs, das Windows-Ereignisprotokoll, `knowledge/CHANGELOG.md` und
der Task Scheduler.

> **Zum Abzug:**
> - Die Startstaende ergeben sich sauber: Endstand minus Wochen-P&L trifft den
>   KW44-Endstand auf **allen vier Konten auf den Cent** (EK 2.811,14 EUR,
>   TTP 99.046,28, IQ 96.906,81, FK 98.299,49 USD).
> - **Diesmal gibt es Handschliessungen:** drei Ausstiege mit `reason` 1 (MT5-Mobile-App),
>   alle am Do 05.11. an der NASDAQ-ORB-Position. Abschnitt 6, Punkt 1.
> - Fuer den Abzug wurde kein Terminal neu gestartet: alle vier Terminals liefen schon
>   (seit Mo 02.11. ca. 02:03), danach dieselben vier Prozesse, kein Fenster offen gelassen.
> - Markt zu, die Kontostaende sind also auch der Wochenendstand.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen mit echtem Geld (`DRY_RUN = False`, heute in allen drei
`config.py` geprueft): **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets 16054) und
**FK Instant Funding** (BeyondIQCapital 17764). Alle sechs Bridge-Tasks stehen auf `Bereit`
(letzter Lauf Fr 06.11. kurz vor Mitternacht, Ergebnis 0), die Einzel-Bots bleiben
`Deaktiviert`. Keine neuen `*-Bridge`/`*-Bot`-Ordner.

**Live-Aenderungen:**

- **Mo 02.11. 20:34, alle drei Bridges (ueber das Repo, `cd5e2358`):** Gold-ASB-Ausfall-Ersatz
  wieder **aus** (`STALE_FALLBACK_ENABLED = False`; die Bridges uebergeben weiter
  `allow_stale=True`, der Schalter ueberstimmt das). Damit ist die KW44-Entscheidung im Sinne der
  Dashboard-Empfehlung umgesetzt. Die Bridge-Dateien selbst sind seit 01.11. unveraendert.
- **Mo 02.11. 20:49, Data Lake (`67e0060b`):** Tageskerzen werden bei Dukascopy-Ausfall aus
  Lake-H1 abgeleitet. Wirkt auf GOLD_D1 (Gold-ASB-Friktion, Trend-Pullback, CTNL-Ribbon).
  In dieser Woche gab es keinen Ausfall, der Pfad wurde also nicht live benutzt.
- **Mo 02.11., `GOLD_D1` neu aus Dukascopy** (539 Twelve-Data-Kerzen ersetzt).

**Stoerungen:** Unerwarteter Neustart **Mo 02.11. 02:01** (`Kernel-Power 41`), danach lief alles;
ein kurzer Netz-/DNS-Aussetzer **Mo 14:20-14:35** (Telegram-DNS, IPC-Timeouts auf EK und FK).
**Di bis Fr keine Luecke ueber 30 Minuten** in den EK-Laufprotokollen, kein Standby.
Die Woche war also technisch die ruhigste seit Wochen; die "Watchdog-Luecke" des Cloud-Monitors
war ein Fehlalarm (Abschnitt 6, Punkt 2).

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Kill-Switch ausgeloest, kein Drawdown-Halt.** In den Logs aller
drei Bridges keine Kill-/Halt-Meldung.

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest; Balance 2.750,19 EUR (-2,17 % in der Woche) |
| EK-Portfolio | Gesamtrisiko-Deckel 30 % | eingehalten; hoechstes gesehenes offenes Risiko ca. 90 EUR (Deckel ca. 841 EUR) |
| EK-Portfolio | Einzeltrade-Deckel 5 % | eingehalten. **Gold ASB 03.11.: Risiko 90,38 EUR = 3,22 %**, Verlust -90,28 EUR. Gewollt (Bein auf effektiv 2,93 % kalibriert, 0,02 Lot aufgerundet) |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgeloest (CTNL hat diese Woche nicht gehandelt) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Di 03.11. -561,06 USD; Balance 99.675,45 = -0,32 % seit Start |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag Di 03.11. -610,80 USD (Gold ASB, 0,63 % <= 1 %). Balance 96.906,81 -> **97.666,89 USD = -2,33 % seit Start, ca. 3.667 USD Abstand** zur 6-%-Grenze (KW44: ca. 2.907) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgeloest |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; schlechtester Tag Fr 06.11. -586,42 USD; Balance 99.519,78 USD (-0,48 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nicht ausgeloest |

**Zur Kenntnis:** IQ hat 760 USD Abstand zurueckgewonnen. Die Handschliessung vom 05.11. (Abschnitt 6)
war **kein** Risiko-Eingriff im Sinne einer Regel: Sie hat Gewinn mitgenommen, keine Grenze war nah.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): -60,95 EUR (-2,17 %) bei 6 Trades.** Gold ASB (03.11., Short,
  -90,28) und Gold-Silber (05.11. Long, am 06.11. ausgestoppt, -73,79) tragen den Verlust; beide
  sind die hoch gewichteten Beine (je ca. 2,9 %). ORB NASDAQ-Short 05.11. **+144,07**, ORB-Longs 06.11.
  -21,98, CLS -18,97. OU eroeffnete drei Positionen (QCOM, SYY, OXY), alle noch offen (+2,42 offen).
- **Funded-Portfolio-Bridge (TTP + IQ): +1.389,25 USD (+0,71 %) bei 11 Trades.** Getragen vom
  **NASDAQ-ORB-Short 05.11. (TTP +1.527,84, IQ +1.949,30)**. Dagegen Gold ASB 03.11. (-1.171,86 auf beiden),
  CLS-Short 06.11. (-518,58) und die beiden ORB-Longs 06.11. (-411,41). OU: NEM von TTP per
  Modell-Abgleich geschlossen (+13,96), drei neue OU-Positionen nur auf TTP.
- **FK Instant Funding: +1.220,29 USD (+1,24 %) bei 5 Trades.** Gleiches Bild: NASDAQ-Short +1.908,51,
  sonst Gold ASB -101,80 (FK faehrt Gold klein), CLS -317,19, ORB-Longs -269,23.

**Muster der Woche:** **Ein Trade traegt alles.** Der NASDAQ-Short vom 05.11. bringt auf den drei
USD-Konten +5.386 USD; die uebrigen 13 USD-Trades zusammen -2.776 USD. Gold ASB verlor auf allen
vier Konten am selben Tag (Gold lief nach dem Short-Fill von 3.917 auf 3.968). Auf drei der vier
Konten wurde der NASDAQ-Gewinner **per Hand verkleinert**; das Konto ohne Eingriff (IQ) verdiente
damit am meisten.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto inkl. Kommission und
Swap. Eine Teilschliessung zaehlt nicht als eigener Trade. Die Prozentwerte beziehen sich auf den
Kontostand zu Wochenbeginn.

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 6 | 16,7 % | **-60,95 EUR** | **-2,17 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 11 | 27,3 % | **+1.389,25 USD** | **+0,71 %** |
| FK Instant Funding (LIVE, echtes Geld) | 5 | 20,0 % | **+1.220,29 USD** | **+1,24 %** |
| **Gesamt (alle 3, echtes Geld)** | **22** | **22,7 %** | **-60,95 EUR / +2.609,54 USD** | **ca. +0,85 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist EK mit 2.811,14 EUR
  (ca. 3.143 USD bei 1,118, dem EURUSD-Kurs der CLS-Fills am 06.11.) in ein Buch von ca. 297.400 USD
  eingerechnet.
- Je Konto: TTP 6 Trades **+629,17 USD (+0,64 %)**, IQ 5 Trades **+760,08 USD (+0,78 %)**.
- **Noch offen:** EK QCOM/SYY/OXY (OU); TTP STT (seit 16.10.), QCOM, SYY, OXY (OU). IQ und FK flach.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das IQ-Konto heisst
  "BeyondIQCapital **Demo** Challenge". Die Einordnung als "echtes Geld" uebernehme ich unveraendert
  aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 02.11. 00:00 bis 06.11. 21:00 (UTC) mit Sizing und
Kostenannahme der jeweiligen Bridge und der Konfiguration von HEUTE.

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 14 Trades / **-1,03 %** | -60,95 EUR (-2,21 %) | 1 (-1,09 R) | - | - (**13 nicht_ermittelbar, +12,35 R**) |
| Funded-Portfolio | 13 Trades / **+0,74 %** | +1.409,71 USD (+0,71 %) | 1 (-1,38 R) | 0 | 12 (+18,12 R) |
| FK Instant Funding | 14 Trades / **+1,82 %** | +1.234,94 USD (+1,24 %) | 1 (-1,24 R) | 1 (-0,32 R) | 12 (+18,12 R) |

(Die Ist-Werte liegen ca. 20 bzw. 15 USD ueber Abschnitt 4, weil das Werkzeug die
Einstiegskommissionen von Gold ASB und CLS nicht mitzaehlt; die Prozentbasis ist dort der heutige
Kontostand.)

**Hauptaussage: Auf Funded trifft Ist das Soll fast genau (+0,71 % gegen +0,74 %), auf FK fehlen
ca. 0,6 Prozentpunkte - aber die Uebereinstimmung ist teilweise Zufall.** Drei Effekte heben sich
gegenseitig auf: ein Gold-ASB-Verlust, den das Soll nicht kennt, ein verpasster ORB-Gewinner, und
die Handschliessung auf NASDAQ.

**Pflicht-Vorbehalte:**

1. **Konfiguration:** Soll rechnet mit dem heutigen Stand. In der Woche gab es keine Bot-Aenderung
   nach Mo 02.11. 20:49 (Ausfall-Ersatz aus, D1-Ableitung, GOLD_D1 neu). Vor dem ersten Handelstag
   relevant ist nur die neu geschriebene `GOLD_D1`-Reihe (siehe Gold ASB unten).
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "13 nicht_ermittelbar" heisst
   genau das, nicht "nie gesehen". Die EK-Ist-Seite hat dazu 108,17 EUR "unattributed": das ist die
   Handschliessung vom 05.11. (Magic 0).
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK (1,30) sind gemessen. EK-Zahlen
   deshalb nicht gegen die anderen beiden stellen.

**Was hinter den Posten steckt:**

- **ORB, "nie gesehen" ist hier ueberwiegend falsch etikettiert** (Werkzeugluecke seit KW41/KW44: ORB-Fills
  werden nicht zugeordnet). Aus den Logs je Tag:
  - **02.11. SP500 Long, Soll +5,96 R (Ziel): wirklich verpasst.** `breakout_passed (hoch=True)`: Der Kurs
    stand beim Platzierungs-Pass um 14:45 UTC schon ueber dem Trigger. Das ist das bekannte
    Erste-Bar-Problem (siehe Memory: `orb_first_bar_and_polled_exits`). Grob **ca. 600 USD je
    Funded-/FK-Konto** (Risiko je Seite TTP 99 USD, x 6 R), auf allen vier Konten. **Groesster Einzelposten
    der Woche.**
  - **02.11. NASDAQ, Soll -1,02 R:** platziert, beide Seiten vor dem Fill storniert ("Kurs erreichte den
    geplanten SL"). Gespart; das Soll kennt das Storno nicht.
  - **03.11. SP500 + NASDAQ (je ca. -1,0 R) und 04.11. SP500 (-1,02 R):** `breakout_passed`, also
    nicht platziert. Drei Verlierer gespart. Am 04.11. lehnte TTP vorher einmal mit `10015 Invalid price` ab.
  - **04.11. NASDAQ:** `filtered_out (Wednesday)`, im Soll gar nicht enthalten. Stimmig.
  - **05.11. NASDAQ Short, Soll +17,9 R (Sessionende):** platziert und gefuellt. Ist auf IQ (nicht angefasst)
    +1.949 USD, auf TTP/FK durch die Handschliessung weniger (Abschnitt 6, Punkt 1).
  - **06.11. SP500 + NASDAQ Long (je ca. -1,0 R):** platziert, beide ausgestoppt. Stimmig.
  - Netto: Durch `breakout_passed` fehlen dem Ist **+2,89 R** gegenueber dem Soll (+5,96 minus drei Verlierer).
- **`orb_us30` (3 Trades, +1,54 R) und `ctnl_continuation` (-1,16 R) zaehlen weiter im Soll**, obwohl US30 seit
  04.10. pausiert und CTNL-Continuation seit 01.10. stillgelegt ist (auf FK korrekt "nicht live"). Werkzeugfehler,
  bekannt aus KW44. Netto +0,38 R zu viel im Soll.
- **Gold ASB 03.11., Short: live auf allen vier Konten gelegt (-1.274 USD + -90 EUR), im Soll "kein Signal".**
  Nachgerechnet: Der Trade (Fill 3.917, SL 3.968) uebersteht ADX-, Trend-, Verzoegerungs- und Silber-Filter und
  faellt **erst im Liquiditaetsfilter** heraus, sowohl im Backtest- als auch im Live-Modus des Solls. Live liess
  derselbe Filter ihn durch. **Ursache offen.** Zwei Kandidaten: (a) `GOLD_D1` wurde am Vorabend (02.11.) neu aus
  Dukascopy geschrieben, live rechnete der Lauf um 07:00 evtl. noch mit einem anderen Stand; (b) das bekannte
  Kippen des expandierenden Quantils beim Nachrechnen (siehe Memory: `gold_asb_liquidity_filter_reproducibility`,
  `gold_asb_friktion_vorgriff`). Die Bridge-Logs enthalten den Friktionswert nicht, deshalb nicht entscheidbar.
  **Im Dashboard eingetragen.**
- **CLS 06.11. Short:** auf allen Konten platziert und wie im Soll ausgestoppt (-1,09 / -1,38 / -1,24 R). Stimmig.
- **Gold-Silber:** EK eroeffnete am 05.11., das Soll datiert das Signal auf 06.11. 00:00 (Datenende, -0,32 R).
  Auf FK (Bein seit 04.10. live) "nicht platziert" - kleiner Posten, nicht weiter geprueft.

## 5b. Edge-Warnstufen je Live-Bein

**Auch diese Woche NICHT frisch - zum dritten Mal in Folge.** `research_live_legs.py tickmill --ampel`
lief ueber eine Stunde bis ca. 21:05, kam mit Dukascopy-Abrufen bis zu einem Instrument bei **2024-09-19 22:15** und
stand dort ueber 10 Minuten still; das Zeitlimit hat den Lauf beendet (kein verwaister Prozess).
`live_trades_tickmill_ampel.csv` stammt damit weiter vom **27.10. 23:35, letzter Trade gesamt 25.10.**
`research_edge_monitor.py --stage status` lief sauber, rechnet aber auf dieser alten Liste. **KW44 und
KW45 sind in der Tabelle nicht enthalten**, und die am 02.11. umgestellte Gold-ASB-Normale
(Live-Wissensstand) wirkt erst mit einer neuen Liste.

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** | **23,2** / 15,2 | alle fuenf rot |
| orb_us30 | **ROT** (pausiert) | 24,5 / 13,2 | alle fuenf rot |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_silver | GELB | 1,7 / 4,9 | roll_mean streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | gruen | - | - |

- **orb_sp500 (ROT):** gegenueber KW44 unveraendert (gleiche Liste). Was die Liste nicht enthaelt: Laut Soll
  hatte SP500 in KW45 +5,96 R und drei Verlierer (netto ca. +2,9 R), das Loch waere danach grob 20-21 R statt
  23,2 R (meine Ueberschlagsrechnung, kein Monitor-Lauf). Entschieden ("ORB bleibt erstmal so", 16.10.),
  kein neuer Dashboard-Eintrag.
- **orb_us30 (ROT):** pausiert seit 04.10., unveraendert.
- **btc_ema_cross, gold_silver (GELB):** unveraendert, beobachten. gold_silver verlor live diese Woche
  -73,79 EUR auf EK (ca. -0,3 R im Soll); nicht in der Liste.
- **Werkzeug:** Dritter Ausfall nach 18.10. und 01.11., immer an einem Dukascopy-Abruf ohne Timeout. Der
  Dashboard-Punkt "Report-Werkzeuge haerten" besteht; solange der nicht erledigt ist, ist diese Tabelle
  wertlos fuer Wochenaussagen. Eine Warnung ist ein Grund hinzusehen, kein Grund, einen Bot zu aendern.

## 6. Auffaelligkeiten / offene Punkte

**(1) NASDAQ-ORB 05.11.: Teilschliessung per Handy auf drei von vier Konten.**
- Der Short (Fill 16:45 Serverzeit, ca. 27.570-27.581) wurde um **21:30-21:31 Serverzeit (ca. 20:30
  Berlin, 14:30 New York)** teilweise geschlossen, mit MT5 `reason = 1` (**Mobile**) und Magic 0:
  FK 1,5 von 2,2 Lot (21:30:06), EK 0,15 von 0,19 (21:30:59), TTP 1,2 von 1,77 (21:31:43). Also
  68-79 % je Konto, innerhalb von 97 Sekunden. IQ blieb unangetastet.
- Die Bot-Logs haben dazu keine Zeile, und NASDAQ faehrt laut Konfiguration seit 04.10. **ohne
  Teilausstieg** (siehe Memory: `ny_open_orb_strategy_state`). Den Rest schloss der Bot zur
  Sessionende-Regel um ca. 23:00-23:03 Serverzeit bei ca. 26.551-26.571.
- **Wirkung (meine Rechnung aus den Fill-Kursen):** Der Kurs fiel nach der Teilschliessung noch ca.
  200-230 Punkte. Ohne Eingriff waeren es grob **+276 USD (TTP), +320 USD (FK) und ca. +26 EUR (EK)
  mehr** gewesen, zusammen also ca. 600 USD. Das ist Rueckschau; in dem Moment war es eine
  Gewinnsicherung.
- **Kein Regelverstoss**, aber ein Eingriff in die Bot-Ausfuehrung, den Soll/Ist und Ampel nicht
  kennen. **Im Dashboard zur Bestaetigung eingetragen:** Warst du das, und ist das eine Regel
  (z. B. "um 14:30 NY Teilgewinn") oder ein Einzelfall? Und warum nicht auf IQ?

**(2) Cloud-Monitor: "Watchdog-Luecke ~96 h" ist ein Fehlalarm - der Push war blockiert.**
- Auf GitHub stehen fuenf Eskalationen des Cloud-Monitors (02.11. bis Fr 06.11. 21:13 UTC, zuletzt
  "~96h, fuenfte Eskalation vor dem Wochenende"). Lokal lief der Watchdog durchgehend im 30-Min-Takt,
  und alle Bridges handelten (EK: 816 bis 1.441 Laeufe pro Tag, keine Luecke ueber 30 Min.).
- **Ursache, aus dem Watchdog-Log woertlich:** "Snapshot-Merge uebersprungen: Working Tree hat 5-9
  offene Aenderung(en) ... Es wird NICHT gestasht". Ab 02.11. 22:31 **254-mal**. Der letzte Snapshot
  auf GitHub ist vom 02.11. 22:07. Lokal ist `main` **334 Commits voraus und 6 zurueck**.
- Der offene Working Tree ist die uncommittete Session-Arbeit vom 02.11. (Daily-Edge, Filter, Locks,
  Dashboard/CHANGELOG) plus Logdateien. **Derselbe Mechanismus wie der Push-Stau 02.10.-31.10.**
  (CHANGELOG 31.10.). Die Dashboard-Frage vom 02.11. ("Kannst du nachschauen, ob der Rechner lief?")
  ist damit beantwortet: **Ja, er lief.** Im Dashboard ergaenzt.
- Dieser Report pusht nicht (Vorgabe). Loesen wuerde es ein Commit der offenen Arbeit, danach der
  naechste Watchdog-Lauf.

**(3) Offene Session-Arbeit + Handoff seit 02.11.** Die Handoff-Datei
`_handoff/2026-11-02_2330_daily-edge-schichtenmodell.md` wurde nicht abgeholt; die Arbeit seit 18.10.
(`htf_daily_trade/`, `fusion_lab/filters/`, Locks) ist nicht committet. Nur ein Hinweis: Seit dem
Stash-Fix (23.09.) ist sie nicht mehr akut gefaehrdet, aber ohne Commit auch nicht gesichert.

**(4) Neustart Mo 02:01 -> EK-Fast-Lane 24 h doppelt.** Nach dem unerwarteten Neustart
(`Kernel-Power 41`, `EventLog 6008`; Ursache nicht ermittelt) liefen **zwei FAST-Ketten parallel**
(Sekunde :12 und :46), bis Di 02:05 die nachgeholte Kette ablief (Wiederholungsdauer 23 h 58 min).
Das erklaert 1.441 statt 816 Laeufe am Montag. Am Montag gab es auf EK keine Order, also keinen
sichtbaren Doppel-Effekt. Ob die Fast-Lane zwei gleichzeitige Laeufe gegen Doppel-Orders absichert,
habe ich nicht geprueft. **Nur beobachten**; wiederholt sich
das bei jedem Neustart, lohnt ein Lauf-Lock auch fuer die EK-Fast-Lane (wie bei Funded).

**(5) TTP-OU: STT ist seit 23 Tagen Waise.** Taeglich "Titel fehlt im aktuellen Scan -- NICHT automatisch
geschlossen" (16.10. eroeffnet, aktuell +1,36 USD, SL 123,69). EK hatte dieselbe Aktie am 27.10. per
`max_hold` geschlossen. NEM (KW44 als Kandidat genannt) ist erledigt: am 05.11. per Modell-Abgleich
geschlossen. **STT braucht eine Entscheidung** (schliessen oder bewusst laufen lassen); steht in
KW43/KW44 schon, keine neue Info ausser der Dauer. Dazu ein harmloser Nebenbefund: IQ meldet
"ou_modell (NEM) ... verpasst", obwohl IQ kein OU handelt (Log-Rauschen).

**(6) Kleineres.**
- `Makro-Daten`-Task: letzter Lauf So 08.11. 07:32 mit Ergebnis `0x41306` (vom Scheduler beendet).
  Nicht naeher geprueft, kein Order-Bezug.
- FK warnt weiter in jedem Lauf "Kontostand weicht von STARTING_EQUITY=100.000 ab" (bekannt).
- Telegram-Bot-Token steht weiter im Klartext in den Bridge-Logs (DNS-Fehler am 02.11.). Nur lokal.
- Dieser Report committet bewusst nur `knowledge/reports/`. Dashboard-/Changelog-Ergaenzungen
  bleiben im Working Tree, zusammen mit der Session-Arbeit vom 02.11.
