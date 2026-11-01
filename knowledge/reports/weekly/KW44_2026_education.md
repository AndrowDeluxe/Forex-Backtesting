# Weekly Checkup - Education - KW44/2026

**Abgedeckte Woche: Mo 2026-10-26 bis So 2026-11-01.** Erzeugt am So 01.11. durch den
geplanten `Forex-Weekly-Report`-Task.

## 1. Was stand die Woche an / Hauptfokus

Eine Woche mit **viel Datenpfad-Forensik** und daneben breiter Research-Arbeit. Sechs Faeden:

- **Live-Stoerungen (Di-So):** Serverzeit-Fix fuer ORB (27.10.), OU-Ausstiege nur zur Kassazeit
  (28.10.), Analyse des Ausfalls 28.-30.10., Ausfall-Ersatz fuer den Gold-ASB-Filter (01.11.).
- **Data Lake (Mi-Fr):** Doppelkerzen aus dem Zeitzonen-Chaos entfernt, `_bar_length()` gehaertet,
  Twelve-Data-Fremdkerzen gefunden und Schreibschutz gebaut (`e6016922`, `ac3be2bb`).
- **Portfolio-Diagnose (Mi):** Residual-Edge-Check, Beine je Regime, Skill-Test ueber ORB + CTNL.
  Dabei entstanden zwei eingefrorene Forward-Filter.
- **Makro-Agent (Mi-Fr):** Plan Phase 2 freigegeben, Regime-Richtungstest durchgefallen, Datenschicht
  A1 gebaut (`635dd81e`).
- **Gekaufte EAs (Mi-Fr):** Portables Tester-Terminal, Quantum-Valkyrie-Nachbau, Klon verworfen.
- **Mentor-Material (Mo-Mi):** Copy Trading OOS und Stufe 2, SMH-Call "Session Pips" nachgerechnet.

**Commits:** Anders als in KW43 wurde die Wochenarbeit gesichert: Sammel-Commit `8143a3bb` (30.10.)
und der Push-Stau geloest (`dd0ec740`, 1.618 lokale Commits). Offen im Working Tree bleibt nur der
Stand vom 01.11. (ASB-Ausfall-Ersatz, Edge Card EURUSD).

## 2. Aktive Zeiten

Nach Memory-Zeitstempeln, CHANGELOG und Commits:

- **Nacht So/Mo ca. 03:30** (Copy-Trading-Raster), danach Standby bis Di mittag,
- **Di abends bis ca. 23:30** (Serverzeit-Fix 17:56, Report, SMH-Call),
- **Mi durchgehend, vormittags bis ca. 22 Uhr** (der dichteste Tag der Woche),
- **Fr vormittags bis mittags und abends bis 22:36** (Lake, Valkyrie, Makro-Daten),
- **Sa und So jeweils vormittags bis ca. 13 Uhr** (Ausfall-Analyse, ASB-Ersatz, EURUSD-Trade).

Do gibt es kaum eigene Spuren; das war der Ausfalltag. Wieder ueberwiegend Abende, diesmal mit zwei
Wochenend-Vormittagen.

## 3. Meine Main Erkenntnisse

### 3.1 Ein Fallback ohne Spur ist gefaehrlicher als ein Ausfall

**Befund:** Vom 28.10. abends bis 30.10. 10:55 fiel die Dukascopy-Aufloesung aus. Twelve Data sprang
ein und schrieb **500 Kerzen rueckwirkend in 11 Lake-Reihen**, ohne eine einzige Logzeile. Die Folgen:
Phantom-Meldungen "Trend Pullback verpasst", GOLD_H4 sprang von 686 auf 1.084 Zeilen, und **Gold ASB
legte am 30.10. auf allen Bridges keine Order** (Sim +1,93 R, grob 2.640 USD auf Funded + FK).

**Mechanismus / Warum:** Der Ingest haengt bis zum Task-Limit und wird abgebrochen, seine Ausgabe geht
dabei verloren, weil PowerShell erst am Ende schreibt. Der Lake veraltet, der Live-Fallback haengt
ebenfalls, alle Dukascopy-Beine melden Scan-Fehler. Der Failover holt pauschal 500 Kerzen statt nur die
fehlenden, und zwar mit anderem H4-Raster.

**Wie es aufgefallen ist:** Der Fingerabdruck war **Volumen 0** und ein Zeilensprung nach der Reparatur vom
28.10. Dabei gab es einen doppelten Fehlschluss: Der Reparatur-Vergleich endete am 22.09. und uebersah die
neuen Kerzen. Die Aussage vom 30.10. "Live-Einstiege im Oktober betroffen" wurde am 31.10. per Backup
zurueckgenommen: Die Fremdkerzen kamen erst mit dem Ausfall. **Neu aus diesem Report:** Auch
`api.binance.com` hatte im selben Fenster 195 Fehler. Das spricht eher fuer das lokale Netz als fuer
Dukascopy (Performance, Abschnitt 6, Punkt 2).

