# Weekly Checkup - Performance - KW42/2026

**Abgedeckte Woche: Mo 2026-10-12 bis So 2026-10-18.** Erzeugt am So
18.10. ab 18:00 durch den geplanten `Forex-Weekly-Report`-Task (puenktlich).

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W42.json`
(Fenster 12.10. 00:00 bis 19.10. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W42.json`, die Logs der drei Portfolio-Bridges,
deren `bridge_state*.json`, das Windows-Ereignisprotokoll und der CHANGELOG
der Woche.

> **Zum Abzug (zweimal fast falsch):**
> - **Kaltes Terminal:** Beim ersten Abzug um 18:01 lieferten EK, TTP und IQ
>   **0 Deals**. Die Terminals liefen vorher nicht und waren Sekunden alt
>   (siehe Memory: `mt5_kaltes_terminal_leere_historie`). Nach 2,5 Minuten
>   kamen 14 / 7 / 4 Deals, in zwei weiteren Abzuegen unveraendert.
> - **FK-Terminal antwortete nicht** (`IPC timeout`, viermal). Ursache: Das
>   FK-Terminal muss mit `/portable` gestartet werden, so wie es die Bridge
>   selbst tut (`executor.py`); `mt5.initialize(path=...)` startet es ohne.
>   Nach einem Neustart mit `/portable` kamen 4 Deals, zwei Minuten spaeter
>   gleich. Das ist eine Luecke in `mt5_pull.py`, kein Problem der Bridge (die
>   war bis Fr 22:14 normal verbunden).
> - Die Kontostaende zu Wochenbeginn passen auf den Cent zu den Endstaenden
>   aus KW41 (IQ 96.606,39, FK 98.442,09). Die vier Terminals hat dieser Lauf
>   selbst gestartet und danach wieder geschlossen.
> - Keine Handeingriffe: kein Deal mit `reason` 0/1/2, keine Balance-Buchung.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen die ganze Woche mit echtem Geld
(`DRY_RUN = False`, heute geprueft): **EK-Portfolio-Bridge** (Tickmill
55918977), **Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets
16054) und **FK Instant Funding** (BeyondIQCapital 17764). Alle sechs
Bridge-Tasks (Slow und Fast) stehen im Task Scheduler auf `Bereit`, die
Einzel-Bots (Gold ASB, CLS, CTNL, OU, BTC-EMA) bleiben `Deaktiviert`.

**Die zweite Woche in Folge ohne Konfigurationsaenderung.** In den drei
Bridge-Ordnern wurde seit dem 04.10. keine `.py`- oder `config`-Datei
geaendert (nur die State-Dateien), und kein Commit der Woche beruehrt
`challenge_portfolio/`, `data_lake/` oder andere von den Bridges importierte
Module. Live-relevant waren nur Entscheide:

- **16.10.: ORB bleibt erstmal so** (Nutzerentscheid): SP500 trotz roter
  Edge-Ampel weiter live, NASDAQ behaelt das Storno am SL, obwohl es ueber 10
  Jahre schlechter abschneidet (Education 3.2).
- **16.10.: Challenge-Gewichtung K60 + ORB** fuer TTP/IQ eingefroren, nur
  Forward ab 19.10. Kein Livegang.
- **12.10.: neuer Daten-Task `G8-Notion-Sync`** (kein Order-Bezug).

