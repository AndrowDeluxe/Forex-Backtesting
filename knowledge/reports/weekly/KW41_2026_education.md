# Weekly Checkup - Education - KW41/2026

**Abgedeckte Woche: Mo 2026-10-05 bis So 2026-10-11.**

**Entstehung:** Abschnitt 3.1-3.6, 4 (bis Fetna/Zarattini-SiP) und 4b wurden
am Di 06.10. auf Nutzerwunsch vorab geschrieben (Gamma-Ergaenzung 07.10.).
Der geplante Lauf (verspaetet, Mo 12.10. nachts) hat Abschnitt 1, 2, 3.7-3.10,
den Rest von 4 sowie 5-7 ergaenzt. Der Vorab-Text ist unveraendert
uebernommen.

## 1. Was stand die Woche an / Hauptfokus

Eine reine Research-Woche: **keine einzige Aenderung an den Live-Bridges**,
dafuer drei grosse Faeden.

- **ORB nach dem Tresor-Bruch (Mo-Mi):** Overfitting-Sperre als
  Standardprozess eingefuehrt (05.10.), ORB nur auf IS neu optimiert und im
  Tresor durchgefallen, Regime-2026-Runde mit 46.656 Varianten je Index
  durchgefallen, echte Gamma-Daten (SqueezeMetrics) geladen, Blindtest
  2012-2016 vorab registriert. Am Mi 07.10. beendet: **ORB-Research-Ansatz
  abgeschlossen**, Live-Bot laeuft unveraendert, Forward-Test mit/ohne
  Gamma-Regler bis 31.12. Am So noch die Oel-Gegenprobe fuer die
  Mentor-Gruppe (`fdab5a88`, `3359d0f3`, `0d71ca8a`, `e6040729`, `4724f0b9`).
- **Faber-Trend (Mo/Di):** mit echten MT5-Kosten fuer Funded und EK
  gerechnet, am 07.10. **pausiert** (`eae74d2d`).
- **Dachprojekt Quant x diskretionaer (Mi-So):** Material-Import (Telegram
  10.427 Nachrichten, OneNote 3.225 Seiten), Notion-Cockpit mit eigener
  API-Integration, Entscheidungslog mit Prueffeldern (`96d12016`, `4209f01b`,
  `b35af446`), dazu die SMH-Elite-Teamaufgabe (runde Zahlen, London-Fix,
  Liquiditaets-Reversal), die SMH-Makro-Reports (120 Reports als JSON), der
  G8-Staerke-Nachbau und am So das Paper "Beat the Market" (Zarattini). Die
  Ergebnisse ab 07.10. stehen im CHANGELOG, sind aber **noch nicht
  committet** (siehe Abschnitt 6).

## 2. Aktive Zeiten

Nach Commit-Zeiten und Datei-Aenderungen im Repo:

- **Di/Mi spaetabends bis nach Mitternacht** (Di 22-01 Uhr: ORB- und
  Gamma-Runden),
- **Mi Vormittag** (09-12 Uhr: Mentor-PDF, ORB-Abschluss),
- **Fr Vormittag und Fr Abend** (10 Uhr Dachprojekt-Import, 21 Uhr der groesste
  Block der Woche mit ca. 200 geaenderten Dateien: Makro-Reports),
- **Sa kurz nach Mitternacht** und **So Vormittag** (09-11 Uhr: G8, Oel,
  Zarattini).

Also wieder ueberwiegend Abende, Naechte und Wochenende, mit zwei
Vormittagsbloecken. Auffaellig: Zwei der Standby-Phasen der Bridges (Mi
10:12-11:51, So ab 11:34) fallen genau auf Arbeitsbloecke am Rechner. Das
stuetzt die Vermutung "Deckel zu / Akku" aus KW40, belegt sie aber nicht.

## 3. Meine Main Erkenntnisse

### 3.1 Der Tresor hat eine ORB-Strategie entlarvt, die nach IS und OOS wie ein Treffer aussah

**Befund:** Die ORB-Strategie (SP500 + NASDAQ) wurde neu und ausschliesslich
auf IS 2016-2022 optimiert, mit 7 Punkten je Index. Danach wurde sie
eingefroren.

| | PF | Σ R |
|---|---|---|
| IS | 1,49 | |
| OOS 2023-09/2025 | 1,34 | +120 |
| Tresor 10/2025-09/2026 | 0,52 | −87 |

Auf einem 100k-Konto mit 1 % Risiko je Trade wurden im Tresor
**100.000 $ → 40.495 $** (MaxDD −62 %).

**Mechanismus / Warum:** Eine Strategie kann in zwei Zeitraeumen hintereinander
funktionieren und trotzdem auf einem Muster beruhen, das nur in einem
bestimmten Marktregime gilt. IS und OOS lagen beide im selben Regime (siehe
3.2). Erst der Tresor fiel in ein anderes.