**Lehre / Regel:** Ein Failover muss laut sein und darf nur anhaengen, nie ueberschreiben. Nach einer Reparatur
die ganze Reihe bis heute pruefen, nicht nur das Fehlerfenster. "Verpasst"-Meldungen erst auf sauberen Daten
nachrechnen.
siehe Memory: `dukascopy_ausfall_kaskade` · `lake_h4_duplikate_bar_length_vorgriff`

### 3.2 Korrekt aussehender Code, falsche Eingabe: zwei Vorgriffe in einer Woche

**Befund:** (a) `_bar_length()` lieferte fuer H4 **1 h statt 4 h**, weil Doppelkerzen den Modus verschoben. Jede
Nachrechnung auf Lake-Daten sah bis zu **3 h in die Zukunft**. Das war der "CTNL 2-3 h Versatz" aus KW42/43.
(b) Der ASB-Liquiditaetsfilter kennt im Backtest Hoch und Tief des ganzen Handelstags: **Backtest Oe +0,308 R (n
273), Live-Wissensstand +0,168 R (n 408)**.

**Mechanismus / Warum:** Im Fall (a) ist der Shift um eine Balkenlaenge kausal richtig, nur die Balkenlaenge wird
aus den Daten geschaetzt. Im Fall (b) datiert `corwin_schultz_spread` den Wert auf t, nutzt aber t und t+1. Der
Name `_causal` bezog sich nur auf die Schwelle, nicht auf den Tageswert. Der Filter ist live also lockerer als
im Backtest: Er laesst 136 Zusatztrades durch, und die haben Oe -0,122 R.

**Wie es aufgefallen ist:** (a) ueber einen Echtzeit-Replay: Daten je Zeitpunkt T auf bis T geschlossene Kerzen
kuerzen, dann stufenweise vergleichen. (b) nebenbei beim Backtest des Ausfall-Ersatzes, weil der Filter mit
"Stand von gestern" ploetzlich andere Trades lieferte. Vermutlich erklaert das auch das alte Raetsel vom 01.09.
(Trade live ja, Nachrechnung nein); direkt geprueft ist das nicht.

**Lehre / Regel:** Ein Name wie `causal` beweist nichts. Bei jedem Filter fragen: Was genau war um die Uhrzeit des
Einstiegs bekannt? **Praktische Folge:** ASB-Sollwerte gegen +0,168 R lesen, nicht gegen +0,3 R. Ein Fix waere eine
gezaehlte Variante und nur per Forward pruefbar. Die Entscheidung steht im Dashboard.
siehe Memory: `gold_asb_friktion_vorgriff` · `lake_h4_duplikate_bar_length_vorgriff`

### 3.3 Das Portfolio ist staerker Gold als die Zahl der Beine vermuten laesst

**Befund:** Eigener Ertrag mit t > 2 nach Abzug des Basiswerts haben nur **trend_pullback 2,96, gold_silver 2,59 und
gold_asb 2,42** (ctnl_reversal 2,15 nur im IS). Nicht gesichert sind orb_sp500 1,24, orb_nasdaq 1,09, ou_modell 0,38.
Kein Bein ist je Wachstums-Inflations-Regime abhaengig (18 Tests, alle p >= 0,08).

**Mechanismus / Warum:** Kein Bein ist verkapptes Halten (R² <= 0,09). Rund 20 % des Ertrags von gold_silver und
trend_pullback kommen dennoch aus dem Gold-Beta der Rallye 2023-26. Faellt die Rallye weg, faellt dieser Teil weg. Die
ORB-Beine zeigen OOS keinen eigenen nachweisbaren Ertrag; das deckt sich mit dem durchgefallenen IS-only-Tresor.

**Wie es aufgefallen ist:** Durch den Skill `residual-edge-analyzer`, der zunaechst pauschal "fragil" meldete. Die Ursache
war eine Methodenfalle: Der 12-Monats-Trendfaktor ist 2023-26 fast deckungsgleich mit dem Basiswert, weil beide nur
stiegen, und die Regression wird singulaer. Die Regime-Auswertung nutzte eine zirkulaere Verschiebung als Zufallstest, damit
die Blockstruktur erhalten bleibt.

