# Weekly Checkup - Performance - KW40/2026

**Abgedeckte Woche: Mo 2026-09-28 bis So 2026-10-04.** Erzeugt am So
2026-10-04 durch den geplanten `Forex-Weekly-Report`-Task, diesmal
puenktlich am Sonntag.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W40.json`
(Fenster 28.09. 00:00 bis 05.10. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W40.json`, die Logs der drei Portfolio-Bridges
(`logs/task_run*.log`) und der CHANGELOG der Woche.

> **Der Abzug ist diesmal belastbar.** Alle fuenf MT5-Terminals liefen schon
> vor dem Abzug. Es wurde also kein Terminal kalt gestartet (siehe Memory:
> `mt5_kaltes_terminal_leere_historie`), und es blieb auch kein neues Fenster
> offen. Jedes Konto lieferte Deals (EK 41, TTP 37, IQ 42, FK 34). Die
> Entry-Zeitpunkte decken sich mit den `ENTRY ... placed`-Zeilen in den
> Bridge-Logs.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche mit echtem Geld
(`DRY_RUN = False`): **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets 16054) und
**FK Instant Funding** (BeyondIQCapital 17764). Alle sechs Bridge-Tasks
(jeweils Slow und Fast) stehen im Task Scheduler auf `Bereit`. Keine Bridge
wurde gestartet oder gestoppt, und kein `DRY_RUN`-Flag hat sich geaendert.
**Diese Woche gab es keinen einzigen Handeingriff**: Kein Deal hat
`reason` 0/1/2 (Desktop/Mobil/Web). Das ist ein deutlicher Unterschied zu
KW39 mit 25 Handschliessungen auf TTP und zwei Hand-Eroeffnungen auf FK.

**Die Konfigurationsaenderungen fallen in zwei Gruppen.** Fuer das Lesen von
Abschnitt 5 ist das entscheidend.

**A. Waehrend der Handelswoche, mit Wirkung auf die Zahlen unten:**

- **Mi 30.09., 21:31-22:58 Berlin, CTNL-Paket auf allen drei Bridges:**
  - **Ribbon-Richtungsgate scharf**: long nur im Aufwaertstrend, short nur im
    Abwaertstrend.
  - **Spike-Filter**: Die Signalkerze muss mindestens 0,75 ATR gross sein.
  - **`ctnl_continuation` stillgelegt.**
  - **CTNL-Kill-Switch jetzt auch auf Funded und EK.** Er loeste dort sofort
    aus (-7,01 %). Um 22:53 wurde er auf den gehandelten Satz (Ribbon + Spike)
    umgestellt, der Wert lag dann bei -1,10 %, und der Schalter hob sich auf.
  - **FK: `ctnl_reversal` laeuft auf der 5-Minuten-Lane.**
  - **EK: Fix fuer die OU-Wiedereinstiegs-Drehtuer.**
- **Do 01.10., 12:46: CTNL-Positionsdeckel von 3 auf 2** (Funded, FK). EK
  bleibt bei 1. Laut Log greift er ab 12:xx (`Grenze 2`).

**B. Am Wochenende, ohne Wirkung auf diese Woche** (erster echter Lauf ist
Mo 05.10.):

- **Gold ASB als ruhende Stop-Order**, Stop 1,5x Range, Storno 03:00 NY
  (03.10.).
- **CTNL Reversal:**
  - Einheitlicher Exit-Standard: Broker-TP 5R, auf EK ausserdem Signal-SL
    und Zeit-Exit nach 4 Handelstagen.
  - Funded und FK steigen eine M15-Bar frueher ein (03.10.).
- **ORB:**
  - SP500/US30 stornieren die Long-Order, wenn der Kurs zuerst nach unten
    ausbricht (03.10.).
  - NASDAQ storniert am geplanten SL und hat kein Teilziel mehr.
  - **US30 ist pausiert** (04.10.).
- **TTP: neue Gewichtung** ueber das kontoeigene `leg_risk_pct` (04.10.).
  IQ und EK bleiben unveraendert.
- **Tick-Rundung zentral** in `_send_order()` (Funded, FK).
- **104 verwaiste `ctnl_reversal`-Eintraege** im Funded-State auf `closed`
  gesetzt.

