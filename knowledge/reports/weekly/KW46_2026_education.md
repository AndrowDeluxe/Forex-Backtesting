# Weekly Checkup - Education - KW46/2026

**Abgedeckte Woche: Mo 2026-11-09 bis So 2026-11-15.** Erzeugt am So 15.11. durch den
geplanten `Forex-Weekly-Report`-Task.

## 1. Was stand die Woche an / Hauptfokus

Die bisher **dichteste Research-Woche**: gut 30 eigene Commits, 13 neue PARA-Notizen, rund 18 neue
oder ergänzte Memory-Einträge. Der Handoff vom 02.11. ist abgearbeitet (am 08.11. committet, Ordner `_handoff/`
leer). Der Fokus lag ganz auf dem Dachprojekt, wie am 10.11. entschieden:

- **Daily-Edge C2 bis zum Ende durchgeprüft** ([[htf-daily-trade-edge-card]]): Filter-Matrix (14 + 12
  Filter), Kandidat eingefroren (`6c55e525`), LTF-Einstieg verworfen, Blindtest 2010-15 und Tresor
  2025-26 **nicht bestanden**. Übrig bleibt die Variante W50 (Vorwochen-Mitte) als reiner Forward-Log.
- **Makro-Agent v2 und v3** ([[makro-scorecard-v2]], [[makro-gates-evidenz]], [[makro-wirkketten-katalog]]):
  Scorecard, Geopolitik, Wirkketten, Forecast-Ledger, 2J/10J-Renditen für alle G8. Befund: Makro-Filter
  verbessern die Live-Edges nicht.
- **Gold Confirmation Framework** (PDF einer Bekannten, [[gold-confirmation-score]]): nachgebaut, kein
  Edge, aber ein Nebenfund. **Daraus ging am So 15.11. die CTNL-Makro-Sperre live**, die einzige
  Bot-Änderung aus der Research dieser Woche.
- **Mentor- und Fremdmaterial geprüft:** Tims CRT-Call, Dennis' COT-Calls, Remy-King-Buch,
  H4-„Final Entry Model“ ([[h4-htf-entry-edge-card]]), Prosper-AI-Bot. Alles ohne Edge.
- **Werkzeuge:** Vorgriff-Wächter ([[vorgriff-waechter]]), Aktien- + Krypto-Screener mit Forward-Ledger
  (Strang 8, [[aktien-analyse-und-bot]]), Overfitting-Sperre gelockert (OOS frei, Tresor einmalig).

**Was liegen blieb:** Die Indikator-Steckbriefe (RSI) und der H4-Kandidat warten auf deine Antworten
(Dashboard). `scripts/research_ctnl_macro_live.py` (die Gegenprobe hinter der Live-Sperre) ist geändert,
aber nicht committet; `knowledge/resources/tradingagents-tauric.md` ist ungetrackt.

## 2. Aktive Zeiten

- **Fünf Nacht-Sessions:** Mo/Di ca. 00:30-02:20, Di/Mi ca. 22:50-01:00, Mi ca. 21:30-23:00, Mi/Do ca.
  01:30-03:00, Sa/So ca. 01:45-02:35 (Commit- und Memory-Zeitstempel). Fast alles nach 22 Uhr.
- **Tagsüber am Handy:** Di 10.11. ca. 11 Uhr (EUR/USD-Short auf FK), Di ca. 17:20 und Mi ca. 16:30 (Gold-Longs
  auf FK und EK in derselben Minute), Mi ca. 22:20 (USD/JPY-Short auf FK und EK). Details im Performance-Report,
  Abschnitt 6.
- **Fr 13.11.:** nur Automatik.

Muster: Research nachts, Handel tagsüber per Handy. Neu ist, dass beides in derselben Woche stark ist.

## 3. Meine Main Erkenntnisse

### 3.1 Makro als Veto funktioniert - aber nur an einer Stelle, und nur auf dem Live-Set gemessen

- **Befund:** Von 17 Bausteinen des Gold Confirmation Frameworks hat keiner im IS |t| ≥ 2. Die eine
  Ausnahme ist der Makro-Block (Realzins + Dollar) als **Veto auf CTNL-Reversal**: Die gesperrten Trades
  verlieren IS −0,69 R (n 109) und OOS −0,75 R (n 69), p ≈ 0,0004. Im Tresor verloren alle 5 gesperrten
  Longs (p 0,06). Auf dem echten Live-Set sperrt die Regel nur 12 von 257 Trades, alle Longs, Ø −1,13 R.
