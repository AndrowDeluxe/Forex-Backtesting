# Weekly Checkup - Education - KW43/2026

**Abgedeckte Woche: Mo 2026-10-19 bis So 2026-10-25.** Erzeugt am Di 27.10.
abends durch den geplanten `Forex-Weekly-Report`-Task (verspaetet).

## 1. Was stand die Woche an / Hauptfokus

Eine Woche mit **zwei Live-Fixes am Montag** und danach fast nur Research im
Dachprojekt Quant x diskretionaer. Sechs Faeden:

- **Live (Mo 19.10.):** OU steigt nur noch auf fertigen Tageskerzen ein
  (Funded, `7c26f58c`), und die Bridges laufen im Akku weiter (Task-Flags,
  Zuklappen = nichts tun). Beides Antworten auf Befunde aus KW42.
- **Key Levels abgeschlossen (Mo):** Magnet-Trade vor dem Level getestet
  (0 von 16 Zellen), danach die Linie auf deinen Entscheid geschlossen. Lock
  `keylevels_v1` bleibt mit 482 Versuchen versiegelt.
- **Makro-Agent (Di/Mi):** Regimekarte Wachstum x Inflation aus First Prints
  nachgebaut (`fusion_lab/macro_regime/`, `80eb8f95`/`b60d538f`),
  Wissensnotiz zu den Wirkketten aus den SMT-Reports, Backtest der
  SMH-Makro-Reports v2 (909 Ideen).
- **Copy Trading "SMH Daily Update" (Mo-So):** Edge Card mit dir fertig,
  Lock, Bild-Auslesung per `claude -p`, Stichprobe, Probelauf, am So/Mo das
  IS-Raster: kein Edge.
- **Quantum OmniGold (Di/Mi):** Nachbau eines gekauften Gold-EAs aus dem
  MT5-Tester (Schritt 3 von 6), dabei zwei Daten-Fallen gefunden.
- **CLS-Praxis-Call (Mi):** Call transkribiert, drei Ideen daraus gegen die
  Engine getestet, alle verworfen.

**Commits der Woche: nur zwei** (`80eb8f95`, `b60d538f`, beide Di 10:47,
Regimekarte), dazu die automatischen Snapshot-Commits. **Der Rest der
Wochenarbeit liegt ungesichert im Working Tree:** `fusion_lab/copy_trading/`,
`mt5_quantum_omnigold/`, `keylevels/magnet.py` + `bos.py` + Ergebnisse, fuenf
neue Projektnotizen, vier Lock-Dateien (u. a. `copy_trading_daily_update_20261020`,
`cls_practical_smh_call`). Das ist dasselbe Muster wie in KW41.

## 2. Aktive Zeiten

Nach Memory-Zeitstempeln, CHANGELOG-Daten, Commits und dem
Energie-Protokoll:

- **Mo 19.10. Vormittag** (10:30-12:15: Akku-Analyse, OU-Fix, Key Levels),
- **Di 20.10. Vormittag** (Regimekarte, Commit 10:47), danach unterwegs im
  Akkubetrieb, **ab 12:36 Standby, ab 13:46 aus bis 20:58**,
- **Di und Mi abends bis ca. 23:15** (OmniGold, SMH-Reports, Copy Trading,
  CLS-Call),
- **Nacht So/Mo 26.10., ca. 03:30** (Copy-Trading-Raster).

Do bis Sa gibt es kaum Spuren; die Copy-Trading-Auslesung stand vom 22. bis
26.10. wegen des Abo-Kontingents (429). Wieder vor allem Abende und Naechte.

## 3. Meine Main Erkenntnisse

### 3.1 Validiert auf dem Schlusskurs, gehandelt auf dem laufenden Kurs: so entstehen verwaiste Positionen

**Befund:** Drei TTP-Positionen (DD seit 15.09., EOG seit 21.09., STT seit
16.10.) liefen wochenlang ohne Modellfuehrung, nur mit einem sehr weiten
Broker-SL (8 Sigma), ohne TP und ohne MA20-Ausstieg. Das Modell waere bei DD
am 22.09. und bei EOG am 05.10. (144,08) ausgestiegen. EOG stand am 22.10.
bei 157,66, als du es von Hand geschlossen hast (+301,90 USD). Dieser Gewinn
ist Glueck, nicht Modell.

