# Weekly Checkup - Performance - KW41/2026

**Abgedeckte Woche: Mo 2026-10-05 bis So 2026-10-11.** Erzeugt am Mo
2026-10-12 gegen 02:00 durch den geplanten `Forex-Weekly-Report`-Task,
**verspaetet**: Der Rechner ging am So 11.10. um 11:34 in den Standby und
wurde danach unerwartet beendet (`Kernel-Power 41` + `EventLog 6008` beim
Neustart Mo 01:42). Der Sonntagslauf um 18:00 fiel deshalb aus.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W41.json`
(Fenster 05.10. 00:00 bis 12.10. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W41.json`, die Logs der drei Portfolio-Bridges,
deren `bridge_state*.json`, das Windows-Ereignisprotokoll und der CHANGELOG
der Woche.

> **Zum Abzug:** Alle vier MT5-Terminals starteten nach dem Neustart um
> 01:44, also kurz vor dem Abzug. Das ist genau die Situation aus Memory
> `mt5_kaltes_terminal_leere_historie` (kaltes Terminal liefert leere
> Historie). Diesmal lieferte aber jedes Konto Deals (EK 26, TTP 13, IQ 7,
> FK 11), und die Kontostaende zu Wochenbeginn passen auf den Cent zu den
> Endstaenden aus KW40 (IQ 96.898, FK 98.725). Der Abzug ist damit
> belastbar. Die Terminals gehoeren zu den laufenden Bridges und wurden
> bewusst **nicht** geschlossen.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche mit echtem Geld
(`DRY_RUN = False`): **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets 16054) und
**FK Instant Funding** (BeyondIQCapital 17764). Alle sechs Bridge-Tasks
(jeweils Slow und Fast) stehen im Task Scheduler auf `Bereit` bzw. `Wird
ausgefuehrt`. Die Einzel-Bots (Gold ASB, CLS, CTNL, OU, BTC-EMA) bleiben
`Deaktiviert`. Keine Handeingriffe: kein Deal mit `reason` 0/1/2.

**Zum ersten Mal seit Wochen gab es keine einzige Konfigurationsaenderung an
den Bridges.** Seit dem 04.10. ist keine `.py`- oder `config`-Datei in den drei
Bridge-Ordnern geaendert worden (nur die State-Dateien), und der CHANGELOG
der Woche enthaelt nur Research und das Dachprojekt. Zwei Entscheidungen
betreffen den Live-Betrieb trotzdem:

- **06.10.: ORB live bleibt, wie es war** (Nutzerentscheid, kein Pausieren,
  keine Risikosenkung), obwohl die IS-only-Neuoptimierung im Tresor
  durchfiel.
- **07.10.: Forward-Test registriert:** ORB live mit/ohne Gamma-Regler, je
  100k ab 05.10., Auswertung fruehestens 31.12.2026. Keine Bot-Aenderung.

**Montag war der Tag der Erstlaeufe** aus dem Wochenende 03./04.10. Was davon
diese Woche sichtbar wurde (Details in Abschnitt 6, Punkt 4):