**Wie es aufgefallen ist:** Durch die neue Overfitting-Sperre (3.3). Der
Tresor (die letzten 12 Monate) war technisch versiegelt und wurde erst nach
dem Einfrieren einmal geoeffnet. Ein Datenfehler wurde ausgeschlossen:
- Die Trades sind normal ueber die Monate verteilt.
- Jeder Verlust ist bei −1 R gedeckelt.
- Es gibt keine doppelten Tage.

**Lehre:** OOS bestanden heisst nicht handelbar. Erst ein einmal geoeffneter
Tresor zeigt, ob ein Edge regimeuebergreifend traegt. Auch die
Deflated-Sharpe-Pruefung war hier schon rot (Vertiefung unten).
siehe Memory: `orb_is_only_tresor_durchgefallen`

### 3.2 Bruchpunkt gefunden: Nicht der ORB ist gekippt, sondern der Trendfilter

**Befund:** Gemessen wurde das Ø R je Trade an Tagen, an denen der EMA-Ribbon
(4H/1D/1W) neutral ist, gegen Tage mit klarem Trend.

| | Vorsprung „neutral“ |
|---|---|
| 2017-2025 | in 16 von 18 Index-Jahren positiv (bis +0,7 R; Ausnahmen NASDAQ 2019 −0,04, 2022 −0,01) |
| 2022 (Zinsschock) | SP500 +0,38 |
| Tresor | erstmals bei beiden Indizes negativ: SP500 −0,65, NASDAQ −0,41 |

Der ORB ohne Filter lag schon immer bei etwa 0 R. Der Bruch beginnt im
Quartal 2025Q4 bzw. 2026Q1.

**Mechanismus / Warum:**
- **Hypothese, nicht belegt:** Das Dealer-Gamma-Regime hat sich gedreht.
- **Positives Gamma:** Market Maker hedgen gegen die Bewegung, daraus
  entstehen Intraday-Umkehrungen. Ausbrueche an Trendtagen werden gefadet.
- **Negatives Gamma:** Sie hedgen mit der Bewegung, daraus entsteht Momentum.
- **Literatur:** Dim/Eraker/Vilkov; Adams et al. (10/2025); SpotGamma
  („neues Volatilitaetsregime“, 03/2026).
- **Umfeld 2026:**
  - 0DTE auf Rekord (~63 % des SPX-Optionsvolumens)
  - Iran-Krieg, Oel > 100 $
  - Q1 −9 % vom Hoch, Q2 das beste Quartal seit 2020
  - Fed-Erhoehung 09/2026

**Wie es aufgefallen ist:**
- **Quartalsweise Zerlegung:** Der Bruch ist abrupt, kein langsames Ausbluten.
- **Zehn Varianten je Index:** Nur der Ribbon-Filter dreht das Vorzeichen.
- **Gegenprobe Jahr fuer Jahr:** 2022 hielt trotz Makrostress, Makro allein
  erklaert es also nicht.
- **Die Eroeffnungsmechanik ist unveraendert** (Follow-through ~50 %,
  Range-Breite, Ausbrueche in beide Richtungen).
- **Querbefund Live-Version:** NASDAQ live hat keinen Ribbon und blieb
  positiv. SP500 live nutzt „neutral“ und lag bei ~0.

**Korrektur (06.10. abends, echte Gamma-Daten von SqueezeMetrics):** 2026
hatte nur an 4 % der Tage negatives SPX-Gamma, 2022 an 42 %, und 2022 hielt
der Filter. Die Gamma-Erklaerung ist damit unwahrscheinlich, die Ursache bleibt
offen. Eine Hypothese mit den echten Daten gegenzupruefen, statt sie mit der
Literatur nur plausibel zu machen, war hier entscheidend.

**Lehre:** Haengt ein Edge fast ganz an einem einzigen Regime-Filter, ist er
so stabil wie das Regime. Filter-Vorzeichen live weiter beobachten, statt sie
als Naturkonstante zu behandeln. siehe Memory: `orb_ribbon_filter_kippt_2026`

### 3.3 Prozessluecke: Wir haben jahrelang „auf OOS“ optimiert, ohne es zu merken

**Befund:** Die Live-ORB-Konfiguration (15 auf den Daten gewaehlte
Entscheidungen, mehrere hundert Varianten) wurde ab Stage 2 direkt auf
OOS-Zahlen ausgewaehlt. Beispiele:
- Stage 3: „alle Zahlen OOS“
- Stage 4a: „OOS-only-Scan“
- Exit-Gitter: „IS und OOS positiv“

**Mechanismus / Warum:** Der Standardprozess nannte den OOS-Split nur in
Phase 6 als Pruefung. Fuer Phase 4/5 gab es keine Regel. Ein Skript, das IS
und OOS nebeneinander ausgibt, verfuehrt zur Auswahl auf OOS, und jeder Blick
macht OOS ein Stueck weit zu IS.

**Wie es aufgefallen ist:** Durch die Nutzerfrage „Haben wir mehr als 9
Parameter optimiert?“. Beim Zaehlen fiel auf, dass praktisch jede Stufe ihre
Wahl mit OOS-Zahlen begruendet hatte.

