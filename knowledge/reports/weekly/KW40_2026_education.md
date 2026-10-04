# Weekly Checkup - Education - KW40/2026

**Abgedeckte Woche: Mo 2026-09-28 bis So 2026-10-04.** Erzeugt am So
2026-10-04 durch den geplanten Report-Lauf. Erstmals im neuen, ausfuehrlicheren
Format (Nutzerwunsch 30.09.).

## 1. Was stand die Woche an / Hauptfokus

**Eine Umbau-Woche: Was KW39 erforscht hatte, ging jetzt live. Und fast jedes
Bein wurde danach noch einmal mit echter Ausfuehrung nachgerechnet.** Die
rund 43 Commits von Hand (dazu 6 von automatischen Routinen, ohne die ~420
Snapshots von Watchdog, FK-Paper-Bot und OU-Scanner) bilden fuenf Straenge:

1. **CTNL Reversal, komplett ueberarbeitet** (Mi-Abend bis Sa):
   - Ribbon-Richtungsgate und Spike-Filter live.
   - `ctnl_continuation` stillgelegt.
   - Kill-Switch auf allen Bridges, gemessen auf dem gehandelten Satz.
   - Positionsdeckel 3 -> 2.
   - Funded/FK steigen eine M15-Bar frueher ein.
   - Ein einheitlicher Exit-Standard mit Broker-TP 5R.

   Dazu kamen die Research-Befunde 18-22 in [[ctnl-kostenvalidierung]]:
   Serienstopp, Haltedauer, asymmetrisches Gate, Meta-Umschalter,
   Exit-Gitter.
2. **ORB, neu vermessen** ([[orb-order-storno-und-haltedauer]]):
   - Erst auf M1, dann mit Dukascopy-Ticks.
   - Dabei gefunden: die Live-Order-Luecke.
   - Umgesetzt: Storno bei Gegenbruch, NASDAQ ohne Teilziel mit Storno am
     SL, US30 pausiert.
3. **Gold ASB: Realkosten-Probe und Optimierung** ([[gold-asb-kostenvalidierung]]).
   - Das Bein ist kostenrobust.
   - Stop 1,5x Range und Storno 03:00 NY sind jetzt als ruhende Stop-Order
     live.
4. **Gewichtungen per Monte Carlo und Walk-Forward mit echter Ausfuehrung**:
   FK, TTP, IQ und EK.
   - Eingespielt: nur TTP (neues `leg_risk_pct`).
   - FK wartet auf deine Entscheidung.
   - EK-Ergebnis ist nicht belastbar.
5. **EK-Risiko und Fundament:**
   - Mindestlot-Effekt beziffert. Dein Entscheid: bewusst akzeptiert.
   - OU-Drehtuer auf EK geschlossen.
   - Zweiter Verursacher des Git-Stash-Verlusts (Watchdog) gefunden, danach
     39 Alt-Stashes geloescht.
   - Daten-Cache schreibt jetzt atomar.
   - Paper-Screening: Overnight-Reversal-Paper verworfen.

## 2. Aktive Zeiten

Commits von Hand je Tag, ohne automatische Snapshots und ohne Merges:

| Mo | Di | Mi | Do | Fr | Sa | So |
|---|---|---|---|---|---|---|
| 4* | 2* | 24 | 10 | 0 | 2 | 7 |

\* Mo/Di stammen ausschliesslich aus automatischen Routinen (Report, Lint,
Bridge Error Monitor), nicht von dir.

**Muster:**
- **Mi 30.09., 21:31-22:58:** Ein langer Abendblock mit 24 Commits in
  90 Minuten. Viele davon sind offensichtlich am Ende einer laengeren
  Session gesammelt eingecheckt worden. Die CHANGELOG-Eintraege des Tages
  reichen bis in den Nachmittag zurueck.
- **Do 01.10.:** Arbeit mittags (12:42-13:10) und spaet abends (23:24).
- **Fr 02.10.:** Pause.
- **Am Wochenende:** Sa-Abend 19:20 und So-Nachmittag 14:59-15:16. Der
  CHANGELOG zeigt dazu Arbeit, die gar nicht als Commit auftaucht, weil die
  Bridge-Dateien ausserhalb von Git liegen: Deploy am 03.10. ~19:28,
  Tick-Rundung und TTP-Gewichte am 04.10.