Was die Woche live gepraegt hat, war keine Aenderung, sondern
**Standby**: Mo 09:55-17:09 und Do 14:49-15:53 lief keine Bridge (Abschnitt
6, Punkt 1).

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Kill-Switch ausgeloest, kein Drawdown-Halt.**

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgeloest |
| EK-Portfolio | Gold-ASB-Risiko je Order | 61,49 EUR (13.10., 0,01 Lot) und **67,84 EUR (15.10., 0,02 Lot) = 2,4 % des Kontos**. Konfiguriert sind effektiv 2,93 % je Trade (`config.py`, gold_asb 0,2816). Das liegt also im Rahmen; die KW41-Einordnung als "Mindestlot-Verzerrung" war fuer Gold ASB zu streng |
| EK-Portfolio | CTNL-Risiko je Order | Mindestlot: Ziel 0,52 EUR, **real 14,05 EUR (26,9x)**, bekannt (siehe Memory: `ek_mindestlot_kehrt_hierarchie_um`) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Do 15.10. -333 USD (Gold ASB) |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag **Do 15.10. -334,56 USD** (Gold ASB), Fr -144,47 (CTNL). Balance **96.127 USD = -3,87 % seit Start, ca. 2.130 USD Abstand** zur 6-%-Grenze (KW41: ca. 2.600) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgeloest |
| Funded / TTP | CTNL-Positionsdeckel 2 | **haelt weiter 3 alte Shorts** (18.09., 2x 30.09.), daher wieder kein neuer CTNL-Entry |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; Balance 98.342 USD (-1,66 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nie ausgeloest; am Mo und Do mehrfach "Scan ohne Trades (Datenluecke?) -- kein Urteil, Zustand bleibt aus" (fail-safe wie vorgesehen) |

**Zur Kenntnis:** IQ naehert sich langsam seiner Grenze: -3,4 % (KW41) →
-3,87 % (KW42). Bei einem schlechten Tag in der Groessenordnung des 01.10.
waere der Abstand noch ausreichend, aber er schrumpft seit Wochen.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): -32,53 EUR (-1,16 %) bei 6 Trades.** Zwei
  Trades machen die Woche: der erste Gold-ASB-Fill (15.10., Zeit-Exit,
  -29,15 EUR) und ein CTNL-Short (15./16.10., ausgestoppt, -13,66 EUR, mit
  26,9-fachem Mindestlot-Risiko). Die vier OU-Schliessungen brachten +10,28
  EUR. Relativ die schwaechste Bridge der Woche, weil Gold ASB auf EK mit
  2,4 % Risiko das groesste Bein ist.
- **Funded-Portfolio-Bridge (TTP + IQ): -793,76 USD (-0,41 %) bei 5 Trades.**
  Gold ASB kostete auf beiden Konten zusammen **-667,68 USD** (TTP -333,12, IQ
  -334,56), der CTNL-Short auf IQ -144,47; TTP-OU +18,39 (zwei
  Abgleich-Schliessungen DHI/SPG). Kein ORB-Trade: zweimal beide Seiten
  storniert, einmal Mittwochsfilter, zweimal durch Standby verpasst.
- **FK Instant Funding: -99,73 USD (-0,10 %) bei 2 Trades.** Gold ASB -63,51,
  CTNL -36,22. Kleine Positionen (Gold ASB 119 USD Risiko) halten den Schaden
  klein.

**Muster der Woche:** Sehr wenig Handel (13 Trades gegen 32 in KW41). Gold
schwankte zwischen ca. 4.136 und 4.196. **Beide neuen Trade-Typen der Woche
liefen gegen uns:** der Gold-ASB-Short vom 15.10. (Fill 07:58, Zeit-Exit um
11:00 NY ca. 21 USD hoeher, ohne den Stop zu erreichen, ca. -0,56 R) und der
CTNL-Short vom 15.10. abends (Stop am 16.10. bei 4.191). ORB NASDAQ hat
diese Woche **keinen einzigen Trade** gemacht.

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto
inkl. Kommission und Swap. Die Prozentwerte beziehen sich auf den
Kontostand zu Wochenbeginn (heutige Balance minus Wochen-P&L).

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 6 | 66,7 % | **-32,53 EUR** | **-1,16 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 5 | 40,0 % | **-793,76 USD** | **-0,41 %** |
| FK Instant Funding (LIVE, echtes Geld) | 2 | 0,0 % | **-99,73 USD** | **-0,10 %** |
| **Gesamt (alle 3, echtes Geld)** | **13** | **46,2 %** | **-32,53 EUR / -893,49 USD** | **ca. -0,31 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist EK
  mit 2.795,74 EUR (ca. 3.270 USD bei angenommenen 1,17, nicht abgefragt) in
  ein Buch von ca. 296.800 USD eingerechnet.
- **Die Winrate taeuscht wieder.** Alle 6 Gewinner sind OU-Schliessungen von
  +0,06 bis +9,90. Die neuen Gold-ASB- und CTNL-Trades gewannen **0 von 6**.
- **Unrealisiert zum Wochenschluss** (nicht in der Tabelle): EK -7,43 EUR,
  TTP **+825,35 USD** (davon +440,74 aus dem CTNL-Short vom 18.09. und +318,44
  aus OU-EOG), IQ +63,93, FK +32,12.
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das
  IQ-Konto heisst "BeyondIQCapital **Demo** Challenge". Die Einordnung als
  "echtes Geld" uebernehme ich unveraendert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 12.10. 00:00 bis 16.10. 21:00,