| Erstlauf | Ergebnis |
|---|---|
| Gold ASB als Stop-Order | laeuft: Mo/Di platziert und um 03:00 NY storniert, Mi-Fr vom Liquiditaetsfilter verworfen. Kein Fill. |
| ORB-Storno-Regeln | greifen: viermal storniert, davon zwei ganze Tage ohne Trade |
| US30-Pause | greift: in jedem Lauf `US30=paused` |
| TTP-Gewichte | greifen: Gold ASB 595 $, OU ca. 49,6 $ Risiko |
| CTNL-Exit-Standard (Broker-TP 5R) | auf Funded/FK **nicht pruefbar**: alle neuen Entries wurden ausgestoppt, bevor ein TP zaehlen konnte |

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Kill-Switch ausgeloest, kein Drawdown-Halt.**

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgeloest (0 Logzeilen) |
| EK-Portfolio | Gold-ASB-Risiko je Order | 51,58 / 64,50 EUR = **1,9-2,3 % des Kontos** bei 0,01 Lot. Bekannte Mindestlot-Verzerrung (Memory `ek_mindestlot_kehrt_hierarchie_um`), keine neue Verletzung |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag 09.10. -114 USD (ORB) |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag **09.10. -423,78 USD (-0,44 %)**, drei CTNL-Stops. Balance 96.606 USD = -3,4 % seit Start, ca. **2.600 USD Abstand** zur 6-%-Grenze |
| Funded (beide) | CTNL-Kill-Switch | nie ausgeloest |
| Funded / IQ | CTNL-Positionsdeckel 2 | greift (3x `Grenze` im Log) |
| Funded / TTP | CTNL-Positionsdeckel 2 | **haelt 3 alte Positionen**, siehe unten |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; Balance 98.442 USD (-1,56 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch / Deckel 2 | Kill-Switch nie ausgeloest; Deckel greift (3x) |

**Zur Kenntnis, keine Verletzung:** TTP haelt weiter **drei**
`ctnl_reversal`-Shorts (18.09. sowie zwei vom 30.09.) bei Deckel 2. Der Deckel
sperrt nur neue Entries. Deshalb hat TTP diese Woche **keinen einzigen**
CTNL-Trade genommen, waehrend IQ und FK je drei Shorts verloren (zusammen
-511 USD). Zufaellig hat das TTP diese Woche Geld gespart. Warum die beiden
30.09.-Positionen nach acht Handelstagen ueberhaupt noch offen sind, steht in
Abschnitt 6, Punkt 1.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): +13,30 EUR (+0,48 %) bei 16 Trades.**
  Die erste Plus-Woche seit fuenf Wochen, getragen von einem einzigen Trade:
  Der CTNL-Short vom 02.10. erreichte am 07.10. sein Broker-TP (+109,30 EUR).
  Dagegen standen drei neue CTNL-Shorts am 08./09.10. (alle ausgestoppt,
  -66,68 EUR), zwei ORB-NASDAQ-Stops (-22,87 EUR) und die OU-Schliessungen
  (9 Trades, zusammen -6,45 EUR). Gold ASB hat auf EK nicht gefuellt.
- **Funded-Portfolio-Bridge (TTP + IQ): -470,05 USD (-0,24 %) bei 10
  Trades.** TTP -178,31 (zwei ORB-NASDAQ-Stops -231, vier OU-Gewinner +53),
  IQ -291,74. IQ verlor mit drei CTNL-Shorts am 08./09.10. -423,78 USD;
  ausgeglichen teilweise durch den Zeit-Exit eines alten Shorts vom 02.10.
  (+132,04). Gold ASB lieferte zwei Stop-Orders, keine fuellte.
- **FK Instant Funding: -283,04 USD (-0,29 %) bei 6 Trades.** Zwei
  ORB-NASDAQ-Stops (-261,09) machen fast den ganzen Verlust aus; die drei
  CTNL-Shorts kosteten wegen kleiner Positionsgroesse nur -87,75, der Zeit-Exit
  des alten Shorts brachte +65,80.

