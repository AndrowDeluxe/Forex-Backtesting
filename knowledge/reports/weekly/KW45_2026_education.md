# Weekly Checkup - Education - KW45/2026

**Abgedeckte Woche: Mo 2026-11-02 bis So 2026-11-08.** Erzeugt am So 08.11. durch den
geplanten `Forex-Weekly-Report`-Task.

## 1. Was stand die Woche an / Hauptfokus

Eine **Ein-Tages-Woche**. Die gesamte eigene Arbeit faellt auf **Montag, 02.11.**, danach gibt
es bis Sonntag keine Session-Spuren mehr (keine Commits ausser Automatik, keine neuen
Memory-Eintraege, keine geaenderten Notizen). Was am Montag passierte, war dafuer dicht:

- **Daily-Edge des Nutzers (Edge Card [[htf-daily-trade-edge-card]]):** Phase 0 abgeschlossen,
  dann in einer Kette getestet: Typ R (Reversal) allein, IPDA-Zyklen zweimal, Makro-Gates (Regime,
  G8), Typ C (Continuation), ein Raster aus Einstieg x Stop x Ziel und zuletzt C2 mit Gold-Filter.
  Ergebnis: kein Edge mit t > 2; einzig "C2 mit Limit-Einstieg" ist durchgehend positiv.
- **Makro-Architektur:** Regime-Quellen verglichen, Recherche [[regime-bestimmung-und-filter]],
  **Schichtenmodell beschlossen**, erster Baustein [[filter-gold-zinskurve]].
- **Gold ASB / Data Lake:** Ausfall-Ersatz vom 01.11. wieder abgeschaltet, `GOLD_D1` aus Dukascopy
  neu geschrieben, D1-Ersatz aus Intraday gebaut (`67e0060b`), Liquiditaetsfilter-Korrektur im OOS
  verworfen, Sollwerte auf Live-Stand umgestellt (`cd5e2358`).
- **Mentor-Material:** Calls "Volumen und Delta" und "COT Teil 1" aus Bildern ausgewertet
  ([[smh-volumen-delta-und-cot-calls]]), Copy-Trading-Annahmen bestaetigt.

**Was liegen blieb:** Die Handoff-Datei `knowledge/_handoff/2026-11-02_2330_daily-edge-schichtenmodell.md`
wartet seit Montag. Sie beginnt mit "Nutzer wuenscht morgen zuerst einen Stand", dazu die offene
und **irreversible** Frage, ob C2 + Gold-Filter in OOS/Blind geht. **Die gesamte Daily-Edge- und
Makro-Arbeit seit 18.10. ist weiter nicht committet** (`htf_daily_trade/`, `fusion_lab/filters/`,
fuenf Locks, drei Notizen). Siehe Performance-Report Abschnitt 6, Punkt 3: Genau dieser offene
Working Tree hat auch den Watchdog-Push die ganze Woche blockiert.

## 2. Aktive Zeiten

- **Mo 02.11. abends ca. 20:30 bis 23:30** (CHANGELOG, Memory 20:35-22:39, Handoff 23:30). Dazu
  live dabei im SMH-Call ca. 20:14-21:06.
- **Di bis So: keine eigenen Spuren im Repo.** Nur Automatik (Telegram-Import taeglich 22:00,
  Makro-Daten, Snapshots).
- **Eine Ausnahme am Do 05.11. ca. 20:30 (Berliner Zeit):** Die NASDAQ-ORB-Position wurde auf
  drei Konten innerhalb von 97 Sekunden **per Handy teilweise geschlossen** (MT5 `reason = 1`,
  Mobile). Details im Performance-Report, Abschnitt 6, Punkt 1.

Muster: wieder ein Abend, diesmal nur einer. Die restliche Woche lief das System allein.

## 3. Meine Main Erkenntnisse

### 3.1 IPDA-Zyklen tragen nichts - die Zyklik steckt im Messwerkzeug