**Mechanismus / Warum:** Das OU-Bein rechnet das Tages-Bollinger-Signal auch
waehrend der US-Session. Die heutige Tageskerze im Lake ist dann noch nicht
fertig. Liegt der Kurs mittags unter dem Band, eroeffnet die Bridge echt.
Schliesst der Tag wieder ueber dem Band, gibt es das Signal in keinem
spaeteren Scan mehr. Die Bridge schliesst Titel, die aus dem Scan fallen,
absichtlich nicht ("NICHT automatisch geschlossen"). Die Position laeuft
also einfach weiter, ohne Plan.

**Wie es aufgefallen ist:** STT fiel am 16.10. zwei Stunden nach dem eigenen
Entry aus dem Scan; in KW42 lag die Hypothese "Datenausfall" nahe. Die
Gegenprobe zeigte frische Lake-Daten. Entscheidend war dann der Vergleich der
Schlusskurse am Einstiegstag mit dem Band: Alle drei lagen darueber (DD
128,04 > 123,06, EOG 141,38 > 140,35, STT 165,72 > 164,75). Ein Nachlauf ueber
sechs Scan-Tage mit fertigen Kursen enthielt keinen der drei Trades.

**Lehre / Regel:** Ein Signal auf einer Kerze, die noch laeuft, ist eine
andere Strategie als die validierte. Live nur auf abgeschlossenen Kerzen
rechnen, und "Titel fehlt im Scan kurz nach dem Entry" zuerst als
Einstiegsfehler pruefen, nicht als Datenluecke. Der Fix hat zwei Teile, die
zusammengehoeren: fertige Tageskerze plus Signalalter in Handelstagen (sonst
verfallen Freitagssignale am Montag).
siehe Memory: `ou_einstieg_auf_laufendem_tageskurs` · [[ou-modell-kostenvalidierung]]

### 3.2 Verfuegbarkeit: Der Akku-Fix vom Montag hat das Standby-Problem verschoben, nicht geloest

**Befund:** Am Mo 19.10. wurde die Ursache der KW42-Ausfaelle gefunden
(Akkubetrieb unterwegs) und abgestellt. Am **Di 20.10. lief trotzdem von
13:50 bis 21:03 keine einzige Bridge**. Verpasst: ein ORB-SP500-Long, der im
Soll mit **+5,97 R** ins Ziel lief, netto mit dem NASDAQ-Verlierer ca.
**+4,9 R, auf Funded + FK grob 1.500 USD**.

**Mechanismus / Warum:** Zwei Ursachen hatten die KW42-Ausfaelle: Zuklappen
im Akku loeste Standby aus, und vier Tasks (EK-Fast, alle Lake-Ingests)
starteten im Akku gar nicht. Seit Montag laufen die Tasks im Akku weiter.
Am Dienstag zeigt das Protokoll: Standby um 12:36 (Akku 9.770 mWh), die
Bridges liefen trotzdem weiter, um 13:46 erneuter Standby bei **2.300 mWh**,
dann bis 20:58 nichts und danach ein **Neustart nach unsauberem Ende**
(`Kernel-Power 41`). Wahrscheinlichste Lesart: Der Akku war leer. Wer die
Maschine unterwegs wach haelt, verbraucht den Akku schneller. Das ist eine
Hypothese, nicht belegt.

**Wie es aufgefallen ist:** Die Soll/Ist-Zerlegung meldete fuer den 20.10.
zwei "nie gesehen". Die Lueckensuche ueber alle Logs zeigte dieselbe Luecke
in **allen** Lanes aller drei Bridges (also die Maschine), dann das
Ereignisprotokoll. Wichtig: die XML-Ansicht nehmen, die Textansicht zeigt
Ortszeit mit "Z".

**Lehre / Regel:** Auf einem Notebook ist Verfuegbarkeit ein Zielkonflikt:
wach bleiben kostet Akku, Standby kostet Trades. Das laesst sich mit
Energieoptionen verschieben, aber nicht loesen. Fuer zeitpunktgebundene Beine
wie ORB braucht es eine Maschine, die nicht unterwegs ist (VPS, Ideen-Inbox
19.10.).
siehe Memory: `standby_watchdog_schlaeft_mit`

### 3.3 Copy Trading: Der "beste" t-Wert war offene Gold-Longs bis zu einer erfundenen Haltegrenze