**Insgesamt:** Abende und Wochenende, wie in den Vorwochen. Der Freitag war
der einzige ruhige Tag.

## 3. Meine Main Erkenntnisse

### 3.1 Ein Positionsdeckel ist ein staerkerer Hebel als jede Ausstiegsregel, und er veraendert, welche Trades ueberhaupt existieren

**Befund:**
- **Deckel:** Bei `ctnl_reversal` (2016-2026, ribbon-gefiltert) senkt der
  Schritt von 3 auf 2 gleichzeitige Positionen die
  Monte-Carlo-Wahrscheinlichkeit fuer einen Drawdown ueber 6 % von
  **43,5 % auf 9,9 %**. PF und Sharpe steigen dabei leicht (1,85 -> 1,90 und
  0,95 -> 0,98), die Median-Rendite faellt von 58,6 % auf 40 %.
- **Haltedauer:** Ohne die 96-h-Grenze ist jeder einzelne Trade besser
  (Oe R +0,680 -> +0,743). In der Summe ist es aber **schlechter**
  (Sigma R +329 -> +300).

**Mechanismus / Warum:**
- **Haltedauer:** Laengere Trades halten Plaetze im Korb besetzt. Waehrend
  ein Gewinner weiterlaeuft, wird ein neues Signal abgewiesen. 225 Signale
  kommen dadurch nicht mehr durch. Der Deckel arbeitet "gierig" in
  Zeitreihenfolge: Wer zuerst kommt, belegt den Platz.
- **Feld-Kennzahlen:** Deshalb aendert jeder Deckelwert nicht nur, WIE VIELE
  Trades es gibt, sondern auch, WELCHE. Die Kennzahl "long im Abwaertstrend
  +0,391 R", gemessen unter Deckel 3, schrumpfte beim live gefahrenen
  Deckel 2 auf 12 Trades und +9,5 R, also belanglos.

**Wie es aufgefallen ist:** Ausgangspunkt war deine Beobachtung, dass die
`max_hold`-Ausstiege abgeschnittene Gewinner sind.
- **Das stimmt:** Diese Ausstiege bringen Oe +1,67 R, und Gewinner laufen im
  Median 56 h, Verlierer 12 h.
- **Die Gegenprobe:** Die Rechnung mit "ohne Grenze" ueber alle Deckelstufen
  (2/3/5) ergab jedes Mal dasselbe Bild: je Trade besser, in der Summe
  schlechter. Der Anker-Walk-Forward waehlte in allen Jahren die 96 h.
- **Die Live-Woche zeigt die andere Seite:** IQ nahm am 29.09. unter
  Deckel 3 zweimal drei Shorts im 15-Minuten-Abstand. Alle wurden
  ausgestoppt (-1.312 USD).

**Lehre / Regel fuer die Zukunft:** Haltedauer, Deckel und jede
"Feld-Kennzahl" nur gemeinsam und nur am **live gefahrenen Betriebspunkt**
beurteilen. Ausserdem muss ein Deckel an beiden Stellen geaendert werden,
im Simulationsfilter und im Live-Deckel. Sonst laufen Backtest und Live
auseinander. Siehe Memory: `deckel_und_haltedauer_haengen_zusammen`,
`ribbon_ist_trendexistenz_filter`.

### 3.2 Ein Schutzschalter muss genau das messen, was gehandelt wird, und jede Serienregel darf nur die Vergangenheit sehen

**Befund:**
- **Kill-Switch:** Der CTNL-Kill-Switch stand bei **-7,01 %** und sperrte
  damit. Die Strategie, die tatsaechlich gehandelt wurde (mit Ribbon und
  Spike-Filter), lag aber nur bei **-1,10 %**. Nach der Umstellung hob er
  sich auf allen Konten auf.
- **Risikohalbierung:** Die Idee "Risiko nach Verlustserie halbieren" sah
  zuerst nach +344 statt +310 Sigma R aus. Sauber gerechnet bringt sie gar
  nichts.