Fast alle Bridge-Aenderungen liegen ausserhalb von Git. Es gibt sie nur als
Dateien plus `_backup_*`-Ordner (siehe Memory:
`external_bridge_files_no_git_safety_net`).

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Konto-Drawdown-Halt, kein Trailing-Bruch.**
Ausgeloest hat nur der CTNL-Strategie-Kill-Switch, auf zwei Bridges mit sehr
unterschiedlicher Dauer.

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest |
| EK-Portfolio | Gesamtrisiko-Deckel 30 % | eingehalten: offenes Risiko 238 EUR bei einem Deckel von 852 EUR (Fr 22:59) |
| EK-Portfolio | `ctnl_reversal` max. 1 gleichzeitig | **greift**: durchgehend `max_concurrent_reached`, nie mehr als 1 Position |
| EK-Portfolio | CTNL-Kill-Switch (seit 30.09. verdrahtet) | nie ausgeloest; Verdrahtung per grep belegt (5 Treffer) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag 30.09. -291,02 USD (-0,29 %) |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag 30.09. **-781,64 USD (-0,80 %)**; Balance 96.898 USD, also -3,1 % seit Start, ca. 2.900 USD Abstand zur 6-%-Grenze |
| Funded (beide) | CTNL-Kill-Switch | **ausgeloest 30.09. 21:58** (-7,01 %), **aufgehoben 22:53** (-1,10 % nach der Umstellung auf den gehandelten Satz); ca. 55 Min. am Abend, kein Signal verpasst |
| Funded (beide) | CTNL-Positionsdeckel 3 -> 2 | greift: 185x `Grenze 3` und ab 01.10. mittags `Grenze 2` im Log |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; Balance 98.725 USD (-1,27 % seit Start) |
| **FK Instant Funding** | **CTNL-Kill-Switch** | **gesperrt von 28.09. 17:43 bis 30.09. 22:53** (-7,59 %), mit zwei kurzen Flacker-Fenstern am 29.09. (siehe unten) |

**Der FK-Kill-Switch hat ein Flackern gezeigt, das inzwischen behoben ist.**
Das Log zeigt am 28.09. um 02:37 "erholt (-2,88 %)". Um 17:43 desselben Tages
sperrte er wieder mit -7,59 %. Am 29.09. folgten 22:10 "erholt (0,00 %)",
22:24 Sperre, 22:35 "erholt (0,00 %)" und 22:40 Sperre. Die "0,00 %" stammen
von einem leeren Scan (Datenluecke), der als Erholung gelesen wurde. Genau
diesen Fall behebt der Flacker-Fix vom 30.09. (CHANGELOG, Punkt 3). In den
beiden Fenstern hat FK **keinen** CTNL-Entry genommen; der Fehler hatte
diesmal also keine Folgen.

**Die Asymmetrie aus KW39 zeigt sich ein letztes Mal, jetzt ist sie
geschlossen.** Am 29. und 30.09. sperrte der Kill-Switch auf FK, waehrend
Funded und EK noch ohne Schalter liefen. Dieselben Gold-Shorts kosteten IQ
**11 Trades / 0 Gewinner / -1.312,47 USD**, TTP **6 / 0 / -337,31 USD** und
EK **3 / 0 / -55,49 EUR**. FK hatte in diesem Zeitraum 0 CTNL-Trades. Seit
30.09. 21:58 haben alle drei Bridges den Schalter (Memory:
`ctnl_kill_switch_nur_auf_fk`, grep-Stand heute 6 / 2 / 5). **Allerdings:**
Mit der neuen Messung auf dem gehandelten Satz (-1,10 %) haette er die Serie
vom 29./30.09. auch auf Funded **nicht** gestoppt. Der Schalter hebt sich ja
gerade auf, sobald nur der gefilterte Satz zaehlt. Wie viel Schutz der
umgestellte Schalter kuenftig bietet, haengt an der neuen Schwelle. Deren
Kalibrierung steht noch aus (Dashboard, Offene Aufgaben).