**Muster der Woche:** Eine ruhige Woche mit wenig Handel (32 Trades gegen 75
in KW40). Gold stieg am 08./09.10. von ca. 4.100 auf 4.196, und
`ctnl_reversal` shortete auf allen Konten mit freiem Platz in diesen Anstieg:
**9 von 9 neuen CTNL-Shorts ausgestoppt.** ORB NASDAQ: 6 von 6 gefuellten
Trades ausgestoppt, je 1-22 Minuten nach dem Fill. Die Storno-Regeln
verhinderten an zwei weiteren Tagen den Einstieg.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto
inkl. Kommission und Swap. Die Prozentwerte beziehen sich auf den
Kontostand zu Wochenbeginn (heutige Balance minus Wochen-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 16 | 43,8 % | **+13,30 EUR** | **+0,48 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 10 | 50,0 % | **-470,05 USD** | **-0,24 %** |
| FK Instant Funding (LIVE, echtes Geld) | 6 | 16,7 % | **-283,04 USD** | **-0,29 %** |
| **Gesamt (alle 3, echtes Geld)** | **32** | **40,6 %** | **+13,30 EUR / -753,09 USD** | **ca. -0,25 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist EK
  mit ca. 2.780 EUR (ca. 3.250 USD bei 1,17) in ein Buch von ca. 297.500 USD
  eingerechnet.
- **Die Winrate taeuscht.** Die Gewinner sind fast nur kleine OU-Schliessungen
  (je +1 bis +30 USD) und zwei Zeit-Exits alter CTNL-Shorts. Neue ORB- und
  CTNL-Trades gewannen diese Woche **0 von 15**.
- **Unrealisiert zum Wochenschluss** (nicht in der Tabelle): EK +2,23 EUR,
  TTP +529,16 USD (davon +381 aus dem CTNL-Short vom 18.09.), IQ -3,96, FK
  -1,83.
- EK hat eine Balance-Buchung von +0,31 EUR (07.10. 01:16, Kommentar
  `B8GHJTU5S8XYTT54`), wie schon in KW40 eine aehnliche Kleinbuchung. Kein
  Trade, nicht in der Zahl. Was der Broker da bucht, ist weiter nicht
  geprueft.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das IQ-Konto
  heisst "BeyondIQCapital **Demo** Challenge". Die Einordnung als "echtes
  Geld" uebernehme ich unveraendert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 05.10. 00:00 bis 09.10. 21:00,
gerechnet mit Sizing und Kostenannahme der jeweiligen Bridge und der
Konfiguration von HEUTE. **Diese Woche ist das ausnahmsweise kein Vorbehalt:**
Zwischen dem 04.10. und heute gab es keine Konfigurationsaenderung (siehe
Abschnitt 1). Es ist die erste saubere Soll/Ist-Woche seit Einfuehrung.

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 12 Trades / **-0,32 %** | +13,30 EUR (+0,48 %) | - | - | - (**12 nicht_ermittelbar, -10,87 R**) |
| Funded-Portfolio | 16 Trades / **-0,35 %** | -468,85 USD (-0,24 %) | 6 (-0,73 R) | 3 (-3,43 R) | 7 (-5,24 R) |
| FK Instant Funding | 11 Trades / **-0,82 %** | -282,79 USD (-0,29 %) | 1 (-1,08 R) | 3 (-3,43 R) | 7 (-5,24 R) |

**Ist liegt auf allen drei Bridges ueber Soll.** Das ist die Hauptaussage der
Woche, und sie ist erklaerbar: Fast jede Luecke ist eine Schutzregel, die
einen Soll-Verlierer abgefangen hat.

**Pflicht-Vorbehalte:**

1. **Konfiguration:** diesmal unveraendert, siehe oben. Aber zwei Regeln, die
   live gelten, kennt das Soll offenbar **nicht** (siehe Zerlegung).
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "12
   nicht_ermittelbar" heisst genau das, nicht "nie gesehen". EKs Ist-Plus
   stammt aus dem TP eines Trades vom 02.10., der im Soll-Fenster gar nicht
   vorkommt.
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Was die Zerlegung zeigt (Funded/FK):**

- **`orb_us30` (3 Soll-Trades, -1,11 R) steht als "nie gesehen", ist aber
  pausiert.** US30 ist live seit 04.10. pausiert, im Log steht in jedem Lauf
  `US30=paused`. **Das Soll rechnet die Pause nicht mit.** Das ist eine Luecke
  im Werkzeug `soll_ist.py`, kein Ausfuehrungsfehler.
- **`orb_nasdaq`: 4 Soll-Trades "nie gesehen", davon 2 ein bekannter
  Zuordnungsfehler, 2 von der Storno-Regel verhindert.**
  - **05.10. und 09.10.:** live gefuellt (13:48 UTC) und ausgestoppt. Das Soll
    setzt den Einstieg auf 13:45 (Bar-Beginn). Die Zuordnung erkennt
    Pending-Order-Fills weiter nicht (bekannt seit KW39/40).
  - **06.10. und 08.10.:** Live stornierte die Bridge **beide Seiten** um
    13:48 UTC mit "Kurs erreichte den geplanten SL vor dem Einstieg (wie im
    Backtest)". Das Soll handelt an beiden Tagen trotzdem (06.10. long 14:05,
    08.10. short 13:50) und verliert je ca. -1,03 R.
  - **Nicht geklaert:** Entweder kennt der Soll-Backtest die NASDAQ-Storno-Regel
    vom 03.10. nicht, oder Live und Backtest legen den "geplanten SL"
    verschieden. Die Logzeile behauptet "wie im Backtest"; diese Woche zeigt
    das Gegenteil. Geldwert: Die Storno-Regel hat live **ca. 2 R gespart**.
- **`ctnl_reversal`: die 3 "nicht platziert" (-3,43 R) sind Schutzregeln.**
  06.10. 12:30: "Signal zu alt (73 Min., Grenze 60)". 08.10. 16:45 und 09.10.
  01:30: "Kurs bereits 0,55-0,82 R gegen das Signal gelaufen (Grenze 0,50 R)".
  Alle drei waren Soll-Verlierer. Die Regeln haben also gespart, nicht
  gekostet.
- **Die platzierten CTNL-Shorts verloren wie im Soll.** IQ und FK nahmen die
  Signale je eine M15-Bar spaeter ("Signal wieder angenommen"); das Ergebnis
  war dasselbe: ausgestoppt.