**Lehre / neue Regel (Overfitting-Sperre, Standardprozess seit 05.10.):**
1. Split IS / OOS / Tresor vor dem ersten Test registrieren.
2. Nur auf IS optimieren.
3. Jede Variante zaehlen (Trial-Register).
4. Einfrieren.
5. OOS und Tresor je genau einmal oeffnen.

Technisch ist das umgesetzt in `research_lock.py`. Dazu gilt als Hinweis ein
Richtwert von max. 9 optimierten Punkten je Index.
siehe Memory: `orb_auswahl_auf_oos_prozessluecke` · [[overfitting-sperre]]

### 3.4 Kosten: Unser ORB-Edge ist groesser als der aus der Literatur, aber genau dieser Teil war gefittet

**Befund:** Eine unabhaengige Replikation (MQL5, 09/2026, 5 Index-CFDs, M1)
findet das Paper-ORB **brutto +0,05 bis +0,13 R, netto null**. Unsere Kosten
liegen gleichauf:

| Rundturn | Wir | Replikation |
|---|---|---|
| SP500 | 0,69 Pkt | 0,80 Pkt |
| NASDAQ | 1,93 Pkt | 2,50 Pkt |

Der Unterschied lag im Brutto-Edge, und den lieferten Filter und Exit-Regeln.

**Mechanismus / Warum:** Was gegenueber der Literatur „extra“ ist, wurde auf
unseren Daten gewaehlt. Genau dort sitzt das Overfitting-Risiko.

**Wie es aufgefallen ist:** Durch die Web-Recherche zu den Kriterien der
Mentor-Folie („Kosten eingerechnet“) und die Kosten-Gegenprobe mit 2×/3×
Kosten.

**Lehre:** Liegt der eigene Edge ein Vielfaches ueber dem, was unabhaengige
Replikationen finden, ist das zuerst ein Warnsignal und erst dann ein Erfolg.

### 3.5 Ein Regimewechsel laesst sich nicht aus der Bruchphase lernen

**Befund:** Die ORB-Strategie wurde neu auf genau dem Halbjahr des Bruchs
optimiert (IS 10/2025-03/2026, 9 Punkte, 46.656 Varianten je Index).

| | SP500 (3. Ausbruch) | NASDAQ (Ausbruch nach Fehlausbruch) |
|---|---|---|
| IS | PF 1,66 | PF 2,20 |
| OOS 04-06/2026 | −31 R | ±0 |
| Tresor | −8 R | −13 R |

Auf dem 100k-Konto waren das −27,6 % im OOS. Der 2./3. Ausbruch war ueber
2016-2026 in keinem Regime besser als der erste.

**Mechanismus / Warum:**
- **Zu wenig Daten fuer zu viele Freiheitsgrade:** ~60-120 Trades gegen
  zehntausende Varianten. Die Suche findet sicher ein Muster, aber fast
  sicher ein zufaelliges.
- **Der Bruch selbst ist kein stabiles Regime:** Das Umkehr-Muster (Fade,
  Fehlausbruch), das im Bruch-Halbjahr ins Plus drehte, hielt in Q2/Q3 2026
  nicht.

**Wie es aufgefallen ist:**
- **Schon im IS:** t-Werte von nur 2,3 bzw. 1,5 und eine Deflated Sharpe
  von ~0.
- **Am Checkpoint offen gesagt;** OOS wurde trotzdem bewusst geoeffnet.
- **Ergebnis:** Die eingefrorene Auswahl fiel durch.

**Lehre:** Nach einem Regimebruch keinen schnell nachoptimierten Ersatz-Edge
handeln. Stattdessen Risiko senken oder pausieren und Forward-Daten sammeln.
Ein IS unter einem Jahr mit vielen Stellschrauben ist ein Warnsignal.
siehe Memory: `regimewechsel_nicht_aus_bruchphase_lernbar` · [[orb-neues-regime-2026]]

### 3.6 Echtes Dealer-Gamma: ein robuster Mechanismus, eine widerlegte Hypothese

**Befund:** Das SPX-Gamma (SqueezeMetrics, gratis, taeglich ab 2011) bestaetigt
**blind** (06/2012-07/2016, vorab registriert): Bei viel Gamma ist die
Tagesrange halb so gross (2,0x / 1,9x, in allen 5 Stufen monoton). Dasselbe
gilt 2016-22, 2023-24 und 2025-26.
- **Widerlegt:** „2026 kippte der ORB-Filter wegen negativen Gammas“. 2026
  hatte nur 4 % der Tage mit negativem Gamma, 2022 42 %.
- **Nicht bestanden:** die Regel „kein ORB bei viel Gamma“.

**Mechanismus / Warum:** Long-Gamma-Dealer hedgen gegen die Bewegung. Das
daempft die Schwankung verlaesslich, sagt aber nicht verlaesslich, ob ein
Ausbruch traegt.