**Befund:** Im IS-Raster der Copy-Trading-Calls (2.784 Setups,
17.03.2025-31.03.2026, Lock mit 124 Versuchen) hatten die nach t-Wert
besten Konfigurationen **bis +1,7 R je Trade, t 2,9**. Ihr ganzes Plus kam aus
Trades, die nie SL oder TP erreichten und erst an der angenommenen
Hoechstdauer von **90 Tagen** bewertet wurden: Gold-, Silber- und
US500-Longs der Rallye 2025 mit engem ATR-Stop (bis +181 R je Trade). Ohne sie
negativ, Shorts negativ, 2026 etwa null. Mit begrenztem Ziel ist das beste
Ergebnis +0,44 R (t 1,4), nicht signifikant.

**Mechanismus / Warum:** "TP ohne" plus eine Haltegrenze, die nie geprueft
wurde, macht aus jedem Long in einem Trendjahr einen Lotterieschein. Ein
t-Wert-Kriterium bevorzugt genau das: wenige riesige Gewinner auf engen
Stops. Gemessen wird dann Trend-Beta von 2025, nicht das Koennen des Callers.

**Wie es aufgefallen ist:** Die Gewinner hatten nur 5-12 % Treffer, das passt
nicht zu Dennis' Track Record. Die Aufteilung nach Ausstiegsgrund (offen
bewertet / SL / TP), Long/Short und Jahr zeigte die Herkunft. Davor hatte
schon deine Stichprobe (9 von 50 Bildern falsch gelesen) eine zweite Lesart
der Watch-Charts erzwungen: Die Zone ist oft das **Ziel** des laufenden
Trades, nicht der Einstieg.

**Lehre / Regel:** Bei Rastern mit offenem Ziel oder Trailing immer zuerst (1)
Anteil und R der offen bewerteten Trades, (2) Abhaengigkeit von den Top 5,
(3) Long/Short und Jahre getrennt pruefen, bevor etwas eingefroren wird. Eine
Haltegrenze ist ein Parameter, keine Nebensache. **Nachtrag 27.10. (nach der
Woche):** Auf deinen Entscheid wurde A2 eingefroren und das OOS einmal
geoeffnet: 70 Trades, **Oe -0,72 R, t -3,65**. Damit verworfen.
siehe Memory: `copy_trading_is_kein_edge_offene_trades` ·
`copy_trading_watch_zone_ziel_oder_einstieg` · [[copy-trading-dennis-edge-card]]

### 3.4 Eine LLM-Auslesung ist erst nach deiner Stichprobe ein Datensatz

**Befund:** Zweimal in derselben Woche war die automatische Auslesung von
Mentor-Material falsch genug, um einen Test zu entwerten. SMH-Makro-Reports
v1: Sterntabellen uebersehen, eine Richtung verdreht, Status falsch
definiert. Copy Trading: 9 von 50 Watch-Charts anders gelesen als von dir.
Erst mit der korrigierten v2 ergab der Report-Backtest ein sauberes Bild:
Richtungs-Calls zum Marktpreis **ohne Edge (A1 -0,027 R, n 604)**, der
Ruecksetzer-Einstieg leicht positiv (**+0,060 R, Sigma +24,6 R, Perm-p 0,06,
DSR 0,47**), kein Beleg.

**Mechanismus / Warum:** Ein Sprachmodell, das "deuten" soll, legt sich bei
mehrdeutigem Material still auf eine Lesart fest, auch mit Zitatpflicht. Bei
Bildern (gemalte Pfade) ist das noch staerker. Der Fehler ist systematisch,
nicht zufaellig, und fliesst damit ungebremst in jede Variante.

**Wie es aufgefallen ist:** Durch deine Stichproben, nicht durch Code-Tests.
Die Extraktion sah formal sauber aus (alle Felder gefuellt, Zitate
vorhanden). Die Konsequenz: Bild-KI liest nur noch Objektives (Pfadschenkel,
Umkehrpunkt, Zone, Farben), und die Deutung wird als gezaehlte Variante in
die Simulation gelegt.

**Lehre / Regel:** Bei jeder LLM-Extraktion eine Nutzer-Stichprobe
einplanen, **bevor** ein Lock eingefroren wird. Inhaltlich fuer den
Makro-Agenten: Der Wert der Reports liegt nicht in der Richtung, sondern im
Einstieg (Ruecksetzer), in der Ueberzeugung (5 Sterne +0,20 R) und im Asset
(Edelmetalle ja, FX-Kreuze nein), alles Forward-Hypothesen bis 31.01.2027.
siehe Memory: `smh_reports_richtung_kein_edge_ruecksetzer` · [[smh-makro-reports-backtest]]

### 3.5 Ein gekaufter Gold-EA: Die Rendite haengt am Tick-Modell des Testers