gerechnet mit Sizing und Kostenannahme der jeweiligen Bridge und der
Konfiguration von HEUTE. **Konfigurationsvorbehalt:** Zwischen 12.10. und
heute gab es keine Aenderung (Abschnitt 1); dieser Vorbehalt greift also
nicht. **Dafuer ist das Soll diese Woche unvollstaendig:** Der ORB-Scan fiel
fuer EK und Funded mit `TimeoutError: Aufruf haengt noch nach 90s
(dukascopy_python-Hang)` aus. Fuer EK und Funded fehlt ORB im Soll ganz.

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 3 Trades / **-0,07 %** (ohne ORB) | -32,53 EUR (-1,16 %) | - | - | - (**3 nicht_ermittelbar, -3,49 R**) |
| Funded-Portfolio | 3 Trades / **-0,09 %** (ohne ORB) | -792,13 USD (-0,41 %) | 0 | 1 (-1,15 R) | 2 (-2,34 R) |
| FK Instant Funding | 9 Trades / **-0,90 %** | -99,48 USD (-0,10 %) | 0 | 1 (-1,15 R) | 8 (-8,50 R) |

(Die Ist-Werte aus `soll_ist.py` weichen um Cent-Betraege von Abschnitt 4 ab,
weil das Werkzeug Einstiegskommissionen anders zuordnet.)

**Hauptaussage: Soll und Ist haben diese Woche fast keine gemeinsamen
Trades.** Kein einziger Soll-Trade wurde live platziert, und die beiden
Live-Verlierer (Gold ASB, CTNL 15.10.) stehen nicht im Soll. Auf FK liegt
Ist deutlich ueber Soll, auf EK und Funded deutlich darunter.

**Pflicht-Vorbehalte:**

1. **Konfiguration:** unveraendert im Fenster, siehe oben.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "3
   nicht_ermittelbar" heisst genau das, nicht "nie gesehen".
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK
   (1,30) sind gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden
   stellen.

**Was die Zerlegung zeigt:**

- **`ctnl_reversal`, Mo 12.10. 05:45 und 06:00 UTC (2 Soll-Trades, -2,34 R,
  "nie gesehen" auf Funded und FK):** Live blieb die Zahl der behaltenen
  Signale den ganzen Montag bei 11, waehrend die Gesamtzahl von 32 auf 38
  stieg; die neuen Signale wurden live also als "gegen den Trend" verworfen.
  Das Soll nimmt sie. **Ursache offen.** Hypothese: Der Trendfilter rechnete
  am Montag nach dem Neustart (01:42) auf veralteten Daten (viele
  `dukascopy_python`-Haenger und `str/float`-Fehler am Montagmorgen; nicht
  bis auf den einzelnen Lauf geprueft). Geldwert:
  Beide waren Soll-Verlierer, verpasst hat das also nichts gekostet.
- **`ctnl_reversal`, Di 13.10. 01:30 Berlin (-1,15 R, "nicht platziert"):**
  ein Soll-Verlierer, den live eine Regel abfing. Welche, steht nicht
  eindeutig im Log (der Spike-Filter verwarf in diesen Minuten ein Signal).
- **Live-Trade ohne Soll-Gegenstueck:** Der CTNL-Short vom Do 15.10. (Entry
  21:58 Berlin auf IQ/FK/EK, auf IQ "Signal wieder angenommen") kommt im Soll
  nicht vor, obwohl er im Fenster liegt. Schon in KW41 waren Live-Signale
  einer M15-Bar spaeter "wieder angenommen" worden. Das Soll kennt diesen Weg
  offenbar nicht.
- **`gold_asb`: Soll "kein Signal", Ist ein Fill auf allen vier Konten**
  (15.10., zusammen ca. -765 USD-Aequivalent). Ein Live-Trade, den das Soll nicht
  sieht, ist genau der Fall aus Memory
  `gold_asb_liquidity_filter_reproducibility` (der expandierende
  Liquiditaetsfilter kann beim Nachrechnen kippen). **Nicht geprueft**, ob es
  daran liegt oder daran, dass das Soll die Stop-Order-Variante nicht
  modelliert. Das ist der wichtigste offene Punkt dieses Abschnitts, weil Gold
  ASB das groesste Bein auf EK und TTP ist.