**Nicht verletzt, aber zur Kenntnis:** TTP haelt zum Wochenende **3**
`ctnl_reversal`-Positionen (vom 18.09. und zwei vom 30.09.), obwohl der
Deckel seit Do bei 2 steht. Das ist korrekt so: Der Deckel sperrt nur neue
Entries, bestehende laufen weiter.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): praktisch flach, -15,65 EUR (-0,56 %)
  bei 21 Trades.** Nach vier Verlustwochen in Folge ist das die kleinste
  Bewegung seit Wochen.
  - **Gewinn:** Gold ASB brachte am 28.09. +117,97 EUR (Short mit
    Zeit-Exit).
  - **Verluste:**
    - ORB: 8 Trades, alle ausgestoppt, -56,49 EUR.
    - CTNL: 3 Shorts vor dem Gate, -55,49 EUR. Der vierte Short vom 02.10.
      ist offen und liegt bei +70,99 EUR.
    - OU: 6 `maxhold`-Schliessungen, zusammen -22,86 EUR.
  - **Drehtuer:** Die drei AIG-Runden vom 29.09. (+1,22 EUR) sind genau
    die Drehtuer, die am 30.09. geschlossen wurde. Danach gab es auf EK
    hoechstens einen OU-Einstieg je Titel und Tag.
- **Funded-Portfolio-Bridge (TTP + IQ): -1.424,11 USD (-0,72 %) bei 38
  Trades und nur 3 Gewinnern.** Die Konten liefen diesmal gleich
  (TTP -309, IQ -1.115); der Unterschied ist nur Groesse.
  - **Gewinner:**
    - Gold ASB am 28.09.: TTP +371,77, IQ +816,79.
    - Ein alter TTP-CTNL-Short vom 18.09. schloss am 28.09. am TP:
      +123,78.
  - **Verlierer:**
    - CTNL-Shorts am 29./30.09.: IQ -1.312, TTP -337. IQ nahm bei Deckel 3
      zweimal drei Shorts im 15-Minuten-Abstand.
    - **ORB komplett negativ:** 16 Trades auf beiden Konten, 0 Gewinner,
      -943 USD. Jeder Stop fiel 2-7 Minuten nach dem Fill.
  - **Offen:** Die neu genommenen Gold-Shorts liegen im Plus
    (TTP 2x +117, IQ 2x +224).
- **FK Instant Funding: -840,44 USD (-0,84 %) bei 16 Trades und 1 Gewinner.**
  - **ORB:** 8 Trades, -717,09 USD. FK riskiert dort am meisten je Trade.
  - **CTNL:** Nach dem Ende der Sperre nahm FK am 01.10. frueh **7 Shorts
    hintereinander**, alle ausgestoppt, -245,55 USD. Diese Signale waren
    ribbon- und spike-konform. Funded nahm sie nicht, weil dort der Korb
    voll war (3 offene). Hier traf der Kill-Switch-gesperrte Teil der Woche
    auf den ersten ungesperrten Tag, und der Deckel (damals noch 3) hat FK
    nicht vor einer Serie bewahrt, weil die Trades nacheinander statt
    gleichzeitig kamen.
  - **Gold ASB:** +122,30 USD.