**Wie es aufgefallen ist:** Die Gamma-These stand zuerst nur auf Literatur
und SpotGamma. Erst die echten Daten zeigten, dass 2026 kein
Negativ-Gamma-Jahr war. Der Blindtest wurde vor dem Laden der Daten
committet. Dabei fiel ein Datenfehler auf: Die Dukascopy-Indexdaten 2012-13
haben ~37 % leere M15-Bars und einen viel zu kleinen ATR, die R-Werte waren
dadurch aufgeblaeht. Bewusst gab es keinen Neutest nach dem Oeffnen.

**Lehre:** Hypothesen mit echten Daten gegenpruefen, bevor man auf ihnen
baut. Vor einem Blindtest die Datenqualitaet der Periode pruefen, nicht
danach. Gamma taugt als Risiko-/Vola-Regler; als Ertragsfilter ist es nicht
belegt. [[gamma-mechanismen-gex]] · siehe Memory: `echte_gamma_daten_sqzme`
· siehe Memory: `dukascopy_index_daten_vor_2014_luckenhaft`

### 3.7 Drei Intraday-Momentum-Edges auf US-Indizes sterben gleichzeitig, und Oel zeigt warum es kein Index-Zufall ist

**Befund:** Nach ORB und dem Baltussen-Tagesend-Momentum ist mit dem
Zarattini-Paper "Beat the Market" der **dritte** Intraday-Momentum-Edge auf
US-Indizes 2025/26 tot. Die Nachbildung trifft das Paper brutto genau
(Jahres-Korrelation 0,92). Netto-Sharpe SP500: IS 0,60 → OOS 0,45 → Tresor
**−1,29**; NASDAQ 1,45 → 0,59 → **−0,62**. Der Brutto-Edge je Trade schmilzt
stetig (NASDAQ 7,9 → 4,0 → −0,9 bps). Die Oel-Gegenprobe mit dem
eingefrorenen ORB: kein Edge (bester PF 1,03), kein Eroeffnungsschock (erste
15-Min-Bar 1,5 ATR gegen 2,4-3,0 bei den Indizes).

**Mechanismus / Warum:** Zwei Ebenen. Erstens sind Schock und Edge
gekoppelt: Wo es keinen Eroeffnungsschock gibt (Oel), gibt es auch keinen
ORB-Edge. Das stuetzt indirekt die These, dass der Index-Edge aus der
Eroeffnungsauktion und erzwungenen Flows kommt. Zweitens: Der Kipp des
Trendfilters 2026 zeigt sich bei Oel **nicht**, wohl aber eine andere
Veraenderung, die alle drei Maerkte gleichzeitig trifft. Die
Tag-zu-Tag-Autokorrelation drehte von Umkehr (2025 stark negativ) zu
Fortsetzung (2026). Hypothese: Der ORB-Edge an "neutralen" Tagen lebte von
einem mehrtaegigen Mean-Reversion-Regime, das marktweit verschwand.

**Wie es aufgefallen ist:** Die Oel-Idee kam vom Mentor in der Gruppenarbeit.
Sie verwandelt die Frage "war der ORB nur overfittet?" in eine pruefbare
Regime-Frage. Beim Zarattini-Paper fiel zuerst die Kostenseite auf: Unsere
CFD-Kosten (1,3-1,6 bps je Rundturn gegen ca. 0,3 bps beim SPY) halbieren
schon im IS das SP500-Sharpe (1,08 → 0,60). Ein echtes GEX-Gate hob den
Bruttoertrag je Trade, halbierte aber die Trades; das Sharpe stieg nicht.

**Lehre / Regel:** Neue Intraday-Index-Papers zuerst in drei Schritten
pruefen, bevor Zeit in Phase 5/6 fliesst: (1) brutto gegen das Paper
kalibrieren, (2) mit CFD-Kosten statt ETF-Kosten rechnen, (3) die Jahre
2025/26 ansehen. Und: Eine Gegenprobe in einem anderen Markt trennt
"Struktur dieses Markts" von "marktweitem Regimewechsel".
[[zarattini-noise-area-momentum]] · [[orb-gegenprobe-oel]] · siehe Memory:
`intraday_momentum_us_indizes_stirbt_2025`

### 3.8 Runde Zahlen sind ein Magnet, keine Wand

**Befund:** In der SMH-Elite-Teamaufgabe brachte der Fade (Gegenbewegung) an
runden Zahlen (x.xx00) auf EURUSD, GBPUSD, USDJPY und AUDUSD (M1, IS
04/2018-03/2023) **brutto −0,054 R je Trade, t = −5,8**. Derselbe Fade an
sechs Schein-Leveln (x.xx13 ... x.xx87) lag zwischen −0,012 und +0,015 R,
also bei null. Alle drei Teamkandidaten scheiterten im Tresor: runde Zahlen
PF 0,65, London-Fix PF 1,31 (nur 52 Trades, OOS negativ),
Liquiditaets-Reversal PF 0,84.