- **Befund:** Die Wendepunkt-Abstaende von 8 / 14 / 21 Tagen kommen auf sechs Maerkten (EURUSD,
  GBPUSD, USDJPY, AUDUSD, Gold, Silber, IS 2016-21) **nicht haeufiger vor als in durchgemischten
  Kursreihen**: echt 19,4 / 7,1 / 1,1 %, Zufall 20,1 / 6,7 / 1,5 %. Auch mit der Nutzer-Definition
  (Quartals-Nullpunkt) kein Effekt: +0,61 ATR gegen +0,21 in der Kontrolle, p 0,26.
- **Mechanismus / Warum:** Jede Kursreihe hat Schwuenge. Zeichnet man Mess-Boxen mit 8, 14 und
  21 Tagen ein, findet man immer Schwuenge, die hineinpassen. Was fehlt, ist der Vergleich mit dem,
  was man ohnehin finden wuerde. Der faellt hier gleich aus.
- **Wie es aufgefallen ist:** Zwei Laeufe. Zuerst Fractal-ZigZag gegen 300 Zufallsreihen (1 von 18
  Zellen mit p < 0,05, also im Rahmen des Zufalls). Weil der Nutzer IPDA anders definiert, folgte ein
  zweiter Test mit seinem Nullpunkt gegen Anker ohne Quartalswechsel. Beide unter dem Lock
  `htf_ipda_zyklen`. Der Nutzer hat das Ergebnis angenommen: IPDA nur noch als optionale Bestaetigung.
- **Lehre:** Ein Muster, das man im Chart "sieht", braucht eine Kontrollgruppe, die dasselbe
  Werkzeug auf Zufallsdaten anwendet. Erst der Abstand zur Kontrolle ist der Edge (siehe Memory:
  `ipda_zyklen_kein_edge`; Vertiefung 4b).

### 3.2 Die Regel trifft deine Trades - und hat trotzdem keinen Edge

- **Befund:** Die Typ-R-Regel (Fractal + RSI-Extrem) fand **7 von 7** deiner EURUSD-Signale 2025/26
  ("sehr gute Stichproben"). Historisch (IS 2016-21, 32 Varianten) bringt die beste Variante aber nur
  **+0,116 R, t 1,10, DSR 0,16**. Das Confluence-Gate (mind. 5 Bestaetigungen) ist in 12 von 16
  Paaren **schlechter** als "alle Signale". Im grossen Raster (152 Versuche je Typ) erreicht keine
  Variante t > 2; einzig "C2 mit Limit auf 50 %" ist in allen 24 Kombinationen positiv (beste
  +0,176 R, t 1,74).
- **Mechanismus / Warum:** Dass eine Regel deine Trades wiederfindet, zeigt nur, dass sie deine
  Auswahl beschreibt. Ob die Auswahl Geld verdient, ist eine zweite Frage. Deine Beispiele stammen aus
  2025/26, einer Phase mit starkem Gold- und USD-Trend; ueber 2016-21 verteilt sich derselbe Aufbau
  auf Phasen ohne diesen Rueckenwind. Mehr Bestaetigungen heisst oft: spaeter einsteigen, weniger
  Restweg.
- **Wie es aufgefallen ist:** Erst der Nachbau an deinen Chart-Beispielen (Kerzen-Tabelle zum
  Gegenlesen), dann der Test strikt nur auf IS. Fast haette ein Stop am Vortages-Extrem mit
  Limit-Einstieg getaeuscht: winziges Risiko, absurde R-Werte. Das ist im Handoff als Falle notiert.
- **Lehre:** "Die Regel trifft meine Trades" ist Validierung der Regel-Beschreibung, nicht des Edges.
  Und Confluence-Zaehlen ist kein Qualitaetsfilter, solange es nicht gezaehlt getestet wurde (siehe
  Memory: `daily_edge_regel_trifft_nutzertrades`, `daily_edge_typ_r_ohne_makro_kein_edge`).

### 3.3 "Regime" ist nicht ein Ding - daher das Schichtenmodell

- **Befund:** Die Landi-Karte (Wachstum x Inflation) und das Zinskurven-Regime nach Angelo stimmen
  nur zu **26,6 %** ueberein, Zufall waere **25,2 %**. Das rohe Zinskurven-Regime wechselt **69x pro
  Jahr**. Die Dennis-Matrix sagt die USD-Richtung mit keiner Quelle vorher (t -1,4 bis +0,7). Einzig
  Gold mit 5 Tage bestaetigtem Zinskurven-Regime: **+93 bp in 20 Tagen, t 2,16**.
