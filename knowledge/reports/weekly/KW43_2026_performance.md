# Weekly Checkup - Performance - KW43/2026

**Abgedeckte Woche: Mo 2026-10-19 bis So 2026-10-25.** Erzeugt am **Di
27.10.** abends durch den geplanten `Forex-Weekly-Report`-Task (**verspaetet**,
der Sonntagslauf fand nicht statt). Abgedeckt ist trotzdem die letzte
vollstaendige Woche, nicht die laufende KW44.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W43.json`
(Fenster 19.10. 00:00 bis 26.10. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W43.json`, die Logs der drei Portfolio-Bridges,
das Windows-Ereignisprotokoll, `knowledge/CHANGELOG.md` und der Task Scheduler.

> **Zum Abzug:**
> - Alle vier Terminals liefen schon (warm), der Abzug lieferte sofort
>   10 / 14 / 13 / 13 Deals. Dieser Lauf hat **kein** Terminal gestartet und
>   keins geschlossen (vorher und nachher dieselben 6 PIDs).
> - Die Kontostaende zu Wochenbeginn stammen aus dem KW42-Abzug (So 18.10.,
>   Markt zu): EK 2.763,21 EUR, TTP 98.159,29, IQ 96.127,36, FK 98.342,36 USD.
> - **Kontostand und offene Positionen im Abzug sind von heute (27.10.)**,
>   nicht vom Wochenende. Mo/Di 26./27.10. haben schon weitergehandelt (siehe
>   Abschnitt 6, Punkt 6).
> - **Diese Woche gab es Handeingriffe**: 6 Schliessungen mit `reason = 1`
>   (Mobile-App) auf TTP, IQ und FK. Sie sind in den Zahlen enthalten und
>   unten getrennt ausgewiesen.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche mit echtem Geld
(`DRY_RUN = False`, heute geprueft): **EK-Portfolio-Bridge** (Tickmill
55918977), **Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets
16054) und **FK Instant Funding** (BeyondIQCapital 17764). Alle sechs
Bridge-Tasks (Slow und Fast) stehen auf `Bereit`, die Einzel-Bots bleiben
`Deaktiviert`.

**Zwei Live-Aenderungen in der Woche, beide am Mo 19.10.:**

- **OU steigt nur noch auf abgeschlossenen Tageskerzen ein** (Funded,
  Nutzerfreigabe, live seit 11:05; Repo `7c26f58c` + Funded-`run_once.py`
  ausserhalb von Git). Ursache waren die verwaisten TTP-Positionen DD/EOG/STT
  (siehe Memory: `ou_einstieg_auf_laufendem_tageskurs`).
- **Akkubetrieb:** Die Flags "Nur bei Netzbetrieb starten" / "Bei Akkubetrieb
  beenden" sind bei `EK-Portfolio-Bridge-Fast` und den drei
  `DataLake-Ingest`-Tasks aus, Zuklappen im Akku = "Nichts unternehmen"
  (Antwort auf die KW42-Standbys, siehe Memory: `standby_watchdog_schlaeft_mit`).

**Nach dem Wochenende, fuer KW44 wichtig:** Am 26. und 27.10. brach auf TTP, IQ
und FK jeder ORB-Scan ab, weil die Bridges die Serverzeit nach der
Winterzeitumstellung falsch umrechneten. Am 27.10. behoben (Funded und FK,
`orb_mt5_source.py` + FK `config.py`; siehe Memory: `broker_serverzeit_ny_plus_7`).
KW43 selbst betrifft das nicht.

