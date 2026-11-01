# Weekly Checkup - Performance - KW44/2026

**Abgedeckte Woche: Mo 2026-10-26 bis So 2026-11-01.** Erzeugt am So 01.11.
durch den geplanten `Forex-Weekly-Report`-Task.

**Datenbasis:** read-only MT5-Abzug `scripts/reports/mt5_2026-W44.json`
(26.10. 00:00 bis 02.11. 00:00 Serverzeit), Soll/Ist
`scripts/reports/soll_ist_2026-W44.json`, die Logs der drei Portfolio-Bridges,
das Windows-Ereignisprotokoll, `knowledge/CHANGELOG.md` und der Task Scheduler.

> **Zum Abzug:**
> - Die Startstaende ergeben sich sauber: Endstand minus Wochen-P&L trifft den
>   KW43-Endstand auf EK, IQ und FK auf den Cent, auf TTP bis auf 0,16 USD
>   (EK 2.855,88 EUR, TTP 99.489,21, IQ 97.461,70, FK 98.395,82 USD).
> - **Keine Handschliessung in der Woche:** Alle Ausstiege haben `reason` 3
>   (Bot) oder 4 (SL). Der eine Sonderfall steht in Abschnitt 6, Punkt 4.
> - Markt zu, die Kontostaende sind also auch der Wochenendstand.

## 1. Wochenkontext

Alle drei Portfolio-Bridges liefen mit echtem Geld (`DRY_RUN = False`, heute
geprueft): **EK-Portfolio-Bridge** (Tickmill 55918977),
**Funded-Portfolio-Bridge** (TTP Konto 2 504072729 + IQ Markets 16054) und
**FK Instant Funding** (BeyondIQCapital 17764). Alle sechs Bridge-Tasks stehen
auf `Bereit`, die Einzel-Bots bleiben `Deaktiviert`.

**Live-Aenderungen:**

- **Di 27.10. 17:56, Funded + FK:** ORB-Serverzeit auf New York + 7 h korrigiert
  (siehe Memory: `broker_serverzeit_ny_plus_7`).
- **Mi 28.10. 19:19, Funded:** OU-Ausstiege warten auf die NYSE-Kassazeit
  (Nutzerfreigabe nach KW43, Backup `_backup_20261028_ou_exit_gate/`).
- **Mi 28.10. und Fr 30.10., Data Lake + `_bar_length()`:** Lake-Reihen repariert,
  Schutzpruefungen beim Schreiben. Wirkt ueber den Lake auf CTNL.
- **So 01.11. 12:54, alle drei Bridges:** Gold-ASB-Ausfall-Ersatz (`allow_stale`)
  aktiv. Faellt nicht mehr in die Handelswoche, greift ab Montag. **Dazu steht eine
  Entscheidung offen** (Empfehlung im Dashboard: abschalten).

Die Woche bestand aus **drei Stoerungen und einem CTNL-Verlust:** rund 25,6 Stunden
Standby (Mo/Di), der Serverzeit-Fehler (bis Di) und der Netz-/DNS-Ausfall (Mi
abends bis Fr vormittag).

## 2. Risk-Management-Compliance

**Keine Regelverletzung. Kein Kill-Switch ausgeloest, kein Drawdown-Halt.**

| Bridge / Konto | Mechanismus | Diese Woche |
|---|---|---|
| EK-Portfolio | Trailing-DD-Kill-Switch 45 % | nicht ausgeloest; Balance 2.811,14 EUR (-1,57 %) |
| EK-Portfolio | Gesamtrisiko-Deckel 30 % | eingehalten; Deckel 843,34 EUR, zum Wochenende 0 offen |
| EK-Portfolio | CTNL-Kill-Switch | nie ausgeloest |
| EK-Portfolio | CTNL-Risiko je Order | **Mindestlot 0,01: Verlust -26,81 EUR = 0,94 % des Kontos in einem Trade.** Bekannt (siehe Memory: `ek_mindestlot_kehrt_hierarchie_um`) |
| Funded / TTP | 7-%-DD-Cap, offenes Risiko 3,5 % | inaktiv; schlechtester Tag Di 27.10. -175,89 USD; Balance -0,95 % seit Start |
| Funded / IQ | 6 % Gesamt-DD / 1 % je Position | inaktiv; schlechtester Tag **Mi 28.10. -297,78 USD**. Balance 96.906,81 USD = **-3,09 % seit Start, ca. 2.907 USD Abstand** zur 6-%-Grenze (KW43: ca. 3.460) |
| Funded (beide) | CTNL-Kill-Switch | nie ausgeloest |
| FK Instant Funding | 5-%-EOD-Trailing-DD | inaktiv; schlechtester Tag Di 27.10. -81,76 USD; Balance 98.299,49 USD (-1,70 % seit Start) |
| FK Instant Funding | CTNL-Kill-Switch | nicht ausgeloest. 128x "Scan ohne Trades (Datenluecke?) -- kein Urteil, Zustand bleibt aus". **Waehrend des Ausfalls konnte der Schalter also nicht urteilen** |