**Befund:** Gleicher EA (Quantum OmniGold), gleicher Zeitraum 07/2023-10/2026,
nur das Tick-Modell gewechselt: mit echten Ticks **+1.315.741 USD**, mit
1-Min-OHLC **+131.842 USD**. Lot-neutral in USD je Unze ist **2026 mit echten
Ticks +492, mit OHLC -212**. Nur die Haelfte der Einstiege ist in beiden
Laeufen identisch.

**Mechanismus / Warum:** Der EA lebt von Mikro-Ausstiegen bei +2 bis +3 USD
(Trefferquote 75-92 %, Erwartungswert 1-3 USD je Trade). Das ist so fein wie
Spread und Slippage live. Welches Tick-Modell der Tester nutzt, entscheidet
dann darueber, welche Ausstiege ueberhaupt passieren. Die Schlagzeilenrendite
ist vor allem Zinseszins plus Lot-Verdopplung.

**Wie es aufgefallen ist:** Beim Nachbau. Zwei Datenfallen kamen dazu: Der
Tester-Server MetaQuotes-Demo hat fuer 2021 bis 04/2025 **keine** XAUUSD-Ticks
(Tester rechnet dort mit Ersatzdaten), und der EA hat eine eingebaute
Datumssperre vor dem 03.01.2022. Die Brokerzeit im Tester ist EU-Regel, nicht
"NY + 7" (Vertiefung 4b).

**Lehre / Regel:** Gekaufte EAs nie nur im Echt-Tick-Modus beurteilen. Immer
eine Gegenprobe mit einem anderen Tick-Modell und lot-neutral rechnen, bevor
Geld daraufgesetzt wird. Ein Edge, der kleiner ist als die Unschaerfe der
Daten, ist nicht messbar.
siehe Memory: `omnigold_edge_haengt_am_tickmodell` ·
`metaquotes_demo_tick_luecke` · [[quantum-omnigold-nachbau]]

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Copy Trading "SMH Daily Update" (Mentor-Calls, kein Paper):** (a)
  Behauptung: Dennis' Track Record 2025 +313 %, 2026 bis 17.09. +19 %; seine
  Chart-Calls sollen kopierbar sein. (b) Edge Card mit dir (20 vorab
  registrierte Varianten, Typ A Trade-Idee und Typ B Watch), Auslesung von
  ca. 4.000 Bildern, IS 17.03.2025-31.03.2026 auf Dukascopy M1. (c) Kein Edge:
  Trade-Ideen kopiert im Probelauf -0,27 R, im Raster nur ein Artefakt offener
  Trades (3.3); bestes begrenztes Ziel +0,44 R, t 1,4. (d) **Verworfen
  (27.10., nach der Woche):** A2 eingefroren, OOS 01.04.-16.10.2026 70 Trades,
  Oe -0,72 R, t -3,65. Der Task `Telegram-Import-SMH-Daily` laeuft weiter. [[copy-trading-dennis-edge-card]] ·
  [[copy-trading-dennis-edge-card-final]]
- **SMH-Makro-Reports v2 (Mentor-Reports):** (a) Die Reports geben
  Richtungen mit Sternen und Gates vor. (b) 909 Ideen aus 116 Reports, Lock
  `smh_macro_reports_v2`, IS 08/2025-10/2026, 5 Varianten. (c) Richtung allein
  ohne Edge (A1 -0,027 R), Ruecksetzer-Limit +0,060 R, DSR 0,47. (d)
  **Forward bis 31.01.2027**, Hypothesen fuer den Makro-Agenten (3.4).
  [[smh-makro-reports-backtest]]
- **SMH CLS-Praxis-Call:** (a) Der Mentor nennt CLS ein Kontext-Framework
  mit kritischer Zeitbox 08:45-09:30; alle Beispiele sind handverlesen. (b)
  Drei Abweichungen von unserer Engine als Varianten, Lock
  `cls_practical_smh_call` (IS bis 31.05.2022), Live-Konfiguration mit
  TTP-Kosten. Basis IS +0,17 / OOS +0,31 R je Trade. (c) V1 Limit am
  06:00-Kurs: IS +0,84 R, aber n = 12, OOS nur +0,15 R; V2 Zeitausstieg 12:00
  und V3 TP an der Range-Gegenseite im IS schlechter. (d) **Verworfen**,
  keine Bot-Aenderung. [[smh-cls-praxis-call]]