**Mechanismus / Warum:**
- **Kill-Switch:** Der Schalter rechnete auf der **ungefilterten**
  Strategie. Er sperrte also die neue Variante fuer die Verluste der alten,
  die so gar nicht mehr gehandelt wird.
- **Risikohalbierung:** Die Serienzaehlung bezog auch Vorgaenger-Trades ein,
  die zum Einstiegszeitpunkt noch **offen** waren. Deren Ausgang ist zu
  diesem Zeitpunkt unbekannt. Das ist klassischer Lookahead: Die Regel
  "wusste", dass die Serie gleich reisst.

**Wie es aufgefallen ist:**
- **Anlass:** die Short-Serie vom 29./30.09.
- **Lookahead:** Beim Nachrechnen fiel auf, dass das Ergebnis nur stimmt,
  wenn man `exit_time <= entry_time` nicht erzwingt. Mit der Bedingung
  verschwand der Vorteil.
- **Kill-Switch:** Beim Scharfschalten auf Funded/EK loeste er sofort aus.
  Die Frage "warum jetzt, obwohl die gefilterte Kurve gut aussieht?"
  fuehrte auf den falschen Satz.
- **Nebenbefund:** Auf FK flackerte der Schalter am 28./29.09. viermal
  zwischen gesperrt und "erholt (0,00 %)". Ein leerer Scan wegen einer
  Datenluecke wurde als Erholung gelesen.

**Lehre / Regel fuer die Zukunft:**
- Jeder Waechter rechnet auf **demselben Filtersatz**, den die Bridge
  handelt.
- "Keine Daten" ist ein dritter Zustand und nie "alles gut".
- Zustands- und Serienregeln im Backtest nur auf Trades rechnen, die beim
  Einstieg schon **geschlossen** waren.

Siehe Memory: `ctnl_serienstopp_vs_risikohalbierung`,
`ctnl_kill_switch_nur_auf_fk`.

### 3.3 Was im Backtest gratis ausgeschlossen ist, muss live ausdruecklich ausgeschlossen werden (die AIG-Drehtuer)

**Befund:** EK hat AIG im OU-Bein **sechsmal eroeffnet und sechsmal
geschlossen**, am 29.09. dreimal innerhalb von 30 Minuten. Ausstieg und
Neueinstieg passierten jeweils im selben Bridge-Lauf. Ertrag: +1,22 EUR,
bezahlt mit sechsmal Spread. Diese Woche stehen davon drei Runden im
Broker-Abzug (+0,01 bis +1,15 EUR je Runde).

**Mechanismus / Warum:**
- **Im Backtest:** Ein- und Ausstieg werden auf **demselben Tagesschluss**
  geprueft, Ausstieg bei Kurs >= MA20, Einstieg bei Kurs
  < MA20 - 2,25 sigma. Beides kann nie gleichzeitig wahr sein.
- **Live:** Die beiden Seiten kamen aus verschiedenen Quellen. Der Ausstieg
  rechnete gegen den Live-Tick, der Einstieg gegen das Signal vom
  Vortagesschluss. Steigt der Kurs ueber Nacht ans Mittel, ist das Signal
  formal noch gueltig, obwohl der Trade laut Modell laengst beendet ist.
- **Die Sperre griff zu kurz:** Die einzige Sperre
  (`position_already_open`) wirkt nur, solange die Position offen ist.

**Wie es aufgefallen ist:** Nicht im Ergebnis, das war praktisch null. Es
fiel im Log auf: Einstiege je Titel gezaehlt, sechs Runden auf einem Titel
gegen zwei auf allen anderen. Gegen die echten Kurse vom 29.09. wurde der
Fix nachgespielt: Der erste Einstieg ist erlaubt, alle drei Wiedereinstiege
sind blockiert. Die Funded-Bridge war **nicht** betroffen. Dort kommen
Einstiege aus der Trade-Liste des Modells selbst, und ein ausgestiegener
Titel faellt automatisch weg. Gleiche Strategie, unterschiedliche
Anfaelligkeit.