**Lehre / Regel:** Bein-Anzahl ist keine Diversifikation. Bei Gewichtungen immer Gold-Konzentration und Beta mitdenken. Die
Regimekarte ist Kontext, kein Bein-Schalter. KW44 passt als Anschauung: 92 % des USD-Verlusts kamen aus einem einzigen
Gold-Gegenlauf (kein Beleg, nur ein Beispiel).
siehe Memory: `residual_edge_gold_traegt_orb_ou_nicht` · `edges_regimeneutral_wachstum_inflation` · [[residual-edge-check]] ·
[[edges-je-regime]]

### 3.4 Exakt nachgerechnet heisst nicht realistisch: Valkyrie

**Befund:** Der Klon eines gekauften Gold-EAs replizierte **94-95 % der Ausstiege auf die Minute** und korrelierte bis **0,9996**
mit der MT5-Kapitalkurve. Trotzdem: Im Tresor zeigt das OHLC-Modell +0,068 R (t 4,3), **echte Ticks -0,001 R**, und
**Zufallseinstiege +0,070 R**. Blindtest nach Kosten -0,000 R. Klon verworfen.

**Mechanismus / Warum:** Das MT5-Modell "1 Minute OHLC" erzeugt vier Ticks je Minute. Ein Trailing von 0,50 $ sieht darin einen
glatten Verlauf und wird seltener ausgestoppt als in der Wirklichkeit. Der Gewinn entsteht im Modell, nicht am Markt.

**Wie es aufgefallen ist:** Die Zufallseinstiegs-Kontrolle war vor dem ersten Lauf festgelegt und schlug den Klon. Das Kriterium hatte
die Sperre `valkyrie_klon_20261030` vorab fixiert, sodass die schoene Korrelation nichts retten konnte. Der EA selbst bleibt auf echten
Ticks positiv (+0,067 R, t 2,74, 17 Monate), aber sein Ausloeser ist nicht nachbaubar (bei 50 % Recall hoechstens 14 % Praezision).

**Lehre / Regel:** Bei Trailing oder Zielen von wenigen Dollar nie allein das OHLC-Modell. Immer Zufallseinstiege plus echte Ticks. Eine hohe
Uebereinstimmung mit dem Tester beweist nur, dass man den Tester verstanden hat.
siehe Memory: `valkyrie_klon_edge_im_tickmodell` · `mt5_ohlc_tickmodell_exakt_nachbaubar` · [[quantum-valkyrie-edge-card]]

### 3.5 Live stoppt intrabar, Soll stoppt zum Schluss: dieselbe Woche, zwei Ergebnisse

**Befund:** Das Soll zeigt fuer CTNL diese Woche **+4,36 R**, live gab es auf Funded **-915 USD**. Allein der Short vom 27.10. steht im Soll mit
**+5,45 R** im Ziel, live waere er ausgestoppt worden: Hoch **4.081,96**, SL 4.076,96, hoechster M15-Schluss nur **4.074,29**.

**Mechanismus / Warum:** Die Engine prueft den Stop auf dem Kerzenschluss, der Broker intrabar. Ein kurzer Docht reicht live. Das ist
als rund 0,1 R je Trade bekannt, kann aber in einer Woche auch 6,5 R auf einem Trade ausmachen, weil danach das weit entfernte Ziel erreicht wird.

**Wie es aufgefallen ist:** Bei diesem Report, beim Abgleich von Soll-Ausstieg und Live-Stopkursen gegen die M15-Kerzen. Die Zuordnung Soll-Trade zu SL
ist erschlossen, nicht aus der Engine ausgelesen. Das "nicht platziert" im Werkzeug hatte zuerst wie ein verpasster Gewinner ausgesehen.

**Lehre / Regel:** Ein grosser Soll-Gewinn ohne Live-Gegenstueck ist zuerst ein Modellverdacht. Vor dem Wort "verpasst" das Kerzenhoch gegen den Live-Stop
legen.
siehe Memory: `engine_schlusskurs_sl_vs_broker_intrabar`

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Skill-Test ORB + CTNL (Trading-Skills, kein Paper):** (a) 69 uebernommene Skills sollen Kontext und Filter liefern. (b) Auf IS mit gezaehlten Varianten
  ueber die Live-Listen getestet. (c) **ORB-H1** (nur nach fallendem 20-Tage-Index) IS Oe R 0,56 → 0,91 (p 0,013, mit Storno; NASDAQ nur 0,53 → 0,55).
  **CTNL-News-Filter** (keine US-High-Impact-Tage) 0,84 → 1,20, p 0,003. (d) **Beide eingefroren, Forward 02.11.2026-31.03.2027**, kein Live-Eingriff.
  [[skill-test-orb-ctnl]]