Was die Woche live gepraegt hat: **ein CTNL-Gewinntag** (Mi/Do 21./22.10.),
**das Abraeumen der Altpositionen von Hand** und **ein siebenstuendiger
Totalausfall am Di 20.10.** (Abschnitt 6, Punkt 1).

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Kill-Switch ausgeloest, kein Drawdown-Halt.**

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest; Balance 2.855,88 EUR zum Wochenende (+3,35 %) |
| EK-Portfolio | Gesamtrisiko-Deckel 30 % | eingehalten: offenes Risiko 115,6 EUR bei einem Deckel von 857 EUR (Fr 22:59) |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgeloest |
| EK-Portfolio | CTNL-Risiko je Order | Mindestlot 0,01; die aktuelle Position (27.10.) hat 13,48 USD Stopabstand, also ca. 11,5 EUR (0,4 % des Kontos) statt ca. 0,5 EUR Ziel. Bekannt (siehe Memory: `ek_mindestlot_kehrt_hierarchie_um`) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Fr 23.10. -87,29 USD (ORB SP500) |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag **Fr 23.10. -228,51 USD** (beide ORB-Longs). Balance zum Wochenende **97.461,70 USD = -2,54 % seit Start, ca. 3.460 USD Abstand** zur 6-%-Grenze (KW42: ca. 2.130) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgeloest |
| Funded / TTP | CTNL-Positionsdeckel 2 | **wieder frei**: Nach dem Handschliessen am 19.10. nahm TTP am 21.10. erstmals seit dem 30.09. wieder einen CTNL-Trade (TP, +428 USD) |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; Balance zum Wochenende 98.395,82 USD (-1,60 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nie ausgeloest |

**Zur Kenntnis:** Der Abstand von IQ zur 6-%-Grenze ist diese Woche zum ersten
Mal seit Wochen **gewachsen** (+1.335 USD). Der Trend aus KW40-42 ist damit
unterbrochen, aber nicht umgedreht: Mo/Di 26./27.10. kosteten IQ schon wieder
ca. 257 USD.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): +92,67 EUR (+3,35 %) bei 5 Trades.** Fast
  alles aus einem Trade: der CTNL-Short vom 21.10. (Einstieg 4.130, TP am
  22.10. bei 4.029, **+91,13 EUR**). OU brachte +14,44 (MSTR, TROW,
  MA20-Ausstieg), ORB -12,90 (NASDAQ-Short 22.10. sofort wieder geschlossen,
  SP500-Long 23.10. nach 90 Sekunden ausgestoppt). Die beste EK-Woche seit
  Wochen, aber mit dem Mindestlot-Risiko des CTNL-Beins erkauft.
- **Funded-Portfolio-Bridge (TTP + IQ): +2.664,87 USD (+1,37 %) bei 15
  Trades.** Davon **+979,34 USD aus 6 Schliessungen von Hand** (die
  CTNL-Altpositionen vom 18.09./30.09./02.10. und die verwaisten OU-Titel EOG
  und DD). **Die Bot-Trades allein: +1.685,53 USD bei 9 Trades.** Getragen
  von CTNL: Die Shorts vom 21.10. liefen auf beiden Konten ins Ziel (IQ zwei
  Positionen +1.475,74, TTP +428,34). ORB kostete netto -124,79 (NASDAQ-Short
  22.10. mit Gewinn sofort geschlossen, Longs 23.10. sofort ausgestoppt).
  Gold ASB hatte keinen Trade.
- **FK Instant Funding: +53,56 USD (+0,05 %) bei 6 Trades.** CTNL +238,86 aus
  den gleichen beiden Shorts (kleine Positionen, 0,01-0,02 Lot), ORB
  -203,85 (dasselbe Muster wie Funded), dazu +18,55 aus einer Handschliessung.

**Muster der Woche:** **Ein Tag macht die Woche.** Die CTNL-Shorts vom Mi
21.10. (Einstieg ca. 4.128-4.136, Gold fiel bis Do auf ca. 4.020) sind auf
allen vier Konten der groesste Posten. Ohne sie und ohne die Handschliessungen
waere die Woche auf allen Bridges leicht negativ (ORB). Die ORB-Trades der
Woche dauerten jeweils **unter drei Minuten**: Am 22.10. griff die Regel
"gefuellt, obwohl der Kurs vorher den SL erreicht hatte -- sofort schliessen"
(diesmal zufaellig mit Gewinn), am 23.10. lief der Kurs nach dem Long-Ausbruch
sofort zurueck in den Stop.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto
inkl. Kommission und Swap. Die Prozentwerte beziehen sich auf den Kontostand
zu Wochenbeginn (KW42-Endstand).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 5 | 60,0 % | **+92,67 EUR** | **+3,35 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 15 | 80,0 % | **+2.664,87 USD** | **+1,37 %** |
| &nbsp;&nbsp;davon Bot-Trades | 9 | 66,7 % | +1.685,53 USD | +0,87 % |
| &nbsp;&nbsp;davon Handschliessungen | 6 | 100 % | +979,34 USD | +0,50 % |
| FK Instant Funding (LIVE, echtes Geld) | 6 | 66,7 % | **+53,56 USD** | **+0,05 %** |
| **Gesamt (alle 3, echtes Geld)** | **26** | **73,1 %** | **+92,67 EUR / +2.718,43 USD** | **ca. +0,96 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist EK
  mit 2.763,21 EUR (ca. 3.230 USD bei angenommenen 1,17, nicht abgefragt) in
  ein Buch von ca. 295.900 USD eingerechnet.