**Zur Kenntnis:** Der Abstand von IQ zur 6-%-Grenze ist wieder geschrumpft (-555 USD).
Der Rueckgewinn aus KW43 ist damit zu rund 40 % weg.

## 3. Was hat gut / nicht gut funktioniert

- **EK-Portfolio-Bridge (Tickmill): -44,74 EUR (-1,57 %) bei 9 Trades.** CTNL -38,95
  (der Short vom 23.10. nahe null, zwei Shorts vom 27.10. ausgestoppt). OU -8,56:
  Am 27.10. schlossen fuenf Positionen per `max_hold`, FLEX allein -15,69. ORB +2,77:
  NASDAQ-Short gefuellt und nach 19 Sekunden wieder geschlossen.
- **Funded-Portfolio-Bridge (TTP + IQ): -997,82 USD (-0,51 %) bei 11 Trades.** Fast
  alles CTNL (**-915,27**): Die beiden Shorts vom 23.10. und die beiden vom 27.10.
  liefen auf beiden Konten in den Stop, auf IQ mit groesseren Lots (zuletzt 0,08 statt 0,05). ORB -83,86
  (nur TTP, US500-Long 30.10. nach 66 Sekunden ausgestoppt). OU +1,31.
- **FK Instant Funding: -96,33 USD (-0,10 %) bei 5 Trades.** Nur CTNL. Klein, weil
  FK 0,01-0,02 Lot faehrt. Der eine Gewinner (+6,33) kam aus einem verschobenen
  Stop, dessen Herkunft unklar ist (Abschnitt 6, Punkt 4).

**Muster der Woche:** **92 % des USD-Verlusts sind ein einziger Gegenlauf.** Gold
stieg vom 27. bis 28.10. bis auf 4.082; alle CTNL-Shorts lagen davor. Danach fiel
Gold bis Fr 30.10. auf 3.891, also genau in die alte Richtung, aber da war CTNL schon
ausgestoppt und **Gold ASB hat den Short vom 30.10. wegen des Ausfalls nicht gelegt**.
Auf Funded wurde aus ORB in der ganzen Woche nur ein Trade (ein Konto, ein Bein).

## 4. Trades, Winrate, Gewinn - Summary

Gezaehlt sind geschlossene Positionen (Ausstiegs-Deal in der Woche), netto inkl.
Kommission und Swap. Die Prozentwerte beziehen sich auf den Kontostand zu Wochenbeginn.

| Bridge | Trades | Winrate | P&L | % |
|---|---|---|---|---|
| EK-Portfolio (Tickmill, echtes Geld) | 9 | 44,4 % | **-44,74 EUR** | **-1,57 %** |
| Funded-Portfolio (TTP + IQ, echtes Geld) | 11 | 9,1 % | **-997,82 USD** | **-0,51 %** |
| FK Instant Funding (LIVE, echtes Geld) | 5 | 20,0 % | **-96,33 USD** | **-0,10 %** |
| **Gesamt (alle 3, echtes Geld)** | **25** | **24,0 %** | **-44,74 EUR / -1.094,15 USD** | **ca. -0,38 %** |

- **Keine Summe ueber beide Waehrungen.** Fuer die Gesamt-Prozentzahl ist EK mit
  2.855,88 EUR (ca. 3.340 USD bei angenommenen 1,17, nicht abgefragt) in ein Buch von
  ca. 298.700 USD eingerechnet.
- Je Konto: TTP 7 Trades **-442,93 USD (-0,45 %)**, IQ 4 Trades **-554,89 USD (-0,57 %)**.
- **Noch offen auf TTP:** STT (seit 16.10., +5,07) und NEM (seit 27.10., -10,52).
- **TTP Konto 2** steht weiter auf `trade_mode = 0` (Demo-Server), das IQ-Konto heisst
  "BeyondIQCapital **Demo** Challenge". Die Einordnung als "echtes Geld" uebernehme
  ich unveraendert aus `CLAUDE.md`.

## 5. Soll/Ist je Bridge