**Mechanismus / Warum:** Oslers Befund (2003) war, dass Kurse an runden
Zahlen abprallen, weil dort Limit-Orders liegen. Bei uns kehrt sich das um:
An runden Zahlen liegen offenbar mehr Stop- und Ausbruchs-Orders als
Abprall-Orders. Wird die Zahl erreicht, loesen sie aus und ziehen den Kurs
hindurch. Die Zahl wirkt wie ein Magnet.

**Wie es aufgefallen ist:** Durch die Kontrollgruppe. Ein negatives Ergebnis
allein haette auch "Fade auf M1 verliert immer" heissen koennen. Erst der
Vergleich mit den Schein-Leveln zeigt, dass gerade die runde Zahl besonders
ist (t −5,8 gegen ca. 0). Die naheliegende Umkehrung (3 Pips hinter der Zahl
mit dem Ausbruch einsteigen) verliert trotzdem, weil auf M1 Ausbrueche
generell zuruecklaufen.

**Lehre / Regel:** Ein starker negativer Befund mit sauberer Kontrollgruppe
ist echtes Wissen, auch ohne handelbare Regel. Fuer die Vertiefung des
"Key-Level-Ansatzes" (dein Wunsch vom 07.10.) sind OOS und Tresor von K1
schon geoeffnet. Eine neue Magnet-Regel braucht deshalb frische Maerkte
(USDCAD, Crosses, Gold) oder Forward-Daten. [[smh-elite-mikrostruktur]] ·
siehe Memory: `runde_zahlen_magnet_statt_wand`

### 3.9 Ein LLM-Agent laesst sich nicht rueckwirkend testen, und Agenten-Team-Vorlagen testen gar nichts

**Befund:** Ein Claude-basierter Makro-Agent (Strang 3 des Dachprojekts) kann
nicht ehrlich auf Vergangenheitsdaten getestet werden, weil das Modell die
Maerkte bis etwa Juni 2026 kennt. Die gepruefte Vorlage "SebAI - 6 Claude
Agents Trading Team" hat viele Leitplanken, aber keinen einzigen Test: Der
Coder schreibt Code, den niemand ausfuehrt, der Risk Manager soll Overfitting
pruefen, hat aber weder Split noch Versuchszaehlung, und jeder Lauf liefert
genau eine Entscheidung (n = 1).

**Mechanismus / Warum:** Bei einem Regelwerk trennt der Datensplit, was die
Regel "gesehen" hat. Bei einem Sprachmodell steckt der Ausgang schon im
Training. Laesst man es Reports fuer 2025 "nachschreiben", fliesst das
Ergebnis unbewusst ein. Das ist ein Lookahead, den kein Split verhindert.

**Wie es aufgefallen ist:** Beim Planen des Makro-Agenten (07.-09.10.) und
bei der Pruefung der Vorlage, Rolle fuer Rolle mit derselben Frage: Ist das
Code (deterministisch, backtestbar) oder LLM (nur vorwaerts messbar)? Die
"historische Einstiegsuebung" der Vorlage fiel dabei als Lookahead auf.

**Lehre / Regel:** Rueckwirkend testbar sind nur regelbasierte Bausteine (z. B.
der G8-Nachbau aus FRED) und datierte, schon veroeffentlichte Reports.
Agenten-Ausgaben ab dem ersten Tag strukturiert loggen und als Forward-Test
werten; Risiko gehoert in Code und darf nur verschaerfen. Uebernommen wurden
nur der Status "unvollstaendig" und die Prueffelder im Entscheidungslog.
[[quant-diskretionaer-fusion]] · siehe Memory: `llm_agent_nur_vorwaerts_testbar`
· siehe Memory: `agenten_team_vorlagen_ohne_test`

### 3.10 Erste saubere Live-Woche: Die Schutzregeln haben gespart, und der State laeuft wieder voll

**Befund:** Zum ersten Mal seit Einfuehrung von Soll/Ist gab es im Fenster
keine Konfigurationsaenderung. Ergebnis: **Ist ueber Soll auf allen drei
Bridges** (Funded −0,24 % gegen −0,35 %, FK −0,29 % gegen −0,82 %). Die
Abweichungen gehen fast alle auf Schutzregeln, die Soll-Verlierer abfingen:
CTNL "Signal zu alt" und "schon 0,5 R gegen das Signal" (−3,43 R vermieden),
die neue ORB-Storno-Regel an zwei Tagen (ca. −2 R vermieden). Gleichzeitig
stehen im CTNL-State wieder ausgestoppte Positionen als `placed`, und vier
echte Altpositionen haben nach 6-8 Handelstagen keinen Zeit-Exit bekommen.

**Mechanismus / Warum:** Der Backtest steigt zum idealen Zeitpunkt ein. Live
kommt ein Signal manchmal spaet, und dann ist der Kurs schon gelaufen. Die
Guards verzichten genau in diesen Faellen, und diese Woche waren es
Verlierer. Der State-Fehler ist ein anderes Thema: Die Bridge merkt sich
Positionen ueber den Signal-Schluessel der Simulation. Passt der Schluessel
nicht mehr (Vermutung: Einstieg seit 03.10. eine Bar frueher), findet der
Zeit-Exit seine Position nicht.