- **FK `orb_nasdaq` (4 Soll-Trades, alle -1,0 R, "nie gesehen"):** Keiner
  davon ist ein Ausfuehrungsfehler. Mo 12.10. und Do 15.10.: Rechner im
  Standby. Di 13.10. und Fr 16.10.: live wurden beide Seiten mit "Kurs
  erreichte den geplanten SL vor dem Einstieg (wie im Backtest)" storniert,
  das Soll handelt trotzdem (bekannte Werkzeugluecke aus KW41). **Geldwert:
  ca. +4,1 R gespart**, je zur Haelfte durch Standby und Storno.
- **FK `orb_us30` (2 Soll-Trades, -2,06 R):** pausiert seit 04.10.; das Soll
  rechnet die Pause weiter nicht mit (Werkzeugluecke aus KW41).

## 5b. Edge-Warnstufen je Live-Bein

**Vorbehalt zuerst: Die Ampel ist diese Woche NICHT frisch.** Die
Neuberechnung `research_live_legs.py tickmill --ampel` blieb in **drei
Versuchen** haengen (Dukascopy-Abruf ohne Timeout, jeweils viele Minuten ohne
CPU-Fortschritt, zweimal an exakt derselben Stelle) und wurde abgebrochen.
`status.csv` beruht deshalb auf der Liste vom **16.10. 12:10, letzter Trade
15.10.** (unveraendert gegenueber Git); gegenueber letzter Woche fehlt also
nur Fr 16.10.

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** | 22,1 / 15,2 | alle fuenf rot |
| orb_us30 | **ROT** (pausiert) | 24,5 / 13,2 | alle fuenf rot |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_silver | GELB | 1,7 / 4,9 | roll_mean streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | gruen | - | - |

- **orb_sp500 (ROT):** unveraendert seit 14.10. Steht bereits im Dashboard
  und ist entschieden ("ORB bleibt erstmal so", 16.10.). Live gab es diese
  Woche auf SP500 keinen Trade (Mo/Di/Mi gefiltert, Do Standby, Fr Gegenseite
  zuerst gebrochen).
- **orb_us30 (ROT):** pausiert seit 04.10., kein neuer Punkt.
- **btc_ema_cross, gold_silver (GELB):** unveraendert, beobachten.
- **gold_asb gruen, obwohl der Live-Fill vom 15.10. verlor:** Die
  Ampel-Liste fuehrt fuer Gold ASB als letzten Trade den 28.09., den
  15.10.-Fill also nicht. Das ist dieselbe Luecke wie im Soll (Abschnitt 5).
  Die Ampel misst das Bein damit gerade nicht ganz so, wie es live handelt.

## 6. Auffaelligkeiten / offene Punkte

**(1) Standby in der Handelszeit: zweimal mit Folgen. Das ist der
wichtigste Befund der Woche.**
- **Mo 12.10., 09:55-17:09** (`Kernel-Power 506/507`): mehr als 7 Stunden kein
  Lauf auf allen drei Bridges. Verpasst: ORB NASDAQ (laut Soll ein
  Verlierer).
- **Do 15.10., 14:49-15:53**: Die ORB-Range endet um 15:45. Der erste Lauf
  danach (15:54) fand auf SP500 und NASDAQ beide Ausbruchsseiten schon
  durchlaufen ("breakout_passed ... vor Platzierung") und platzierte
  nichts. Die Logzeile `[ORB-PRAEZISE] Range-Ende in 110s` fehlt an diesem
  Tag. Geldwert diesmal positiv (Soll-Verlierer), aber ORB ist das einzige
  Bein, das ein verpasstes Fenster nie nachholt.
- **Nach dem Aufwachen am Do** war der Data Lake bis mindestens 17:06
  veraltet (`LakeStaleDataError`, letzte Daten 12:41 UTC). Alle Laeufe fielen
  auf Live-Abrufe zurueck und wurden langsam. Auf EK kam der Gold-ASB-Zeit-Exit
  dadurch **13 Minuten zu spaet** (18:13 statt 18:00 Serverzeit), diesmal
  zufaellig zum besseren Kurs (4.152,88 statt ca. 4.157).
- Weitere Standbys: Fr 16.10. 11:36-12:16, Fr 23:47-00:04 (ohne Folgen), Sa
  ab 15:02 bis So 11:09 (Wochenende).