- **Mechanismus / Warum:** Beide "Regime" messen Verschiedenes: das eine langsame Konjunktur, das
  andere die kurzfristige Bewegung der Zinskurve. FX-Kurse haengen ausserdem an **Differenzen**
  zwischen Laendern, ein US-Regime allein kann sie nicht erklaeren.
- **Wie es aufgefallen ist:** Der Daily-Edge wurde mit Regime-Gate kaum besser (+0,120 R, t 0,91).
  Statt weitere Gates zu stapeln, wurden die Quellen gegeneinander gestellt. Die Uebereinstimmung
  auf Zufallsniveau war der Hinweis, dass "das Regime" nicht existiert.
- **Lehre:** Bevor man einen Filter aus einer Quelle baut, pruefen, ob die Quellen fuer "dasselbe"
  ueberhaupt uebereinstimmen. Beschlossen: Schichten (Kontext, Zinsen, FX relativ, Risiko) als Veto,
  nicht ein Regime als Schalter (siehe Memory: `regime_quellen_unabhaengig`,
  `schichtenmodell_makro_beschlossen`; [[filter-gold-zinskurve]]).

### 3.4 Die Korrektur eines Vorgriffs kann schlechter sein als der Vorgriff

- **Befund:** Der Gold-ASB-Liquiditaetsfilter sieht im Backtest den ganzen Handelstag (Fenster t,
  t+1). Die naheliegende Korrektur V1 ("letztes vollstaendiges Fenster") gewinnt das IS (+0,266 R,
  t 2,64), faellt im OOS aber auf **+0,082 R (t 0,72)**, gegen **+0,126 R** fuer den heutigen
  Live-Stand. Der Live-Filter bleibt.
- **Mechanismus / Warum:** Live wird ohnehin schon "kausal" gerechnet, nur eben mit dem halben Tag.
  V1 ist eine dritte Variante, nicht die Live-Wahrheit. Sie war im IS gut, weil sie im IS gewaehlt
  wurde.
- **Wie es aufgefallen ist:** Unter einer eigenen Sperre (`gold_asb_liq_fix_20261102`) mit
  eingefrorenem IS-Gewinner, OOS genau einmal geoeffnet. Gleichzeitig wurden Soll/Ist und Ampel auf
  den Live-Wissensstand umgestellt (Soll +0,308 -> +0,168 R; Ampel-Normalwert +0,146 R).
- **Lehre:** Ein gefundener Bug im Backtest heisst nicht "Live-Code aendern". Erst die Messlatte
  (Soll, Ampel) auf das setzen, was live wirklich passiert; jede Code-Korrektur ist eine gezaehlte
  Variante (siehe Memory: `gold_asb_friktion_vorgriff`).

### 3.5 Ein Fail-safe kann einen Fehlalarm erzeugen, der fuenfmal eskaliert

- **Befund:** Der Cloud-Monitor meldete ab Mo 02.11. eine "Watchdog-Luecke" und eskalierte bis Fr
  auf **~96 h** (fuenf Commits auf GitHub). **Lokal lief der Watchdog die ganze Woche** im 30-Min-Takt;
  die Bridges handelten normal.
- **Mechanismus / Warum:** Der Watchdog committet seine Snapshots lokal, mergt und pusht aber nur bei
  sauberem Working Tree. Das ist absichtlich so (seit dem Stash-Verlust 23.09. wird nie mehr
  gestasht, siehe Memory: `git_sync_stash_frisst_sessionarbeit`). Seit Montagabend liegen 5-9
  uncommittete Aenderungen im Working Tree, also wurde ab 02.11. 22:31 **254-mal** "Snapshot-Merge
  uebersprungen" geloggt; der letzte Snapshot auf GitHub ist vom 02.11. 22:07. Lokal 334 Commits
  voraus, 6 zurueck (die 6 sind die Eskalations-Commits des Monitors).
- **Wie es aufgefallen ist:** In diesem Report. Die EK-Laufprotokolle zeigen 816+ Laeufe pro Tag
  ohne Luecke ueber 30 Min., das Watchdog-Log nennt den Grund woertlich. Es ist **derselbe
  Mechanismus wie der Push-Stau vom 02.10. bis 31.10.**, nur diesmal nach drei Tagen statt einem Monat
  bemerkt.