**Wie es aufgefallen ist:** Beim Soll/Ist-Abgleich fielen die Guards als
"nicht platziert" auf; erst die Logzeilen zeigten, dass jede davon ein
Verlierer war. Der State-Fehler fiel ueber ein Detail auf: Von zwei
gleichartigen IQ-Shorts vom 02.10. wurde einer per `max_hold` geschlossen,
der Zwilling 15 Minuten spaeter nicht. Ein gutes Beispiel dafuer, dass Paare
mit unterschiedlichem Ausgang die besten Hinweise auf Fehler sind.

**Lehre / Regel:** Ein Soll/Ist-Vergleich ist erst lesbar, wenn die
Konfiguration im Fenster stillsteht; diese Woche zeigt, wie viel klarer er
dann wird. Und: Exit-Logik, die ueber Sim-Schluessel statt ueber echte
Broker-Positionen laeuft, muss nach jeder Aenderung am Signal-Timing
gegengeprueft werden. Details: `KW41_2026_performance.md`, Abschnitt 5 und 6.

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Gao, Han, Li, Zhou (JFE 2018):**
  - **Aussage:** Die erste halbe Stunde sagt die letzte halbe Stunde voraus
    (SPY 1993-2013, R² 1,6 %), staerker an Volumen- und News-Tagen.
  - **Bei uns:** Die Korrelation erste gegen letzte 30 Min. lag 2016-2022 bei
    SP500 +0,09, 2023-24 bei ~0, im Tresor bei +0,11. Das ist kein stabiler
    Effekt.
  - **Status:** Hintergrund, geparkt.
- **Baltussen, Da, Lammers, Martens (JFE 2021):**
  - **Aussage:** Intraday-Momentum ueber 60 Futures, verursacht durch
    Gamma-Hedging.
  - **Bei uns:** staerkster Mechanismus-Kandidat fuer den ORB.
  - **Status:** nicht testbar ohne GEX-Historie, Ideen-Inbox.
- **Dim, Eraker, Vilkov (SSRN 2024/25):**
  - **Aussage:** Positives Market-Maker-Gamma staerkt Reversals, negatives
    Momentum.
  - **Bei uns:** Das passt zum Ribbon-Kipp (3.2).
  - **Status:** Hypothese.
- **Adams, Dim, Eraker, Fontaine, Ornthanalai, Vilkov (SSRN 10/2025):**
  - **Aussage:** 0DTE daempft die Index-Volatilitaet (−60 bis −90 bp
    annualisiert), mit staerkeren Order-Flow-Reversals und schwaecherem
    Momentum.
  - **Bei uns:** Hintergrund zum alten Regime.
- **Ladia (SSRN 07/2026):**
  - **Aussage:** Opening-Range-REVERSAL in Dow-Futures 2023-03/2026: Short
    an der Eroeffnung trifft zu 59,8 %, vorher 45 %. Das passt zeitlich zum
    0DTE-Wachstum (keine Kausalitaet belegt).
  - **Status:** Kandidat fuer die neue ORB-Runde.
- **Fetna (SSRN 09/2026):**
  - **Aussage:** Vorregistriert, 225 ORB-Zellen, 9 Futures, 2010-2026: keine
    einzige traegt nach Kosten. Die 5-Min-Range ist die schlechteste.
  - **Status:** Warnung, gelesen.
- **Zarattini, Barbon, Aziz (SSRN 2024):**
  - **Aussage:** ORB nur auf „Stocks in Play“ (abnormales
    Eroeffnungsvolumen): +0,38 R gegen −0,02 R.
  - **Status:** Kandidat fuer einen Volumen-Filter (Ideen-Inbox).
- **Markt 2025/26 (SpotGamma, Cboe, Quartalsberichte):**
  - 0DTE ~63 % des SPX-Optionsvolumens, Rekord 3,3 Mio. Kontrakte pro Tag
    (06/2026)
  - Half-Penny-Ticks seit 11/2025 (nur Aktien/ETFs)
  - Nasdaq-23h-Handel ab 12/2026 geplant
**Ab 07.10. dazugekommen (Sonntagslauf):**

- **Zarattini, Aziz, Barbon, "Beat the Market" (SSRN 4824172):** (a)
  Intraday-Momentum am Rand einer "Noise Area" um die Eroeffnung, im Paper
  auf SPY mit hohem Sharpe. (b) Bei uns nachgebaut auf SP500/NASDAQ-CFDs
  2016-09/2026, mit Overfitting-Sperre (19 Versuche, eingefroren, OOS und
  Tresor je einmal geoeffnet); die Nachbildung trifft das Paper (Korrelation
  0,92/0,85). (c) Tresor-Sharpe netto **SP500 −1,29, NASDAQ −0,62**, der
  Brutto-Edge je Trade ist im Tresor schon vor Kosten negativ. (d)
  **Verworfen** - dritter Fall eines sterbenden Intraday-Index-Momentums
  (3.7). [[zarattini-noise-area-momentum]]