- **Neu gegenueber KW40/41:** Das Muster "Standby faellt auf Arbeitsbloecke"
  passt diesmal nicht: Am Mo und Do gibt es tagsueber keine Commits. Die
  Ursache bleibt offen (siehe Memory: `standby_watchdog_schlaeft_mit`); der
  Watchdog schlief wieder mit.

**(2) CTNL-Altpositionen: weiter offen, ohne Zeit-Exit.** Unveraendert
seit KW41 (Dashboard "Braucht deine Bestaetigung", 12.10.):
- TTP: 18498503 (18.09., unrealisiert +440,74), 18696522 und 18696950
  (30.09.), alle ohne TP; ca. 21 bzw. 13 Handelstage alt (Zeit-Exit-Standard:
  4 Handelstage).
- IQ 1973249 und FK 1973231 (02.10.), 10 Handelstage alt.
- Folge diese Woche: TTP nahm wieder **keinen** CTNL-Trade (Deckel 3/2). Das
  hat am 15./16.10. zufaellig wieder Geld gespart (IQ -144, FK -36).
- Nichts angefasst (echtes Geld).

**(3) Soll/Ist sieht die beiden Live-Verlierer der Woche nicht.** Gold ASB
15.10. und CTNL 15.10. stehen live auf allen Konten, im Soll nicht (Abschnitt
5). Zusammen mit den bekannten ORB-Luecken (US30-Pause, NASDAQ-Storno) und
dem ORB-Timeout fuer EK/Funded ist Soll/Ist diese Woche kaum lesbar. Die
Gold-ASB-Luecke betrifft auch die Edge-Ampel (5b).

**(4) TTP-OU: Positionen ohne Modellfuehrung.** Neben DD (seit 15.09.) und
EOG (seit 21.09., bekannt und bewusst offen) meldet der Lauf jetzt auch
**STT** als "Titel fehlt im aktuellen Scan -- NICHT automatisch
geschlossen", und zwar am 16.10. um 21:43, **zwei Stunden nach dem eigenen
Entry** (19:43). Ein Titel, der gerade noch ein Einstiegssignal war und zwei
Stunden spaeter aus dem Scan faellt, deutet auf einen Datenausfall im
OU-Universum hin, nicht auf eine Modellentscheidung. Nicht geprueft.

**(5) `mt5_pull.py`: zwei stille Fehlerwege an einem Abend.** (a) 0 Deals bei
kaltem Terminal (bekannt), (b) FK nur mit `/portable` erreichbar. Beides
haette ohne Gegenprobe einen falschen Report ergeben ("EK 0 Trades", "FK
fehlt"). Ein Warte-und-Wiederholen bei 0 Deals mit offenen Positionen und
der `/portable`-Start wie in `executor.py` wuerden beides abfangen.

**(6) Datenpfad: nach jedem Aufwachen schlecht, sonst ruhig.** Gehaeuft am
Mo (nach Neustart 01:42) und Do (nach Standby): `str`/`float`-Fehler in
CLS/CTNL/Trend-Pullback-Scans, `dukascopy_python`-Haenger und IPC-Timeouts
beim Verbinden auf allen Funded/FK-Terminals (je zweiter Versuch teils auch
fehlgeschlagen). Am Di, Mi und Fr kaum Auffaelliges. FK zusaetzlich: am Di
dreimal "Server-Zeitzonen-Verifikation fehlgeschlagen (-8 bis -18 Minuten)",
ORB-Setup in diesen Laeufen abgebrochen; die NASDAQ-Orders wurden an dem Tag
trotzdem platziert (und storniert).

**(7) Kleineres.**
- FK warnt weiter in jedem Lauf "Kontostand weicht von STARTING_EQUITY=100.000
  ab". Bekannt, Floor-Pruefung offen.
- **Beantwortet sich nebenbei:** Die Dashboard-Frage "Kann IQ NASDAQ
  handeln?" (Noise-Area/Challenge, 16.10.). Ja: Die Funded-Bridge platzierte
  auf IQ am 13.10. und 16.10. ORB-Orders auf `NAS100.gbe` (Risiko je Seite
  ca. 107 USD). Ob das fuer K60 reicht (Haltedauer bis 16:00, Kosten), ist
  damit nicht gesagt.
- Research-Stand: Der Sammel-Commit `9ebdc80a` hat den grossen Teil gesichert;
  ungetrackt sind noch die Runde-2-Locks `smh_k4`-`k7` und
  `smh_microstructure/*.py`. Dieser Report committet bewusst nur
  `knowledge/reports/`.