- **Residual-Edge-Check:** (a) Skill trennt Beta und eigenen Ertrag. (b) OOS + Tresor aller Live-Beine gegen "Basiswert halten". (c) Nur Gold-Beine t > 2 (3.3).
  (d) **Diagnose, keine Aenderung.** [[residual-edge-check]]
- **Beine je Regime:** (a) Annahme: Edges haengen am Wachstums-Inflations-Regime. (b) 9 Beine x 2 Linsen, nur IS. (c) Alle p >= 0,08. ORB schwach und trend_pullback
  stark in g up/slow x pi up/accel, nicht gesichert. (d) **Keine Regel.** [[edges-je-regime]]
- **Regime-Richtung je Asset:** (a) Assets laufen je Regime in eine stabile Richtung. (b) 25 Assets, First Prints, IS 2000-2014. (c) IS Sharpe **1,60**, OOS **0,14**, Tresor
  **-0,30**; 250 gewaehlte Vorzeichen. Nur Gold hielt (OOS 0,92). (d) **Verworfen als Regel**, Regimekarte bleibt Kontext. [[regimekarte-wachstum-inflation]]
- **Quantum Valkyrie (gekaufter EA):** (a) Viele kleine Gewinne um 3,70 $ durch enges Trailing. (b) Nachbau aus drei MT5-Berichten, Lock mit vorab festem Kriterium. (c) Blindtest
  -0,000 R, Zufall gleichauf (3.4). (d) **Klon verworfen**; den Original-EA zu bewerten bleibt eine eigene Frage. [[quantum-valkyrie-edge-card]]
- **Copy Trading:** (a) Dennis' Calls sollen kopierbar sein. (b) A2 auf OOS 01.04.-16.10.2026, Stufe 2 mit seinen Nachfass-Anweisungen auf IS. (c) OOS **-0,72 R, t -3,65**. Stufe 2 IS
  +0,47 → +0,08 R: BE rettet 17 Verlierer und kappt 11 grosse Gewinner. (d) **Verworfen; Stufe 2 Forward bis 31.03.2027.** [[copy-trading-dennis-edge-card]]
- **SMH-Call "Session Pips" (Mentor):** (a) Stundenprofil stabil, Ruck zu festen Terminen, Umkehr nach ausgeschoepfter Stunde. (b) Nachgerechnet, dann Inventur. (c) 07:00-Ruck nur 1,10x
  (Kontrolle 1,16x); Termin-Sperre traefe nur 13 Trades; Fade brutto t 5,8, aber netto -0,122 T, 0/7 Maerkte. (d) **Verworfen**, Vorgehen "Nachrechnen → Inventur → Test" als Regel behalten.
  [[smh-session-pips-call]]
- **Makro-Datenschicht A1:** kein Test, Baustein. Dabei fiel auf, dass OECD-Reihen auf FRED still enden (JP 2022, GB/CA 03/2025). [[makro-datenquellen]]
- **Edge Card EURUSD Lower-High-Limit:** dein Short vom 30.10., Phase 0 **wartet auf deine Bestaetigung**. [[eurusd-lower-high-limit-edge-card]]

**Ideen-Inbox neu (26.10.-01.11.):**
- (28.10.) ORB-Pivots: Paar-Handel SP500/NASDAQ, Fade am Open, Pullback-Einstieg - unsortiert, jede waere eine neue Sperre.
- (28.10.) IBD-Befund umgedreht: ORB verdient in Distribution-Phasen - nicht separat testen, deckt sich mit ORB-H1.
- (27.10.) OU-Research-Skripte auf NY+7 umstellen - offen, nur Research.

## 4b. Vertiefung: Residual-Analyse - was bleibt, wenn man den Markt abzieht?

**Was es ist:** Man erklaert die Tagesrendite einer Strategie per Regression durch das, was man auch billiger haben koennte, meist "Basiswert halten": Rendite = Alpha + Beta x
Basiswert + Rest. **Beta** ist die mitgekaufte Marktbewegung, **Alpha** der Rest-Ertrag, den die Regel selbst beitraegt. Der t-Wert des Alphas sagt, ob dieser Rest von null
unterscheidbar ist. Weil Renditen ueber die Zeit zusammenhaengen, nimmt man robuste Standardfehler (HAC, also Newey-West).