- **Die Winrate ist diese Woche geschoent.** 7 der 19 Gewinner sind
  Handschliessungen alter Positionen oder OU-Ausstiege. Die neuen Trades der
  Woche: CTNL 5 von 5 im Ziel, ORB 3 von 8 (alle drei mit wenigen Dollar).
- Je Konto: TTP 9 Trades **+1.330,08 USD (+1,36 %)**, IQ 6 Trades
  **+1.334,79 USD (+1,39 %)**.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das
  IQ-Konto heisst "BeyondIQCapital **Demo** Challenge". Die Einordnung als
  "echtes Geld" uebernehme ich unveraendert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 19.10. 00:00 bis 23.10. 21:00
(UTC), gerechnet mit Sizing und Kostenannahme der jeweiligen Bridge und der
Konfiguration von HEUTE. **Konfigurationsvorbehalt:** Im Fenster und danach
gab es zwei Aenderungen. (a) OU nur auf fertigen Tageskerzen (19.10. 11:05):
greift im Soll nicht, weil das Soll fuer OU "kein Signal" meldet. (b) ORB-
Serverzeit NY+7 (27.10.): rechnet im Sommer identisch, aendert fuer das
Fenster also nichts. **Der Vorbehalt verfaelscht diese Woche keine Zeile.**

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 10 Trades / **+0,26 %** | +92,67 EUR (+3,29 %) | - | - | - (**10 nicht_ermittelbar, +12,79 R**) |
| Funded-Portfolio | 10 Trades / **+0,36 %** | +2.665,89 USD (+1,36 %) | 2 (+10,26 R) | 0 | 8 (+3,08 R) |
| FK Instant Funding | 10 Trades / **+0,58 %** | +53,71 USD (+0,05 %) | 2 (+10,26 R) | 0 | 8 (+3,08 R) |

(Die Ist-Werte aus `soll_ist.py` weichen um Cent-Betraege von Abschnitt 4 ab,
weil das Werkzeug Einstiegskommissionen anders zuordnet; die Prozentbasis ist
dort der heutige Kontostand.)

**Hauptaussage: Die beiden Trades, die die Woche tragen, sind sauber
platziert.** Die CTNL-Shorts vom 21.10. 12:45/13:00 UTC stehen im Soll mit
+5,28 / +4,98 R und live auf allen Konten mit TP. Ist liegt auf Funded weit
ueber Soll, weil (a) die Handschliessungen nicht im Soll stehen und (b) IQ
das CTNL-Bein mit 1/3 statt 1/6 Kapitalanteil faehrt.

**Pflicht-Vorbehalte:**

1. **Konfiguration:** siehe oben, ohne Wirkung auf das Fenster.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "10
   nicht_ermittelbar" heisst genau das, nicht "nie gesehen".
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Was hinter den 8 "nie gesehen" steckt (Funded und FK gleich):**

- **Di 20.10., ORB SP500 Long (+5,97 R, Ziel) und ORB NASDAQ Short
  (-1,02 R): wirklich nie gesehen.** Der Rechner war von 13:50 bis 21:03 aus
  (Abschnitt 6, Punkt 1). **Netto ca. +4,9 R verpasst**, auf Funded + FK
  grob geschaetzt **ca. 1.500 USD** (Risiko je Seite TTP/IQ/FK ca. 74-99 /
  108 / 123 USD aus den Platzierungen am 22./23.10., mal R; nicht je Konto
  nachgerechnet). Das ist der teuerste Punkt der Woche.