- **Mechanismus / Warum:** CTNL-Reversal kauft Rücksetzer. Steigen gleichzeitig Realzins und Dollar,
  drückt ein fundamentaler Strom gegen Gold; der Rücksetzer ist dann oft der Anfang einer Bewegung.
  Shorts gegen das Makro filtert der Ribbon-Filter schon heraus, deshalb trifft die Sperre live nur Longs.
- **Wie es aufgefallen ist:** Als Nebenbefund eines Tests, der eigentlich einen Score-Edge suchte. Die
  Veto-Tests liefen erst auf dem Rohset aller CTNL-Signale. Erst die Gegenprobe auf dem Live-Set (Ribbon +
  Spike) zeigte, wie klein die Wirkung live ist: 12 statt ~180 Trades. Die naheliegende Erweiterung
  „doppeltes Risiko bei Trades mit dem Makro“ sah im Tresor gut aus (+1,24 R), kippte im IS aber auf
  −0,45 R und wurde verworfen.
- **Lehre:** Einen Filter für ein Live-Bein immer auf den Trades messen, die das Bein live wirklich
  nimmt, nicht auf seinen Rohsignalen. Und: Ein Veto ist billiger zu belegen als eine Skalierung, weil es
  nur die schlechten Fälle braucht (siehe Memory: `gold_confirmation_score_momentum`).

### 3.2 t > 2 ist kein Edge, wenn der Markt sowieso steigt

- **Befund:** Die Prosper-Bot-Trendregel erfüllt auf D1 das vorab gesetzte Kriterium (OOS +0,17 / +0,23 R,
  t 2,2 / 2,8 über 13 Märkte). Zufällige Long-Einstiege mit gleicher Anzahl, Haltedauer und Kosten liegen
  aber höher: +0,25 / +0,33 R. Beim Gold-Score dasselbe: Score-Long +0,36 R gegen „immer long, gleiche
  Mechanik“ +0,43 R.
- **Mechanismus / Warum:** Ein t-Test gegen null fragt: „Verdient die Regel Geld?“ In einer Hausse
  (Krypto, Indizes, Gold 2023-26) verdient jede Long-Regel Geld. Die richtige Frage lautet: „Verdient sie
  mehr als zufällige Longs?“ Erst diese Differenz ist das Timing.
- **Wie es aufgefallen ist:** Die Kontrolle „Zufalls-Long“ lief beim Prosper-Test von Anfang an mit, weil
  dasselbe Muster schon beim K4b-Nachtest (Dollar-Drift) aufgetaucht war. Ohne sie wäre die Regel nach den
  eigenen Kriterien durchgegangen.
- **Lehre:** Bei jeder Long-only- oder Short-only-Regel gehört die Zufallseinstiegs-Kontrolle **in das
  Bestehenskriterium**, nicht in die Zusatzinfo (siehe Memory: `t_wert_besteht_aber_nur_long_beta`).

### 3.3 Der Daily-Edge lag im Limit-Preis und in den Jahren 2016-22

- **Befund:** Dieselben Daily-Ideen per Market-Order bringen IS +0,03 / OOS +0,01 R, mit Limit-Einstieg
  +0,55 / +0,40 R. Der eingefrorene Kandidat fällt dann im Tresor durch (2025 −0,22 R, 2026 −0,48 R) und im
  Blindtest 2010-15 (+0,07 R, t 0,36). Jahresreihe: 2016-22 meist +0,3 bis +1,0 R, 2023 +0,20, 2024 +0,02.
- **Mechanismus / Warum:** Das Limit wählt aus. Nur Ideen mit Rücksetzer werden gefüllt (Füllquote
  ca. 50-60 %), und diese bekommen zudem einen besseren Preis. IS (2016-21) und OOS (2022-24) lagen beide im
  selben Marktumfeld, deshalb hat das OOS den Zerfall nicht gezeigt. Ein enger LTF-Stop schneidet genau das
  Tagesrauschen ab, das der Trade aushalten muss: 83-91 % Stopquote.
- **Wie es aufgefallen ist:** Durch den Twin-Trade-Test (Market gegen Limit, gleiche Ideen) und dann durch
  zwei unabhängige Prüfungen außerhalb 2016-24. Beide fielen durch, obwohl IS und OOS gut aussahen.