**Soll** ist ein Backtest ueber das Fenster 26.10. 00:00 bis 30.10. 21:00 (UTC) mit
Sizing und Kostenannahme der jeweiligen Bridge und der Konfiguration von HEUTE.

| Bridge | Soll | Ist | platziert | nicht platziert | nie gesehen |
|---|---|---|---|---|---|
| EK-Portfolio | 12 Trades / **+5,33 %** | -44,74 EUR (-1,59 %) | - | - | - (**12 nicht_ermittelbar, -0,92 R**) |
| Funded-Portfolio | 12 Trades / **+0,21 %** | -996,74 USD (-0,51 %) | 1 (-1,09 R) | 1 (+5,45 R) | 10 (-5,39 R) |
| FK Instant Funding | 12 Trades / **-0,52 %** | -96,08 USD (-0,10 %) | 1 (+5,45 R) | 1 (-1,09 R) | 10 (-5,39 R) |

(Die Ist-Werte weichen um rund 1 USD von Abschnitt 4 ab, weil das Werkzeug
Einstiegskommissionen anders zuordnet. Die Prozentbasis ist dort der heutige Kontostand.)

**Hauptaussage: Die Soll-Zahl ist diese Woche kein brauchbarer Massstab.** Ihr groesster
Posten, CTNL +5,45 R, ist sehr wahrscheinlich ein Modellartefakt, und drei weitere Posten
gehoeren zu einem stillgelegten bzw. pausierten Bein.

**Pflicht-Vorbehalte:**

1. **Konfiguration:** Soll rechnet mit dem heutigen Stand. Die ORB-Serverzeit (27.10.) und
   das OU-Gate (28.10.) aendern am Soll nichts, weil das Soll weder die Live-Zeitpruefung
   noch OU-Signale enthaelt. Die Lake-Reparaturen sind im Soll enthalten, live galten sie
   bis 30.10. nicht. Der Ausfall-Ersatz (01.11.) ist nicht im Soll.
2. **EK laesst sich nur grob zerlegen** (SQLite statt Signal-Ledger). "12 nicht_ermittelbar"
   heisst genau das, nicht "nie gesehen". Die +5,33 % entstehen durch die Mindestlot-Verzerrung.
3. **EKs Kostenannahme ist geschaetzt** (0,50 Pips), Funded (2,05) und FK (1,30) sind
   gemessen. EK-Zahlen deshalb nicht gegen die anderen beiden stellen.

**Was hinter den Posten steckt (Funded und FK gleich, soweit nicht anders genannt):**

- **CTNL 27.10. 15:00 UTC, Short, Soll +5,45 R (Ziel am 30.10.): sehr wahrscheinlich
  Artefakt des Schlusskurs-Stops.** FK platzierte einen passenden Short mit SL 4.076,96.
  Der Lake zeigt am 28.10. 20:00 UTC ein Hoch von **4.081,96**, aber der hoechste
  M15-Schluss bleibt bei **4.074,29**. Beim Broker waere der Stop also gefallen, die Engine
  prueft nur den Schluss. Die Zuordnung Soll-Trade zu SL ist aus den Kursen erschlossen und
  nicht je Trade aus der Engine ausgelesen (siehe Memory:
  `engine_schlusskurs_sl_vs_broker_intrabar`). Dazu passt der zweite Soll-Trade: Der stoppt
  um 19:45 UTC beim Schluss 4.074,29, also ueber dem Live-SL 4.073,55.
- **Dass TTP und IQ diesen Short nicht haben ("nicht platziert"):** vermutlich der
  CTNL-Deckel von 2, weil dort schon zwei Shorts offen waren. Nicht je Lauf geprueft.
- **Gold ASB 30.10., Short, +1,93 R: wirklich verpasst, der teuerste Punkt der Woche.**
  Grob **ca. 2.640 USD** auf Funded + FK (Risiko je Konto vom 26.10.: 597 / 650 / 119 USD,
  mal R), auf EK grob 99 EUR. **Vorbehalt:** Der am 01.11. gebaute Ausfall-Ersatz haette
  diese Order laut CHANGELOG ebenfalls nicht gelegt (Friktion ueber der Schwelle).
- **ORB 26.10., NASDAQ +2,76 R und SP500 -1,03 R: wirklich nie gesehen, Standby.** Netto
  +1,73 R, grob **+600 USD** auf Funded + FK (mit Risiken je Seite der Vorwoche). **Auch EK
  verpasste beide** (+2,87 / -1,03 R).
- **ORB 27.10., NASDAQ Short -1,02 R:** TTP, IQ und FK durch den Serverzeit-Fehler blockiert,
  es wurde also ein Verlierer gespart. EK war dabei und schloss mit +2,77 EUR.