**Lehre / Regel fuer die Zukunft:** Entscheidet das Modell Ein- und Ausstieg
auf derselben Preisbeobachtung, muss die Live-Umsetzung beides gegen dieselbe
Beobachtung pruefen. Ein Modell, das einmal taeglich entscheidet, darf von
einer Bridge im 15-Minuten-Takt hoechstens einmal je Tag gehandelt werden.
Das ist kein Zusatzfilter, sondern die Modellsemantik. Siehe Memory:
`backtest_prueft_ein_und_ausstieg_auf_demselben_balken`.

### 3.4 Bei sehr engen Stops entscheidet die Bar-Aufloesung ueber das Ergebnis, und live lag eine ganze Trade-Klasse, die der Backtest nicht kennt

**Befund:**
- **Bar-Aufloesung:** Die ORB-Engine prueft den Stop nicht in der Fuell-Bar.
  Auf M5 beruehren aber **~70 %** der Fuell-Bars schon den SL. Auf M1 sinkt
  Oe R deutlich: SP500 0,65 -> 0,49, US30 0,40 -> 0,24 (OOS +0,005),
  NASDAQ 0,25 -> 0,14.
- **Live-Order-Luecke:** Live blieb bei SP500/US30 die Long-Order nach einem
  Bruch nach unten bis 16:00 liegen. Der Backtest verwirft solche Tage. Live
  ergab das ~60 % mehr Trades und den doppelten MaxDD.
- **Diese Woche live:** **32 von 32 ORB-Trades ausgestoppt.** Die
  SP500-Trades stehen gar nicht im Soll (ca. 630 USD), einer davon wurde
  vier Stunden nach der Eroeffnung gefuellt.

**Mechanismus / Warum:**
- **Bar-Aufloesung:** Der Stop liegt bei 0,6x M15-ATR, also nur 8-10 bps
  und immer innerhalb der Opening Range. Innerhalb einer M5-Bar laesst sich
  nicht sagen, ob erst der Fill oder erst der Stop kam. Der Backtest nahm
  implizit immer die guenstige Reihenfolge an.
- **Live-Order-Luecke:** `_find_stop_breakout()` nimmt den ersten Bruch in
  **irgendeine** Richtung. Ist er nach unten, gibt es fuer die long-only
  Instrumente im Backtest keinen Trade. Live dagegen wartete die
  Long-Order einfach weiter.

**Wie es aufgefallen ist:**
- **Ausgangspunkt:** deine Idee "Order am geplanten SL stornieren".
- **Mehrdeutige Fuell-Minuten:** Die 1.225 Faelle wurden mit
  Dukascopy-**Ticks** aufgeloest. Nur 12-22 % sind echte Stop-outs nach dem
  Fill, M1 ist also nahe an der Wahrheit. Die zuerst genannte "pessimistische
  Schranke" war viel zu streng.
- **Fallstrick dabei:** `dukascopy_python` liest naive Zeitangaben als
  **Ortszeit**.
- **Live-Order-Luecke:** Sie fiel erst auf, als die Trade-Mengen von Live
  und Backtest verglichen wurden (594 gegen 362 bei SP500).

**Lehre / Regel fuer die Zukunft:**
- Ist die Stopdistanz kleiner als die typische Spanne einer
  Ausfuehrungs-Bar, auf der naechstfeineren Aufloesung rechnen und
  Mehrdeutigkeiten mit Ticks aufloesen.
- Bevor man einem Backtest traut: die **Trade-Menge** live gegen Backtest
  vergleichen, nicht nur die Kennzahlen.

Siehe Memory: `orb_fill_bar_stop_and_live_order_gap`.

### 3.5 Ein Waechter auf derselben Maschine schlaeft mit (Standby am Mo 28.09.)

**Befund:** Am Mo 28.09. gab es von **10:33 bis 17:16** in keinem einzigen
Log einen Lauf. Betroffen waren alle sechs Bridge-Lanes **und** der
Bridge-Watchdog. Die NY-Eroeffnung wurde auf allen Konten verpasst. Geld hat
es diesmal nicht gekostet, denn beide verpassten ORB-Signale waren laut Soll
Verlierer.