- **`ou_modell` (Funded): 5 Soll-Trades "platziert".** Darunter steht **DE
  09.10.** als platziert, obwohl der TTP-Entry im Log scheiterte
  ("Lot-Groesse 0,0 unter volume_min 1,0", siehe Abschnitt 6, Punkt 3). Die
  Zuordnung ist hier also zu grosszuegig. Der Geldwert ist klein (OU-Soll
  r = 0,0).

## 6. Auffaelligkeiten / offene Punkte

**(1) CTNL-State: Zwei Sorten verwaister Eintraege. Das ist der wichtigste
Befund der Woche.**
- **(a) Offene Positionen ohne Zeit-Exit.** Laut Exit-Standard schliesst
  `ctnl_reversal` nach 4 Handelstagen (`max_hold`). Am 08.10. um 19:13 Berlin
  schloss die Bridge auf IQ und FK je **einen** der beiden Shorts vom 02.10.
  mit `max_hold` (Signal 12:45). Der **zweite** (Signal 13:00, 15 Minuten
  spaeter: IQ Ticket 1973249, FK 1973231) ist heute, 6 Handelstage spaeter,
  noch offen, ohne TP. Auf TTP sind die beiden Shorts vom **30.09.** (18696522,
  18696950) nach 8 Handelstagen ebenfalls noch offen, auch ohne TP. Im State
  stehen alle vier als `placed`, sie werden also verfolgt, aber nicht
  geschlossen.
- **(b) Ausgestoppte Positionen bleiben `placed`.** Im FK-State stehen die
  **sieben** Shorts vom 01.10. weiter als `placed`, obwohl alle am 01.10.
  ausgestoppt wurden (KW40). Auf IQ und FK stehen zudem die Shorts von 08.10.
  17:00 und 09.10. 01:45 als `placed`, obwohl der Broker sie am 09.10.
  ausstoppte. Der Eintrag vom 09.10. 00:30 steht dagegen korrekt als
  `closed`. Am 04.10. wurden 104 solcher Eintraege von Hand bereinigt (KW40);
  sie wachsen also wieder nach.
- **Hypothese, nicht verifiziert:** Der Zeit-Exit haengt am Signal-Schluessel
  der Simulation. Seit dem 03.10. steigen Funded und FK eine M15-Bar frueher
  ein. Damit koennte sich der Schluessel alter Signale um 15 Minuten
  verschoben haben: Der 12:45-Eintrag fand ein passendes Sim-Signal und
  bekam seinen `max_hold`, der 13:00-Eintrag nicht mehr. Das passt zu IQ/FK.
  Fuer die TTP-Positionen vom 30.09. erklaert es nicht alles. Verwandtes
  Muster: Memory `ctnl_sim_filter_is_not_live_gate`.
- **Folgen:** Das Risiko ist begrenzt, weil jede dieser Positionen einen
  Broker-SL hat. Aber sie laufen ohne Ende, und auf TTP blockieren sie den
  CTNL-Deckel (3 offen bei Grenze 2). Damit nimmt TTP gar keine neuen
  CTNL-Signale mehr, solange diese drei offen sind.
- **Offen:** Dazu gehoert eine Entscheidung (alte Positionen von Hand oder per
  Skript schliessen? Exit-Abgleich gegen Broker-Positionen statt
  Sim-Schluessel?). Das geht um echtes Geld, deshalb nur gemeldet, nichts
  angefasst. Eingetragen im Dashboard unter "Braucht deine Bestaetigung".

**(2) Soll/Ist-Werkzeug: zwei neue Luecken.** `soll_ist.py` rechnet die
US30-Pause nicht mit und handelt NASDAQ an Tagen, an denen die Bridge laut
eigener Storno-Regel ("wie im Backtest") beide Orders storniert. Zusammen mit
der seit KW39 bekannten Pending-Order-Zuordnung steht damit das ganze
ORB-"nie gesehen" der Woche (7 Trades) auf Werkzeugfehlern, nicht auf
Ausfuehrungsfehlern. Solange das so ist, ist "nie gesehen" fuer ORB nicht
lesbar.

**(3) TTP: OU-Entries scheitern am Mindestlot.** Seit der neuen TTP-Gewichtung
(04.10.) riskiert OU je Trade ca. 49,6 USD. Bei teuren Aktien mit weitem Stop
reicht das nicht fuer 1 Stueck: GRMN (08.10., Verlust je Stueck 63 USD) und DE
(08.10. und 09.10., 122-129 USD) wurden mit "Lot-Groesse 0,0 unter
volume_min" verworfen. Das ist die Mindestlot-Logik aus Memory
`ek_mindestlot_noetige_kontogroesse`, jetzt auch auf TTP. Ob das bei der
Gewichtung bedacht war, weiss ich nicht. Bisher geht es um 3 Signale in einer
Woche.