- **Lehre:** HTF-Ideen immer mit Limit in eine Rücksetzzone testen. Bei jedem Kandidaten die Jahresreihe der
  letzten 3-4 Jahre zeigen, nicht nur IS/OOS. Teilen IS und OOS dasselbe Regime, prüft das OOS wenig
  (siehe Memory: `c2_edge_liegt_im_limitpreis`, `daily_c2_tresor_durchgefallen`).

### 3.4 Makro ist Kontext, kein Schalter - und vier Gates sind kein Vierfach-Signal

- **Befund:** Die Banken-Scorecard (5 Faktoren, G8) hat keinen Edge: IS Sharpe −0,27, OOS −0,21.
  Makro-Filter (Stress, Realzins, Scorecard) verbessern Gold ASB, C2 und ORB nicht; der IS-Vorteil kippt im
  OOS. Die SMT-Gates P, B und R messen zum großen Teil dasselbe Momentum. Beim CPI 10.11. lagen von fünf
  „4/4“-Märkten zwei richtig und zwei falsch.
- **Mechanismus / Warum:** Die Live-Edges leben von Intraday- und Preisstruktur, nicht von der Makrolage.
  Flows und Positionierung laufen gleichzeitig mit dem Preis, nicht vorher. Drei Gates, die alle Momentum
  messen, ergeben ein Signal, das dreimal gezählt wird.
- **Wie es aufgefallen ist:** Beim Faktencheck der Gates gegen Literatur und Marktquellen. Ein Zwischenfehler
  hätte fast getäuscht: Der point-in-time-Backtest schloss frisch geladene Reihen aus, Value fehlte
  stillschweigend. Nebenbei: Öl drückt Gold 2026 nur über den Fed-Kanal (Brent +10 % hebt die US-2J um
  5,4 bp statt früher 2,3 bp).
- **Lehre:** Neue Gates erst auf Überschneidung mit bestehenden prüfen, dann historisch testen. Makro
  bleibt im Fact Sheet als Erklärung; als Filter nur mit Forward-Test (siehe Memory:
  `makro_scorecard_ohne_edge`, `makro_gates_zaehlen_momentum_dreifach`, `makro_filter_hilft_edges_nicht`,
  `oel_gold_ueber_fed_kanal`).

### 3.5 „Der Sweep hat die Stops geholt“ ist eine Stopweiten-Regel

- **Befund:** Tims CRT verliert schon brutto (−0,02 bis −0,07 R). Seine Kernregel scheint roh zu stimmen
  (Stopquote 50 % statt 60 %). Bei gleicher Stopweite und gleichem CRV verschwindet der Unterschied
  (−1,5 bis +3,7 Pp). Das H4-„Final Entry Model“ (456 Varianten) ist brutto ≈ 0 und nicht besser als Zufall.
- **Mechanismus / Warum:** Ein langer Docht bedeutet einen weiteren Stop. Ein weiterer Stop wird seltener
  getroffen, dafür ist das CRV kleiner. Die Regel misst also Mechanik, nicht Marktpsychologie.
- **Wie es aufgefallen ist:** Durch den Vergleich innerhalb gleicher Stopweiten-Klassen. Die händischen
  Beispiele (30 von 185 Signalen EURUSD 2023) waren Auswahl, nicht die Regel.
- **Lehre:** Jede Sweep- oder Manipulations-Regel nur innerhalb gleicher Stopweite und gleichem CRV
  vergleichen (siehe Memory: `crt_manipulation_ist_stopweiten_mechanik`).

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Gold Confirmation Framework (PDF)** ([[gold-confirmation-framework-pdf]], [[gold-confirmation-score]]).
  (a) Aussage: Gold-Longs nur, wenn Flows, physische Nachfrage, Preisreaktion und Makro bestätigen; keine
  Zahlen. (b) Getestet: 17 Bausteine aus 7 freien Quellen (GLD-Bestand ab 2004, CFTC, IMF, SGE), IS 2010-19.
  (c) Urteil: Score-Edge OOS +0,03 R; Long schlägt „immer long“ nicht. (d) **Verworfen als Signal; der
  Makro-Block als CTNL-Veto ist seit 15.11. live**, die übrigen Bausteine sind gespeichert
  ([[gold-bausteine-fuer-andere-edges]]).