- **ORB-Gegenprobe Oel (Mentor-Hinweis):** (a) Frage: Ist der ORB-Kipp
  2026 ein Index- oder ein Marktphaenomen? (b) Eingefrorener ORB auf WTI
  2016-09/2026, 8 feste Versuche ohne Optimierung. (c) Bester PF **1,03**,
  kein Eroeffnungsschock; der Filter-Kipp ist index-spezifisch, die Drehung
  der Tag-zu-Tag-Autokorrelation dagegen marktweit. (d) **Abgeschlossen**,
  als PDF fuer die Gruppenarbeit erweitert. [[orb-gegenprobe-oel]]
- **SMH-Elite-Teamaufgabe Mikrostruktur (Osler 2003, WM/R-Fix, Nagel 2012):**
  (a) Drei Literatur-Effekte: Abprall an runden Zahlen, Bewegung um den
  London-4pm-Fix, Liquiditaets-Reversal. (b) M1-Daten 2018-heute fuer vier
  FX-Paare und zwei Indizes, Split IS 04/2018-03/2023, OOS bis 09/2025,
  Tresor danach, 27 Versuche. (c) Tresor: K1 PF **0,65**, K2 PF 1,31 bei nur
  52 Trades und negativem OOS, K3 PF **0,84**. (d) **Alle verworfen**, der
  Magnet-Befund (3.8) bleibt als Wissen. [[smh-elite-mikrostruktur]]
- **G8-Waehrungsstaerke (SMH-Zustandsmodell), Nachbau:** (a) Das taegliche
  G8-Bild des Mentors ist laut Quelle ein "Zustandsmodell, kein
  Handelssignal". (b) Aus FRED-Kursen ab 1999 nachgebaut, gegen 23
  veroeffentlichte Tabellen kalibriert: Rang-Korrelation **0,95**. Als
  Strategie (Long stark/Short schwach) in IS 2000-2017 getestet. (c) Alle 4
  Varianten negativ (Sharpe −0,13 bis −0,42), Deflated Sharpe des Gewinners
  0,06. (d) **Als Kontext-Baustein behalten**, nie allein als Einstieg; OOS und
  Tresor bewusst noch zu. Neu als Datenbank im Notion-Cockpit. Siehe Memory:
  `g8_staerke_nachgebaut_kein_signal`
- **SMH-Makro-Reports (120 Reports, 800 Ideen):** als JSON extrahiert, Lock
  registriert und **vor** jedem Ergebnis eingefroren. **In Arbeit**: wartet
  auf deine Stichprobe von 11 Reports (Dashboard). [[quant-diskretionaer-fusion]]
- **Faber 10-Monats-SMA (GTAA):** mit echten Tickmill-/TTP-Kosten: TTP
  0,45-0,59 % p.a., EK 0 Trades (Mindestlot). Bester Neustart-Stand: EK mit
  5 % Risiko ca. 5,5 % p.a. bei −20 % MaxDD. **Pausiert** (07.10.), weil ein
  Drawdown-Senker strukturell nicht zu Konten passt, die mit kleinem Risiko
  +10 % verdienen muessen. Siehe Memory: `monatstrend_auf_funded_zu_klein`

**Ideen-Inbox neu (05.-11.10.):**
- (05.10.) ORB-Mechanismus-Test (Gap/Volumen) - offen.
- (05.10.) ORB-Gamma-Regime-Filter - teils einsortiert (Gamma-Regler als
  Forward-Test registriert).
- (07.10.) Copy-Trading-Bot aus den Marktupdates des Mentors - offen, erst
  die alten Calls nachtesten.
- (07.10.) Faber: Rotation nur mit Deckel - geparkt mit dem Projekt.
- (09.10.) Sechs-Bot-Architektur als Zielbild fuer den Makro-Agenten (+
  SebAI-Leitfaden) - offen, wartet auf Plan-Modus zu Strang 3/6.

## 4b. Vertiefung: Deflated Sharpe Ratio

**Was es ist:** Testet man viele Varianten und nimmt die beste, sieht diese
auch dann gut aus, wenn keine einen echten Edge hat. Das liegt allein an
der Auswahl. Die Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) rechnet
aus, welcher Sharpe beim Besten von N Versuchen schon durch Zufall zu
erwarten ist. Sie gibt die Wahrscheinlichkeit an, dass der gefundene Sharpe
darueber liegt. Ueblich ist eine Schwelle von 0,95.

**Beispiel mit unseren Zahlen:** Der IS-Gewinner fuer NASDAQ hatte t = 3,5.
Das sieht stark aus.
- Gegen 3.780 getestete Varianten ergibt die Deflated Sharpe 0,01.
- Selbst bei nur 15 unabhaengigen Versuchen waeren es 0,81, also unter 0,95.

Der Tresor hat das dann bestaetigt (PF 0,57).