**Mechanismus / Warum:**
- **Ursache:** Windows-Ereignisprotokoll, `Kernel-Power 506` um 10:32:54,
  `507` um 17:16:09. Der Rechner (Surface) war im **Modern Standby**. Das
  ist dieselbe Ursache wie die naechtliche 9-h-Luecke vom 02.09. und der
  verpasste KW38-Report (Standby So 20.09.). Im Netzbetrieb ist der Standby
  laut `powercfg` aus. Warum er trotzdem eintrat (Akku? Deckel?), ist offen.
- **Warum kein Alarm kam:** Der Watchdog laeuft als Scheduled Task auf
  **demselben** Rechner. Schlaeft der Rechner, schlaeft der Watchdog. Er
  kann seinen eigenen Ausfall nicht melden.

**Wie es aufgefallen ist:**
- **Spur:** Erst beim Soll/Ist dieses Reports. Zwei ORB-Soll-Trades vom
  28.09. standen als "nie gesehen", und im Funded-Log hiess es nach dem
  Aufwachen `range_not_ready` und dann `breakout_passed`.
- **Laufzaehlung:** Laeufe je Stunde zaehlen ergab dieselbe Luecke in
  **jeder** Lane, auch im Watchdog-Commit-Takt.
- **Beleg:** Erst das Ereignisprotokoll belegte den Standby.
- **Fast getaeuscht:** Das Dashboard zaehlt genau diese Luecke ("28.09.
  ~8 h") bisher als Indiz fuer haengende Laeufe wegen veralteter Lake-Daten.
  Fuer den 28.09. trifft das nicht zu, fuer den 01.10. weiterhin vielleicht.

**Lehre / Regel fuer die Zukunft:**
- **Eine Luecke einordnen:** Erst fragen, ob **alles** gleichzeitig still
  war (dann Maschine) oder **eine** Lane (dann Code oder Daten).
- **Wo der Waechter laufen muss:** Ein Ausfallwaechter gehoert auf eine
  andere Maschine, oder er braucht einen externen "Totmannschalter". Ein
  Beispiel waere ein Cloud-Task, der alarmiert, wenn der letzte
  Watchdog-Snapshot auf GitHub aelter als X ist.

Siehe [[DASHBOARD]] (Untersuchung "Lake veraltet").

## 4. Neues Wissen diese Woche (Papers/Ideen)

**Paper: Iwanaga/Sakemoto, "Does overnight return predict the first
half-hour return for U.S. market indices?"** (SSRN 5807282),
[[overnight-reversal-erste-halbe-stunde]].
- **These:** Eine hohe Overnight-Rendite sagt eine **negative** Rendite der
  ersten 30 Minuten voraus. Retail kauft ueber Nacht, Arbitrageure verkaufen
  tagsueber. SPY-Koeffizient b = -9,2, Sharpe 1,51 brutto.
- **Unser Test:** Nachbau auf SP500/NASDAQ/US30 mit Dukascopy M5,
  2016-07 bis 2026-09.
- **Ergebnis:** b = -1,2 / -3,5 / -3,3, also 3-8x schwaecher. Ohne das Jahr
  2020 liegt die Paper-Strategie brutto bei ~0. Mit 1 bp Kosten liegt sie
  bei -1,3 bis -2,6 % p.a.
- **Die einzige Teilvariante mit t~2:** "nur long nach negativer Nacht". Sie
  lebt komplett im Open-Print. Eine M5-Bar spaeter eingestiegen (09:35) ist
  sie auf allen drei Indizes ~0.
- **Status: verworfen in Phase 4**, von dir bestaetigt ("schliesse ab").
  Siehe Memory: `open_reversal_edge_nur_im_open_print`.

**Gold ASB, eigene Strategie, Kostenvalidierung und Optimierung**
([[gold-asb-kostenvalidierung]]).
- **Frage:** Haelt der Edge echte Kosten und Live-Lag aus?
- **Unser Test:** Realkosten-Probe p6_5-p6_8 mit gemessenem Spread im
  ASB-Fenster, dazu ein Gitter aus Einstieg, Order-Logik, Filtern und
  Ausstieg, mit Anker-Walk-Forward.
- **Ergebnis:** **kostenrobust.** Der Stop liegt im Median beim 15-fachen
  der Round-Trip-Kosten, und Oe R geht nur von +0,51 auf +0,44 zurueck.
  Breakeven, TP, Trailing und Teilausstieg sind auf dem gefilterten Satz
  alle schlechter. Im Walk-Forward stabil sind nur Stop 1,5x Range (Sharpe
  1,02 -> 1,20) und Storno 03:00 statt 02:00 NY. Der Edge hat sich seit 2022
  etwa halbiert, ist aber in 11 von 11 Jahren positiv. Shorts sind staerker
  als Longs.
- **Status: live seit 03.10.** als ruhende Stop-Order. Erster echter Lauf
  ist Mo 05.10.

**ORB, Storno am SL, Haltedauer und M1/Tick-Nachtest**
([[orb-order-storno-und-haltedauer]]).
- **Frage:** Bringt das Stornieren der Order am geplanten SL etwas, und
  stimmt die Haltedauer bis 16:00?
- **Unser Test:** M1-Exit-Gitter mit 112 Varianten je Instrument,
  Tick-Aufloesung der Fuell-Minuten, Portfolio-Monte-Carlo.
- **Ergebnis:**
  - NASDAQ: Das 3R-Teilziel halbiert den Edge. Ohne Teilziel und mit Storno
    am SL kommt NASDAQ auf Oe R 0,46, OOS 0,37, positiv in 8 von 8 Jahren.
  - US30 hat seit 2023 keinen Edge mehr (+1 R auf 197 Trades).
  - Portfolio: Das Verhaeltnis Ertrag/DD steigt von 8,5 auf 11,8.
- **Status: live ab 05.10.** NASDAQ geaendert, US30 pausiert, SP500
  unveraendert.

**CTNL, Befunde 18-22** ([[ctnl-kostenvalidierung]]). Das ist kein Paper,
aber die meiste neue Erkenntnis der Woche.
- **Spike-Filter >= 0,75 ATR:** Der Walk-Forward waehlt ihn in 8 von 8
  Jahren. P(DD>6 %) faellt von 43 % auf 18 %.
- **Asymmetrisches Gate und Meta-Umschalter:** beide schlechter als heute.
- **Exit-Gitter mit 240 Varianten:** Keine Variante schlaegt den
  Funded-Standard signifikant. Die EK-Struktur kostet -0,17 R je Trade.
- **Bilanz 2026:** Der gesamte Gewinn stammt aus Januar und Februar. Seit
  Maerz steht das Bein bei -5,4 R.
- **Status:** Spike-Filter, Deckel 2 und Exit-Standard sind live. E1
  (Spread-Annahme 8 bps vs. gemessen 0,5-2) und E4 (Risikokalibrierung)
  sind offen.

**Ideen-Inbox, neu seit dem letzten Report:**
- *CTNL: Engine-Pfad und Live-Pfad laufen nach der ersten Welle auseinander*
  (30.09.). Unsortiert. Das Soll/Ist dieser Woche liefert ein weiteres
  Beispiel (FKs 7 Shorts vom 01.10. stehen nicht im Soll).
- *Geplante Auswertung der Ribbon-Verwurf-Quote* (03.10.). Unsortiert.
  Erster Live-Datenpunkt: Laut Log werden 63-68 % der Signale verworfen,
  erwartet waren ~60 %.
- Nicht in der Inbox, aber im CHANGELOG vom 30.09. als offen markiert: ein
  **instrumenteigener Ribbon** fuer die Nicht-Gold-Beine.

**Clippings:** weiter 14 unverarbeitet, unveraendert seit 09.09.

## 4b. Vertiefung: Monte-Carlo-Block-Bootstrap und "P(Bruch)"

Diese Woche stand mehrfach eine Zahl wie "P(Bruch) 11,9 %/Jahr" im Raum,
zuletzt bei der FK-Gewichtung. Was steckt dahinter?

**Was es ist:** Man nimmt die historischen **Tagesergebnisse** des
Portfolios, gerechnet mit echter Ausfuehrung: Kosten, Versatz, Gates,
Lot-Rundung. Daraus wuerfelt man viele kuenstliche Jahre zusammen, hier
2.000 Pfade. Gezogen werden aber nicht einzelne Tage, sondern **Bloecke von
10 aufeinanderfolgenden Tagen**. So bleiben Verlustserien und
Volatilitaetsphasen zusammen, die es real gibt; einzelne Tage zu mischen
wuerde sie kuenstlich zerstreuen. Fuer jeden Pfad prueft man, ob er die
Kontoregel bricht, bei FK also 5 % Trailing-Drawdown auf Tagesschluss-Basis.
Der Anteil der Pfade mit Bruch ist P(Bruch).

**Beispiel mit unseren Zahlen:**
- **Heutige FK-Gewichtung** (29.08.): **11,9 %** P(Bruch) pro Jahr. Etwa
  jedes achte Jahr wuerde das Konto die Grenze reissen. Die
  Ereignis-Simulation 2019-2026 tut es tatsaechlich, am 14.05.2024.
- **Der Vorschlag vom 03.10.:** **1,1 %** bei einem Median-Ertrag von
  +10,8 % statt +11,9 %. Fast derselbe Ertrag, ein Zehntel des Risikos.
- **Am 29.08.** hatte dieselbe Methode fuer dieselbe Gewichtung nur
  **2,1 %** ergeben. Damals lief sie auf **reibungsfreien** Kurven und nur
  ueber zwei Jahre. Allein Kosten und Ausfuehrung haben das Bruchrisiko
  also fast versechsfacht.

**Warum es fuer unsere Bots zaehlt:** Fuer Prop-Konten mit harter Grenze ist
P(Bruch) die eigentliche Zielgroesse, nicht Rendite oder Sharpe. Ein Bruch
beendet das Konto. Zwei Grenzen der Methode gehoeren dazu:
1. **Sie kann nur Tage neu mischen, die es gab.** Ein Regime, das in der
   Historie fehlt, kann sie nicht simulieren.
2. **Sie ist nur so gut wie die Tagesreihe.** Die Gegenprobe vom 04.10.
   zeigt, dass die Simulation seit Livegang ueber den echten Konten liegt:
   TTP +0,6 % gegen real -0,65 %, IQ +1,4 % gegen -2,5 %. Siehe Memory:
   `sim_optimistischer_als_live`, `fk_gesamtportfolio_2026_trailing_bruch`.

Ein P(Bruch) aus der Simulation ist deshalb eher eine **Untergrenze** als
eine Punktschaetzung.

## 5. Verbesserungen

- **CTNL:** Ribbon-Gate und Spike-Filter live, `ctnl_continuation` (ohne
  Edge) stillgelegt, Deckel 2, Kill-Switch auf allen drei Bridges und auf
  den gehandelten Satz umgestellt, Flacker-Fix, frueherer Einstieg (+0,091 R
  je Trade im Backtest), Exit-Standard mit Broker-TP.
- **FK sieht CTNL-Signale jetzt rechtzeitig.** `ctnl_reversal` laeuft auf
  der 5-Minuten-Lane. Bisher handelte FK nur 31 % seiner Signale, Funded
  50-57 %. Siehe Memory: `scan_takt_gegen_signal_timeframe`.
- **ORB:** Die Live-Order-Luecke ist geschlossen. NASDAQ hat Storno am SL
  und kein Teilziel mehr, US30 ist pausiert. Die Telegram-Texte sind
  korrigiert: Ein "Teilausstieg (SL)" war in Wahrheit gar keiner.
- **Gold ASB** laeuft als ruhende Stop-Order mit den Walk-Forward-stabilen
  Parametern. Die Logik liegt zentral in `asian_range_breakout/pending.py`.
- **OU/EK:** Die Wiedereinstiegs-Drehtuer ist geschlossen.
- **TTP-Gewichtung** neu, kontoeigen ueber `leg_risk_pct`.
- **Fundament:**
  - Git-Stash-Verlust an beiden Verursachern geschlossen, seit 30.09. kein
    neuer Stash.
  - 39 Alt-Stashes geloescht.
  - Daten-Cache schreibt atomar.
  - Lake-Daten werden auch beim Lesen validiert.
  - Telegram-Sperrmeldungen sind flankengesteuert: eine Meldung je
    Wechsel statt bis zu 96 am Tag.
  - Zentrale Tick-Rundung in `_send_order()`.
  - EK-Backup angelegt.
- **Funded-State aufgeraeumt:** 104 verwaiste `placed`-Eintraege stehen
  jetzt auf `closed`.

## 6. Verschlechterungen / offene Probleme

- **Live-Ergebnis:** Die Woche lag ueber alle Bridges bei -0,76 %.
  - ORB: 0 von 32.
  - CTNL: 1 von 28 geschlossenen Trades; der eine Gewinner ist ein alter
    TTP-Short vom 18.09.
  - Einziger Gewinner: Gold ASB.
- **Sehr viele Erstlaeufe gleichzeitig am Mo 05.10.:** Gold-ASB-Stop-Order,
  CTNL-Exit und frueherer Einstieg, ORB-Storno, US30-Pause, TTP-Gewichte,
  Tick-Rundung. Alles ist nur offline getestet. Faellt am Montag etwas aus,
  ist die Ursache schwer zu isolieren.
- **Standby am 28.09.:** Der Rechner schlief 6,7 Stunden an einem
  Handelstag, und der Watchdog konnte es nicht melden (siehe 3.5). Warum
  trotz "Standby aus" im Netzbetrieb, ist ungeklaert.
- **Datenpfad:**
  - `str`/`float`-Fehler im CLS-Scan noch am 28.09., 29.09. und 01.10.
  - Haenger in `dukascopy_python` (Funded 26x, FK 9x).
  - Hunderte Lake-Fallbacks.
  - Seit dem atomaren Cache-Schreiben ist es noch nicht unter Last
    beobachtet.
- **Bridge-Dateien ohne Git:** Kill-Switch-Verdrahtung, Gold-ASB-Pending,
  ORB-Storno, Tick-Rundung und TTP-Gewichte existieren nur als Dateien plus
  Backup-Ordner. Ein Ueberschreiben schaltet sie still ab. Die
  grep-Pruefbefehle stehen im Dashboard bzw. in der Memory.
- **Soll/Ist-Werkzeug:**
  - Erkennt ORB-Pending-Entries weiter nicht. Jetzt minutengenau belegt.
  - Die EK-Soll-Rendite (+1,33 % bei -9,69 R) ist nicht nachvollziehbar.
- **Split-Schutz fuer Einzelaktien fehlt weiterhin.** Der Alarm ist
  beschlossen, aber noch nicht gebaut.
- **CTNL 2026:** Seit Maerz -5,4 R. Die Filter heben die Qualitaet je Trade,
  bisher aber nicht das Ergebnis.

## 7. Optimierungsmoeglichkeiten

1. **Mo 05.10. gezielt gegenlesen** (Reihenfolge nach Uhrzeit):
   - 07:00 Gold-ASB-Order.
   - Erster CTNL-Entry: Broker-TP gesetzt? EK-SL auf dem Signal-Niveau?
   - NY-Open: ORB-Storno-Meldungen.
   - Erster TTP-Entry: Risiko ~600 $ bei Gold ASB.
2. **Totmannschalter ausserhalb des Rechners:** Ein Cloud-Task alarmiert,
   wenn der letzte Watchdog-Snapshot auf GitHub aelter als ca. 60 Minuten
   ist (nur Mo-Fr). Dazu einmal klaeren, warum der Rechner am 28.09.
   trotz `standby-timeout-ac 0` schlief.
3. **Soll/Ist reparieren:** ORB-Pending-Entries per Kommentar
   (`orb_* P/R/F`) und Minute zuordnen. Dann sind die ORB-Zeilen wieder
   lesbar. Zusaetzlich die EK-Soll-Rendite nachrechnen.
4. **FK-Gewichtung entscheiden.** P(Bruch) 11,9 % gegen 1,1 % bei fast
   gleichem Ertrag ist der groesste Risikohebel, der gerade auf dem Tisch
   liegt.
5. **CTNL-Kill-Switch-Schwelle auf dem gehandelten Satz neu kalibrieren.**
   Ohne das schuetzt der Schalter derzeit kaum: Bei -1,10 % ist er weit von
   der alten Schwelle -6,6 % entfernt.
6. **Sim-gegen-Live-Luecke Bein fuer Bein zerlegen**, vor jeder weiteren
   Gewichtungsrunde (TTP -0,65 % real gegen +0,6 % Sim).