- **Quantum OmniGold (gekaufter EA):** (a) Tester-Bericht: aus 100k werden
  1,4 Mio. USD in drei Jahren. (b) Nachbau aus 1.424 Tester-Einstiegen gegen
  Dukascopy und MT5-Ticks. (c) Die Rendite haengt am Tick-Modell, 2026
  lot-neutral mit OHLC -212 USD je Unze (3.5). (d) **In Arbeit** (Schritt 3
  von 6: Regeln herleiten), kein Geld darauf. [[quantum-omnigold-nachbau]]
- **Regimekarte Wachstum x Inflation (Brief von A. Landi):** (a) Assets
  verhalten sich je BIP-/CPI-Regime (Richtung und Tempo) verschieden. (b)
  Nachbau aus ALFRED-First-Prints, 7 Assets; am 18.09. dasselbe Regime wie die
  Vorlage, Tagesanteile +-1,5 pp. (c) Kein Test einer Handelsregel, nur der
  Kontext; aktuell g up/slow x pi up/accel. (d) **Baustein fuer den
  Makro-Agenten**, Automatik erst mit dem Agenten. [[regimekarte-wachstum-inflation]]
- **Wirkketten und Regeln aus den SMT-Deep-Dives:** (a) Jede These als Kette
  (Kette / So laeuft sie / Woran man sieht / Was sie stoppt), ">= 75 %
  eingepreist = kein Trigger", Positionierungs-Gate. (b) Destilliert, nichts
  getestet. (c) - (d) **Blaupause fuer den Makro-Agenten**; Engpass ist das
  OIS-Pricing aus einem Bezahlterminal. [[makro-wirkketten-und-regeln]]
- **Key Levels, Abschluss:** Magnet-Trade (Einstieg 10/20 Pips vor dem Level,
  ca. 917.000 Einstiege, nur IS) 0 von 16 Zellen; Linie am 19.10. geschlossen.
  [[keylevel-edge-card]]
- **Edge Card "Dayli Trade mit IPDA" (eigene Strategie):** Phase 0 seit
  18.10. als Entwurf, **wartet auf deine Antworten**. [[htf-daily-trade-edge-card]]

**Ideen-Inbox neu (19.-25.10.):**
- (19.10.) Bridges auf einen VPS statt aufs Notebook - **von dir auf November
  verschoben**; nach dem 20.10. dringender (3.2).
- (20.10.) Regimekarte: Automatikbetrieb erst beim Bau des Makro-Agenten -
  Nutzerentscheid, geparkt.
- (Nachtrag 27.10.) OU-Research-Skripte auf NY+7 umstellen - offen, nur
  Research.

## 4b. Vertiefung: Serverzeit ist eine Eigenschaft des Brokers, und sie zeigt sich nur zweimal im Jahr

**Was es ist:** MT5-Server stempeln Kerzen und Deals in ihrer eigenen
"Serverzeit". Zwei Konventionen sind verbreitet: (1) **EU-Regel** (Zeitzone
Europe/Helsinki bzw. Athens, UTC+2 im Winter, UTC+3 im Sommer, Umstellung am
letzten Sonntag im Maerz und Oktober), (2) **"NY-Close" = New York + 7
Stunden**: Der Handelstag beginnt um 17:00 New York, und das ist immer
00:00 Serverzeit. Diese Variante stellt mit den USA um (zweiter
Maerz-Sonntag, erster November-Sonntag).