**Muster der Woche ueber alle Bridges:** Gold ASB gewann ueberall. ORB
verlor ueberall, **32 von 32 Trades ausgestoppt**. CTNL gewann nur 1 von
28 geschlossenen Trades, und dieser eine war ein alter TTP-Short vom 18.09.,
der am 28.09. das TP erreichte. Die offenen Shorts vom 02.10. stehen aber im
Plus.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto
inkl. Kommission und Swap. Die Prozentwerte beziehen sich auf den
Kontostand zu Wochenbeginn (heutige Balance minus Wochen-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 21 | 19,0 % | **-15,65 EUR** | **-0,56 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 38 | 7,9 % | **-1.424,11 USD** | **-0,72 %** |
| FK Instant Funding (LIVE, echtes Geld) | 16 | 6,3 % | **-840,44 USD** | **-0,84 %** |
| **Gesamt (alle 3, echtes Geld)** | **75** | **10,7 %** | **-15,65 EUR / -2.264,55 USD** | **ca. -0,76 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist
  EK mit ca. 2.800 EUR (ca. 3.270 USD bei 1,17) in ein Buch von ca.
  299.800 USD eingerechnet. Weil EK nur rund 1 % ausmacht, haengt die Zahl
  praktisch nicht am Kurs.
- **Unrealisiert zum Wochenschluss** (nicht in der Tabelle): EK +55,29 EUR,
  TTP +572,66 USD (davon +493 aus dem CTNL-Short vom 18.09.), IQ
  +223,86 USD, FK +112,54 USD. Den groessten Teil davon tragen die
  Gold-Shorts. Auf Equity-Basis waere die Woche also etwas besser als die
  realisierte Zahl.
- **Keine Handeingriffe**, also ist "nur Bot" diesmal gleich "Konto".
- EK hat zusaetzlich eine Balance-Buchung von +1,10 EUR (30.09. 01:17,
  Kommentar `LQK178I9RNEXIL7D`). Sie ist kein Trade und nicht in der Zahl
  enthalten. Was der Broker da gebucht hat, ist nicht geprueft.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server). Wie in den
  Vorwochen fuehre ich es unter Echtgeld. Das IQ-Konto heisst im Bridge-Log
  "BeyondIQCapital **Demo** Challenge IQCEV100K". Ob die Challenge-Konten als
  "echtes Geld" zaehlen, haengt an der Kontoart (Gebuehr bezahlt, Kapital
  simuliert). Die Einordnung uebernehme ich unveraendert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 28.09. 00:00 bis 02.10. 21:00,
gerechnet mit Sizing und Kostenannahme der jeweiligen Bridge. **Er rechnet
mit der Konfiguration von HEUTE.** Diese Woche ist das ein besonders grosser
Vorbehalt, siehe die Konfigurationsschnitte in Abschnitt 1.

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 15 Trades / **+1,33 %** | -15,65 EUR (-0,55 %) | - | - | - (**15 nicht_ermittelbar, -9,69 R**) |
| Funded-Portfolio | 15 Trades / **-0,56 %** | -1.419,90 USD (-0,72 %) | 4 (+0,55 R) | 5 (-4,29 R) | 6 (-6,15 R) |
| FK Instant Funding | 15 Trades / **-1,63 %** | -839,69 USD (-0,85 %) | 2 (+2,80 R) | 6 (-5,36 R) | 7 (-7,23 R) |

(Die Ist-Zahlen weichen um wenige USD von Abschnitt 4 ab. Soll/Ist grenzt
anders ab: Deals bis Fr 21:00 statt geschlossene Positionen.)

**Pflicht-Vorbehalte:**

1. **Die Konfiguration hat sich mitten im Fenster geaendert.** Das Soll kennt
   bereits das Ribbon-Gate, den Spike-Filter, Deckel 2, die stillgelegte
   `ctnl_continuation` und rueckwirkend die neuen Gold-ASB-Parameter. Live
   galt das erst ab Mi-Abend bzw. Do-Mittag, beim Gold-ASB-Pending noch gar
   nicht. **Die CTNL-Luecke am 29./30.09. ist deshalb ein
   Konfigurationsschnitt, kein Ausfuehrungsfehler:** Live handelten IQ 11
   und TTP 6 Shorts unter Deckel 3 und ohne Gate, das Soll kennt fuer
   dieselbe Zeit nur 6 Shorts.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "15
   nicht_ermittelbar" heisst genau das. **Ausserdem nicht nachvollzogen:**
   Das EK-Soll weist **+1,33 %** aus, obwohl die Soll-Trades in Summe
   **-9,69 R** ergeben. Der einzige Gewinner ist Gold ASB (+1,17 R), und der
   ist auf EK durch den Mindestlot schwer gewichtet. Rechnerisch habe ich es
   nicht aus den Zahlen rekonstruieren koennen, deshalb die EK-Soll-Rendite
   bitte nicht als belastbar lesen.
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips). Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Was die Zerlegung tatsaechlich zeigt, Bein fuer Bein (Funded/FK):**