- **Remy King „Top 1 %“ (E-Book)** ([[remy-king-trading-strategie-top1]]). (a) Aussage: Zinsdifferenz,
  Carry und Konsens-Drift treiben FX. (b) Getestet: Fair Value, Carry, Konsens-Drift auf ForexFactory-Historie
  2007-26, Vetos B4-B8. (c) Fair Value IS t 1,08; Carry OOS Sharpe −0,18; nach Daten keine Drift, sondern Rücklauf
  (t ≈ −3,2). (d) **Verworfen**; Carry und Rohstoff-Veto als Bausteine, das Rohstoff-Veto steckt im C2-Kandidaten.
- **Tim, „OC CRT“** ([[tim-oc-crt-call]]) und **Dennis, COT-/Volumen-Calls** ([[smh-dennis-cot-volumen-calls]]).
  (a) CRT: Stop/Break-even nach geholter „Early Ones“-Manipulation; Dennis: Hedgefonds-Aufbau als Filter.
  (b) Gold + EURUSD M15-H4 bzw. C2-Filter. (c) CRT brutto negativ; COT-Filter OOS +0,18 statt +0,13 R.
  (d) **Als Bausteine geparkt**; Volumen/Delta (B/E/F/D) warten auf Daten.
- **H4 „Final H4 HTF Entry Model“** ([[h4-htf-entry-edge-card]]). (a) Sweep über ≥ 2 Vorkerzen + BIAS.
  (b) 9 Märkte, 2.733 Varianten. (c) Grundvarianten IS/OOS −0,06 bis −0,23 R; nur 15:00-Einstieg auf FX knapp
  positiv (OOS +0,12 R, t 0,9). (d) **Wartet auf deine Kandidatenwahl.**
- **Prosper-AI „Grok Trading Team“** ([[prosper-bot-trendregel-echtdaten]]). (a) Trendregel eines
  KI-Bots. (b) 1:1 nachgebaut, 13 Märkte. (c) D1 t 2,2-2,8, aber Zufalls-Long besser. (d) **Verworfen** (3.2).
- **Makro-Agent: Scorecard, Gates-Evidenz, Wirkketten** ([[makro-scorecard-v2]], [[makro-gates-evidenz]],
  [[makro-wirkketten-katalog]]). Siehe 3.4. Status: **im Fact Sheet als Kontext**, kein Filter.
- **TradingAgents (Tauric Research)** (`knowledge/resources/tradingagents-tauric.md`, ungetrackt). Als
  Signalquelle ungeeignet; Workflow-Bausteine (Entscheidungs-Log, Pflicht-Gegenposition) für den Makro-Agenten.
  **Vorschlag, nicht entschieden.**
- **Indikator-Steckbriefe** ([[indikator-steckbriefe]]): RSI + RSI Multi Length als Entwurf, **warten auf dich.**

**Ideen-Inbox, neu seit KW45:**
- (09.11.) Remy-King-Bausteine: abgearbeitet (siehe oben).
- (10.11.) Eigenes „SMT-Terminal“ / Trading-Jarvis: noch nicht einsortiert, nach dem Fact-Sheet-Checkpoint.
- (10.11.) CRT + COT-Fluss als Bausteine: einsortiert (geparkt).
- (12.11.) TradingAgents-Workflow für den Makro-Agenten: noch nicht entschieden.
- (15.11.) AI-Pathways: Auswahl-Routine walk-forward testen; KI-Einschätzungen vor Marktöffnung versiegeln.
  Noch nicht einsortiert; der Vorgriff-Wächter aus derselben Quelle ist gebaut.

## 4b. Vertiefung: Der Abschneide-Test - wie man einen Vorgriff findet, bevor er Geld kostet

**Was es ist.** Ein Vorgriff (Lookahead) liegt vor, wenn ein Backtest an Tag t eine Information benutzt,
die es an Tag t noch nicht gab. Der Abschneide-Test prüft das mechanisch: Man rechnet das Signal einmal auf
den vollen Daten. Dann schneidet man die Daten an einem zufälligen Stichtag ab und rechnet neu. Alles, was
bis zum Stichtag schon feststand, muss in beiden Rechnungen gleich sein. Ändert sich ein Signal der
Vergangenheit, sobald man die Zukunft wegnimmt, hat es in die Zukunft geschaut. `lookahead_guard.check_truncation`
macht das an 30 Stichtagen.