**Beispiel mit unseren Zahlen:** Im Sommer sind beide Konventionen UTC+3 und
liefern identische Zeitstempel. Nur in zwei Fenstern im Jahr liegt eine
Stunde dazwischen: Mitte bis Ende Maerz und vom letzten Oktober- bis zum
ersten November-Sonntag, also **dieses Jahr vom 25.10. bis 01.11.** Genau
dort brach am 26.10. jeder ORB-Scan auf TTP, IQ und FK ab ("erwartet
Europe/Helsinki, Abweichung +60 Min."), zwei Tage ohne ORB. Der Beleg kam aus
der Historie: Der US-Cash-Open liegt bei TTP/IQ ganzjaehrig um **16:30
Serverzeit**, auch vom 09. bis 27.03. Tickmill (EK) stellt dagegen wirklich
mit der EU um. In derselben Woche zeigte der OmniGold-Nachbau das
Spiegelbild: Der MT5-Tester (MetaQuotes-Demo) folgt der EU-Regel, und die
alte Annahme "NY + 7" traf nur **91,9 %** der Einstiege statt **99,2 %**; die
Fehltreffer haeuften sich genau in diesen Umstellungswochen.

**Warum es fuer unsere Bots zaehlt:** Jede Messung im Sommer bestaetigt jede
UTC+3-Annahme. Die richtige Regel zeigt erst eine Umstellungswoche oder ein
Blick in die Historie (Open-Uhrzeit im Maerz und im Januar). Deshalb gilt:
Serverzeit je Broker festlegen und belegen, nie pauschal. Die
Sicherheitspruefung (`verify_server_offset()`) hat hier richtig gehandelt:
lieber kein ORB als ein ORB auf der falschen Range. Offen bleiben die
Research-Skripte `research_ou_*`, die TTP noch mit Helsinki rechnen.
siehe Memory: `broker_serverzeit_ny_plus_7` ·
`mt5_tester_zeitzone_eet_eu_sommerzeit`

## 5. Verbesserungen

- **OU nur auf fertigen Tageskerzen** (19.10., `7c26f58c` + 5 Tests,
  Funded-`run_once.py` mit Signalalter in Handelstagen). Keine neuen
  verwaisten OU-Positionen mehr zu erwarten.
- **Akkubetrieb:** Task-Flags aus, Zuklappen im Akku = nichts tun (19.10.).
  Die Ursache der KW42-Standbys ist erklaert und abgestellt.
- **Altpositionen geraeumt (von dir, 19./22.10.):** alle CTNL-Altpositionen
  und die OU-Waisen DD/EOG. TTP handelt CTNL wieder (Deckel frei).
- **Key Levels sauber abgeschlossen**, mit versiegeltem Lock und klarer
  Restaussage (Magnet nur fuer Stop-Platzierung nutzbar).
- **Neue Werkzeuge:** Regimekarte (`fusion_lab/macro_regime/`, Notion-Sync),
  Copy-Trading-Pipeline (extract mit Wiederholung bei Abo-Limit, sim, review),
  Task `Telegram-Import-SMH-Daily` (taeglich 23:00).
- **Nach der Woche (27.10.):** ORB-Serverzeit auf TTP/IQ/FK korrigiert,
  Ursache sauber belegt.

## 6. Verschlechterungen / offene Probleme

- **Di 20.10.: sieben Stunden Totalausfall**, vermutlich Akku leer; ein
  ORB-Gewinner (+5,97 R im Soll) verpasst. Der Akku-Fix vom Vortag hat das
  Problem verschoben (3.2).
- **ORB 26./27.10. auf drei Konten ausgefallen** (Serverzeit), am 27.10.
  behoben. Faellt in KW44.
- **Wochenarbeit nicht committet:** Copy Trading, OmniGold, Key-Levels-Code
  und -Ergebnisse, fuenf Projektnotizen, vier Locks. Die Locks sind der
  Nachweis fuer das einmalige Oeffnen; ohne Commit sind sie nicht
  git-gesichert (siehe Memory: `git_sync_stash_frisst_sessionarbeit`).
- **OU-Ausstieg sendet bei geschlossener Boerse** (94 abgelehnte Orders fuer
  LEN). Harmlos, aber Rauschen.
- **Soll/Ist ordnet ORB-Fills nicht zu** und sieht CTNL-Signale zwei Stunden
  versetzt, die zweite Woche in Folge.
- **TTP-OU:** STT weiter offen, FLEX/UAL ungeprueft.

## 7. Optimierungsmoeglichkeiten

1. **VPS vorziehen** (Ideen-Inbox 19.10., von dir auf November gelegt): Der
   20.10. zeigt, dass das Notebook auch mit den neuen Einstellungen Trades
   kostet. Vorher VPS/IP-Regeln bei TTP und BeyondIQ klaeren.
2. **Research der Woche committen** (Copy Trading, OmniGold, Key Levels,
   Locks, Notizen), bevor ein Auto-Task den Working Tree anfasst.
3. **Boersenzeiten-Gate fuer OU-Ausstiege** (echtes Geld, nur mit Freigabe).
4. **`soll_ist.py`: ORB-Fills zuordnen und das Storno modellieren**; ohne das
   ist der ORB-Teil von Soll/Ist jede Woche falsch.
5. **STT/FLEX/UAL auf TTP pruefen:** Werden sie vom Modell gefuehrt? STT ist
   nach 3.1 sicher eine Waise.
6. **Edge Card "Dayli Trade mit IPDA":** Phase 0 wartet seit 18.10. auf deine
   Antworten; das ist laut Trade-Inventur dein ertragreichster Stil.