- **Lehre:** Ein Schutz, der still "spaeter" sagt, braucht eine Obergrenze und eine eigene Meldung.
  Sonst sieht ein entfernter Beobachter nur Schweigen und deutet es als Ausfall.

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **SMH-Calls "Volumen und Delta" + "COT Teil 1"** ([[smh-volumen-delta-und-cot-calls]]).
  (a) Aussage: Sweeps unter Tiefs mit grossem Verkaufs-Delta (Absorption) markieren Wenden;
  Profile laufen "vom Extrem zum POC"; COT flach in der Range kuendigt das Auseinanderlaufen nach dem
  Sweep an. Keine Zahlen gezeigt. (b) Getestet: nichts, nur aus Bildern gelesen, weil beide
  Aufnahmen nach 9 bzw. 20 s keinen Ton mehr haben. (c) Urteil: keins. (d) **Geparkt**, vier
  Kandidaten A-D; D (Absorption) braucht Footprint-Daten. Die Lesarten warten im Dashboard auf dich.
- **Recherche Regime-Bestimmung** ([[regime-bestimmung-und-filter]]). (a) Aussage der Literatur:
  FX wird von relativen Makrodaten (Zins-/Wachstumsdifferenzen) getrieben, ein Regime-Schalter fuer
  alle Assets ist zu grob. (b) Getestet: drei Quellen auf IS 2016-21 (Lock
  `regime_quelle_vergleich`, 3 Versuche). (c) Urteil: USD-Richtung mit keiner Quelle, Gold mit
  geglaetteter Zinskurve t 2,16. (d) **In Arbeit** als Schichtenmodell.
- **Filter "Gold-Zinskurve"** ([[filter-gold-zinskurve]]). (a) Aussage: In Goldilocks/Reflation
  nur Gold-Long, in Inflation nur Short. (b) Getestet an Daily-Edge C2, nur Gold: mit Filter
  +0,70 / +0,64 R, gegen den Filter -0,22 / -0,07 R. (c) n ~24, t <= 1,6, DSR 0,12-0,16: Richtung
  stimmt, Beleg fehlt. (d) **In Arbeit**; naechster Schritt Pruefung an Gold ASB / CTNL /
  Trend-Pullback (Trendrichtungs-Strategien).
- **Zinsdaten-Quellen** (siehe Memory: `zinsdaten_zentralbanken_quellen`): EZB, MoF Japan, BoC, BoE
  liefern taeglich frei, die RBA blockt (403). Grundlage fuer die FX-Schicht. Status: Loader noch
  nicht gebaut.

**Ideen-Inbox, neu seit KW44:**
- (02.11.) LTF-/Scalping-Edge nur in Richtung eines frischen Typ-C-Signals, Kandidat Tradezella-
  Playbook "LTF Session Engineering". **Noch nicht einsortiert**, erst nach der Daily-Edge-Card.

## 4b. Vertiefung: Permutationstest - die Kontrollgruppe aus gemischten Kursen

**Was es ist.** Ein Permutationstest fragt: Wie oft wuerde ich mein Muster finden, wenn es keins
gaebe? Dazu nimmt man die echten Daten und zerstoert gezielt nur die Eigenschaft, die man testen
will. Bei IPDA ist das die zeitliche Ordnung: Die Tagesrenditen werden durchgemischt und wieder zu
einer Kursreihe aufsummiert. Volatilitaet und Renditeverteilung bleiben gleich, jede echte Zyklik
ist weg. Auf jede dieser Reihen laesst man **dasselbe Messwerkzeug** laufen (hier Fractal-ZigZag)
und zaehlt. 300 Wiederholungen ergeben die Verteilung "so viel findet man auch ohne Effekt".

**Beispiel mit unseren Zahlen.** Wendepunkt-Abstaende von 14 (+-1) Tagen: echt 7,1 %, Mittel der
300 Zufallsreihen 6,7 %. Der p-Wert ist der Anteil Zufallsreihen mit mindestens 7,1 %, hier deutlich
ueber 5 %. Bei 18 geprueften Zellen (3 Laengen x 6 Maerkte) waere schon rein zufaellig etwa eine
mit p < 0,05 zu erwarten, und genau eine wurde gefunden.