- **ORB "nie gesehen" ist zur Haelfte ein Zuordnungsfehler, und das ist
  jetzt minutengenau belegt.**
  - **KW39** hatte das vermutet: Die Soll/Ist-Zuordnung erkennt die
    Pending-Order-Entries von Variante C nicht.
  - **Diese Woche** stehen von den 6 "nie gesehenen" ORB-Soll-Trades drei
    **mit identischer Minute** im Broker-Abzug: NASDAQ 29.09. 15:25 UTC
    (live 15:26), NASDAQ 01.10. 13:45 (live 13:46) und US30 02.10. 13:45
    (live 13:45). Die IQ/FK-Serverzeit ist UTC+3.
  - **Echt "nie gesehen"** sind nur drei:
    - Zwei am **28.09.** (NASDAQ und US30): An diesem Tag war der Rechner
      im Standby, siehe Abschnitt 6 (7).
    - Ein NASDAQ-Long am 02.10.: Im Log steht "breakout_passed ... vor
      Platzierung".
  - Alle drei waren Soll-Verlierer, zusammen ca. -3 R. Die Ausfaelle haben
    also nichts gekostet.
- **`orb_sp500`: Das Soll kennt kein Signal, live gab es 2 Trades je
  Konto** (Funded -346,87 USD, FK -260,24, EK -21,21 EUR).
  - **Am 01.10.** fuellte die Long-Order erst ca. vier Stunden nach der
    Eroeffnung.
  - **Am 30.09.** kam der Fill 20 Minuten nach dem Rangeende, an einem Tag,
    den der Backtest nicht handelt.
  - **Einordnung:** Beides ist die "Live-Order-Luecke" (Memory:
    `orb_fill_bar_stop_and_live_order_gap`), die der Fix vom 03.10.
    schliesst. Dass sie in dieser Woche **ca. 630 USD** gekostet hat, ist die
    konkrete Zahl, die den Fix rechtfertigt.