**Warum es fuer unsere Bots zaehlt:** Jede Gitter-Suche erhoeht N. Ein t-Wert
von 3 ist nach 20.000 Versuchen nichts Besonderes. Deshalb fuehrt die
Overfitting-Sperre jetzt ein Trial-Register und verlangt die Deflated Sharpe
fuer jeden Gewinner.

## 5. Verbesserungen

- **Overfitting-Sperre als Standardprozess** (05.10.): `research_lock.py` mit
  Split-Registrierung, Trial-Register, `freeze`, einmaligem `unseal` und
  Deflated Sharpe, 10 Tests gruen, verankert in `CLAUDE.md`. Diese Woche schon
  achtmal angewendet (ORB, Gamma, Baltussen, SMH K1-K3, Makro-Reports, G8,
  Oel, Zarattini). [[overfitting-sperre]]
- **Vorab-Registrierung von Blindtests** vor dem Laden der Daten (Gamma
  2012-2016, Commit `2593f8d4`) und ein **Forward-Test mit technisch
  gesperrtem Oeffnen** bis 31.12. (ORB mit/ohne Gamma-Regler).
- **Live, erste Woche mit echten Orders:** Gold ASB als Stop-Order mit
  Storno 03:00 NY, ORB-Storno am geplanten SL, US30-Pause und die
  TTP-Gewichte laufen wie geplant. Die Storno-Regel hat in der ersten Woche
  ca. 2 R gespart.
- **Datenpfad ruhiger:** keine `str`/`float`-Fehler mehr ausserhalb von
  Aufwachmomenten (KW40: bis zu 47 am Tag).
- **Dachprojekt-Infrastruktur:** Notion-Cockpit mit eigener API-Integration
  (geplante Laeufe koennen ohne Session schreiben), OneNote-Import repariert
  (368 ueberschriebene Seiten wegen der Seiten-ID-Falle nachgeladen),
  Entscheidungslog mit Status "unvollstaendig".

## 6. Verschlechterungen / offene Probleme

- **CTNL-State laeuft wieder voll** und vier echte Altpositionen haben keinen
  Zeit-Exit bekommen (TTP 2x seit 30.09., IQ und FK je 1x seit 02.10.). Auf
  TTP blockieren sie den CTNL-Deckel. Nicht angefasst, Entscheidung im
  Dashboard.
- **Soll/Ist-Werkzeug:** kennt die US30-Pause nicht und handelt NASDAQ an
  Tagen, an denen die Bridge per Storno-Regel nicht handelt. Dazu die alte
  Pending-Order-Zuordnung: ORB-"nie gesehen" ist damit diese Woche komplett
  Werkzeugfehler.
- **TTP-OU scheitert bei teuren Aktien am Mindestlot** (GRMN, DE), seit der
  Gewichtung vom 04.10.
- **Standby waehrend der Handelszeit** (Do 08.10. fast 4 Stunden, Mi drei
  kurze) und ein **zweites unerwartetes Herunterfahren** in drei Wochen (So
  11.10.). Der Watchdog schlaeft weiter mit.
- **Viel Research-Arbeit ungesichert:** die Ergebnisse vom 07.-11.10. (SMH,
  Zarattini, Oel, G8, Makro-Reports, 14 Lock-Dateien) stehen im CHANGELOG,
  sind aber nicht committet. Die Lock-Dateien sind der Beweis, dass OOS und
  Tresor nur einmal geoeffnet wurden; gehen sie verloren, ist dieser
  Nachweis weg.
- **Inhaltlich:** Drei Intraday-Momentum-Ideen auf US-Indizes sind tot, und
  der Live-ORB laeuft unveraendert weiter, obwohl seine IS-only-Version im
  Tresor durchfiel. Das ist dein bewusster Entscheid (06.10.), der Preis ist
  der Forward-Test bis 31.12.

## 7. Optimierungsmoeglichkeiten

1. **CTNL-Exit-Abgleich gegen Broker-Positionen** statt gegen
   Sim-Schluessel, und die vier Altpositionen entscheiden. Das betrifft echtes
   Geld und blockiert TTPs CTNL-Bein, deshalb zuerst.
2. **Research der Woche committen** (inkl. `knowledge/_research_lock/`),
   bevor ein Auto-Task oder eine parallele Session sie gefaehrdet.
3. **`soll_ist.py` nachziehen:** pausierte Beine aus dem Soll nehmen, die
   ORB-Storno-Regel modellieren, Pending-Order-Fills zuordnen. Erst dann ist
   ORB in Soll/Ist lesbar. Nebenbei klaeren, ob die Logzeile "wie im
   Backtest" stimmt.
4. **Standby-Ursache klaeren** (Deckel/Akku/Energieplan), oder den Watchdog
   auf ein Geraet legen, das nicht mitschlaeft.
5. **Key-Level-Vertiefung** (dein Wunsch): Magnet-Regel nur auf frischen
   Maerkten oder vorwaerts testen, mit eigenem Lock.
6. **TTP-OU-Mindestlot:** entscheiden, ob teure Titel mit weitem Stop aus dem
   TTP-Universum fallen oder ob das OU-Risiko dort angehoben wird.