- **ORB 29.10. und 30.10., NASDAQ je -1,02 R:** live storniert ("Kurs erreichte den geplanten
  SL vor dem Einstieg"). Das Soll kennt das Storno nicht (Werkzeugluecke seit KW41). Gespart.
- **`ctnl_continuation` 3 Trades, -4,96 R: Werkzeugfehler.** Das Bein ist seit 01.10.
  stillgelegt, `soll_ist.py` fuehrt es auf EK und Funded aber weiter als `live_bein`. Auf FK
  steht korrekt "nicht live". **Ohne dieses Bein** liegt das Soll um fast 5 R hoeher.
- **`orb_us30` -1,04 R: pausiert seit 04.10.**, trotzdem im Soll.
- **TTP US500 30.10. (-83,86 USD) ohne Soll-Gegenstueck:** TTP wurde gefuellt, IQ und FK
  stornierten ("Kurs brach zuerst in Gegenrichtung"). Das ist wieder der andere Kursfeed je
  Konto (wie am 23.10.).

## 5b. Edge-Warnstufen je Live-Bein

**Diese Woche NICHT frisch, der Stand ist der von KW43.** `research_live_legs.py tickmill --ampel`
lief zweimal ohne Ergebnis: Lauf 1 stand ab 18:35 still (bei einem Dukascopy-Abruf 2019) und wurde
vom 50-Minuten-Limit beendet. Lauf 2 kam bis ORB US30 und wurde nach 60 Minuten abgebrochen (Exit 124).
Die Liste `live_trades_tickmill_ampel.csv` stammt damit weiter vom **27.10. 23:35, letzter Trade gesamt
25.10.** `research_edge_monitor.py --stage status` lief sauber, rechnet aber auf dieser alten Liste.
**KW44 ist in der Tabelle also nicht enthalten.**

| Bein | Warnstufe | Drawdown R / Schwelle R | Signal |
|---|---|---|---|
| orb_sp500 | **ROT** | **23,2** / 15,2 | alle fuenf rot |
| orb_us30 | **ROT** (pausiert) | 24,5 / 13,2 | alle fuenf rot |
| btc_ema_cross | GELB | 2,0 / 5,4 | roll_mean, cusum, sprt streng rot |
| gold_silver | GELB | 1,7 / 4,9 | roll_mean streng rot |
| gold_asb, ctnl_reversal, cls_practical, orb_nasdaq, ou_modell, trend_pullback | gruen | - | - |

- **orb_sp500 (ROT):** gegenueber der Vorwoche keine Aussage moeglich. Das Soll enthaelt fuer KW44 einen
  Verlierer (26.10., -1,03 R), das Loch waere danach grob 24,2 R (meine Ueberschlagsrechnung, kein
  Lauf des Monitors). Steht im Dashboard und ist entschieden ("ORB bleibt erstmal so", 16.10.), kein neuer Eintrag.
- **orb_us30 (ROT):** pausiert seit 04.10., unveraendert.
- **btc_ema_cross, gold_silver (GELB):** unveraendert, beobachten.
- **Bekannte Luecke bleibt:** gold_asb fuehrt als letzten Trade weiter den 28.09.; der Live-Fill vom 15.10. fehlt
  (Dashboard-Punkt aus KW42). Eine Warnung ist ein Grund hinzusehen, kein Grund, einen Bot zu aendern.
- **Werkzeug:** Das ist nach dem 18.10. der zweite solche Ausfall (Dukascopy-Abruf ohne Timeout). Im Dashboard
  steht der Punkt "Report-Werkzeuge haerten" bereits, ich habe ihn ergaenzt.

## 6. Auffaelligkeiten / offene Punkte

**(1) Korrektur zu KW43: Am Mo 26.10. lag ORB nicht nur am Serverzeit-Fehler, die ganze
Flotte schlief.**
- Alle Lanes aller drei Bridges haben dieselbe Luecke: **Mo 26.10. ca. 10:38 bis Di 27.10.
  12:13** (Berlin), also ca. 25,6 Stunden.
- Ereignisprotokoll (UTC): Eintritt 26.10. 09:38 (Grund 15/28), kurzer Austritt 11:25
  (Grund 55), Austritt **27.10. 11:11**. Der Akku stand bei ca. 46.000 mWh, der Verbrauch
  bei 269 und 179 mWh. **Kein leerer Akku wie am 20.10.**, auch kein `Kernel-Power 41`.
  Die Grundcodes habe ich nicht entschluesselt, die Ursache ist **offen**.
- **Folge:** ORB am 26.10. auf allen Konten verpasst, auch auf EK. KW43 und CHANGELOG schreiben
  "EK nicht betroffen" und "2 Tage ohne ORB wegen Serverzeit"; das stimmt fuer den Di, am Mo
  haette es auf TTP/IQ/FK den Fehler zwar auch gegeben, praktisch entschied aber der Standby.
- Der Watchdog schlief wieder mit. Der OU-`max_hold` auf EK (11 Tage bei Grenze 10) kam
  vermutlich deshalb einen Tag spaet; nicht belegt.

**(2) Neuer Hinweis zum Ausfall 28.-30.10.: Das sieht eher nach dem lokalen Netz aus als nach
Dukascopy.** Das Dashboard laesst die Frage offen und nennt "fast nur freeserv.dukascopy.com".
Im EK-Log gibt es aber im selben Fenster auch **195 Fehler auf `api.binance.com`** (28.10. 22:29
bis 30.10. 10:49), dazu `Authorization failed` beim MT5-Verbinden auf allen Bridges um 22:16-22:18
(Berliner Zeit). Damit fielen mindestens zwei unabhaengige Anbieter aus. Kein Beweis, aber die
Massnahme waere eine andere (DNS am Rechner statt Datenquelle). Die Details zur Kaskade stehen
schon im Dashboard (siehe Memory: `dukascopy_ausfall_kaskade`).

**(3) EK 29.10.: `can't start new thread` und OpenBLAS-Speicherfehler** (20:18 bzw. 10x ab 21:14),
dabei fielen `ORB-Setups`, `trend_pullback_gold` und `trend_pullback_silver` je einen Lauf aus.
Bereits im Dashboard, Zusammenhang mit haengenden Aufrufen weiter nur vermutet. Eine Haeufung
gab es in dieser Woche nur am Ausfalltag.

**(4) FK: SL ohne Bot-Spur verschoben.** Die Position 2624779 (Short ab 4.061,34, im Log
`sl=4076.96`) schloss am 28.10. 21:36 Serverzeit als SL-Ausstieg bei **`[sl 4058.00]`, +6,33 USD**.
Der SL lag also unter dem Einstieg. Das FK-Log enthaelt zu diesem Ticket keine Zeile. Der Stop wurde
also vermutlich von Hand gezogen, was ohne diese Verschiebung ein Verlust von ca. 32 USD gewesen waere.
**Nicht belegt, im Dashboard zur Bestaetigung eingetragen.**

**(5) TTP-OU: Die KW43-Frage ist beantwortet.** UAL und FLEX werden vom Modell gefuehrt (`ABGLEICH
... Modell ist ausgestiegen`: UAL 28.10. +8,64, FLEX 30.10. -7,33). **STT bleibt die Waise**: Sie
meldet weiter "Titel fehlt im Scan", waehrend EK dieselbe Aktie am 27.10. per `max_hold` schloss.
**NEM** (neu seit 27.10., Risiko 49,72 USD) meldet das auch, allerdings nur am 29./30.10. und damit
im Ausfall. Beobachten.

**(6) OU-Gate wirkt erst seit Mittwochabend.** Vor dem Fix gab es fuer UAL am 28.10. von 05:12 bis
14:28 noch **66 abgelehnte Schliess-Orders** (`10018 Market closed`). Danach keine weiteren im Log.

**(7) Soll/Ist braucht Pflege.** `ctnl_continuation` und `orb_us30` zaehlen im Soll, das
ORB-Storno fehlt, ORB-Fills werden nicht zugeordnet, und CTNL rechnet mit Schlusskurs-Stop. In dieser
Woche verschieben diese vier Punkte zusammen mehr R als das ganze Ergebnis.

**(8) Kleineres.**
- Scan-Fehler `'>' not supported between 'str' and 'float'` trat nur beim Aufwachen auf (26./27.10.,
  dann veralteter Lake). Das passt zur Vermutung im Dashboard.
- FK warnt weiter in jedem Lauf "Kontostand weicht von STARTING_EQUITY=100.000 ab" (bekannt).
- Die Logs der Bridges enthalten den Telegram-Bot-Token im Klartext (Fehlermeldung mit URL).
  Geprueft: nicht in `bridge_status/snapshot.json` und nicht im Repo. Nur lokal, Hinweis fuer den
  Fall, dass Logs je geteilt werden.
- Dieser Report committet bewusst nur `knowledge/reports/`. Im Working Tree liegen die uncommitteten
  Aenderungen der Session vom 01.11. (`pending.py`, `reader.py`, Edge Card EURUSD).