- **CTNL auf FK: Die 7 Shorts vom 01.10. (-245 USD) stehen nicht im Soll.**
  - **Was die Zahlen zeigen:** Im Soll sitzen am 01.10. zwei Positionen
    (Einstieg 30.09. 08:15 und 08:30). Bei Deckel 2 ist der simulierte Korb
    damit voll.
  - **Was live passierte:** FK selbst hatte wegen der Kill-Switch-Sperre
    keine offene CTNL-Position und damit freie Plaetze.
  - **Vermutung, nicht verifiziert:** Der simulierte und der echte Korb
    liefen auseinander, und FK nahm Signale, die der Simulationsfilter
    unterdrueckt haette. Das Muster kennt Memory
    `ctnl_sim_filter_is_not_live_gate`. Die Ideen-Inbox fuehrt seit 30.09.
    denselben Effekt ("Engine-Pfad und Live-Pfad laufen nach der ersten
    Welle auseinander").
- **CTNL-`nicht_platziert` auf FK (5 Trades, darunter die Verlierer vom
  29./30.09.)** ist der Kill-Switch bei der Arbeit, also korrekt.
- **`cls_practical` 01.10. (Soll -3,2 bis -3,4 R, nicht platziert):** Im Log
  steht "war bereits offen UND geschlossen (stop), bevor diese Bridge es je
  gesehen hat". Der Trade ging innerhalb einer M5-Bar auf und zu. Damit ist
  er echt verpasst, aber zum Glueck. **Nicht geklaert** ist, warum ein
  einzelner Stop-Trade im Soll mit -3,2 R statt ca. -1 R steht. Moegliche
  Gruende sind der CLS-Zins-Multiplikator im R oder ein Gap ueber den Stop.
- **Gold ASB:** Soll 1 Trade, +1,17 R, auf allen drei Bridges platziert und
  gewonnen. Das ist die einzige saubere Eins-zu-eins-Zeile der Woche.

## 6. Auffaelligkeiten / offene Punkte

**(1) ORB: 32 von 32 Trades ausgestoppt, mehrere davon Stunden nach der
Eroeffnung gefuellt.**
- **Ablauf:** Jeder ORB-Trade der Woche (NASDAQ 29.09. + 01.10., SP500
  30.09. + 01.10., US30 02.10., auf allen vier Konten) wurde gefuellt und
  2-7 Minuten spaeter ausgestoppt.
- **Kosten:** zusammen ca. -1.660 USD auf Funded/FK und -56 EUR auf EK.
- **Die Spaet-Fills:** Der SP500-Fill vom 01.10. kam auf IQ/FK um 20:47
  Serverzeit, also rund **vier Stunden nach der NY-Eroeffnung**. Das ist
  genau der Fall aus der ORB-Studie vom 01.10. (Memory:
  `orb_fill_bar_stop_and_live_order_gap`): Die Long-Order bleibt nach einem
  Bruch nach unten bis 16:00 liegen, und der Backtest kennt diese Tage gar
  nicht.
- **Was ab Montag gilt:**
  - Die Long-Order wird storniert (Fix 03.10.).
  - NASDAQ storniert am geplanten SL.
  - US30 ist pausiert.
- **Offen:** Dass die Woche fast komplett aus genau diesen Trades bestand,
  ist ein starker Hinweis, dass die Aenderungen am richtigen Punkt ansetzen.
  Belegt ist es damit nicht. Die naechste Woche ist der erste echte Test.

**(2) CTNL nach dem Gate: Der erste ungesperrte Tag auf FK war 0 von 7.**
- Die 7 FK-Shorts vom 01.10. haben Ribbon und Spike-Filter passiert und
  verloren trotzdem alle.
- Das ist kein Gegenbeweis. Memory `ctnl_regime_filter_einziger_hebel` und
  der CHANGELOG vom 01.10. sagen ausdruecklich: Seit Maerz liegt CTNL bei
  -5,4 R, und das Gate hebt die Qualitaet je Trade, nicht die Trefferquote.
- Hinweisen moechte ich trotzdem darauf: Die Serie kam **nacheinander** (Stop
  bei Stop, sofort Neueinstieg), nicht gleichzeitig. Gegen eine solche Serie
  hilft der Positionsdeckel nicht. Ein Serienstopp hilft laut Befund 18 im
  Backtest aber auch nicht (Memory: `ctnl_serienstopp_vs_risikohalbierung`).
- Nur Beobachtung, keine Empfehlung.

**(3) Ribbon-Verwurfquote: ein erster Live-Datenpunkt fuer die Ideen-Inbox.**
- **Log seit 01.10.:** "9 von 28 Signalen behalten; 19 gegen den Trend
  verworfen". Je nach Lauf liegt die Quote bei 63-68 %.
- **Erwartung** (Dashboard-Inbox, 03.10.): ca. 60 %.
- **Befund:** Das Gate greift live, und zwar in der erwarteten
  Groessenordnung. Damit ist auch der Dashboard-Pruefpunkt "Gegenlesen beim
  naechsten CTNL-Signaltag (Log muss 'N von M behalten' zeigen)" belegt.
- **Nicht abgehakt.** Das Abhaken liegt bei dir.

**(4) Datenpfad: Fehlerzeilen weiter da, Ursache noch offen.**
- **Fehlerzeilen der Woche:**
  - `str`/`float` im CLS-Scan: 28.09. (47x), 29.09. (11x), 01.10. (20x).
  - Haenger `dukascopy_python` im Fast-CLS-Scan: Funded 26x, FK 9x.
- **Lake-Fallbacks:** Pro Bridge und Woche gibt es Hunderte
  `LakeStaleDataError`.
- **Was schon getan ist:** Die Lese-Validierung vom 28.09. und das atomare
  Cache-Schreiben vom 04.10. (`cbce4434`) sind die bisherigen Schritte. Seit
  01.10. 13:xx gab es keine `str`/`float`-Zeile mehr. Ob das am Fix liegt
  oder Zufall ist, laesst sich nach einem Tag ohne Handel nicht sagen.
- **Stand:** Alles ist im Dashboard zu einer Untersuchung zusammengefuehrt.
- **Neu waere hoechstens:** Auch der Soll/Ist-Lauf dieses Reports lief auf
  denselben `LakeStaleDataError` (Lake-Stand 02.10. ~22:00 UTC). Das ist am
  Wochenende erwartbar und kein Befund.

**(5) EK: ein `Authorization failed` (29.09. 00:34) und ein `Failed to
launch python` (28.09. 03:56) im Fast-Log.** Beide traten einzeln auf und
hatten keine erkennbare Folge.

**(6) FK-Warnung "Kontostand weicht von STARTING_EQUITY=100.000 ab"** kommt
weiter in jedem Lauf. Laut Text beeinflusst sie den Trailing-DD-Floor. Sie
war schon in den Vorwochen da und ist kein neuer Befund. Ich fuehre sie hier,
weil sie im Log das Signal-Rausch-Verhaeltnis verschlechtert. Geprueft habe
ich nicht, ob der Floor korrekt sitzt.

**(7) Mo 28.09., 10:33-17:16: Der Rechner war im Standby, also auch der
Watchdog. Das ist der wichtigste neue Befund der Woche.**
- **Befund:** Fuer etwa 6,7 Stunden gibt es **in keinem Log einen Lauf**.
  Betroffen sind alle sechs Bridge-Lanes (Funded/FK/EK, jeweils Slow und
  Fast) **und** der Bridge-Watchdog (letzter Snapshot-Commit 10:32,
  naechster 17:16).
- **Beleg im Windows-Ereignisprotokoll:** `Kernel-Power 506` (Eintritt in
  Modern Standby) um **10:32:54**, `507` (Austritt) um **17:16:09**. Danach
  folgte ein zweites Standby von 17:28 bis 18:45.
- **Folgen:**
  - Die NY-Eroeffnung (15:30 Berlin) wurde auf allen Bridges verpasst. Im
    Log steht nach dem Aufwachen `range_not_ready` und danach
    `breakout_passed ... vor Platzierung`.
  - Der Watchdog konnte nicht alarmieren, weil er auf derselben Maschine
    mitschlief.
  - Geldwert diesmal: keiner. Die beiden verpassten Soll-Trades (NASDAQ und
    US30) waren Verlierer.
- **Was das an der Dashboard-Untersuchung aendert:** Die Untersuchung
  "Lake veraltet -> Laeufe haengen" zaehlt die **~8-h-Luecke vom 28.09.**
  als Indiz fuer haengende Laeufe. **Das passt nicht.** Am 28.09. hing
  nichts, der ganze Rechner schlief. Der 01.10. ist anders: Dort zeigt das
  Ereignisprotokoll nur Standby-Ereignisse von 15 und 28 Sekunden, die
  ~1-h-Luecke bleibt damit ein echter Kandidat fuer das Haengen.
- **Weitere Ereignisse im Protokoll:**
  - Am 28.09. um 02:28 steht `Kernel-Power 41` + `EventLog 6008`, also ein
    unerwartetes Herunterfahren. Das erklaert, warum der KW39-Report erst
    Montagfrueh lief.
- **Bezug zu frueheren Massnahmen:** Am 02.09. wurde Standby im
  Netzbetrieb abgeschaltet (CHANGELOG 02.09.). `powercfg` zeigt heute fuer
  Netzbetrieb weiter "Ruhezustand nach: 0".
- **Offene Frage:** Warum ging der Rechner trotzdem in den Standby? Moeglich
  sind Akkubetrieb, ein zugeklappter Deckel oder ein Tastendruck. Geprueft
  habe ich das nicht. Ich trage es als Hinweis bei der Untersuchung im
  Dashboard ein.

**(8) Montag ist der Tag der vielen Erstlaeufe.**
- **Was zum ersten Mal live laeuft:** Gold-ASB-Stop-Order, CTNL-Exit-Standard
  und frueherer Einstieg, ORB-Storno-Regeln, US30-Pause, TTP-Gewichte und
  Tick-Rundung.
- **Teststand:** Alles ist offline getestet, aber keins davon hat schon
  einmal eine echte Order geschickt.
- **Wann wo nachsehen:**
  - **07:00 Berlin, Gold ASB:** Order oder Grund fuer "keine Order" im Log.
  - **Erster CTNL-Entry:** Gibt es einen Broker-TP? Liegt der EK-SL auf dem
    Signal-Niveau?
  - **NY-Open, ORB:** Storno-Meldungen.
  - **Erster TTP-Entry:** Gold ASB sollte ca. 600 $ Risiko zeigen, OU ca.
    50 $.
- **Wo die Punkte stehen:** alle unter "Braucht deine Bestaetigung" im
  Dashboard. Hier stehen sie nur, damit die Summe sichtbar ist. Viele
  gleichzeitige Erstlaeufe heissen auch: Geht am Montag etwas schief, ist
  die Ursache schwerer zu isolieren.