**Beispiel mit unseren Zahlen:** gold_silver hat t 2,59, und rund 20 % seines Ertrags stammen aus dem Gold-Beta. Heisst: Vier Fuenftel sind eigene Leistung, ein Fuenftel haette auch
blosses Halten waehrend der Rallye 2023-26 gebracht. gold_asb liegt bei 9 % Beta und t 2,42. orb_nasdaq dagegen zeigt t 1,09: In OOS + Tresor ist ein eigener Ertrag nicht nachweisbar,
obwohl die Live-Version dort im Plus liegt. R² <= 0,09 sagt zugleich: Kein Bein laeuft einfach mit dem Markt.

**Die Falle dieser Woche:** Nimmt man einen 12-Monats-Trendfaktor dazu, ist er 2023-26 fast identisch mit dem Basiswert, weil beide nur stiegen. Zwei fast gleiche Erklaerer machen die Regression
singulaer, das Ergebnis springt, und der Skill meldet "fragil". Das ist dann eine Aussage ueber die Daten, nicht ueber die Strategie.

**Warum es fuer unsere Bots zaehlt:** Ein hoher Backtest-Ertrag in einer Goldrallye beweist noch nichts. Erst das Alpha sagt, was in einer Gold-Baisse bliebe. Fuer Gewichtungen ist das die ehrlichere
Zahl, und fuer neue Edges wird der Check nach Phase 6 zur zusaetzlichen Gegenprobe.
siehe Memory: `residual_edge_gold_traegt_orb_ou_nicht` · [[residual-edge-check]]

## 5. Verbesserungen

- **ORB-Serverzeit korrigiert** (27.10., Funded + FK): lief danach auf allen Konten, wie das Storno am 29./30.10. zeigt.
- **OU-Ausstiege nur zur Kassazeit** (28.10., Funded): Schluss mit dem Rauschen aus abgelehnten Orders.
- **Data Lake:** Reihen repariert, Raster-Pruefung und Historienschutz beim Schreiben, Failover nur noch anhaengend (`e6016922`).
- **`_bar_length()` gehaertet** (`ac3be2bb`), auf sauberen Daten bit-identisch.
- **Git-Push-Stau geloest** (`dd0ec740`); die "Watchdog-Ausfall"-Meldungen des Cloud-Monitors seit 02.10. erklaeren sich damit.
- **Makro-Datenschicht A1** mit Task `Makro-Daten`, 12 Tests.
- **Research gesichert:** Sammel-Commit `8143a3bb`, anders als in KW43.
- **Neue Werkzeuge:** Portables Tester-Terminal, `mt5_tester_lock.py`, `research_lock.skip_oos()`, ORB-Listen mit Storno.

## 6. Verschlechterungen / offene Probleme

- **Mo/Di 25,6 Stunden Standby, Ursache offen** (kein leerer Akku), ORB 26.10. verpasst, auch auf EK. Korrigiert die KW43-Darstellung.
- **Ausfall 28.-30.10.:** Gold ASB verpasst, Ursache laut neuem Hinweis eher lokales Netz, ungeklaert.
- **ASB-Vorgriff im Filter** und **`GOLD_D1` zu 540 von 557 Zeilen aus Twelve Data**: beide nicht behoben. Der Lake-Schutz deckt D1 nicht ab.
- **Ausfall-Ersatz ohne belegten Edge** ist auf allen drei Bridges aktiv, Entscheidung offen.
- **IQ wieder naeher an der 6-%-Grenze** (ca. 2.907 USD Abstand).
- **`soll_ist.py`** zaehlt stillgelegte und pausierte Beine, kennt das Storno nicht und stoppt zum Schluss.
- **Edge-Ampel nicht aktualisiert:** zwei Laeufe abgebrochen, der Stand ist der von KW43.
- **STT** auf TTP weiter Waise; **FK-SL 2624779** ohne Spur verschoben.

## 7. Optimierungsmoeglichkeiten

1. **VPS jetzt angehen** (von dir auf November gelegt, und es ist November): Standby 26./27.10., Akku 20.10., wohl auch das lokale Netz. Vorher VPS/IP-Regeln bei TTP und BeyondIQ klaeren.
2. **Totmannschalter ausserhalb des Rechners:** Der Watchdog hat auch diesen Standby nicht melden koennen.
3. **Ausfall-Ersatz ASB entscheiden** (Empfehlung im Dashboard: abschalten) und zusammen damit den Filter-Vorgriff.
4. **`GOLD_D1` reparieren und den Lake-Schutz auf D1 ausdehnen**, weil die Reihe den ASB-Filter speist.
5. **`soll_ist.py` pflegen:** stillgelegte Beine raus, Storno rein, optional Intrabar-Stop. Sonst ist die Zahl in Wochen wie dieser nicht lesbar.
6. **DNS-Hinweis pruefen** (Binance-Fehler, Event-Log), bevor weitere Dukascopy-Absicherung gebaut wird.