**Beispiel mit unseren Zahlen.** Der Gold-ASB-Liquiditätsfilter rechnete die Friktion im Backtest über das
Fenster t bis t+1, sah also den ganzen Handelstag. Der Test fängt genau das: Das Signal für Tag t ändert sich,
wenn Tag t+1 fehlt. Wie teuer so etwas ist, zeigte der 02.11.: Mit dem Live-Wissensstand fiel das Gold-ASB-Soll
von +0,308 R auf +0,168 R. Die beiden anderen alten Vorgriffe (Lake-H4-Duplikate, CTNL-Halbierung) fängt der
Test ebenfalls. Der CTNL-Signalweg ist sauber (12 Stichtage, 31.195 Zeilen).

**Warum das für uns wichtig ist.** Alle drei bisherigen Vorgriffe wurden spät und von Hand gefunden, einer
erst Wochen nach dem Livegang. Diese Woche zeigt das Filter-Protokoll an 2 von 3 Tagen, dass die Friktion des
Vortags nachträglich überarbeitet wird. Die Datenquelle selbst ändert also die Vergangenheit. Grenzen: Der Test
gehört auf die fertige Signalfunktion, nicht auf Bausteine wie Fraktale, die absichtlich nach vorn datieren.
Bei Kerzen mit Eröffnungs-Stempel muss `known_after` die Balkenlänge sein, sonst gibt es Fehlalarme. Seit
15.11. ist der Test Pflicht in Phase 4 (deine Bestätigung steht im Dashboard noch aus).

## 4c. Makro-Wochenprüfung

**Die Vorgehensweise kurz** ([[makro-agent-report-pruefung]]): (1) Report ganz lesen, auch die Kanal-
Nachrichten. (2) Jede prüfbare Zahl gegen eigene Daten. (3) Widersprüche suchen. (4) Gegen die eigene Evidenz
gewichten (Richtung allein ≈ 0 R, Rücksetzer-Limit positiv). (5) Trade-Tabelle inkl. „auslassen“.
(6) Mentor-Chart einarbeiten, Alarmliste. **Gegenwährung wählen:** Stärke aus Zinsen + Angst nur gegen
Rohstoffwährungen (AUD/NZD/CAD), nie gegen CHF/JPY; jede Rohstoffwährung hat ihren eigenen Rohstoff-Schalter
(CAD: Brent über 105); Trades mit demselben Treiber zählen als ein Risiko.

**Nachprüfung KW46** (Lake-Kurse M15/M5, EUR/CHF und DXY über yfinance; in die Notiz zurückgeschrieben):

| Trade | Sicht | Ergebnis |
|---|---|---|
| AUD/USD Short, Limit 0,6905 | Agent (Rang 1) | gefüllt Mo, Fr-Schluss 0,6769 → **+1,60 R offen** (halbe Größe), Ziel 0,6670 noch offen |
| EUR/USD Short, Limit 1,1192 | Dennis | gefüllt Mo, **Stop Di 08:00 UTC (−1 R)**, danach Fall bis 1,1020 |
| USD/CAD Long, Limit 1,4009 | Dennis | nicht gefüllt (Tief 1,4077), Kurs danach 1,4266 |
| Gold Long, Limit 4.045 (CPI-Notiz) | Kanal-Limit, Zuordnung offen | gefüllt in der CPI-Minute, Stop → **−1 R** |
| AUD/USD Short, Limit 0,6968 | Kanal-Limit | nicht gefüllt |
| Gold > 4.150 / USD/JPY < 157,40 (nur bei weicher Zahl) | Agent | nicht ausgelöst, richtig so |

**Was hielt:** Die Gegenwährungs-Leitlinie (AUD −2,3 %, CAD −1,0 %, Euro −1,0 % gegen USD) und Dennis'
DXY-Pfad (C-Welle bis 101,49, dann über 102,6 bis 103,4). Die Warnung der Prüfung, Dennis' EUR/USD-Stop
liege unter dem Hoch vom 04./05.11. und könne abgefischt werden, traf ein: 7 Pips über dem Stop drehte der
Kurs. „Füllung unsicher“ bei USD/CAD stimmte ebenfalls.
**Was nicht hielt:** Die CPI-Schätzung (Kern 0,296 % statt 0,1-0,2; „heiß“ hatten wir mit ~20 % bewertet) und
die eigene Gold-Neigung. Der Report-Satz „Gold fällt bei steigenden Renditen“, den wir als Widerspruch
abgewertet hatten, traf zu (Gold −4,6 %). Die Invalidierung „Schluss < 4.000“ hätte geschützt.