- **Mo 19.10., ORB NASDAQ (-1,03 R):** live beide Seiten storniert ("Kurs
  erreichte den geplanten SL vor dem Einstieg"). Das Soll kennt das Storno
  nicht (Werkzeugluecke seit KW41). Gespart.
- **Do 22.10. ORB NASDAQ Short und Fr 23.10. ORB SP500/NASDAQ Long (je ca.
  -1 R):** **live sehr wohl platziert und gefuellt** (22.10. sofort wieder
  geschlossen, 23.10. ausgestoppt wie im Soll). Das Werkzeug ordnet
  ORB-Fills dem Soll nicht zu. **Werkzeugfehler, kein Ausfuehrungsfehler.**
- **Fr 23.10., `ctnl_reversal` 10:15 und 10:30 UTC (+1,08 / +1,16 R, beim
  Datenende noch offen):** live gab es am 23.10. zwei CTNL-Shorts, aber um
  12:13 und 13:43 UTC, also zwei bzw. drei Stunden spaeter. Gleiches Muster
  wie in KW42 (Live-Signale ohne Soll-Gegenstueck und umgekehrt). **Ursache
  offen.** Beide Live-Shorts liefen nach dem Wochenende ins Minus
  (Abschnitt 6, Punkt 6).

## 5b. Edge-Warnstufen je Live-Bein

**Diesmal frisch:** `research_live_legs.py tickmill --ampel` lief in ca. 30
Minuten ohne Haenger durch (anders als KW42). Liste
`live_trades_tickmill_ampel.csv`, **letzter Trade gesamt 25.10.**, Status
`edge_monitor/results/status.csv` vom 27.10. 23:36.

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** | **23,2** / 15,2 (KW42: 22,1) | alle fuenf rot |
| orb_us30 | **ROT** (pausiert) | 24,5 / 13,2 | alle fuenf rot |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_silver | GELB | 1,7 / 4,9 | roll_mean streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | gruen | - | - |

- **orb_sp500 (ROT):** Das Loch ist um 1,1 R tiefer geworden (23.10.
  ausgestoppt; der Ziel-Trade vom 20.10. steht in der Liste, live war der
  Rechner aus). Steht bereits im Dashboard und ist entschieden ("ORB bleibt
  erstmal so", 16.10.); kein neuer Eintrag.
- **orb_us30 (ROT):** pausiert seit 04.10., unveraendert.
- **btc_ema_cross, gold_silver (GELB):** unveraendert, beobachten.
- **Bewegung im Gruenen:** ctnl_reversal steht nach dem 21./22.10. auf einem
  neuen Hoch (Drawdown 3,5 → 0,0 R); orb_nasdaq ist tiefer im Loch (4,2 →
  8,3 R), aber weit unter der Schwelle von 27,9 R.
- **Bekannte Luecke bleibt:** gold_asb fuehrt als letzten Trade weiter den
  28.09.; der Live-Fill vom 15.10. fehlt in der Liste (Dashboard-Punkt aus
  KW42).

## 6. Auffaelligkeiten / offene Punkte

**(1) Di 20.10., 13:50-21:03: Totalausfall, vermutlich Akku leer. Das ist
der wichtigste Befund der Woche.**
- **Alle** Lanes aller drei Bridges (EK Slow/Fast, Funded Fast, FK Fast)
  haben dieselbe Luecke, also die Maschine und nicht der Code.
- Ereignisprotokoll (UTC in Klammern): Standby-Eintritt **12:36** (10:36,
  `Kernel-Power 506`, Grund 12, Akku 9.770 mWh), Austritt und sofort
  erneuter Eintritt **13:46** (Grund 53, **Akku nur noch 2.300 mWh**), dann
  nichts bis **20:58: `Kernel-Power 41` + `EventLog 6008`** = Neustart nach
  nicht sauberem Herunterfahren. Meine Lesart (nicht bewiesen): Der Akku lief
  im Standby leer, das Geraet ging hart aus und startete erst am Netz wieder.
- Auffaellig: Zwischen 12:36 und 13:46 liefen die Bridges trotz
  Standby-Eintrag weiter (Logzeilen alle 5 Minuten). Das passt zu den neuen
  Einstellungen vom 19.10. (Tasks laufen im Akku weiter). **Moegliche
  Nebenwirkung des Fixes:** Wer die Bridges im Akku wach haelt, leert den
  Akku schneller. Unbelegt.
- **Folgen:** ORB vom 20.10. verpasst (Soll netto ca. +4,9 R, siehe
  Abschnitt 5), der OU-Ausstieg LEN kam einen Tag spaeter (21.10.,
  zufaellig zum besseren Kurs 78,07 statt 75,98). Der Watchdog schlief mit.
- Die VPS-Idee (Ideen-Inbox 19.10., "auf November verschoben") ist damit die
  einzige Massnahme, die das strukturell loest.

**(2) Handeingriffe der Woche: Altpositionen abgeraeumt, Dashboard-Punkte
teilweise erledigt.**
- Mo 19.10. ca. 11:27 Serverzeit: CTNL-Altpositionen per Mobile-App
  geschlossen (TTP 18498503 +415,10 und 18696950 +17,83, IQ 1973249 +37,01,
  FK 1973231 +18,55). Passt zum Dashboard-Update vom 19.10.
- **Do 22.10. ca. 20:01 Serverzeit, TTP:** die auf Break-even gesetzte
  CTNL-Position 18696522 (+166,00) und die **verwaisten OU-Titel EOG
  (+301,90) und DD (+41,50)**, ebenfalls per Mobile-App. Damit ist der
  Dashboard-Punkt "(a) DD/EOG/STT von Hand schliessen?" fuer DD und EOG
  faktisch entschieden. **STT ist weiter offen** (Stand 27.10. +6,72), dazu
  **FLEX** (seit 15.10., -10,81) und **UAL** (seit 16.10., +8,57). Ob FLEX und
  UAL vom Modell gefuehrt werden oder ebenfalls aus dem Scan gefallen sind,
  ist **nicht geprueft**.
- Nichts davon wurde von diesem Report angefasst.

**(3) OU-Ausstieg schickt Orders bei geschlossener Boerse.** Seit dem Fix vom
19.10. wird der MA20-Ausstieg auf der fertigen Tageskerze nachts berechnet und
sofort gesendet. Fuer LEN gab es vom 20.10. 06:13 bis 21.10. 15:43 **94
abgelehnte Schliess-Orders** (`retcode 10018, Market closed`), alle 15
Minuten. Harmlos (der Broker lehnt ab, nichts wird ausgefuehrt), aber
Log-Rauschen, das echte Fehler verdeckt. Ein Boersenzeiten-Gate vor dem
Senden wuerde das abstellen. Echtes Geld, also nur als Vorschlag.

**(4) Soll/Ist: ORB-Fills werden nicht zugeordnet.** Drei der acht "nie
gesehen" sind live gefuellte ORB-Trades (Abschnitt 5). Zusammen mit dem
fehlenden Storno-Modell (seit KW41) liest sich ORB in Soll/Ist dauerhaft
falsch. Die CTNL-Zeitverschiebung (23.10.) ist die zweite offene
Soll/Ist-Frage, schon die zweite Woche in Folge.

**(5) Datenpfad: ruhiger als KW42, aber nicht sauber.** Funded: 10x
`OU-Modell-Scan fehlgeschlagen ... (dukascopy_python-Hang)`, 6x CLS
`'>' not supported between 'str' and 'float'`, 5x Timeout beim
Terminal-Check auf TTP. Lake-Fallbacks (`LakeStaleDataError`) gehaeuft rund
um den Ausfall am 20.10. EK-Fast: einmal `Authorization failed` beim
Verbinden. FK warnt weiter in jedem Lauf "Kontostand weicht von
STARTING_EQUITY=100.000 ab" (107x, bekannt).

**(6) Nachtrag Mo/Di 26./27.10. (gehoert zu KW44, hier nur zur Einordnung).**
- Die beiden CTNL-Shorts vom 23.10. schlossen nach dem Wochenende im Minus;
  Mo/Di zusammen: EK -32,93 EUR, TTP -175,77, IQ -256,76, FK -81,71 USD.
- **ORB lief am 26. und 27.10. auf TTP, IQ und FK gar nicht**
  (Serverzeit-Pruefung brach ab, am 27.10. behoben). EK war nicht betroffen.
- Heute 17:42-18:47 Serverzeit eroeffnete CTNL neue Shorts auf allen Konten
  (Gold ca. 4.047-4.061).

**(7) Kleineres.**
- TTP verpasste am 23.10. den NASDAQ-Long ("breakout_passed ... vor
  Platzierung" schon um 15:45:12), IQ und FK bekamen ihn. Er war ein
  Verlierer; die Ursache ist der andere Kursfeed je Konto.
- Research-Stand: Ein grosser Teil der Wochenarbeit (Copy Trading,
  Key-Levels-Abschluss, OmniGold, SMH-Reports, CLS-Call) liegt **nur im
  Working Tree, ohne Commit** (siehe Education-Teil). Dieser Report committet
  bewusst nur `knowledge/reports/`.