**Warum das fuer uns wichtig ist.** Viele diskretionaere Konzepte (Zyklen, Key Levels, Sessions)
werden mit Werkzeugen "gesehen", die auf jeder Kursreihe etwas finden. Der Vergleich gegen Null
("kommt das vor?") ist dann wertlos; der Vergleich gegen die Permutation ("kommt das **oefter** vor
als ohne Ursache?") trennt Muster von Messartefakt. Dieselbe Logik steckt in den Zufallseinstiegen
beim Valkyrie-Klon und im Zufallsfenster beim K4b-Nachtest. Grenze: Durchmischen zerstoert auch
Volatilitaets-Cluster; fuer Fragen, die davon abhaengen, nimmt man Block-Permutationen.

## 5. Verbesserungen

- **D1-Ersatz bei Dukascopy-Ausfall** (`67e0060b`): Tageskerzen werden aus Lake-H1 abgeleitet,
  centgenau wie Dukascopy, spaeter automatisch ersetzt. Schliesst die Luecke, die am 30.10. Gold ASB
  gekostet hat.
- **`GOLD_D1` repariert** (539 Twelve-Data-Kerzen ersetzt) und kein Twelve-Data-Failover mehr fuer
  Tagesreihen.
- **Ehrlichere Messlatte fuer Gold ASB:** Soll/Ist und Edge-Ampel rechnen auf dem Live-Wissensstand.
- **Makro-Architektur entschieden** (Schichtenmodell), erster wiederverwendbarer Filterbaustein mit
  Pruefprotokoll.
- Mehrere Dashboard-Bestaetigungen geschlossen (Copy Trading Stufe 2, Lake-Schreibregeln, Valkyrie).

## 6. Verschlechterungen / offene Probleme

- **Daily-Edge-Arbeit seit 18.10. nicht committet** und Handoff seit 02.11. offen (Abschnitt 1).
- **Watchdog-Push blockiert seit 02.11.** -> Cloud-Monitor-Fehlalarm (3.5). Wiederholung des
  Oktober-Staus.
- **Unerwarteter Neustart Mo 02.11. 02:01** (`Kernel-Power 41`, `EventLog 6008`); danach lief der
  EK-Fast-Takt 24 h doppelt (Performance-Report 6.4).
- **Gold ASB im Ausfall wieder ohne Ersatz** (Ersatz bewusst abgeschaltet). Durch den D1-Ersatz
  entschaerft, aber nur fuer die Tagesreihe; im echten Ausfall kommen die H1-Kurse von Twelve Data,
  ungetestet.
- **Edge-Ampel zum dritten Mal nicht aktualisiert** (Dukascopy-Abruf ohne Timeout haengt); Stand weiter 25.10.
- **Daily-Edge ohne Edge:** Die zwei Jahre Kern-Edge (IPDA) sind widerlegt; tragend bleibt bisher
  nur eine schwache Familie (C2, t 1,74).

## 7. Optimierungsmoeglichkeiten

1. **Den Handoff abarbeiten und committen**, dann die C2-OOS-Frage bewusst entscheiden (irreversibel).
   Ein Commit loest nebenbei den Watchdog-Push.
2. **Watchdog: Obergrenze fuer "Merge uebersprungen"** (z. B. nach 6 h Telegram-Meldung "Push
   blockiert, Working Tree offen") statt stiller Wiederholung. Und dem Cloud-Monitor beibringen,
   "kein Push" von "kein Lauf" zu unterscheiden.
3. **Gold-Zinskurven-Filter an Gold ASB / CTNL-Continuation / Trend-Pullback pruefen**, als gezaehlte
   Variante in je eigenem Lock (Pruefprotokoll steht).
4. **FX-Zinsdaten-Loader** (EZB, MoF, BoC, BoE) fuer die FX-Schicht.
5. **Manuelle Teilschliessung vom 05.11. einordnen** (Performance 6.1): bewusste Regel oder
   Einzelfall? Wenn Regel, waere sie als Variante testbar.