**Laufende Bilanz:** Agent 1 Trade, 1 Treffer, **+1,60 R** · Dennis 1 Trade, 0 Treffer, **−1,0 R** ·
Kanal-Limits 1 Trade, −1,0 R. Nach einer Woche ist das kein Urteil, nur der Start der Zählung.
**Nebenbefund:** Du hast die Ideen real per Handy umgesetzt. Der EUR/USD-Wiedereinstieg nach Dennis' Stop
brachte +631 USD auf FK, drei Gold-Longs am 4.030-Alarm −145 USD / −124 EUR. Die Spalte „Nutzer real“
steht jetzt mit in der Notiz.

**Für KW47 gibt es noch kein Beispiel** in der Notiz (keine Report-Prüfung vom 15.11.).

## 5. Verbesserungen

- **CTNL-Makro-Sperre live** (15.11.) mit eigenem Daten-Task, fail-safe „durchlassen“ bei alten Daten.
- **Gold ASB: Filter-Protokoll je Tag, Soll folgt der Bot-Entscheidung** (`4c0bcc53`). Die KW45-Frage (03.11.)
  ist damit beantwortet.
- **FK `gold_silver` kann wieder einsteigen** (laufende H4-Kerze als Platzhalter, `ce42e5ef`).
- **Vorgriff-Wächter** mit 14 Tests, als Pflicht in Phase 4 eingetragen.
- **Makro-Datenschicht:** 2J/10J-Renditen für alle G8, Kern-Inflation und Leitzinsen aus Ersatzquellen,
  Realzinsen, Geopolitik-Index, Forecast-Ledger.
- **Screener (Strang 8)** mit Forward-Ledger und Archiv; **C2-Forward-Log** (W50) läuft.
- **Prozess:** Overfitting-Sperre gelockert (OOS frei, Tresor einmalig), Dashboard-Fokusregel, 37 verwaiste
  Bot-Einträge bereinigt, Watchdog-Push läuft wieder.

## 6. Verschlechterungen / offene Probleme

- **Handtrades auf EK und FK** mit bis zu 4,5 % Risiko je Trade auf EK; EK −8,35 % in der Woche
  (Performance-Report 6.1).
- **ORB an der ersten Kerze: ca. 20 R Soll-Differenz in einer Woche** (verpasste NASDAQ-Gewinner + Fill-Kerzen-Stop
  bei SP500).
- **Dachprojekt ohne Live-Kandidat:** Daily-C2 im Tresor und Blindtest durchgefallen, H4 ohne Edge.
- **STT auf TTP noch offen**, obwohl am 10.11. „schließen“ entschieden.
- **`mt5_pull.py` meldet bei kalten Terminals still 0 Deals** (dritter Fall); Soll/Ist zählt `orb_us30` weiter
  und die FK-Kopfzeile passt nicht zur Bein-Summe.
- **Edge-Ampel zum vierten Mal nicht aktualisiert** (Dukascopy-Abruf hängt, Stand 25.10.).
- **Gegenprobe-Skript der Live-Sperre nicht committet** (`scripts/research_ctnl_macro_live.py`).

## 7. Optimierungsmöglichkeiten

1. **Regel für Handtrades auf Bot-Konten** festlegen (erlaubt? Größe? eigenes Konto?). Eine Zeile im
   Dashboard reicht für die Entscheidung.
2. **`mt5_pull.py` härten:** nach dem Terminal-Start warten, bis die Historie geladen ist, FK mit `/portable`
   starten, und bei 0 Deals mit Saldoänderung einen Fehler statt einer leeren Liste melden.
3. **Soll/Ist-Werkzeug:** `orb_us30` aus dem Soll nehmen, ORB-Fills zuordnen, FK-Kopfzeile korrigieren.
4. **ORB-Fill-Kerze im Backtest prüfen** (Stop in der Fill-Kerze). Dann sind Soll und Ampel für SP500 ehrlich,
   unabhängig davon, ob am Erste-Bar-Problem live etwas geändert wird.
5. **Makro-Agent: CPI-Schätzung als Forecast-Ledger-Eintrag führen**, damit die Trefferquote solcher Schätzungen
   mitgezählt wird, nicht nur die Trades.