**(4) Erstlaeufe vom Montag: was belegt ist und was nicht.**
- **Gold ASB als Stop-Order:** belegt. Mo und Di wurde um 07:00 Berlin
  platziert (TTP 595,57 $, IQ 647,70 $, FK 119,81 $, EK 51,58 EUR) und um
  09:00/09:03 Berlin = 03:00 NY ohne Fill storniert. Mi bis Fr: "filtered_out
  (Liquiditaet: Friktion 0,024-0,038 > Schwelle 0,018)". Drei von fuenf Tagen
  verworfen ist viel, aber ohne Vergleichswert kein Befund. Ein Fill mit
  Zeit-Exit 11:00 NY ist noch nicht vorgekommen.
- **ORB-Storno:** belegt, viermal (Mo Short-Seite, Di beide, Do beide, Fr
  Long-Seite).
- **US30-Pause und TTP-Gewichte:** belegt.
- **CTNL Broker-TP 5R auf Funded/FK:** nicht pruefbar. Alle Entries nach dem
  03.10. wurden ausgestoppt, und der State speichert kein TP-Feld. Die
  Altpositionen haben `tp = 0`. Auf **EK** ist der TP belegt (TP-Treffer
  07.10.).
- Die Dashboard-Punkte dazu bleiben offen; das Abhaken liegt bei dir.

**(5) Standby mitten in der Handelswoche, zweimal.**
- **Do 08.10., 10:22-14:14 Berlin** (`Kernel-Power 506/507`): In den
  Bridge-Logs fehlen die Laeufe von 10:33 bis 14:15 (222 Minuten), der
  Watchdog schwieg ebenfalls (Snapshot 10:31, dann 14:15). Geldwert: keiner.
  In dem Fenster lag kein Soll-Trade, Gold ASB (07:00) und ORB (15:30) lagen
  ausserhalb.
- **Mi 07.10.:** drei kurze Standbys (10:12-10:17, 10:56-11:47,
  11:48-11:51). Danach gab es die einzigen Datenpfad-Fehler der Woche: 8x
  Ribbon-`TypeError` (str/float) im Funded-Fast-Log um 10:34-10:39 und ein
  `dukascopy_python`-Haenger, der auf EK um 11:14 `cls_practical` abbrach.
- **So 11.10.:** Standby ab 11:34, danach unerwartetes Ende, Neustart erst Mo
  01:42. Am Wochenende ohne Handelsfolge, aber deshalb lief dieser Report
  verspaetet. Es ist das zweite unerwartete Herunterfahren in drei Wochen
  (zuletzt 28.09.).
- Das Muster aus KW40 bestaetigt sich: Die Standbys fallen auf Zeiten, in
  denen am Rechner gearbeitet wurde (Mi-Vormittag Research-Commits, So
  Vormittag), was auf zugeklappten Deckel oder Akku hindeutet. Belegt ist das
  nicht (Memory `standby_watchdog_schlaeft_mit`).

**(6) Datenpfad: deutlich ruhiger.** Ausserhalb der Aufwachmomente gab es
keine `str`/`float`-Zeile mehr (KW40: 47x, 11x, 20x an drei Tagen). Haenger
`dukascopy_python`: Funded 10, FK 3, EK 2. `LakeStaleDataError`-Fallbacks
weiter in den Hunderten (Funded 363). Ein Einzelfehler: 09.10. 10:18 lief die
Terminal-Pruefung fuer IQ (`Get-Process`) in einen 20-s-Timeout, ohne
erkennbare Folge.

**(7) FK-Warnung "Kontostand weicht von STARTING_EQUITY=100.000 ab"** kommt
weiter in jedem Lauf. Bekannt aus den Vorwochen, Floor-Pruefung weiter offen.

**(8) Viel Research-Arbeit liegt ungesichert im Working Tree.** Die
Ergebnisse vom 07.-11.10. (SMH-Mikrostruktur, Zarattini, Oel-Gegenprobe,
G8, `fusion_lab/g8/`, `fusion_lab/macro_reports/`, `noise_area_momentum/`, 14
Research-Lock-Dateien) sind nicht committet. Der CHANGELOG nennt sie, Git hat
sie nicht. Memory `git_sync_stash_frisst_sessionarbeit` zeigt, wie so etwas
verloren gehen kann. Dieser Report committet bewusst nur
`knowledge/reports/`.
