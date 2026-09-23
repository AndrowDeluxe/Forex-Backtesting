# Changelog

Vollständiges, chronologisches Log relevanter Änderungen (neueste oben).
Ein Eintrag pro Änderung: Datum, Bereich, Kurzbeschreibung, Commit-Hash wo
zutreffend. Wird von Claude bei jeder relevanten Änderung ergänzt (siehe
`CLAUDE.md`). Nicht committen vergessen wird hier nichts eingetragen, was
nicht auch tatsächlich passiert ist — dieses Log ist reine Beobachtung,
keine Planung (dafür ist `DASHBOARD.md`).

---

- **2026-09-23** [EK-Portfolio-Bridge / CTNL] **E5-c umgesetzt:
  `ctnl_reversal` haelt auf EK ab sofort hoechstens EINE gleichzeitige
  Position** (Nutzerentscheid; die Mindestlot-Anhebung bleibt ausdruecklich
  erhalten, gedeckelt wird die Anzahl).
  Neu: `config.py::CTNL_REV_MAX_CONCURRENT = 1`, ausgewertet in
  `legs/ctnl_edge/executor.py::check_and_execute_reversal()` per
  `getattr(config, ..., signal_source.REV_MAX_CONCURRENT)`.
  **Bewusst NICHT in `gold_smc_htf_ltf/live_signal.py`:** die dortige
  `REV_MAX_CONCURRENT = 3` ist die STRATEGIE-Vorgabe und wird von
  Funded-Portfolio-Bridge und FKInstantFunding mitbenutzt -- eine Aenderung
  dort haette alle drei Bridges getroffen. Dies ist eine reine
  KONTO-Beschraenkung wegen der Kontogroesse. Faellt die Konstante weg, gilt
  automatisch wieder die Strategie-Vorgabe.
  **Wirkung:** der Beitrag des Beins sinkt von 2,59 % auf ~0,86 % der Equity.
  **Gegen die Live-Lage getestet:** Strategie-Vorgabe 3, Konto-Deckel 1,
  3 Positionen real offen -> `{'status': 'skipped', 'reason':
  'max_concurrent_reached', 'count': 3, 'limit': 1}`. Die drei offenen
  Positionen (alle mit SL) laufen unveraendert weiter und werden NICHT
  zwangsgeschlossen -- der Deckel wirkt nur auf neue Entries, gleiches Muster
  wie Kill-Switch und Risiko-Deckel. Das Bein bleibt damit gesperrt, bis die
  drei ausgelaufen sind; danach laeuft es mit einer Position weiter.

- **2026-09-23** [OU-Modell / alle Bridges + Git-Sync] **Umbau auf Logik D +
  BB_K 2,25 umgesetzt, Git-Sync repariert** (Nutzerfreigabe, Plan
  `.claude/plans/quirky-painting-pancake.md`). **Nicht scharf geschaltet** --
  DRY_RUN unveraendert, kein Live-Lauf ausgeloest.
  **Code:** `portfolio.py::simulate_bracket_portfolio(ma_exit=...)` neu
  (Default False, Bestandsverhalten unveraendert, Regression bestaetigt:
  alte Logik gepinnt liefert weiter -0,0536R OOS); `paper_bot.py` auf
  stop_sigma 8,0 / BE 0 / kein TP / ma_exit / k=2,25; `scanner.py` mit lokalem
  BB_K 2,25 und Stop 8,0, ohne TP, plus **neu `ou_exit_levels.csv`**;
  EK-Bridge mit MA20-Ausstieg, echtem Max-Holding-Schluss und Breakeven aus.
  `ek_portfolio/paper_bot.py` blieb unangetastet -- der simuliert die Strategie
  nicht, er liest ihre realisierten Tagesrenditen.
  **Warum ou_exit_levels.csv:** `scanner_signals.csv` enthaelt nur Titel mit
  EINSTIEGSsignal. Eine gehaltene Position ist keiner davon mehr -- der
  MA-Ausstieg der EK-Bridge waere stillschweigend nie gefeuert.
  **Ergebnis auf der Trade-Liste, die der Live-Pfad wirklich erzeugt:** FK
  **+0,0117R (PF 1,12)**, EK **+0,0165R (PF 1,17)**, 3 von 4 OOS-Jahren
  positiv, P(DD>7 %) = 0,00 %. Vorher: -0,052R (PF 0,83) bzw. -0,028R, 0 von 4
  Jahren. Rund 20 % unter der Studienerwartung, weil der MA-Ausstieg jetzt in
  der Engine statt im Replay greift -- andere Belegung des Risikodeckels, 764
  statt 665 Trades. Ehrlich ausgewiesen statt die Studienzahl weiterzutragen.
  **Git-Sync (Ursache der verschwindenden Arbeitsstaende):** `git_sync_push` und
  `Bridge-Watchdog/watchdog.py` stashten bei JEDEM Lauf und setzten bei einem
  kollidierenden Pop per `reset --hard` zurueck -- 93 Stashes, und am 23.09.
  zweimal mitten in einer Session zugeschlagen (erst ein Dashboard-Eintrag,
  dann zwei Code-Edits). Jetzt: kein Stash/Merge, wenn nichts eingeht (der
  Normalfall), und bei echtem Konflikt eine Markierungsdatei
  `knowledge/_handoff/GIT_STASH_KONFLIKT.md`. Beide Pfade getestet.
  **Scanner-Befunde:** 45 von 57 Titeln hatten um 22:20 Uhr erst den
  Vortagesschluss (yfinance liefert nach Handelsende nicht sofort alles) --
  `ou_exit_levels.csv` deckt abends daher nur einen Teil ab, die EK-Bridge
  meldet fehlende Schwellen jetzt taeglich. Und `_refresh_universe_prices()`
  liess Ticker ohne Antwort still fallen ("scanning 58", Rechnung mit 6);
  meldet die Abdeckung jetzt.

- **2026-09-23** [Research / EU-Open-Fenster] **Edge-Kandidat durchgerechnet --
  ehrliches Negativergebnis, nicht gebaut.** Nutzerauftrag "gehe alle Punkte
  durch". Neu: `scripts/research_eu_open_window.py`, `_decay.py`,
  `_windowscan.py`; Daten in `knowledge/_data/eu_open_*.json` +
  `broker_spreads_indices_euopen.json`. Alles rein lesend, kein Bot beruehrt.
  **Schritt 0 (Kosten) bestanden**: Nacht-Spreads 05:30-09:30 Berlin sind
  NICHT weiter als tagsueber (Tickmill 0,23-0,39 bps, TTP 0,49-0,83) --
  gegen eine Break-even-Schwelle von 3,08 bps waere das Faktor 4-13 Puffer
  gewesen. **Schritt 1 (Decay) gescheitert**: ueber 2018-2026 nominal positiv
  (SP500 +3,5 %, NASDAQ +5,2 %), aber **2020 allein traegt alles** (+24,3 /
  +24,4 / +28,4 %); ohne 2020 bleiben +0,67 / **-0,29** / +2,07 % bei t<1,2,
  also **unter den Handelskosten**. Unser 2020-Wert trifft die vom Paper
  berichteten +24,5 % fast exakt -- die Pipeline misst richtig, der Zerfall
  danach ist echt. Die konditionale Rettung des Papers (Tagesauswahl ueber
  Overnight-Vol) sieht mit +8 % p.a. stark aus, **kollabiert ohne 2020 aber
  auf +0,9 bis +1,8 % bei t=0,31-0,49** -- sie selektiert im Wesentlichen
  2020. Gegenchecks: Berlin- und ET-Verankerung liefern dasselbe; ein Scan
  ueber alle 42 Vier-Stunden-Fenster findet **kein einziges** ueber der
  White-(2000)-Schwelle |t|>=3,7, und das EU-Fenster rangiert ab 2021 auf
  Rang 38/42 (SP500) bzw. 40/42 (US30) -- nicht verschoben, sondern tot.
  Phase 6 bewusst NICHT gerechnet (nichts Positives zum Stresstesten).
  **Dabei ein eigener Bug gefunden und behoben**: Fenster ueber Mitternacht
  wurden mit dem Endzeitpunkt DESSELBEN Kalendertags gepaart (minus 20 h
  statt plus 4 h) und wiesen ET-Fenster faelschlich mit -13 bis -19 % p.a.
  aus -- haette unentdeckt wie ein spektakulaerer Short-Edge ausgesehen.

- **2026-09-23** [scripts/reports/mt5_pull.py] **Fenster-Fix: Tagesabzuege
  verlieren die letzten Stunden nicht mehr** (Nutzerauftrag "fixe das").
  `pull()` fragt `history_deals_get()` jetzt beidseitig um einen Tag geweitet ab
  und filtert danach selbst gegen die Serverzeit (`frm <= ts < to`, obere Grenze
  exklusiv wie bisher). Gefiltert wird gegen DIESELBE Zeitbasis, die als
  `time_iso` rausgeht -- Unix-Zeitstempel als UTC gelesen == Serverzeit.
  **Verifiziert:** (a) der gemeldete Fall -- `--from 2026-09-23 --to 2026-09-24`
  gab vorher EK 13 / TTP 11 Deals, jetzt **22 / 14**; (b) `--to 2026-09-25`
  liefert exakt dasselbe wie `--to 2026-09-24`, das Fenster ist also nicht mehr
  von der Obergrenze abhaengig; (c) der alte Lauf war an BEIDEN Raendern
  verschoben -- er zog Spaet-Deals des VORTAGS mit herein (deshalb TTP alt 16,
  neu 14) und liess die des Zieltags fallen; (d) **Wochenabzug unveraendert**:
  2026-W38 gegen den archivierten Report gerechnet, identische Deal-Zahlen und
  Summen (EK 40/−227,31, TTP 89/−898,07, IQ 98/+1.411,14) -- `week_bounds()`
  hatte durch die Montag-00:00-Grenze genug Puffer. `py_compile` sauber, Modul
  bleibt rein lesend (keine Handelsfunktion, nur `account_info`,
  `history_deals_get`, `positions_get`). Docstring von `week_bounds()`
  entsprechend nachgezogen.
  **Auswirkung auf die Auswertung vom 22.09.:** nur TTP am 22.09. +320,86 ->
  +325,26 (der CF-Exit um 22:13 Serverzeit lag jenseits der alten Grenze),
  Zwei-Tage-Summe +601,49 -> +605,89 USD. Alle Aussagen dieser Auswertung
  bleiben unveraendert.
  **Nebenbefund:** `mt5_pull.py` und `soll_ist.py` sind **nicht git-getrackt**
  (`??` im Status, nicht per `.gitignore` ausgeschlossen) -- kein Backup, keine
  Historie, gleiches Muster wie `data_lake/` am 06.09. In DASHBOARD.md zur
  Freigabe gelegt, nicht eigenmaechtig committet.

- **2026-09-23** [OU-Modell / Funded + EK] **Logik D + Signalseite UMGESETZT -- das Bein laeuft jetzt nach der validierten Konfiguration.** Nutzerfreigabe nach `projects/ou-modell-kostenvalidierung.md`. **Neu:** `stop_sigma` 3 -> 8, Break-Even-Stop aus, **kein TP mehr** (auch nicht fuer S&P), Ausstieg beim **Ruecklauf ans MA20**, `BB_K` 2,0 -> 2,25, `max_hold` 10 unveraendert. **Ergebnis OOS:** -0,052R (PF 0,83) -> **+0,008R (PF 1,08)** auf TTP-Kosten, -0,028R -> **+0,013R (PF 1,13)** auf Tickmill; schlechtester Trade -2,54R -> -0,90R (die Position ist bei gleichem Dollar-Risiko nur noch 37,5 % so gross). Phase 6: P(DD>7 %) = 0,00 %, negative MC-Pfade 30 % -> 18 %. **Ehrliche Lesart: von "verliert zuverlaessig" auf "verdient wenig" -- kein Edge-Nachweis, 2023 bleibt in jeder Variante negativ.**
  **Geaendert:** `ou_paper_backtest/scanner.py` (Stop 8 Sigma, kein TP, `BB_K` lokal 2,25 statt der globalen Konstante -- die wirkt auf jeden Paket-Nutzer; neue Spalte `ma20` als Ausstiegsschwelle fuer die Bridges), `challenge_portfolio/paper_bot.py` (Funded, live: Sigma/BE/rr_ratio + `ma_exit=True`, `k=2.25`), `EK-Portfolio-Bridge/config.py` (BE-Trigger 0) und `EK-Portfolio-Bridge/legs/ou_modell/` (`ma20_by_ticker()` im signal_source; Executor: Break-Even-Zweig entfernt, MA20-Ausstieg neu, **und `max_hold` schliesst jetzt wirklich** statt nur CRITICAL zu loggen -- am 23.09. musste der Nutzer 9 ueberfaellige Positionen von Hand schliessen).
  **Sizing/Risiko je Konto bewusst unveraendert** (Funded 1/6 bzw. 1/3, EK 1/8 x LEG_RISK_PCT). FK hat kein OU-Bein -- die FK-Zahlen im Bericht sind ein Kostenprofil, kein eigenes Bein.
  **Tests:** Ausstiegslogik mit simuliertem Broker 9/9 (MA20 trifft nur den richtigen Ticker, max_hold schliesst, kein Break-Even mehr, NYSE zu -> keine Order, fehlende MA20-Daten -> halten statt raten). Kommentar der Schliess-Order auf `EK-OU-<grund>` gekuerzt, damit der Grund Tickmills 16-Zeichen-Limit ueberlebt.

- **2026-09-23** [CTNL / Entry-Herkunft] **Der Edge von `ctnl_reversal` liegt
  VOLLSTAENDIG auf der Long-Seite -- groesster Einzeleffekt der ganzen
  Untersuchung.** Neues Skript `research_ctnl_entry_origin.py`, Ergebnis als
  Befund 11 + Entscheidung E6 in `projects/ctnl-kostenvalidierung.md`,
  Rohdaten `_data/ctnl_entry_origin.json`. Nichts geaendert.
  **Zahlen:** long 662 Trades Ø R +0,391 / PF 1,46 / ΣR +258,9; short 591
  Trades Ø R **-0,207** / PF 0,79 / ΣR **-122,3**. Die Short-Seite vernichtet
  knapp die Haelfte des Long-Ertrags.
  **Walk-Forward:** die Prozedur waehlt in 5 von 8 Jahren `long + Regime`,
  nie die Baseline und nie `nur short`. OOS +171,8 vs. +143,4 ΣR,
  Ø R +0,542 vs. +0,165, PF 1,68 vs. 1,19.
  **Monte Carlo (0,15 %/Trade):** `long + Regime` senkt den Median-MaxDD von
  **-15,63 % auf -4,84 %** und P(MaxDD>6 %) von **99,9 % auf 23,3 %**, bei
  Median-Return +38,6 % statt +18,8 % und Sharpe 0,83 statt 0,25.
  **Der Vorbehalt, der alles relativiert:** Gold ist ueber den gesamten
  Stichprobenzeitraum gestiegen (2016 ~1.150 -> 2026 ~4.400). „Long
  funktioniert, Short nicht" auf einem einseitig steigenden Markt ist nahe an
  einer Tautologie; eine echte Gold-Baisse fehlt in der Stichprobe.
  Gegenindiz aus der Walk-Forward-Tabelle selbst: **2022** (Zinserhoehungs-
  phase) ist eines der Jahre, in denen die Richtungsbeschraenkung SCHLECHTER
  ist als die Baseline (-19,2 ΣR) -- dort haben die Shorts gearbeitet.
  **Long-only ist damit eine Wette auf den fortgesetzten Aufwaertstrend, keine
  Struktur-Erkenntnis.** Empfehlung E6: erst mitlaufen lassen (d), dann
  Long-only ohne scharfen Regime-Filter (c).
  **Eigene Luecke, die das aufgedeckt hat:** der Signal-Sweep vom selben Tag
  (Befund 9b) hat an den MTF-Kaskaden-Parametern gedreht, ohne zu pruefen, ob
  die Kaskade auf beiden Richtungen ueberhaupt funktioniert. Parameter
  optimieren, bevor man die Struktur anschaut, war die falsche Reihenfolge.
  **Weitere Eimer (deskriptiv, NICHT walk-forward-geprueft):** Wochentag
  Mi +0,644 / Do +0,426 gegen Mo/Di/Fr -0,13..-0,25; Stopdistanz Q4 (weit)
  +0,422 gegen Q2/Q3 negativ; Session NY +0,253 am besten. Wochentagseffekte
  sind der Klassiker unter den Data-Mining-Artefakten -- bewusst nicht
  weiterverfolgt. `ctnl_continuation` ist in JEDEM Eimer negativ (Richtung,
  Session, Wochentag, Stopdistanz) -- stuetzt E3 zusaetzlich.

- **2026-09-23** [EK-Portfolio-Bridge / Risiko] **🔴 Auf EK kehrt die
  Mindestlot-Anhebung die Risiko-Hierarchie um -- `ctnl_reversal` riskiert
  real das 46-fache seines Ziels.** Nutzerhinweis ("zu viel Risiko im
  Markt"), read-only nachgerechnet, **nichts geaendert**.
  **Nicht die Ursache:** `CAPITAL_WEIGHT` wird seit 2026-09-10 korrekt
  angewendet (`core/sizing.py:67`) -- der alte 8x-Fund ist behoben, die
  Memory dazu ist jetzt als ueberholt markiert.
  **Die Ursache:** bei 2.939 EUR Equity ist das Ziel-Risiko von
  `ctnl_reversal` 1/8 x 0,15 % = **0,55 EUR**. Das kleinste handelbare Lot
  (0,01 XAUUSD) riskiert bei der aktuellen Stopdistanz von 28,90 Punkten
  aber **25,38 EUR**. Faktor **46x**; `ctnl_continuation` (Ziel 1,84 EUR)
  liegt bei **14x**. Die beiden CTNL-Beine sind die einzigen Gold-Beine, die
  angehoben werden -- und landen dadurch bei einem Viertel dessen, was
  `gold_asb` als GROESSTES Bein beabsichtigt (103,47 EUR), obwohl sie auf
  1/56 bzw. 1/188 davon kalibriert sind.
  **Real offen:** `ctnl_reversal` haelt mit 3 Positionen
  (`REV_MAX_CONCURRENT = 3`) **2,59 % der Equity** im Risiko (beabsichtigt
  0,06 %) und **12.860 EUR Nominal auf einem 2.939-EUR-Konto = 4,4x Hebel**
  -- aus dem Bein, das das konservativste sein sollte. Gesamt offen 194 EUR
  (6,59 %), Gesamthebel 5,1x, 13 Positionen, alle mit SL.
  **Kein Bug:** die Anhebung ist Nutzerentscheid vom 2026-09-10
  (`core/sizing.py`, Muster aus FK), damit kleine Beine auf einem 3-k-Konto
  nicht verstummen; es gibt eine Log-Warnung. Aber die beiden Deckel greifen
  hier nicht: `MAX_SINGLE_TRADE_RISK_PCT = 5 %` liegt bei 147 EUR (nie
  ausgeloest) und `MAX_TOTAL_RISK_PCT = 30 %` ist zu 22 % ausgeschoepft.
  **Entscheidung E5** in `projects/ctnl-kostenvalidierung.md` (Befund 10):
  (a) nichts, (b) Anhebung fuer CTNL abschalten, (c) `REV_MAX_CONCURRENT`
  auf EK 3 -> 1, (d) CTNL-Risiko anheben bis Ziel >= Mindestlot. Empfehlung
  b oder c, VOR E1-E4. **Nicht geprueft:** ob dasselbe Muster auch
  `cls_practical`, `ou_modell` und die ORB-Beine trifft -- deren Ziele
  (19,40 / 10,77 / 10,58 EUR) liegen ebenfalls niedrig.

- **2026-09-23** [Aufraeum-Aktion Nutzer + Nachkontrolle] **Alle verwaisten
  Positionen sind geschlossen -- am Broker verifiziert.** Der Nutzer hat am
  23.09. zwischen 22:40:39 und 22:42:02 Serverzeit (21:40-21:42 Berlin) von
  Hand aufgeraeumt, `reason=1` (Client) und leerer Kommentar an jedem Deal.
  **Geschlossen:** die 4 OU-Solo-Waisen auf TTP Konto 2 (AFL −33,00, NUE −5,64,
  UAL −32,11, TXT −200,55) + APD −48,50, DAL auf Tickmill (−0,35), die 8
  ueberfaelligen EK-OU-Positionen (ADI +26,50, DHI −5,97, GRMN +13,80,
  AMGN +15,90, EXPE −11,70, LEN +1,98, COF −10,84, GIS −0,97) und zwei
  CTNL-Shorts auf TTP (+210,08 / +192,96). Saldo der Handschliessungen:
  **EK +20,56 EUR, TTP +30,22 USD.**
  **Nachkontrolle:** kein `OU-Modell auto`-Kommentar mehr auf irgendeinem
  Konto; offene Positionen jetzt EK 13, TTP 6, IQ 3, FK 2. Kein EK-OU-Titel
  mehr ueber dem 10-Tage-Limit. `ctnl_reversal` liegt ueberall unter der
  Grenze 3 (ttp 2, IQ 3, FK 0) -- das Bein ist auf allen Konten wieder frei.
  **Preis der Freigabe, ohne Wertung:** IQ hat noch am selben Tag 6 frische
  ctnl_reversal-Entries genommen und alle ausgestoppt (−982,00 USD); Portfolio
  heute −1.256,52 USD.
  **Nebenbefund an der Reporting-Kette:** `mt5_pull.py` verliert bei knapper
  Obergrenze die letzten Stunden -- `--to 2026-09-24` gab EK 13 / TTP 11 Deals,
  `--to 2026-09-25` gab 22 / 16. Genau die 22:40er-Schliessungen fehlten, ich
  habe sie im ersten Abzug nicht gesehen. Die naive Zeitgrenze wird nicht in
  Serverzeit ausgewertet. Weekly-Report nicht betroffen (`week_bounds()` hat
  zwei Tage Puffer). Nicht gefixt, in DASHBOARD.md zur Freigabe gelegt.

- **2026-09-23** [Second Brain / Git-Sync] **Korrektur zu meiner Verlust-Diagnose:** ich hatte gemeldet, die Eintraege vom 21./22.09. seien unwiederbringlich weg, weil "keiner der 72 Stashes sie enthaelt". Das war ein Messfehler -- `git show stash@{N}` zeigt auf einem Stash (ein Merge-Commit) einen KOMBINIERTEN Diff, in dem die Zeilen nicht als Zusatz auftauchen; sichtbar werden sie erst mit `git diff stash@{N}^ stash@{N} -- <pfad>`. Die parallele Session hat den Stand darueber vollstaendig zurueckgeholt (Eintrag weiter unten). Zweiter Fehler im selben Zug: meine Erfolgskontrolle suchte mit `grep` nach einem Begriff, der im Markdown ueber einen Zeilenumbruch lief -- dadurch meldete sie faelschlich "fehlt", und ich habe denselben Eintrag acht Mal eingefuegt (bereinigt). Lehre: bei Datei-Diagnosen erst einen Testmarker schreiben und zurueklesen, und nur zeilenanker-feste Muster zur Kontrolle verwenden.

- **2026-09-23** [EK-Portfolio-Bridge / Risiko] **Hebel auf 1,2x angehoben + Einzeltrade-Deckel 3 % -> 5 %.** Nutzerentscheid: "die 40 %-Grenze sollte ueber ein Jahr halten, Risikobereitschaft offen, passe an die groessere Option an." Damit wechselt die Messgroesse vom Drawdown ueber die volle Historie auf das rollierende JAHR (`scripts/research_ek_leverage_1y.py`, 4.000 Pfade, Monatsbloecke): 1,0x -> P(MaxDD>40 % im Jahr) 3,0 % | **1,2x -> 9,1 %** (gewaehlt, groesste Stufe <= 10 %) | 1,4x -> 26,9 % (Klippe, nicht linear). P(Jahr<0) bleibt bei 0,2 %. Neue effektive Risiken je Trade: gold_asb/btc_ema_cross/gold_silver 3,52 %, trend_pullback 2,20 %, cls_practical 0,66 %, orb je Instrument 0,36 %. **`ou_modell` NICHT mitskaliert** (wird gerade umgebaut und separat verifiziert). **`MAX_SINGLE_TRADE_RISK_PCT` musste mitwachsen:** `core/sizing.py` LEHNT Trades ueber dem Deckel AB, statt sie zu verkleinern -- bei 3 % haetten die drei groessten Beine ab sofort gar nicht mehr gehandelt. **Einordnung:** die Median-Jahresrendite der Modellkurven (+443 %) ist KEINE realistische Erwartung (Backtests; live handelt EK bislang nur einen Teil der Beine) -- belastbar ist die relative Aussage zum Hebel, nicht das Renditeniveau.

- **2026-09-23** [Alle Systeme] **TTP-Konto 504069845 (ttp1) vollstaendig ausgebaut und als abgeschlossen gewertet** (Nutzerentscheid). Entfernt aus: `Funded-Portfolio-Bridge/config.py` (bereits am 19.09.), `scripts/collect_ou_modell_daily_log.py` (Attach-Spec), `scripts/close_ou_solo_orphans_once.py` (Schliess-Ziele DAL/UAL/NUE) und `scripts/reports/_kw37_pull.py` (Zeile enthielt auch Zugangsdaten). Dashboard-Statustabelle auf 2 Konten korrigiert, die beiden offenen ttp1-Punkte geschlossen. Historische Berichte, Logs und Code-Kommentare bleiben als Beleg stehen.

- **2026-09-23** [CTNL-Optimierung] **Diagnose + Walk-Forward-Optimierung
  beider Beine abgeschlossen. Reine Auswertung, kein Bot geaendert.**
  Neue Skripte `research_ctnl_regime_diagnosis.py` und
  `research_ctnl_optimization.py`, Ergebnis in
  `projects/ctnl-kostenvalidierung.md` (Befunde 7-9, Entscheidungsvorlage
  E1-E4), Rohdaten `_data/ctnl_regime_diagnosis.json` +
  `_data/ctnl_optimization.json`.
  **Methodik:** Anker-Walk-Forward -- Parameter je Jahr auf allen Trades
  DAVOR gewaehlt, auf dem Jahr selbst ausgewertet. Gemessen wird die
  Auswahlprozedur, nicht der Rueckspiegel.
  **Das Regime-Bild musste korrigiert werden:** "funktioniert nur ab
  2024-08" haelt jahresweise nicht. `ctnl_reversal` ueber die volle
  Historie Ø R +0,114 / PF 1,13, **6 von 11 Jahren positiv**, und die guten
  liegen nicht nur am Ende (2016 +0,46, 2022 +0,38; 2023 ist mit -0,44 das
  schlechteste Jahr ueberhaupt). Schwacher, verrauschter Edge -- kein
  Regime-Schalter.
  **Vier Schrauben bringen nichts:** (a) TP -- Flaeche flach von 5R bis 10R,
  Auswahl verliert OOS (1 von 8 Jahren), 5R bleibt; (b) Signal-Parameter --
  `ohne_ema_reject` ist IS-Sieger in ALLEN acht Jahren und verliert
  out-of-sample (-60,6 ΣR, PF 1,06 vs. 1,19), exakt das OU-Muster;
  (c) SL -- ein auf 0,5R verengter Stop haette 49,5 % der Gewinner gekillt;
  (d) Ausfuehrung -- der 13-Min-Versatz ist Altlast (Ingest-Lane :10 statt
  moeglicher :02, belegt: M5-Bar 19:25 lag um 19:31:52 im Lake) und real
  auf ~3-4 Min. kuerzbar, aber Lag 1 schlaegt Lag 0 im Backtest
  (+107,7 vs. +84,0 ΣR). Robustheitsargument, kein Renditeargument.
  **Eine Schraube bringt etwas:** der **Regime-Filter** (Effizienz-Quantil
  q50, feste Schwelle statt mitlaufendem Quantil). Walk-Forward waehlt in
  8/8 Jahren dieselbe Schwelle, OOS +170,8 vs. +143,4 ΣR. Monte Carlo
  (0,15 %/Trade): **Median MaxDD -15,6 % -> -8,4 %, Median Return +18,8 %
  -> +32,2 %, Sharpe 0,25 -> 0,56** -- beide Achsen besser. Haken: verliert
  2022/2024/2025, gewinnt 2019-2021/2023.
  **`ctnl_continuation` ist ueber die Historie nicht zu retten:** PF 0,94,
  3 von 11 Jahren positiv, jede Variante negativ, Monte Carlo bei 0,50 %
  Median Return **-16,4 %**, Sharpe -0,20. Existenz- statt Parameterfrage.
  **Risiko-Nebenbefund:** die dokumentierte FK-Kalibrierung (Median MaxDD
  -3,5 %, P(>6 %) 7,8 %) stammt aus EINEM OOS-Jahr; ueber zehn Jahre liegt
  allein das Reversal-Bein bei -15,6 % Median und P(>6 %) = 99,9 %. Nicht
  direkt vergleichbar (anderer Zeitraum, anderes Portfolio), aber die
  Kalibrierung ruht damit auf einem Jahr.
  **Zwei eigene Korrekturen:** meine MFE-Hypothese aus der Diagnose (ein
  niedrigeres Ziel sammle die zwischen 3R und 5R zurueckfallende Haelfte
  ein) ist vom Walk-Forward widerlegt -- sie uebersah, dass ein niedrigeres
  Ziel auch die echten 5R-Laeufer kappt. Und die MFE-Zensur verbietet nur
  die DIAGNOSTISCHE Aussage ueber hoehere Ziele, nicht die Simulation.

- **2026-09-23** [OU-Modell Research] **Signalseite auf Basis der Logik D
  durchgetestet -- ein Hebel gefunden, vier Einstellungen bestaetigt.**
  Nutzerauftrag. Neu: `scripts/research_ou_signal_side.py`, Ergebnisse
  `signal_side_20260923.json`, `signal_k_plateau_20260923.json`,
  `signal_k_montecarlo_20260923.json`.
  **Bestaetigt (nicht anfassen):** `BB_LOOKBACK` 20 ist IS-Sieger, der
  Regimefilter Benchmark > EMA200 ist IS- UND OOS-Sieger (aus: OOS +0,002 statt
  +0,008), `half_life` 5-200 ist kein Hebel, sp500+nasdaq100 zusammen schlaegt
  jedes Universum allein, und der TTP-Handelbarkeitsfilter kostet nichts.
  **Verdacht widerlegt:** `THETA_MIN = 0,03` filtert tatsaechlich nichts (kein
  Titel unter theta 0,036) und `p_value < 0,2` waehlt aus einer Verteilung ohne
  jede Signifikanz (0,117-0,297) -- der Filter ist aber trotzdem der wirksamste
  im System: auf 0,25 gelockert kippt IS von +0,004 auf **-0,023** und OOS von
  +0,008 auf -0,007. Bei 0,15 bleiben 0 Titel uebrig, die Schwelle sitzt also am
  Rand des Moeglichen.
  **Der Hebel: `BB_K`.** Heute 2,0 (Einstieg 2 Sigma unter dem Mittel). Jeder
  getestete Wert darueber schlaegt 2,0 out-of-sample, auf beiden Brokern, und
  hebt die positiven OOS-Jahre von 2 auf 3 (bei k=3,0 auf 4). Monte-Carlo in
  echten Live-Risikogroessen: negative Pfade **30 % -> 18 % (k 2,25) -> 9 %
  (k 2,5)**, Ertrag +0,58 % -> +0,83 % -> +1,31 % (FK), Drawdown faellt
  gleichzeitig. Mechanismus: der Ausstieg liegt am Mittel, ein tieferer
  Einstieg gibt also mehr Weg bei gleichen bps-Kosten.
  **Empfohlen wird 2,25, NICHT der IS-Sieger 2,5** -- dessen IS-Nachbarn kippen
  im Vorzeichen (2,25 -0,003 · 2,40 +0,010 · 2,50 +0,016 · 2,60 -0,011), das
  ist eine Rauschspitze. 2,25 behaelt mehr Trades und liegt im stabilen
  Bereich. Nichts umgesetzt.

- **2026-09-23** [DASHBOARD-Durchsicht] **Fuenf offene Punkte nachgeprueft und
  geschlossen, fuenf mit aktuellen Zahlen nachgezogen** (Nutzerauftrag "zieh die
  geklaerten Punkte nach"). Jeder Punkt gegen echte Daten geprueft, nichts nur
  abgehakt.
  **Geschlossen:** (1) *Git-Sync*: `origin/main` hat am 21.09. 82, am 22.09. 82
  und am 23.09. 29 Commits bekommen, Rueckstand 0 -- die Stash-Logik vom 09-19
  traegt im Echtbetrieb. (2) *Funded/OU-Signaldatum-Drift*: genau die
  erwarteten 5 "ABGLEICH"-Meldungen am 17.09. 15:43:21, seitdem 6 weitere
  (EXPE, MDLZ, OXY, UPS, AMGN, CF) -- Mechanik laeuft. (3) *ttp1-Log-Stille seit
  09-19*: erwartete Folge, das Konto wurde am 09-19 auf Nutzerauftrag
  VOLLSTAENDIG aus `ACCOUNTS` entfernt (`state_id="ttp1"` kommt in der config
  nicht mehr vor) -- die Bridge laeuft es schlicht nicht mehr an, nichts klemmt.
  (4) *Zeitzonen-Fix beobachten*: seit `tzutil` am 17.09. 10:33 steht die
  Abweichung in JEDEM Kernel-General-Id-1-Event auf -120 (Berlin), kein Flip
  mehr; einziges Event seitdem ist eine normale Hardware-Uhr-Resynchronisation
  am Sa 20.09. 02:21 nach ~9,4 h Schlaf (Wochenende, ohne Handelswirkung).
  (5) *Cloud-Bridge-Monitor-Alarme 09-16/17/18*: im Punkt selbst bereits als
  geklaert dokumentiert.
  **Nachgezogen:** (a) *Verwaiste CTNL-Positionen*: ttp 32 -> **4**, FK 11 ->
  **0**, IQ 0 -- FK und IQ nehmen wieder Entries an, nur ttp liegt mit 4 noch
  ueber der Grenze 3. (b) *Order-Flut-Fix*: am 22.09. live bestaetigt, Korb
  sauber abgebaut (8 -> 6 -> 4 -> 3). (c) *EK/OU-Max-Holding*: nicht mehr 4,
  sondern **9 von 19** Positionen ueber dem 10-Tage-Limit (DAL 33, ADI/DHI/GRMN
  20, AMGN/EXPE 12, LEN/COF/GIS 11); AXP am 22.09. ausgestoppt. (d) *FK
  SP500 "Invalid stops"*: seit dem Fix kein SP500-Signal mehr aufgetreten
  (21./22.09. beide `filtered_out`), Gegenbeweis steht also noch aus.
  (e) *Kurztakt-Task-Ausfaelle*: 1.275 Fast-Laeufe seit 09-17, keine Luecke
  ausser Wochenende und 65 Min am Fix-Tag selbst.
  DASHBOARD.md 552 -> 525 Zeilen.

- **2026-09-23** [Second Brain / Reports] **Education-Journal-Zwischeneintrag
  KW39 von Hand angelegt** (`reports/weekly/KW39_2026_education.md`,
  Nutzerwunsch) -- Abschnitte 3+4 mit den Erkenntnissen aus der
  Paper-Sichtung vom 22.09.; der Sonntagslauf ersetzt die Datei, der Inhalt
  bleibt erhalten, da Memory + committete PARA-Notizen als Quellen gesetzt
  sind. **Dabei zwei Eintraege vom 22.09. wiederhergestellt**, die eine
  parallele Session mit Commit `1fc8645` ueberschrieben hatte: die
  DASHBOARD-Rueckfrage zum Paper-Screening und der Abschnitt "Externe
  Paper-Einordnung 2026-09-22" in `projects/ny-open-orb-sp500.md`. Bekanntes
  Muster (Memory `parallele_sessions_ueberschreiben_knowledge`), diesmal erst
  beim ZWEITEN grep-Check gefunden -- einmal pruefen reicht nicht, wenn
  zwischen Schreiben und Weiterarbeiten Stunden liegen. Nebenbei
  festgehalten: **fuer KW38 existiert kein Report**, obwohl
  `scripts/reports/mt5_2026-W38.json` vorliegt -- nicht untersucht.

- **2026-09-23** [SL/TP-Pruefung aller vier Live-Konten] **Alle 37 offenen
  Positionen haben einen SL -- keine Ausnahme.** Nutzerauftrag nach dem
  manuellen CTNL-Aufraeumen. Read-only ueber `positions_get()`/`orders_get()`
  (Skript im Scratchpad, nichts ins Repo gelegt). Keine offenen Pending-Orders
  zum Pruefzeitpunkt. Verteilung: EK 21, TTP 14, IQ 0, FK 2.
  **TP: 12 ohne -- davon 10 by design.** Funded- und FK-Bridge setzen bei
  Markt-Entries GRUNDSAETZLICH keinen Broker-TP (`target=None`, dokumentierte
  Design-Entscheidung 2026-08-29: Exit signalgetrieben beim naechsten Scan,
  Broker-SL als harte Grenze); nur ORB-Pending-Orders bekommen seit 2026-09-16
  einen Broker-TP. EK dagegen setzt TP aus dem Signal.
  **Zwei echte Abweichungen gefunden:**
  (a) **EK ADI + MDLZ ohne TP, obwohl die uebrigen 19 EK-Positionen einen
  haben.** Ursache vollstaendig geklaert: `ou_paper_backtest/scanner.py`
  schreibt je Universum eine Zeile, und das validierte 1:1,5-TP gilt laut
  Code-Kommentar NUR fuer S&P (nasdaq100/dax bleiben bewusst auf "kein TP").
  MDLZ und PEP stehen in BEIDEN Indizes -> zwei `tradeable=True`-Zeilen mit
  unterschiedlicher TP-Config in `scanner_signals.csv`. Welche gewinnt,
  entscheidet der 0-Tick frisch selektierter Symbole: die erste Zeile (S&P, mit
  TP) scheitert mit `entry_deviation_too_large, deviation=1.0`, die zweite
  (Nasdaq, ohne TP) geht Sekunden spaeter durch. Im EK-Log fuer ADI (02.09.
  15:35) und MDLZ (22.09. 15:44) genau so belegt. Der Code-Kommentar sichert
  ausdruecklich die eine Richtung ab (kein ungetestetes TP nach Nasdaq/DAX) --
  die Gegenrichtung (validiertes S&P-TP geht verloren) war nicht bedacht.
  Nichts geaendert, Entscheid liegt beim Nutzer (DASHBOARD.md).
  (b) **TTP-Position 18497256 (`FP ctnl_reversal`) HAT einen TP (4.260,48),
  obwohl die Funded-Bridge nie einen setzt** -- vermutlich beim manuellen
  Aufraeumen am 21.09. mitgesetzt.
  **Nebenbefund:** FKs zwei offene Positionen (XAUUSD.gbe seit 14.09.,
  EURUSD.gbe seit 16.09., +250 USD schwebend) haben leeren Order-Kommentar und
  stehen in KEINEM State -- keine Bridge verwaltet sie, nur der Broker-SL
  traegt. In DASHBOARD.md zur Entscheidung gelegt.

- **2026-09-23** [EK-Portfolio-Bridge / Risiko] **EK-Kalibrierung komplett nachgerechnet -- die 7,8 % vs. 33,9 % sind KEIN Fehler, sondern zwei Zeithorizonte.** 40 % Drawdown reissen: binnen 1 Jahr 3,6 %, binnen 2 Jahren 7,8-9,8 % (= die dokumentierte Zahl), ueber die volle 6-Jahres-Historie 39,3 %. Rechenkette der Studie vollstaendig reproduzierbar (combo/6 x 2,20 = Ist-Zustand; CAGR 227,8 % und MaxDD -38,1 % punktgenau). **Korrektur zum 22.09.:** ich hatte die Einheiten der Studie falsch gelesen und daraus einen Widerspruch gemacht -- es war keiner. **Nebenbefund:** `ou_modell` laeuft mit Faktor 4,40x statt 2,20x (doppeltes Gewicht), ausgerechnet das out-of-sample negative Bein. Nichts geaendert. Details: `projects/ek-risiko-kalibrierung-audit.md`.

- **2026-09-23** [Second Brain / Git-Sync] **Der verloren geglaubte Stand ist
  zurueck: 21 CHANGELOG-Eintraege und 4 DASHBOARD-Punkte aus den Stashes
  wiederhergestellt** -- meine (CTNL) UND die der beiden parallelen Sessions
  (ORB-Umbau, Papers-Screening, OU-Phase-6, Auswertung 21./22.09.).
  **Warum die Suche vorher ins Leere lief:** ein Stash ist ein
  Merge-Commit, und `git show stash@{N}` zeigt darauf einen KOMBINIERTEN
  Diff -- die betroffenen Zeilen erscheinen dort nicht als Zusatz. Erst
  `git diff stash@{N}^ stash@{N} -- <pfad>` macht sie sichtbar. Der Schluss
  "keiner der 72 Stashes enthaelt sie" beruhte auf diesem Artefakt, nicht auf
  der Datenlage.
  **Was tatsaechlich passiert ist:** `git_sync_push` legt bei jedem Lauf den
  offenen Stand in einen Stash und setzt bei einem Konflikt beim Zurueckholen
  per `reset --hard` zurueck. Weil das seit Tagen scheitert, hat **jede**
  Session auf einem CHANGELOG ohne die Eintraege der vorherigen
  weitergeschrieben -- die vier Stashes sind deshalb DISJUNKT (3.687 / 3.447 /
  3.467 / 3.500 Zeilen), keiner enthaelt alles. Zurueckgeholt wurde die
  Vereinigung, dedupliziert ueber Datum + Bereich + Titelanfang; bei zwei
  Fassungen desselben Eintrags gewann die spaetere (betraf einen: die
  ORB-SL/TP/BE-Neubewertung).
  **Ebenfalls zurueck:** `scripts/measure_broker_spreads.py` (die
  XAUUSD-Kommissionsumrechnung + FK als Messziel), `areas/realkosten-und-
  ausfuehrungs-probe.md` und `projects/gold-ctnl-edge-portfolio.md`. Diese
  drei waren in HEAD seit der Stash-Basis unveraendert, also konfliktfrei
  direkt zurueckholbar. Untracked angelegte Dateien
  (`projects/ctnl-kostenvalidierung.md`, `scripts/research_ctnl_execution_
  costs.py`, `_data/*.json`) waren nie betroffen -- `git stash` ohne `-u`
  fasst sie nicht an.
  **Anzuschauen:** der Eintrag vom 2026-09-21/22 ("Stop-Orders auf allen vier
  Konten + Exit-Variante C") war die Zusammenfassung, die eine Session als
  Ersatz fuer die verloren geglaubten Eintraege geschrieben hat. Die
  Originale stehen jetzt wieder darunter -- der Eintrag ist damit redundant.
  Ich habe ihn NICHT geloescht (fremder Eintrag), das ist deine Entscheidung.
  **Konsequenz, die bleibt:** `knowledge/` sofort nach jeder Aenderung
  committen. Die Stash-Halde von 72 Eintraegen ist der eigentliche Alarm --
  die Ursache in `git_sync_push.ps1` ist damit NICHT behoben, nur ihr
  Schaden rueckgaengig gemacht.

<!-- Die folgenden Eintraege wurden am 2026-09-23 aus git-stash@{8,45,70,71}
     wiederhergestellt (git_sync_push hatte sie beiseitegelegt). Siehe den
     Eintrag vom 2026-09-23 oben. -->

- **2026-09-22** [EK-Portfolio-Bridge / ORB] **ORB-Risiko auf EK neu
  kalibriert: 0,042 % -> 0,30 % je Instrument (7,2x).** Nutzerauftrag, nachdem
  aufgefallen war, dass ORB dort mit rund 1/70 von gold_asb lief.
  **Ursache der Luecke:** die MC-Kalibrierung vom 2026-09-10 enthielt ORB
  nicht -- `ek_v2_realistic_final.json` fuehrt es unter `removed_strategies`
  ("keine Evidenz, dass der Broker die noetigen Instrumente anbietet"). Das
  bezog sich auf das alte, verworfene `orb_strategy`-Paket und ist widerlegt.
  Stehen geblieben war FKs konservativer Default.
  **Nachgeholt** (`scripts/research_ek_orb_risk_calibration.py`): ORB frisch
  unter Variante C simuliert, zusammen mit den 6 Kernbeinen auf deren
  gemeinsamem Fenster (2018-12-02..2026-07-28, 2.796 Handelstage), Monte Carlo
  3.000 Pfade, Block-Bootstrap ueber Kalendermonate.
  **Befund: mehr ORB senkt die Reissgefahr**, weil das Bein weitgehend
  unkorreliert zu Gold/BTC/FX ist --
  0,042 %: CAGR 237 %, P(MaxDD>40 %) 33,9 % | 0,30 %: 333 %, 24,1 % |
  0,40 %: 375 %, 24,0 % | 0,75 %: 543 %, 34,3 %. Ab 0,75 % kippt es.
  **Gewaehlt 0,30 % statt des Minimums bei 0,40 %:** beide liegen im Rauschen
  gleichauf (5 Startwerte, Spanne +/-2 Punkte), 0,30 % sitzt mitten in der
  flachen Mulde statt an deren Rand.
  **Nebeneffekt geloest:** bei 3.174 EUR Equity waren 1,34 EUR Risiko so wenig,
  dass die Lot-Rundung 14 % Abweichung erzeugte (0,05 Lots, Teilung 0,02/0,03).
  Jetzt 9,52 EUR -> 0,41 Lots, Teilung 0,20/0,21, Abweichung 0,7 %.
  Deckel-Auslastung durch ORB: 0,9 % der Equity von 30 % erlaubt.
  Nur EK geaendert -- Funded und FK behalten ihre Werte (enge Prop-Caps).
  Ausserdem: kaputte Emoji-Escapes in EKs Telegram-Meldungen behoben (zeigten
  `🟡` statt des Symbols).

- **2026-09-22** [Alle Portfolio-Bridges / ORB] **🔍 Offener Befund: EKs
  Reissgefahr liegt nach meiner Rechnung bei 33,9 %, dokumentiert sind 7,8 %.**
  Kein Code geaendert, gehoert NICHT zur ORB-Kalibrierung. Meine Rekonstruktion
  trifft den historischen MaxDD der 09-10-Studie exakt (-38,1 %), nur ihre
  Zukunftsrechnung nicht. **Korrektur zu meiner ersten Vermutung:** es liegt
  NICHT an der Bootstrap-Methode -- Block-Bootstrap (22,7 %) und reine
  Tagespermutation (24,7 %) liefern bei mir dasselbe Bild. Woher die 7,8 %
  kommen, ist offen. Betrifft die grossen Beine (gold_asb/btc_ema_cross/
  gold_silver mit je 2,93 % je Trade), nicht ORB. Siehe DASHBOARD.

- **2026-09-22** [Alle Portfolio-Bridges / ORB] **Erster voller Tag unter
  Variante C.** Platzierung 15:45:09-15:45:10 auf allen vier Konten (EK
  15:45:08). NASDAQ loeste beidseitig-OCO aus, LONG gefuellt, Gegenseite
  storniert; beide Scheiben liefen in den Stop: TTP -62,49 $ (-1,13R),
  IQ -115,72 $ (-1,04R), FK -130,44 $ (-1,04R). US30 wurde nicht ausgeloest
  und bei Session-Ende storniert. SP500 gefiltert (Dienstag, Bias 1.0).
  Keine Fehlermeldung, OCO und Session-Ende sauber auf allen Bridges.

- **2026-09-22** [Research / Papers] **Drei geteilte Papers nach Standardprozess
  Phase 2+3 gesichtet und gescreent (Bondarenko/Muravyev SSRN 3596245,
  Kinoshita SSRN 7276738 + 7091018).** Nutzerauftrag. Neu:
  `resources/24h-renditestruktur-und-informationskette.md` (Destillat),
  `projects/eu-open-renditefenster.md` (neuer Edge-Kandidat), neuer Abschnitt
  "Externe Paper-Einordnung 2026-09-22" in `projects/ny-open-orb-sp500.md`.
  **Kein Code, kein Backtest, keine Aenderung an einem laufenden Bot.**
  Ergebnis fuer den ORB: kein neuer Entry-Filter, aber (a) die US-Cash-Session
  traegt im Mittel keine Risikopraemie (t=0,89) -- long-only ist dort also kein
  verstecktes Beta; (b) Mechanismus-Hypothese fuer den bisher unerklaerten
  EMA-neutral-Filter, mit eigener Gegenprobe; (c) zeitbasierter Ausstieg 15:45
  statt 16:00 als Gitter-Ablation vorgeschlagen (klein, Paper markiert den
  Befund selbst als schwach); (d) **Richtungsfilter aus Europa/Asien vor dem
  Bau verworfen** -- Kinoshitas Leg Europa->NY traegt +0,07 pt, die
  Null-Parameter-Regel dort 48,89 % (unter Zufall), waehrend alle anderen Legs
  +10,6 bis +15,0 pt tragen. Separat: das EU-Open-Fenster (05:30-09:30 Berlin,
  Sharpe 1,67, jedes Jahr positiv) als eigener Edge-Kandidat aufgenommen,
  kollidiert zeitlich nicht mit dem ORB -- Kostenprobe im Nachtfenster und
  Nachrechnen auf 2018-2026 stehen als erste Schritte aus.

- **2026-09-22** [OU-Modell Research] **Phase 6 fuer die empfohlene
  Konfiguration gerechnet -- besteht die Robustheitspruefung, aber nur knapp.**
  Nutzerauftrag. Neu: `scripts/research_ou_phase6.py`, Ergebnisse
  `phase6_ou_final_20260922.json` + `phase6_ou_montecarlo_live_20260922.json`.
  p6_2 Monte-Carlo (Block-Bootstrap der Trade-Sequenz, 5.000 Pfade): FK
  Ergebnis Median **+0,57 %** ueber OOS bei MaxDD Median -1,10 %, **P(DD > 7 %)
  = 0,00 %** (TTP-Grenze ungefaehrdet), 32 % der Pfade negativ; EK +1,88 % bei
  MaxDD -2,28 %. p6_3 Kostenpuffer: Breakeven bei 25,5 bps Einstieg (heute
  16,9) bzw. 2,5 bps Swap/Tag (heute 1,71) -- rund 50 % Puffer, aber nicht
  beides. p6_4 **Schwachstelle: 2023 (-0,033) und 2024 (-0,015) sind auch mit
  der neuen Konfiguration negativ**, der positive OOS-Schnitt stammt komplett
  aus 2025/2026. p6_7 Nominal nur 0,06x Konto (bei 3 Sigma 0,16x). p6_8 Stop =
  41x Round-Trip-Kosten, kein Trade unter 3x (der `cls_practical`-Fehler von
  09-09 existiert hier nicht).
  **Korrektur an der Vertiefung vom 19.09.:** dort stand "-25,3R, rund -25 %
  Konto". Falsche Bezugsgroesse -- live riskiert das Bein
  `capital_weight x LEG_RISK_PCT`, auf FK 1/6 x 0,01 = 0,167 %, auf EK
  1/8 x 0,0293 = 0,366 % je Trade. Die -25,3R sind rund -4,2 % der
  FK-Kontoequity. Notiz korrigiert.
  **Bezugsgroessen verifiziert:** die EK-Kapitalverduennung ist seit
  2026-09-10 scharf, und zwar INNERHALB `core/sizing.py`, nicht an den
  Aufrufstellen (die Memory dazu war bereits am 20.09. nachgezogen worden).
  **Fazit:** Bein von "verliert zuverlaessig" auf "kostet nichts mehr" gehoben,
  nicht auf "verdient Geld". Nichts umgesetzt, Entscheidung offen.

- **2026-09-22** [Auswertung 21./22.09., alle vier Live-Konten] **Erste zwei
  Plus-Tage in Folge -- Ausfuehrung sauber, Ergebnis haengt an einem Trade.**
  Read-only-Abzug ueber `scripts/reports/mt5_pull.py --from 2026-09-21 --to
  2026-09-23` (kein Eingriff).
  **Ergebnis** (realisiert, EUR->USD @1,144): 21.09. +309,08 USD, 22.09.
  +292,41 USD, zusammen +601,49 USD ueber 87 geschlossene Positionen
  (Trefferquote 48 %, PF 1,19). Mit dem 18.09. (+1.916 USD) sind das drei
  Handelstage in Folge im Plus -- erstmals im September; der Monat steht
  trotzdem bei -1.653 USD. Je Konto: EK/Tickmill -135,56 EUR (Equity
  3.173,66 inkl. +144,82 offen), TTP Konto 2 +1.175,63 USD, IQ -859,57 USD
  (beide Tage negativ), FK +440,51 USD.
  **Ausfuehrung: keine einzige Fehlermeldung** in beiden Bridge-Logs ueber
  die zwei Tage (kein Traceback, kein Reject, kein Exit-Fehler). Fills gegen
  das eigene SL/TP-Level: Median unter 0,4 bp auf allen vier Konten
  (Ausreisser EK XAUUSD -5,08 bp, IQ -2,86 bp). ORB beide Tage auf allen drei
  Konten um 15:45:06-15:45:10 Berlin platziert (~9 s nach Range-Ende), OCO
  korrekt storniert, Session-Ende korrekt (21.09. Position geschlossen,
  22.09. nicht ausgeloeste US30-Order storniert). Die Risiko-Deckel griffen
  sichtbar: TTPs 3,5-%-Offenes-Risiko-Limit blockierte am 21.09. den ganzen
  Vormittag neue Entries, die ctnl_reversal-Konkurrenzgrenze uebersprang
  Signale (Zaehler prueft gegen echte Broker-Positionen, nicht gegen den
  State -- `_count_open_leg_positions()` verifiziert per `positions_get`).
  **Einschraenkung 1 -- ein Trade traegt alles:** cls_practical EURUSD short
  am 22.09. 09:58->10:18 Berlin (TP) brachte +2.191,98 USD ueber alle vier
  Konten. Ohne diesen einen Trade stehen die zwei Tage bei -1.590 USD;
  Trefferquote am 22.09. nur 24 %.
  **Einschraenkung 2 -- TTPs 21.09. kam nicht vom Bot:** 18 ctnl_reversal-
  Positionen vom 17./18.09. wurden am 21.09. zwischen 14:30:44 und 14:33:05
  Berlin im Abstand von 3-8 s geschlossen (+884 USD). Kein Bridge-Log-Eintrag
  dazu, weder in der 15-Min- noch in der 5-Min-Lane; 17 der 18 State-Eintraege
  stehen bis heute auf `status="placed"`. Vom Nutzer am 2026-09-23 BESTAETIGT: manuelles
  Aufraeumen des fehlerhaften CTNL-Ueberbestands. Die +884 USD sind also kein
  Bot-Ergebnis.
  **Einschraenkung 3:** TTP Konto 2 (`trade_mode=0`, Demo) liefert das
  groesste Plus der zwei Tage. Echtgeld-Konto EK hatte am 22.09. mit
  -192,61 EUR (-6,1 % der Kontogroesse) seinen schlechtesten Tag im September.
  **Nebenbefunde:** (a) 37 (TTP) bzw. 51 (IQ) verwaiste ctnl_reversal-
  Eintraege stehen im State auf "placed" ohne offene Position -- fuer die
  Konkurrenzgrenze harmlos, als Historie aber unbrauchbar. (b) Der
  CTNL-Korb ist weiter ueber der Grenze: TTP am 22.09. frueh 8 offene
  ctnl_reversal bei Grenze 3, arbeitet sich runter (jetzt 4). (c) FK hat die
  ctnl_continuation vom 22.09. nicht gehandelt und ~300 USD Verlust vermieden
  -- nicht durch einen Filter, sondern durch Datenlatenz: FK sah das Signal
  erst um 07:28 Berlin (40 Min nach Funded um 06:48), da war es bereits
  ausgestoppt ("bereits offen UND geschlossen ... verpasst"). (d) FK loggt bei
  JEDEM Lauf "Kontostand 99.978,89 weicht von STARTING_EQUITY=100.000 ab --
  beeinflusst den Trailing-DD-Floor".

- **2026-09-21** [Alle Portfolio-Bridges / ORB] **Variante C UMGESETZT --
  Teilausstieg/Break-Even nach der Neubewertung umgestellt, Risiko je Konto
  unveraendert.** Nutzerfreigabe nach `projects/orb-exit-logik-neubewertung.md`.
  **Neue Exit-Config:** SP500 Ziel 6R ohne Teilausstieg | US30 Ziel 6R,
  Teilausstieg erst 3R | NASDAQ weiterhin ohne Ziel, Teilausstieg 3R statt 1,5R
  | **Break-Even ueberall aus** | Stop unveraendert 0,6 ATR.
  **Geaendert in 5 Dateien:** `challenge_portfolio/paper_bot.py` (Funded live),
  `fk_instant_funding/paper_bot.py` (FK live), `EK-Portfolio-Bridge/config.py`
  (EK live), `ek_portfolio/paper_bot.py` (Paper, pausiert -- stand ohnehin
  falsch: NASDAQ noch mit 4R-Ziel statt None) und
  `app_pages/ny_open_orb_portfolio.py` (Research-Dashboard, damit es zeigt was
  live laeuft). Zusaetzlich `EK-.../legs/ny_open_orb/signal_source.py`
  None-sicher gemacht -- die abgeloeste Funktion waere mit
  `partial_exit_r=None` hart abgestuerzt.
  **Sizing/Risikologik bewusst NICHT angefasst** (Nutzerauftrag), live
  gegengerechnet: TTP 55,07 $ (0,0556 %), IQ 111,18 $ (0,1111 %), FK 124,80 $
  (0,1246 %), EK 1,34 EUR (0,0417 %) je Instrument -- exakt die Werte von vor
  der Aenderung.
  **Zweitrundeneffekt geprueft:** ohne Teilausstieg/BE bleibt offenes Risiko
  laenger stehen. Worst Case (3 Beine gleichzeitig, kein Abbau) gegen den
  jeweiligen Deckel: TTP 0,167 % von 3,5 % (4,8 % Auslastung), IQ 0,333 % von
  3,0 % (11,1 %), FK 0,374 % von 5,0 % (7,5 %), EK 0,125 % von 30 % (0,4 %) --
  unkritisch, kein Bein wird dadurch ausgebremst.
  **Verifiziert je Bridge** (nichts platziert): Order-Form stimmt -- SP500
  erzeugt jetzt EINE Order mit 6R-TP, US30/NASDAQ zwei Scheiben mit
  Teilausstieg bei exakt 3,0R; `order_check` gegen Tickmill "Done".
  **WICHTIG -- greift erst ab dem naechsten Handelstag:** die heute um 15:45
  gelegten US30-Orders auf allen vier Konten tragen noch das ALTE Schema
  (Teil 2R / Ziel 4R / BE an). Sie laufen konsistent zu Ende, weil der
  Lebenszyklus die im State gespeicherten Werte nutzt, nicht die Config. Ein
  Austausch mitten in der Session waere unnoetiges Risiko gewesen.

- **2026-09-21** [Alle Portfolio-Bridges / ORB] **Erster gemeinsamer
  Handelstag mit Stop-Orders auf ALLEN vier Konten -- Platzierung 6-9 Sekunden
  nach Range-Ende.** Log 15:45:06 (FK), 15:45:09 (TTP + IQ), 15:45:05 (EK,
  Server 09:45:05 NY). Alle vier legten US30 (SP500 gefiltert: Montag,
  Bias 1.0; NASDAQ Ausbruch bereits vor Platzierung gelaufen).
  **Der IQ-Sizing-Fix wirkt live:** 111,36 $ statt der bisherigen 55 $.
  Stand 20:00: Orders ruhen noch, keine Ausloesung, keine Fehlermeldung.

- **2026-09-21** [NY-Open ORB / Research] **SL-, TP- und BE-Logik mit realen
  Kosten neu bewertet -- Grundlage fuer Variante C oben.** Nutzerauftrag
  2026-09-19, vollstaendig in `projects/orb-exit-logik-neubewertung.md`.
  *(Dieser und die zwei Eintraege darunter wurden am 2026-09-21 ZWEIMAL von
  einer parallel laufenden Session ueberschrieben und aus dem Chatverlauf
  wiederhergestellt -- siehe Memory `parallele-sessions-ueberschreiben-knowledge`.)*
  **Warum die alte Entscheidung neu zu pruefen war:** der Stage-6-Teilausstieg
  wurde ohne reale Kosten UND mit dem Marktorder-Einstieg validiert -- beide
  Annahmen sind seit dem 17.09. widerlegt.
  **Befunde** (396 Kombinationen je Instrument, 2019-2026, Stop-Order-Entry,
  gemessene Spreads, Einstiegs-Slippage 0,45 bps aus fuenf echten Fills):
  Teilausstiege kosten Edge, je frueher desto mehr (NASDAQ Ø R +0,037 bei 1,0R
  gegen +0,192 ohne); weite Ziele schlagen nahe (6R > 5R > 4R > 3R > 2R); der
  Stop ist die unwichtigste Schraube (0,4-0,6 ATR flach -- 0,6 bewusst behalten,
  weil bei 0,4 die gemessene Slippage >15 % des Risikos frisst).
  **Zwei Befunde, die vor einem Schnellschuss schuetzen:** (a) NUR den BE
  abzuschalten waere schlechter als heute (-10 % bei gleichem Drawdown); (b)
  US30 vertraegt "kein Ziel" nicht (OOS -0,101R), NASDAQ ist genau damit am besten.
  **Phase 6 (3.000 Pfade, Block-Bootstrap ueber Kalendermonate) drehte die
  Empfehlung:** der historische Einzelpfad liess Variante C schlechter aussehen
  (MaxDD -56,7R vs. -40,6R), ueber 3.000 Pfade ist ihr Tail-Drawdown praktisch
  identisch mit dem heutigen (-67,7 vs. -67,4R). Ergebnis +71 % (OOS Ø R +0,236
  statt +0,100, 8/8 Jahre positiv).
  Neue Skripte: `scripts/research_orb_exit_{grid,candidates,portfolio,montecarlo}.py`.

- **2026-09-21** [FK Instant Funding + EK-Portfolio-Bridge / ORB]
  **Stop-Order-Logik auf beide restlichen Bridges uebertragen -- ORB laeuft
  jetzt auf ALLEN Konten ueber ruhende Stop-Orders.** Nutzerauftrag 2026-09-19
  (beide gleichzeitig, kein Rueckfall auf Marktorders, jede Bridge behaelt ihre
  dokumentierte Risikoformel).
  **FK** (nahezu Portierung): neues `orb_pending.py`, Order-Bausteine in
  `executor.py` (`place_pending_stop`, `cancel_pending`, `pending_order_state`,
  `split_volume`, `closed_by_take_profit`, `round_price_to_tick`),
  `manage_orb_pending()` in `run_once.py`, praeziser 09:45-Pass in
  `run_once_fast.py`; ORB aus dem `_process_leg`-Marktorderpfad genommen. Die
  bisherige Teil-Rundung (nur SL) ging in eine vollstaendige Tick-Rundung auf --
  damit erledigt sich der offene "Invalid stops"-Fehler auf `SPX500.gbe`.
  **EK** (eigener Umbau): neue `legs/ny_open_orb/pending_source.py` +
  `pending_executor.py` mit eigener Tabelle `orb_pending_orders` (die alte
  `orb_positions` kann den Fall nicht abbilden: (Tag, Instrument) ist dort
  Primaerschluessel, jetzt braucht es bis zu 4 Zeilen je Tag). JEDE Order traegt
  `config.LEG_MAGIC[leg]`; Kommentar auf 16 Zeichen gekappt.
  `manage_open_positions()` ueberspringt Tickets des neuen Pfads ueber
  `is_pending_ticket()` -- sonst zweiter Teilausstieg auf dieselbe Position.
  **Korrektur zu meiner Aussage im Plan-Gespraech:** EKs Kapitalverduennung war
  NICHT offen -- sie sitzt seit 2026-09-10 in `core/sizing.py`.
  **Tests:** Zustandsmaschine mit simuliertem Broker FK 12/12, EK 16/16 (EK
  gegen eine TEMP-DB); `order_check` gegen beide Broker 6/6 "Done", 0 Orders im
  Buch; Trockenlauf mit echten Terminaldaten (17./18.09.) -- Sperren
  `breakout_passed`/`session_over` greifen. **Quercheck:** FKs Level fuer den
  17.09. (NASDAQ 29.430,90 / SP500 7.646,70) identisch mit Funded-IQ am selben
  Broker; EK (Tickmill) erwartungsgemaess daneben (29.428,56).

- **2026-09-21** [Funded-Portfolio-Bridge] **IQ handelte ORB mit dem halben
  vorgesehenen Risiko + TTP-Konto 504069845 entfernt.**
  (a) `manage_orb_pending()` rechnete mit dem globalen `pb.CAPITAL_WEIGHT`
  (1/6) statt `account.capital_weight` -- IQ (1/3) platzierte am 17./18.09. mit
  55,25 $ statt 111 $. Behoben, heute live bestaetigt (111,36 $).
  (b) Neue Log-Zeile "ORB ohne Order: <Instrument>=<Grund>".
  (c) TTP "Konto 1" (504069845, Echtgeld) auf Nutzerauftrag **vollstaendig aus
  der Bridge entfernt** -- Konto gebreacht, Broker hatte den Handel schon am
  18.09. gesperrt. **7 Positionen (DAL, UAL, NUE, AMGN, APD, IVZ, DD) bleiben
  offen und werden von KEINER Bridge mehr verwaltet** -- alle mit Broker-SL.

- **2026-09-21** [CTNL-Kostenvalidierung] **Alle vier Proben (p6_5-p6_8)
  durchgerechnet, beide Beine. Reine Auswertung, kein Bot geaendert.**
  Ergebnis + Entscheidungsvorlage A/B/C in
  `projects/ctnl-kostenvalidierung.md`, Rohdaten in `_data/`
  (`broker_spreads_xauusd.json`, `ctnl_execution_costs{,_ttp,_iq}.json`).
  **Probe 1: die 8 bps sind 4- bis 11-fach ZU HOCH, nicht zu niedrig**
  (gemessen TTP 1,95 / BeyondIQ 0,73 / Tickmill 1,07 bps). Umgekehrte
  Richtung zum CLS-Fall -- der Backtest ist bei CTNL konservativ.
  **Probe 2/3: bei echten Kosten sind BEIDE Beine profitabel**, am realen
  Betriebspunkt (Lag 1) reversal +0,266 R / PF 1,31 und continuation
  +0,194 R / PF 1,22 (TTP-Kosten). Die Lag-Kurve ist in keinem der vier
  Laeufe monoton -- der Versatz ist hier Rauschen, anders als bei CLS.
  **Probe 3, wichtigster Einzelfund: der 0,50R-R-Detektor ist tragend.**
  Ohne ihn kippt `ctnl_continuation` schon bei Lag 1 auf PF 0,99 und
  einzelne Trades erreichen Hebel bis 380x. Mit Gate liegt der gemessene
  Maximalhebel bei 1,94-2,00 -- die Identitaet 1/(1-0,5) = 2,0 bestaetigt
  sich exakt.
  **Probe 4: die engen Stops waren ein Artefakt der falschen Kostenzahl.**
  Bei 8 bps sahen 75,7 % der continuation-Trades nach zu engem Stop aus (Ø R
  eng -0,312 vs. weit +0,321, exakt das CLS-Muster); bei gemessenen Kosten
  sind es 5,8 % (TTP) bzw. 0,0 % (IQ). **Ein absoluter Stop-Boden ist NICHT
  faellig.**
  **Empfehlung (Variante B):** `spread_bps` broker-getrennt auf die
  gemessenen Werte setzen. Haken, der mitentschieden werden muss: die
  Phase-6-Referenz `CTNL_KILL_SWITCH_DD_THRESHOLD = -0,066` ist mit den
  alten Kosten gezogen und muesste neu gerechnet werden.
  **Bewusst NICHT quantifiziert:** ob EKs Stop-Neuverankerung Edge kostet.
  Die Replay-Methode rechnet nur die Einstiegsseite neu -- zulaessig, weil
  Stop/Ziel am Signal-Niveau haengen. Bei EK wandert das Stop-Niveau mit,
  also verschiebt sich auch die Ausstiegsseite; das braucht einen eigenen
  Engine-Lauf. Geschaetzt wird hier nichts.

- **2026-09-21** [CTNL-Kostenvalidierung / Research] **Proben p6_5-p6_8 fuer
  beide CTNL-Beine begonnen (Nutzerauftrag 09-19, Umfang bestaetigt 09-21).
  Reine Auswertung, kein Bot geaendert.** Neue Notiz
  `projects/ctnl-kostenvalidierung.md`, neues Skript
  `scripts/research_ctnl_execution_costs.py`.
  **Zwei Befunde stehen schon:**
  (1) **Der Ausfuehrungsversatz ist gross, aber getaktet** -- gemessen an 134
  echten Broker-Fills: Signal-Label -> Live-Entry Median 28 Min., Streuung
  min 28 / max 29. Eine Minute Streuung ueber 134 Fills heisst: das ist
  Scan-Taktung, kein Marktrauschen, also gezielt verkleinerbar. Gegen die
  Signalbar trifft der real gezahlte Preis am besten das Open der Bar T+30
  (1,28 Preispunkte Abweichung, gegen 3,44 bei T+15). Der fuer Probe 2
  relevante Versatz gegenueber dem Backtest betraegt aber nur ~13 Min., weil
  der Backtest selbst erst zum Open der Bar T+15 fuellt.
  (2) **Die drei Bridges sizen CTNL unterschiedlich.** Funded und FK nutzen
  das absolute Signal-SL-Niveau plus `MAX_CONSUMED_R_FOR_ENTRY = 0.50`
  (Hebel bei 2,0x gedeckelt). **EK verankert den Stop am Live-Kurs neu**
  (`legs/ctnl_edge/executor.py::_send_entry`: `stop_price = entry_price -
  direction * sl_distance`) und hat deshalb konsequenterweise gar kein
  Hebel-Gate -- eine Aufblaehung ist dort strukturell unmoeglich. Der Haken:
  genau diese Variante hat EK fuer das CLS-Bein selbst vermessen und am
  09-11 verworfen (PF 1,42 vs. 1,85, Ø R 0,25 vs. 0,42, auf jeder Kennzahl
  ausser dem Maximalhebel schlechter). **Fuer CTNL faehrt EK bis heute die
  fuer CLS unterlegene Variante.** Ob das fuer CTNL genauso gilt, ist NICHT
  gezeigt -- begruendeter Verdacht mit Gegenbeleg aus dem eigenen Repo,
  Quantifizierung steht aus.
  **Noch offen:** Probe 1 (XAUUSD-Kosten je Broker, Messung laeuft),
  Probe 2 (Edge-Verlust je Lag-Stufe), Probe 3 (Hebelverteilung unter 0,50R),
  Probe 4 (Stopdistanz gegen Kosten), Entscheidungsvorlage A/B/C.

- **2026-09-21** [scripts/measure_broker_spreads.py] **Zwei Luecken
  geschlossen, damit die CTNL-Kostenmessung ueberhaupt tragen kann.**
  (a) Die Kommissions-Umrechnung stand auf `usd_per_pip_per_lot = 10.0`,
  hartkodiert auf EURUSD -- fuer XAUUSD um Faktor 10 zu klein, die Kommission
  waere also 10x zu guenstig ausgewiesen worden. Ersetzt durch
  `info.trade_contract_size * pip` (100.000 x 0,0001 = 10,0 fuer EURUSD,
  100 x 0,01 = 1,0 fuer XAUUSD). **Regressionstest bestanden:** Lauf mit
  `--symbols EURUSD` liefert TTP $4,00/Lot = 0,40 Pips und IQ $5,00/Lot =
  0,50 Pips, identisch zu `resources/broker-kostenmodell-eurusd.md`.
  (b) **FK Instant Funding fehlte komplett als Messziel** -- faehrt beide
  CTNL-Beine mit echtem Geld und waere sonst ausgelassen worden. Ergaenzt,
  bewusst ueber Suffix-Aufloesung statt per Import: FKs `SYMBOL_MAP` steht in
  `run_once.py`, und dieses Modul zu importieren zoege `executor`/
  `orb_pending` in `sys.modules` -- Namen, die es in der Funded-Bridge ein
  zweites Mal mit anderem Inhalt gibt. Indizes sind von der
  Suffix-Aufloesung ausgenommen (SP500 -> "SPX500.gbe", kein reines Suffix).

- **2026-09-21** [Reporting / Soll-Ist] **Aufgeklaert, woher die
  `ou_modell`-Trades kommen, die im Soll "kein Signal" haben.** Reine
  Analyse, nichts geaendert. Zwei voneinander unabhaengige Ursachen:
  (a) **Fenstersemantik:** `build_soll()` filtert auf **Entry** im Fenster,
  `build_ist()` zaehlt nur **schliessende** Deals (`entry == 1`) im Fenster.
  Eine Position, die vorher eroeffnet und im Fenster geschlossen wird, kann
  im Soll gar nicht auftauchen. Bei OU (Haltedauer mehrere Tage) ist das der
  Normalfall: von den 5 EK-Closes der KW38 wurde **keiner** im Fenster
  eroeffnet, bei Funded 3 von 4 (nur APD 15.09.->17.09. lag ganz drin).
  (b) **EK misst das Bein ueberhaupt nicht:** `ek_portfolio/paper_bot.py`
  hat keine `_scan_ou_modell()`, und `_scan_all()` ueberspringt fehlende
  Scan-Funktionen **ohne Meldung** (`if fn is None: return None`). Auf EK
  heisst "kein Signal" also "nicht gemessen". Die Live-Bridge handelt das
  Bein aus eigenem `legs/`-Code, den der Repo-Paper-Bot nie gespiegelt hat
  (passt zum Fund vom 09-13, dass EK das OU-Bein von der abgeschalteten
  `OU-Modell-MT5-Bridge` uebernommen hat). Folge: die EK-Soll-Rendite ist die
  eines Portfolios **ohne** OU-Bein und mit dem Ist nicht vergleichbar --
  ausgerechnet beim groessten Verlustposten (KW37 -55,25, KW38 -73,41).
  **Nebenbefund (offen):** bei Funded existiert `_scan_ou_modell()`, der Lauf
  vom 09-19 lieferte aber 0 Trades im Fenster, ein Re-Scan am 09-21 mit
  identischem `end` liefert 3 (DD 14.09., IVZ 15.09., PEP 18.09.) -- genau
  die drei, die die Bridge laut `bridge_state_ttp.json` mit Ticket platziert
  hat. Ursache noch offen, in `DASHBOARD.md` als Aufgabe eingetragen.

- **2026-09-21** [Funded-Portfolio-Bridge + FKInstantFunding-MT5-Bridge]
  **Live-Deckel fuer gleichzeitig offene Positionen eines Beins eingebaut
  (Nutzerauftrag, behebt die CTNL-Order-Flut vom 09-17/18).** Uebernommen aus
  `EK-Portfolio-Bridge/legs/ctnl_edge/executor.py::check_and_execute_reversal()`
  -- der einzigen Bridge, die den Deckel bisher an der richtigen Stelle zog.
  Neu in beiden `run_once.py`: `LEG_MAX_CONCURRENT`
  (`ctnl_reversal`: 3 aus `gold_smc_htf_ltf/live_signal.py::REV_MAX_CONCURRENT`,
  `ctnl_continuation`: 1) + `_count_open_leg_positions()`, aufgerufen in
  `_process_leg()` als letztes Gate vor der Order.
  **Gegen den BROKER gezaehlt, nicht gegen den State** -- der State ist genau in
  dem Szenario unzuverlaessig, das das Gate abfangen soll (er haelt verwaiste
  "placed"-Eintraege zu laengst per SL geschlossenen Positionen). Der State
  liefert nur Ticket-Kandidaten, die Wahrheit kommt aus `positions_get()`;
  der Order-Kommentar-Abgleich ist nur Zusatz fuer Positionen mit verlorenem
  State-Eintrag (auf Kommentare allein ist kein Verlass, siehe
  `MT5 Comment-Length Order Reject`).
  **Bewusst OHNE "missed"-State-Eintrag und mit Sammelmeldung statt einer
  Zeile je Signal:** ein voller Positionskorb ist ein VORUEBERGEHENDER Zustand
  (gleiches Muster wie der Kill-Switch-Zweig). Ein "missed"-Eintrag wuerde das
  Signal endgueltig verwerfen, obwohl es nach dem naechsten Exit legitim
  handelbar waere -- derselbe Fehler wie beim 0-Tick-Fund vom 09-08.
  **Tests (Flut vom 09-17 mit gefaketem MT5/Executor nachgespielt):**
  (a) Funded: 32 Signale je M15-Bar -> 3 eroeffnet, 29 geblockt, Buch = 3;
  (b) FK: 15 Signale -> 3 eroeffnet, 12 geblockt; (c) nach einem Exit rueckt
  genau EINE Position nach (kein Dauer-Stopp); (d) 2 kuenstlich verwaiste
  State-Eintraege veraendern die Zaehlung nicht. Gegen die ECHTE Lage
  verifiziert: auf `ttp` zaehlt das Gate 32 (State sagt 44) und blockt, auf
  `iqmarkets` zaehlt es 0 (State sagt 40) und laesst 3 zu.
  Die Fast-Lanes erben das Gate automatisch (beide `run_once_fast.py` rufen
  `slow._process_leg()`); `ctnl_reversal` laeuft ohnehin nur auf der Slow-Lane.
  **Noch nicht im Echtbetrieb ausgeloest** -- erster Lauf der Woche war
  2026-09-21 00:13, bis dahin kein frisches CTNL-Signal.

- **2026-09-21** [Funded-Portfolio-Bridge + FKInstantFunding-MT5-Bridge]
  **Verwaiste ctnl_reversal-Positionen gegen den Broker abgeglichen (read-only,
  nichts geschlossen).** `ttp` (Demo): 32 von 44 State-Eintraegen real noch
  offen, netto -0,32 Lots, offener P/L +493,52, Equity 98.156,59.
  `iqmarkets` (Echtgeld): 0 von 40 real offen, Equity 100.625,54 -- alles per
  Broker-SL glattgestellt, Konto im Plus. `fk_instant_funding` (Echtgeld):
  11 von 12 real offen, netto -0,10 Lots, offener P/L +31,42, Equity
  100.081,72. **Folge des neuen Deckels:** solange diese Positionen offen
  sind, nimmt `ctnl_reversal` auf `ttp` und FK KEINE neuen Entries an. Das ist
  gewollt (die Positionen sind real und zaehlen zum Risiko), aber es heisst,
  dass das Bein dort bis zum Abbau praktisch stillsteht.

- **2026-09-19** [Reporting / Soll-Ist] **Soll/Ist KW38 (14.-18.09.) gerechnet**
  (`scripts/reports/soll_ist.py --week 2026-W38`, Ergebnis
  `soll_ist_2026-W38.json` + MT5-Abzug `mt5_2026-W38.json`). Reine
  Auswertung, nichts geaendert. **Soll ist auf allen drei Bridges quasi
  identisch positiv** (EK +0,09 %, Funded +0,10 %, FK +0,36 % bei je 15
  Trades), das Ist faellt auseinander:
  (a) **EK -74,48 (-2,37 %)** -- die 5 platzierten Soll-Trades stehen bei
  **+6,30 R**, der Verlust kommt praktisch vollstaendig aus `ou_modell`
  (5 Deals, -73,41), das im Soll gar kein Signal hat. Zweite Woche in Folge
  dasselbe Muster (KW37: -55,25).
  (b) **Funded +513,07 (+0,26 %) -- Zahl NICHT belastbar:** `ttp1` ist seit
  dem Breach am 09-18 aus `config.py` entfernt, `mt5_pull.py` entdeckt die
  Konten ueber genau diese Liste. Der Abzug enthaelt also nur ttp + iqmarkets;
  ausgerechnet das Konto, auf dem die Woche entschieden wurde, fehlt.
  (c) **FK 0 Deals ist ein Messfehler, kein Ergebnis:** `initialize failed:
  (-10005, 'IPC timeout')`, Konto nicht erreichbar. Der Bridge-State weist
  fuer dieselbe Woche **7 Signale mit Ticket** aus -- FK haette damit zum
  ersten Mal seit Livegang (08-09) gehandelt. **Unverifiziert**, muss gegen
  das Konto nachgezogen werden, sobald das Terminal wieder antwortet.
  (d) **`ctnl_reversal`: Soll 9 Trades / -7,16 R, Ist auf Funded 60 Deals /
  +259,85.** Dieselbe Order-Flut wie im Eintrag oben, hier von der anderen
  Seite sichtbar; dass sie im Plus endete, ist Zufall, nicht Design. EK hat
  von denselben 9 Soll-Trades **0** platziert -- sein
  `_own_positions()`-Gate hat gehalten.

- **2026-09-19** [CTNL Reversal / alle Bridges] **Ursache der Order-Flut
  gefunden: `_cap_concurrent_reversals()` ist ein Simulations-Filter, kein
  Live-Gate -- Funded-Portfolio-Bridge und FKInstantFunding-MT5-Bridge haben
  gar keinen Live-Deckel.** Reine Analyse, nichts geaendert.
  **Mechanik (reproduziert):** `_scan_ctnl()` simuliert bei JEDEM Lauf neu
  ueber das rollierende Lookback-Fenster. Ein noch offener Trade bekommt
  `exit_reason="data_end"`, und `run_once.py::_process_leg()` liest genau das
  als "Signal ist offen" -> echter Entry. Beim naechsten Scan wandert
  `data_end` mit; die Exits der aelteren Trades verlaengern sich, wodurch die
  Greedy-Kappung den gerade erst eroeffneten Trade RUECKWIRKEND verwirft --
  die Zeile verschwindet komplett aus dem Scan-Output. Direkt gemessen:
  Scan 13:00 liefert Entry 13:00 als offen, Scan 14:00 kennt diese Zeile
  nicht mehr, dafuer Entry 14:00. Die Bridge macht daraus "Schluessel nicht
  mehr da -> nichts zu tun": die reale Position ist verwaist (kein
  max_hold, kein Target, kein Bridge-Exit -- nur noch der Broker-SL), und im
  selben Lauf wird die naechste eroeffnet. Ergebnis: **eine neue Position pro
  M15-Bar, unbegrenzt.**
  **Warum erst jetzt:** zwischen 2026-08-28 und 2026-09-17 gab es gar kein
  Reversal-Signal. Der Fehler lag ~3 Wochen latent und schlug erst beim
  ersten dichten Signal-Cluster durch (Gold-Rally 4305 -> 4415 am 09-17).
  **Zahlen:** 0 CTNL-Entries bis 09-16, dann 100 am 09-17 und 34 am 09-18
  (Funded-Bridge, 3 Konten); FK Instant Funding 11 + 4 (laeuft stuendlich
  statt alle 15 Min.). Auf ttp1 zum Breach-Zeitpunkt (09-18 09:49) **38
  offene ctnl_reversal-Positionen mit $2.850 kumuliertem Sollrisiko gegen
  eine Design-Obergrenze von 3 x $75 = $225 -- Faktor 12,7.** Alles
  XAUUSD, alles dieselbe Richtung, also voll korreliert. Die Bridge hat von
  42 Entries nur 4 Exits ueberhaupt gesehen (-255 $ gebucht), die uebrigen
  38 liefen unbemerkt in den Broker-SL.
  **EK-Portfolio-Bridge war als einzige geschuetzt:**
  `legs/ctnl_edge/executor.py::check_and_execute_reversal()` zaehlt mit
  `_own_positions()` die ECHTEN offenen Broker-Positionen und lehnt ab
  (`max_concurrent_reached, count: 3`) -- genau das Gate, das den beiden
  anderen Bridges fehlt.
  **Aktueller Stand (Sa, 19.09., Maerkte zu, kein Lauf seit 09-19 00:01):**
  ttp1 ist heute bereits aus `config.py` entfernt. Verwaiste
  ctnl_reversal-Eintraege im State: iqmarkets (Echtgeld) 40 / $6.000
  Sollrisiko, ttp (Demo) 44 / $3.300, FK (Echtgeld) 12 / $454. Alle drei
  Tasks stehen auf "Ready" -- **ohne Eingriff wiederholt sich das am
  Montag.**

- **2026-09-19** [OU-Modell Research] **SL/TP-Logik und Broker-Kosten
  EK vs. FK -- finale Konfiguration steht als Empfehlung, nichts umgesetzt.**
  Neu: `scripts/research_ou_exit_logic.py` (Ausstiegslogiken),
  `scripts/research_ou_broker_costs.py` (Kosten je Broker, rein lesend aus
  beiden MT5-Terminals). Ergebnisse `exit_logic_20260919.json`,
  `exit_logic_engine_20260919.json`, `exit_logic_sigma_plateau_20260919.json`,
  `broker_costs_ou_20260919.json`.
  **Befunde:** (a) der TP 1,5R feuert in **4,8 %** der Trades -- er liegt bei
  4,5 Sigma ueber dem Einstieg, die Mean Reversion bei 2 Sigma; "MA-Ausstieg
  ODER TP" ist rechnerisch identisch mit "nur MA-Ausstieg"; (b) der
  3-Sigma-Stop ist der groesste Einzelfehler: auf 8 Sigma verbreitert steigt
  OOS von -0,015 auf +0,008R UND der schlechteste Trade faellt von -2,54R auf
  -0,90R (die Position ist bei gleichem Dollar-Risiko nur noch 37,5 % so
  gross); ueber 8/10/12/16 Sigma ein Plateau, kein Rand-Artefakt; (c)
  Trailing-Stop und TP-Sweep bringen nichts; (d) **EK/Tickmill ist beim Spread
  halb so teuer wie FK/TTP (2,63 vs. 5,67 bps Median), beim Swap exakt gleich
  (-6,23 vs. -6,24 % p.a.)** -- dieselbe Strategie verliert auf EK halb so viel
  (-0,028 statt -0,052R), ohne Vorzeichenwechsel; davon 0,011R Broker-Kosten,
  0,013R Ausfuehrungsfamilie.
  **Finale Empfehlung:** Stop 8 Sigma, Breakeven aus, kein TP, Ausstieg am
  MA20, max_hold 10 -> FK +0,008R (PF 1,08), EK +0,013R (PF 1,13); mit
  Folgetags-Schluss-Einstieg +0,015 bzw. +0,020R. Braucht eine Code-Aenderung
  (der MA-Ausstieg fehlt in `simulate_bracket_portfolio`), ist also keine reine
  Config-Aenderung. Phase 6 fehlt weiterhin. Details + Option D im Dashboard
  und in `projects/ou-modell-kostenvalidierung.md`.
  **Nebenfund am Messweg:** `measure_broker_spreads._connect` loggt sich per
  separatem `mt5.login()` ein -- auf einem frisch gestarteten Tickmill-Terminal
  scheitert das mit "Authorization failed"; die Bridges uebergeben die
  Zugangsdaten direkt an `initialize()`. In `research_ou_broker_costs.py` als
  `_connect_direct()` nachgebaut (ein Versuch, kein Retry: wiederholte
  Fehlanmeldungen sperren Live-Konten).

- **2026-09-19** [OU-Modell Research] **Kosten-/Zeitraum-Optimierung
  durchgerechnet (Bloecke 0-3) -- reine Auswertung, kein Bot geaendert.**
  `scripts/research_ou_execution_optimization.py` (am 17.09. gebaut, nie
  gelaufen) vollstaendig ausgefuehrt; Ergebnis
  `ou_paper_backtest/results/execution_optimization_20260917.json`,
  Zusatzlaeufe `ou_be_isolation_20260919.json` + `ou_stopfloor_20260919.json`.
  Regressionstest bestanden (A +0,0969R / C$ -0,0103R wie am 16.09.).
  **Befunde:** (a) Spread-Kurve bestaetigt (27,9 bps um 09:35 NY, 8,3 zum
  Schluss) -- aber nur 0,017R auf die Median-Stopdistanz; (b) keine von 20
  Ausfuehrungsvarianten ist out-of-sample positiv, die 3,5-%-Abweichungsgrenze
  ist wirkungslos; (c) Einstiegsstunde ist kein Hebel (alle Stunden IS
  negativ); (d) **Zeitraumtest: der Edge lebt** (+0,075R OOS reibungsfrei),
  er wird von Ausfuehrung (0,058R) + Kosten (0,064R) aufgefressen; (e) BE-Stop
  aus ist IS-Sieger aller 54 Parameter-Kombinationen und dreht das
  OOS-Vorzeichen, `max_hold` kuerzen hilft NICHT. Zusammen mit dem spaeteren
  Einstieg (+ Mindest-Stopdistanz 3 % gegen versteckten Hebel) kommt das Bein
  von -0,051R auf +0,020R OOS (PF 1,07, KI umschliesst die Null).
  Entscheidungsvorlage A/B/C in `projects/ou-modell-kostenvalidierung.md`,
  Dashboard nachgefuehrt. **Code-Aenderung nur am Research-Skript:** die
  Block-3-Ausfuehrungswahl kannte `close_d1` nicht und waere sonst auf die
  schlechteste Ausfuehrung zurueckgefallen.

- **2026-09-19** [Git-Sync / 11 Auto-Tasks + Bridge-Watchdog] **Ursache des
  Push-Staus behoben** (Nutzerauftrag). `scripts/lib/git_sync_push.ps1` und
  `Bridge-Watchdog/watchdog.py` (gleiche Logik, eigene Implementierung)
  stashen offene Aenderungen jetzt VOR dem Merge und holen sie nach dem Push
  zurueck; die Warnung unterscheidet echten Inhaltskonflikt, "nicht
  committete Aenderungen im Weg" und unklare Ursache.
  **Bewusst NICHT `-c merge.autoStash=true`:** im Wegwerf-Repo getestet -- das
  holt die Aenderungen zurueck, bevor feststeht, ob es konfliktfrei geht, und
  hinterlaesst bei Ueberschneidung Konfliktmarker in der Datei einer laufenden
  Session PLUS einen liegengebliebenen Stash. Stattdessen: erst mergen+pushen
  (GitHub in jedem Fall aktuell), dann zurueckholen; kollidiert das, raeumt
  `reset --hard HEAD` den Konflikt aus Index UND Working Tree (ein
  `checkout -- .` reicht nicht -- die Konflikt-Stufen stehen im Index) und die
  Arbeit bleibt vollstaendig im Stash.
  **Vier Faelle getestet, PowerShell und Python:** (A) offene Aenderung auf
  derselben Zeile wie der Remote -> Push geht durch, keine Marker, Stash
  behalten, Warnung; (B) offene Aenderung auf anderer Zeile -> Push geht
  durch, Aenderung sauber zurueck, kein Stash; (C) echter Konflikt zwischen
  zwei Commits -> Push uebersprungen, korrekt benannt, offene Aenderung
  zurueck; (D) sauberer Working Tree -> unveraendert wie bisher.
  Erster echter Lauf am Montag (Wochenendpause).
  **Nebenbei:** Commit `ee55b0a` enthaelt zusaetzlich den ttp1-Handelssperre-
  Eintrag der parallelen Session (lag ungespeichert im Working Tree).

- **2026-09-19** [Funded-Portfolio-Bridge] **🔴 Echtgeld-Konto ttp1 (TTP Konto 1,
  Login 504069845) ist seit 2026-09-18 09:58 vom Broker fuer den Handel
  gesperrt** -- `account_info().trade_allowed=False`, jeder Entry-Versuch
  seitdem mit `retcode=10026 "AutoTrading disabled by server"` abgelehnt
  (9 Versuche: 7x ctnl_reversal, 1x orb_nasdaq, 1x ou_modell/PEP; letzter
  16:13). **Kein Bot-Fehler und keine eigene Regelverletzung:** Kill-Switch
  inaktiv, Equity 94.711,78 (−2,0 % seit Kontostart 96.664,38, Tagesverlust
  09-18 −0,99 %), Peak-DD −2,2 %. Das TTP-DEMO-Konto (`ttp`) haengt am
  **selben** Server `TTPMarkets-Server` und darf normal handeln -- also
  kontospezifisch, keine Wochenend-/Serversache. 7 Positionen offen (DAL, UAL,
  NUE, AMGN, APD, IVZ, DD), **alle mit SL** -- falls auch das Schliessen
  blockiert ist, greift weiterhin der Broker-SL. Nichts geaendert, Ursache nur
  beim Anbieter klaerbar. Nebenbefund: die Bridge meldet so etwas nur als
  einzelne Entry-Fehler, es gibt keine Sammelwarnung "Konto darf nicht mehr
  handeln".

- **2026-09-19** [Funded-Portfolio-Bridge / ORB Stop-Orders] **Erste zwei
  Handelstage ausgewertet (09-17, 09-18, Demo `ttp` + `iqmarkets`) -- Mechanik
  laeuft vollstaendig wie gebaut, keine einzige Fehlermeldung im ORB-Pfad.**
  **Platzierung:** beide Tage 15:45:13 bzw. 15:45:16 Berlin, also **13-16 s nach
  Range-Ende**, alle Gruppen in einem Durchgang (Log: "Range-Ende in 107s").
  **Einstiegsabweichung gegen das Level:** 09-17 long +0,11 bis +0,24 Punkte
  (0,07-0,17 bps), 09-18 short −2,60 bis −3,05 Punkte (0,88-1,03 bps,
  Durchbruch-Gap). Mittel ~0,44 bps gegen 0,30 bps Backtest-Annahme.
  **OCO:** beide Tage sauber -- 09-17 Long ausgeloest/Short storniert, 09-18
  umgekehrt, auf beiden Konten.
  **Teilausstieg + BE (09-18 NASDAQ short):** P-Scheibe am Broker-TP
  (+36,15 TTP / +38,64 IQ), SL der R-Scheibe auf Break-even, R spaeter am
  BE-Stop (−1,34 / −0,14). Genau der Backtest-Ablauf; einzige Abweichung: BE
  liegt auf dem ECHTEN Fill, nicht auf dem Level (3 Punkte Unterschied).
  **Session-Ende:** nicht ausgeloeste US30-Orders beide Tage storniert.
  **Ergebnis (klein, 3 bzw. 2 gefuellte Setups -- Rauschen, kein Beleg):**
  TTP −81,69 $ (−1,50R), IQ −16,62 $ (−0,32R).
  **Feed-Divergenz belegt:** 09-17 SP500 -- TTP-Level 7.644,96 wurde gefuellt
  und ausgestoppt (−60,17), IQ-Level 7.646,70 (+1,74 = 2,3 bps, passt zum
  gemessenen TTP-Versatz −1,97 bps) wurde nie erreicht; IQ sparte den Verlust.
  **Markt vs. Stop-Order (09-17 NASDAQ, gleiches Signal):** ttp1 stieg 5 Min
  spaeter, aber 9,7 Punkte guenstiger ein (29.417,93 vs 29.427,60), gleicher
  SL-Bereich -> kleinere Distanz, groessere Position, am Ende derselbe Verlust
  (−56,84 vs −56,33). Am 09-18 haette ttp1 den Gewinner gehandelt, wurde aber
  vom Broker-Block (Eintrag darueber) gestoppt.
  **Beobachtungsluecke:** nicht platzierte Instrumente (gefiltert, Ausbruch
  schon passiert, Session vorbei) tauchen im Log NICHT auf -- am 09-17 fehlte
  bei IQ die US30-Gruppe ohne erkennbaren Grund. Nicht behoben.

- **2026-09-19** [Git-Sync] **GitHub-Rueckstand aufgeloest: 242 Commits
  gepusht** (Nutzerauftrag). Stand vorher: lokal 240 vor / 4 hinter
  `origin/main`, seit 09-16 09:08 kein Push mehr.
  **Die stuendliche Meldung "vermutlich ein echter Konflikt" war eine
  Fehldiagnose.** `git merge` brach mit *"Your local changes to the following
  files would be overwritten by merge: knowledge/CHANGELOG.md,
  knowledge/DASHBOARD.md"* ab -- also wegen NICHT committeter Aenderungen, nicht
  wegen widerspruechlicher Inhalte. `scripts/lib/git_sync_push.ps1` setzt laut
  eigenem Kommentar einen sauberen Working Tree voraus; die Auto-Tasks
  committen aber nur ihre eigenen Dateien, Session-Aenderungen an `knowledge/`
  bleiben liegen. Sobald der Remote dieselbe Datei anfasst (hier: drei
  Bridge-Monitor-Eintraege der Cloud-Session), blockiert das jeden Push --
  **unveraendert, der Fall kann jederzeit wiederkommen** (Vorschlag unten im
  DASHBOARD).
  **Ablauf:** lokale Aenderungen committet (`7c61c1e`), `origin/main` gemergt
  (`27b9b35`), zwei Textkonflikte von Hand aufgeloest, gepusht.
  **Inhaltlich:** der Cloud-Fix in `cls_practical/rates.py` (Dedup nach der
  `.date`-Trunkierung) bleibt -- er ergaenzt den Lake-Fix vom 09-16, beide
  greifen an verschiedenen Stellen derselben Kette. Die drei
  Bridge-Monitor-Alarme sind ueberholt: der Watchdog lief lokal die ganze Zeit
  normal (letzter Snapshot 09-18 23:31), eingefroren war nur GitHub. Ein beim
  Aufraeumen stehengebliebenes Fragment (Pip-Boden-Tabelle) entfernt.

- **2026-09-17** [FK Instant Funding Paper-Bot] **Scan-Fehler als
  Sammelmeldung** (Nutzerauftrag). `scan_once()` meldet einen Scan-Fehler
  (z. B. haengendes dukascopy) je Bein nur noch beim ERSTEN Auftreten pro Tag
  sofort per Telegram; weitere werden nur gezaehlt und stehen wie bisher mit
  Anzahl im Tagesabschluss. Getestet mit erzwungenem Fehler ueber 3 Laeufe
  (dry_run, state_override): 1 Meldung, Zaehler 3.

- **2026-09-17** [knowledge/ Lint] **Aufgeraeumt** (Nutzerentscheid bei der
  Dashboard-Durchsicht). Tote Links: „cls-practical" ->
  „cls-practical-kostenvalidierung", „gap-fade"/„execution-overlay"
  (Abschnitte derselben Datei) entlinkt, „risiko-kalibrierung-methodik" ->
  Memory-Pfad, zwei literale Beispiel-Wikilinks umformuliert. Verwaiste Seiten
  verlinkt: 3 Archiv-Notizen aus `strategie-backlog-inventar.md`,
  `paper-bot-architecture` aus `paper-bot-zu-live-bridge.md`,
  `persoenlicher-tradingplan-validierung` aus `edge-card-workflow.md`.
  Lint danach: 0/0/0, nur die 14 Clippings bleiben (naechster Lint).
  Dashboard: "Als Naechstes" Punkt 0 (FK-ORB-MT5-Bars, Phase 2 Funded)
  verworfen, Monatsjournal bleibt als naechstes Vorhaben. Dashboard gesamt
  1115 -> ~430 Zeilen.

- **2026-09-17** [Funded-Portfolio-Bridge / OU-Modell] **Signaldatum-Drift
  behoben: hoechstens eine Position je Titel, verwaiste Positionen werden
  geschlossen** (Nutzerauftrag). `run_once.py`: neue
  `_reconcile_ou_positions()`, laeuft vor `_process_leg()` im OU-Dispatch;
  Schluesselbau in `_signal_key()` zentralisiert (vorher inline); je Titel wird
  nur noch die aelteste offene Modell-Zeile weitergereicht.
  **Regel je Titel:** Modell offen -> eine Position bleibt (die unter dem
  aktuellen Schluessel, sonst die aelteste) und wird auf den aktuellen
  Schluessel umgehaengt, weitere werden geschlossen. Modell fuehrt den Titel
  nur noch geschlossen -> alle Positionen schliessen. Titel fehlt ganz im Scan
  -> **nicht** schliessen, nur einmal taeglich warnen (Datenausfall ist von
  "Modell draussen" nicht unterscheidbar). Schliessen nur bei offener NYSE.
  **Verifiziert:** 24 Offline-Faelle
  (`knowledge/scripts/test_funded_bridge_ou_reconcile.py`) + Trockenlauf auf
  Kopien der echten States mit dem echten Scan: Konto 2 schliesst FAST, ADI
  (Modell per Max-Holding draussen), AMGN 09-11, APD 09-14 (Duplikate); Konto 1
  schliesst AMGN 09-11. **Abweichung von der Liste vom Vortag:** APD auf Konto 1
  ist kein Waise -- dort die einzige APD-Position, das Modell haelt APD offen;
  sie wird nur auf den aktuellen Schluessel umgehaengt und bleibt. Greift beim
  ersten Funded-Lauf in der US-Session (15:43).
  Backup: `Funded-Portfolio-Bridge/_backup_20260917/`.

- **2026-09-17** [OU-Modell-Solo-Altlasten] **Schliess-Skript fuer die 8
  verwaisten Solo-Bot-Positionen gebaut -- Einplanen durch den Auto-Modus
  blockiert, Ausloesen liegt beim Nutzer.** `scripts/close_ou_solo_orphans_once.py`:
  feste Ticketliste (Konto 2 AFL/NUE/UAL/TXT, Konto 1 DAL/UAL/NUE, Tickmill
  DAL), vor dem Schliessen Pruefung auf Symbol/Volumen/magic 0/Kommentar, nur
  bei offener NYSE (echte UTC, nicht Rechnerzeit), TTP-Konten unter dem
  Funded-State-Lock, Ergebnis in Telegram + `scripts/close_ou_solo_orphans_once.log`.
  Vorschau-Lauf 11:05 gegen die echten Konten: alle 8 gefunden und verifiziert,
  zusammen -168,97 schwebend (TTP) bzw. -16,91 EUR (Tickmill) vor Swap.
  Der Versuch, es als einmaligen Task um 15:35 einzuplanen, wurde vom
  Claude-Code-Auto-Modus abgelehnt (Echtgeld-Ausloeser).

- **2026-09-17** [Funded-Portfolio-Bridge / Executor] **Fill-Preis wird
  zuverlaessig zurueckgelesen** (Nutzerauftrag). Im State standen 14 von 30
  Positionen mit `entry_price 0.0` (TTP 12/25, IQ 2/5 -- nicht nur TTP).
  Ursache an TTP-Tickets 18395480/18417751/18444889 read-only belegt:
  Positions-ID == Order-Ticket, `price_open` korrekt -- `positions_get()`
  direkt nach `order_send()` kam nur zu frueh (Position noch nicht
  synchronisiert). Fix in `place_market_entry()`: bis 5x/200 ms nachfragen,
  sonst Einstiegs-Deal (`DEAL_ENTRY_IN`) aus `history_deals_get(position=)`,
  sonst Warnung. Gezielte Zeilen-Aenderung (die parallele Session hatte die
  Datei heute 10:43 geaendert). Bestehende 0.0-Eintraege im State NICHT
  nachgetragen.

- **2026-09-17** [FK Instant Funding] **Order-Kommentare auf 16 Zeichen
  gekappt** (Nutzerentscheid, vorsorglich). `run_once.py` `[:31]` -> `[:16]`,
  `executor.py` Teilausstieg `"FKIF partial-exit"` (17) -> `"FKIF part-exit"`.
  Zuordnung Trade->Bein laeuft ueber Tickets, nicht Kommentare. `order_check`
  auf dem FK-Broker akzeptierte zuvor auch 22 Zeichen -- Verdacht damit nicht
  bewiesen, aber ausgeschlossen.

- **2026-09-17** [Dashboard-Durchsicht mit Nutzer] Entscheidungen: Funded
  Offenes-Risiko-Kill-Switch TTP 3,5 %/IQ 3,0 % bestaetigt; fuenf Alt-
  Annahmen (Restlaufzeit-Gate ohne ou/btc, last_error-Logging, Dedup 1x/Tag,
  Exit-Retry, EK-Margin-Info) bestaetigt; Kurztakt-Ausfaelle eine Woche
  beobachten; TradingView NICHT auf UTC umstellen; CLS-Bewaehrung: Pruefung
  nach 30 Live-Trades; Mindest-Stopabstand fuer weitere Beine erst nach den
  Kosten-Checks (CTNL ja, OU nein); FK-Paper-Sammelmeldung beauftragt;
  Verweise nach ausserhalb von `knowledge/` kuenftig als Pfad in Backticks
  (README ergaenzt, 2 Links umgeschrieben).

- **2026-09-17** [FK Instant Funding / cls_practical] **5-Pip-Stop-Boden
  nachgezogen** (Nutzerentscheid). `fk_instant_funding/paper_bot.py::
  _scan_cls_practical` ruft `simulate_cls_practical(..., min_sl_pips=5)` wie
  Challenge (09-10) und EK (09-11). Wird von der Live-Bridge zur Laufzeit
  importiert, wirkt also ab dem naechsten Lauf. Verifiziert per Scan
  (source=lake, ab 09-01): der 3,6-Pip-Trade vom 09-09 ist weg, uebrig bleibt
  ein 9-Pip-Trade. **Dabei geklaert (Nutzervorgabe Risiko pro Position):**
  FK max 0,5 %, Funded (IQ + TTP) max 1 %, EK ohne Deckel -- ist im Code
  bereits exakt so (`MAX_POSITION_LOSS_PCT=0.005` vom Startkapital;
  `MAX_POSITION_RISK_PCT=0.01` der aktuellen Equity, Zins-Multiplikator wirkt
  VOR dem Deckel), keine Aenderung noetig.

- **2026-09-17** [Dashboard] **Aufgeräumt (Nutzerauftrag "Dashboard
  minimieren").** 37 durchgestrichene/erledigte Punkte entfernt (-309 Zeilen,
  stehen alle schon hier im Changelog). Dazu fünf offene Aufgaben per Log
  als erledigt belegt und entfernt: (1) DD-Entry nach dem OU-Tick-Fix wurde
  am 09-15 22:43 auf beiden TTP-Konten platziert; (2) Funded
  `cls_practical` `'>' str/float`: letztes Vorkommen 09-15 12:15, seitdem
  keins mehr; (3) EK `cls_practical`-Scanfehler: seit 09-14 nur noch der am
  09-16 behobene Duplikat-Fehler; (4) IQ-Gewichtung live bestätigt: dasselbe
  NASDAQ-Signal am 09-14 mit $110,25 auf IQ vs. $54,91 auf TTP (2,0x), null
  OU-Versuche auf IQ seit 09-14; (5) FK SP500 "Invalid stops" auf einen
  Rest-Check gekürzt.
  **Nebenfund:** lokaler `main` ist **112 Commits vor / 2 hinter**
  `origin/main` -- seit 09-16 ~09:08 gehen die Auto-Pushes nicht mehr durch.
  Nur notiert, nicht angefasst.

- **2026-09-17** [Alle 3 Bridges / Lückenliste] **Punkte 5, 6, 8 erledigt;
  1, 3, 4 geprüft -- zwei davon mit anderem Ergebnis als erwartet.**
  Nutzerauftrag "gehe die nächsten Punkte an" (Liste aus
  `areas/systemlandkarte.md`, Punkt 2 vorher verworfen, 7 am 09-16 erledigt).
  **Punkt 6 -- `check_symbols.py` (Funded + FK) neu gebaut.** Prüft jetzt
  echte Handelbarkeit statt nur den Namen: Auflösung über die Bridge-eigene
  Zuordnung (`run_once.resolve_symbol` bzw. `SYMBOL_MAP`/`LEG_TO_SYMBOL`,
  keine kopierte Liste), `trade_mode`, echter Kurs nach dem Wählen (3 s
  Wartezeit gegen den bekannten 0-Tick-Fehlalarm), plus Tickgröße/
  Nachkommastellen/Stopabstand/Mindestlot. Beide gegen die echten Terminals
  gelaufen, rein lesend, 0 Probleme bei aktiven Beinen. **Zwei Befunde aus
  dem ersten Lauf:** `SPX500.gbe` hat Tickgröße 0,1 bei 2 Nachkommastellen
  -- betrifft nicht nur FK, sondern auch das **Funded-IQ-Konto** (dort am
  09-14 ebenfalls `Invalid stops`); Platin hat auf allen Konten ein
  Mindestlot von **1,0**.
  **Punkt 8 -- Spalte "Letzter echter Entry" in der Statustabelle.** Neu
  `soll_ist.py --last-entries`: letzter Eröffnungs-Deal je Bridge, der der
  Bridge zugeordnet ist (EK Magic, Funded/FK Tickets), Fremdpositionen
  getrennt. Stand: EK 09-16 ou_modell, Funded 09-16 orb_sp500 (TTP1),
  **FK 09-14 orb_nasdaq -- erster echter FK-Entry seit Livegang**; mein
  "FK 0 Orders" vom 09-13 ist damit überholt. Auf FK liegen wiederholt
  manuelle Positionen (zuletzt EURUSD 09-16 23:48), die ohne die Trennung
  wie Bridge-Aktivität ausgesehen hätten.
  **Punkt 5 -- Hard-Timeout: Lücke bestand so nicht, nichts gebaut.** Jeder
  Datenabruf ist bei Funded/FK schon hart auf ~66 s begrenzt (`_retry` 3×20 s,
  Daemon-Thread) -- strenger als EKs 600 s. Ein Timeout um die
  Order-Verarbeitung wäre schädlich: ein abgebrochener, aber doch
  durchgegangener `order_send()` fehlt im State und wird beim nächsten Lauf
  doppelt gesendet. Letzte Sicherung bleibt das Task-Limit mit `IgnoreNew`.
  `areas/bridge-infrastruktur-vergleich.md` korrigiert (stand dort als "keiner").
  **Punkt 1 -- Order-Ebene: Ursachen geklärt, eine Härtung blockiert.**
  `order_send()=None` auf FK war **nicht** die Kommentarlänge (Vermutung vom
  09-13), sondern ein `SizingResult` im `volume`-Feld, am 09-09 behoben --
  seither null Vorkommen. `Invalid stops` ist pfadweise behoben (Parallel-
  Session). Offen: Funded rundet im Market-Pfad nicht. Mein Versuch, das im
  gemeinsamen `_send_order()` zu härten, wurde **mittendrin** vom
  Auto-Mode-Classifier blockiert (erstes Edit durch, `import math` nicht) --
  **vollständig zurückgenommen**, `py_compile` ok, Logs ohne `NameError`,
  Bridge lief normal weiter. Wartet auf Freigabe (DASHBOARD).
  **Punkt 3 -- für ORB überholt.** Die Stop-Order-Studie der Parallel-Session
  (09-16, PF 0,82 Market vs. 1,36 Stop) beantwortet die grundsätzlichere
  Frage: der Restlaufzeit-Filter hat einen strukturell verlustbringenden
  Ausführungsweg gebremst. Stop-Orders laufen bisher nur auf den zwei
  Funded-Demokonten -- Funded-Echtgeld, FK und EK handeln ORB weiter per
  Market-Order.
  **Punkt 4 -- Voraussetzung verschoben, zurück an den Nutzer.** Die
  Stale-Fenster liegen dort, wo Ingest und Bridge gleichzeitig ausfielen
  (springende Zeitzone, Schlaf); ein breiteres Fenster würde das verdecken.

- **2026-09-17** [OU-Modell / alle 3 OU-Konten] **Live-Auswertung +
  Kostenvalidierung: der Edge ist nach realen Kosten weg, dazu drei
  Betriebsschaeden. Reine Auswertung, an keinem Bot etwas geaendert.**
  Nutzerfrage. Live: MT5-Deals read-only von TTP Konto 1/2 und Tickmill
  (123 Positionen). Backtest: neues `scripts/research_ou_execution_costs.py`
  (Modell-Trades fix, Neuausfuehrung auf OHLC in 6 Varianten, Replay-A
  reproduziert die Engine exakt), Ergebnis
  `ou_paper_backtest/results/execution_costs_20260916.json`.
  Modell +0,097R -> realistisch +0,05R -> mit Live-Kosten (Spread 12 bps,
  zur Eroeffnung 26; Swap 6,5 % p.a.) -0,013R, PF 0,96; seit 2023 -0,046R.
  Gefunden: (1) Signaldatum wandert zwischen Scans -> doppelte Einstiege im
  selben Titel und 6 verwaiste Funded-Positionen; (2) 8 verwaiste
  Solo-Bot-Positionen; (3) MNST-Split von TTP nicht umgebucht, -2.492,56 $
  auf Konto 1. Nebenbei bestaetigt: der DD-Einstieg aus dem Fix vom
  2026-09-15 ist auf beiden TTP-Konten ausgefuehrt worden (dazu APD/IVZ).
  Die 22:38-Logzeit jener Einstiege war der Zeitzonensprung des Rechners
  (Eintrag darunter), MT5-Deals zeigen 15:37 New York.
  Details: `projects/ou-modell-kostenvalidierung.md`.

- **2026-09-17** [Rechner] **Automatische Zeitzone abgeschaltet, fest auf
  Berlin** (Nutzerauftrag). Dienst `tzautoupdate` gestoppt + `Disabled`
  (Registry Start=4), `tzutil /s "W. Europe Standard Time"`, per UAC-Freigabe.
  **Warum der Rechner sprang:** der Windows-Standortdienst ortet den Rechner
  ueber das WLAN bei **37,93 N / 40,21 E = Diyarbakir, Tuerkei** (Genauigkeit
  500 m; Tuerkei = ganzjaehrig UTC+3). Die automatische Zeitzone folgt dieser
  Ortung immer wieder und springt zurueck, sobald eine andere Ortung
  (vermutlich ueber die IP) gewinnt. Wahrscheinlich ist der Router/Access Point
  in der Standort-Datenbank falsch eingetragen, das ist nicht nachpruefbar.
  Die Wechsel liefen auch in der Nacht weiter (09-17 04:17, 05:22). Am 09-16
  12:26 wurde die Einstellung schon einmal aus- und nach 20 s wieder
  eingeschaltet, das Eventlog zeigt es.

- **2026-09-17** [FK Instant Funding / Executor] **SL wird aufs Preisraster
  gerundet -- "Invalid stops" bei SP500 behoben** (Nutzerauftrag).
  `executor.py::_round_stop_to_tick()` rundet auf `trade_tick_size`, immer
  von der Position weg (long ab, short auf), damit der Stop nie enger wird.
  Angewandt in `place_market_entry()` VOR dem Sizing (Lots rechnen mit dem
  tatsaechlich gesendeten Stop) und in `move_stop_to_breakeven()`.
  **Verifiziert:** 8 Faelle auf SPX500/NAS100/US30/EURUSD/XAUUSD gegen die
  echten Symboldaten, alle auf dem Raster, kein Stop enger; Broker-
  `order_check` (sendet nichts): ungerundet -> `10016 Invalid stops`,
  gerundet -> `0 Done`. Gleiche Ursache wie im Funded-Eintrag darunter
  (IQ SPX500), dort separat gefixt. Externe Bridge-Datei, nicht git-getrackt.

- **2026-09-16/17** [Funded-Portfolio-Bridge / ORB Stop-Orders, nur Demo-Konten
  `ttp` + `iqmarkets`] **Erster Stop-Order-Tag ausgewertet, OCO + broker-seitiger
  Teilausstieg + praeziser 09:45-Pass gebaut.** Echtgeld `ttp1` unveraendert
  (Marktorder-Pfad).
  **Wie der 16.09. lief:** auf beiden Demo-Konten KEINE Order -- (1)
  `orb_pending.todays_setups` las die Level aus der Range-Bar (NaN) -> immer
  `range_not_ready`; (2) nach dem Fix (23:11, nach Sessionende) versuchte die
  Bridge alle 5 Min die Orders der geschlossenen Session zu legen. TTP/US30
  scheiterten an "Market closed", **IQ SPX500 war offen** und scheiterte nur
  an "Invalid stops" (SL ungerundet, tick 0.1) -- ohne das haette um 23:13 eine
  veraltete Order im Buch gelegen. ttp1 (Markt) SP500 @ 7612,40, am SL
  ausgestoppt (-54,76 $); Stop-Order-Level waere 7606,15 gewesen.
  **Gefixt:** `session_over`-Sperre; `breakout_passed`-Sperre (Level vor
  Platzierung schon beruehrt -> heute verpasst statt spaetem Entry); Level/SL/TP
  auf `trade_tick_size` gerundet (per `mt5.order_check` gegen beide Broker fuer
  alle 3 Instrumente x 2 Seiten validiert: 12/12 "Done", nichts platziert).
  **Befund Teilausstieg:** lief NICHT wie gebacktestet -- gepollt alle 5 Min
  statt intrabar. Nachgerechnet 2019-2026 (`ny_open_orb/engine.py::simulate`
  neuer Parameter `partial_check="close"`): Ø R SP500 0,297->0,255, US30
  0,305->0,198, **NASDAQ 0,180->0,057**. Neu: je Richtung zwei Orders --
  P-Scheibe (50 %, Broker-TP am Teilausstiegs-Level) + R-Scheibe (Rest, TP 4R
  bzw. ohne); BE fuer R, sobald P per TP geschlossen (naechster Lauf). Nicht
  teilbare Lots -> eine Order mit altem gepolltem Teilausstieg.
  **OCO (NASDAQ):** beide Seiten liegen, erste gefuellte storniert die
  Gegenseite; beide gefuellt -> spaeter gefuellte sofort schliessen. Gemessen:
  Gegenseite in Folgebar bei 2,0 % der Trades beruehrt.
  **Befund Timing:** 58-65 % aller ORB-Entries fallen in die erste M5-Bar nach
  Range-Ende (US30 Ø R ohne sie 0,063 statt 0,305). Der 5-Min-Takt kam erst
  09:48. Neu `run_once_fast.py`: der Lauf ~09:43 NY wartet bis 09:45:03 und
  platziert nur die Stop-Orders (in NY-Zeit gerechnet, sommerzeitfest; Setups
  ~1 s je Konto). Ausserdem: Exit-Erkennung fuer Broker-SL/TP mit P/L-Meldung,
  max. 3 Platzierungsversuche mit Aufraeumen halb gelegter Orders, Tagesreport
  zaehlt Pendings nicht als Positionen.
  **Zwischenfall beim Bau:** ein Such-/Ersetz-Muster traf zuerst
  `place_market_entry` -- fuer ~15 Min (ca. 23:17-23:33) haette jeder
  Markt-Entry aller Beine mit NameError abgebrochen; laut Log gab es keinen
  Entry-Versuch. Ausserdem fiel der Fast-Lauf 23:23 an einem Syntaxfehler aus.
  Ein Testaufruf schickte dabei einen `order_send` an IQ-Demo (abgelehnt,
  "Market closed"). Behoben, Diff gegen Backup geprueft, pyflakes sauber.
  Tests: Zustandsmaschine mit simuliertem Broker (16/16), DRY_RUN mit echten
  Terminaldaten fuer 15./16.09. Backups `%TEMP%\*.bak_20260916`.

- **2026-09-16** [Rechner / alle Bridges] **Tagesreview: die "verschobenen
  TradingView-Stempel" (Eintrag darunter) kamen vom Rechner selbst -- die
  Windows-Zeitzone springt seit 2026-09-15 21:35 hin und her.** Nur Befund,
  kein Code und keine Systemeinstellung geaendert.
  **Beleg:** System-Eventlog, `Kernel-General` Id 1 mit `reason=3`
  (Zeitzonenwechsel, UTC-Zeit unveraendert) am 09-15 um 21:35/23:40 und am
  09-16 um 00:45, 01:50, 04:06, 05:11, 11:02, 12:26 (dieser eine ueber die
  Einstellungen-App), 17:27, 18:27, 21:13, 21:45. Die EK-Logdateinamen
  (Lokalzeit) gegen ihre Datei-mtime (UTC) bestaetigen es: 22:44Z ->
  `run_..._004412`, 22:46Z -> `run_..._014612` -- die Lokalzeit lief
  zeitweise auf UTC+3 statt UTC+2. Automatische Zeitzone ist aktiv
  (Dienst `tzautoupdate`, Start=3).
  **Wirkung 1 -- CLS-Zinsreihen:** `tradingview/data.py` (tvDatafeed) stempelt
  mit `datetime.fromtimestamp()`, also in LOKALZEIT. In jedem UTC+3-Fenster
  kamen die D1-Stempel eine Stunde spaeter (08:00 -> 09:00) -- genau die
  Verdopplung von heute morgen. Die TradingView-Quelle hat nichts verschoben.
  Einziger tvDatafeed-Nutzer im Live-Pfad sind die zwei 2y-Zinsreihen; der
  Kalendertag-Dedup von heute faengt weitere Flips dort ab.
  **Korrektur zum Eintrag darunter:** "EK war nicht betroffen" stimmt nicht --
  EKs CLS-Bein brach 43-mal mit demselben Fehler ab (09-15 22:36 bis 09-16
  10:44), die Datei war nur ueber den Lake-Fix mit repariert.
  **Wirkung 2 -- Scan-Luecken:** jeder Vorwaerts-Sprung laesst ~1 h
  Scheduled-Task-Laeufe auf ALLEN Bridges aus (EK/Funded/FK identisch:
  00:44-01:46, 04:03-05:08, 10:58-12:03, 17:23-18:28, 21:13-21:48 Lokalzeit);
  jeder Rueck-Sprung wiederholt eine Stunde. Session-Logik der Bridges laeuft
  ueber UTC/Serverzeit und war nicht betroffen; `date.today()`-Tages-Keys
  sind heute nicht ueber Mitternacht gekippt.
  **[FK Instant Funding / ORB] "Invalid stops" aufgeklaert** (offen seit
  09-13): `symbol_info` (rein lesend) zeigt `SPX500.gbe` mit
  `trade_tick_size = 0.1` (NAS100/US30: 0.01) und `trade_stops_level = 0`.
  Das ungerundete SL (heute 7604,5535...) liegt nicht auf dem 0,1er-Raster.
  Mindestabstand als Ursache damit ausgeschlossen. SP500 scheiterte damit
  3 von 3 (09-11, 09-14, heute 15:53 -- 14,9 Lots); NAS100 ging am 09-14 mit
  ebenso ungerundetem SL durch, weil dort 0.01 = digits gilt. **Noch nicht
  gefixt** (Echtgeld-Code), siehe DASHBOARD.

- **2026-09-16** [Data Lake / cls_practical] **🔴 CLS-Bein war auf Funded und FK
  seit 2026-09-15 22:38 komplett tot -- Ursache gefunden und behoben.**
  Beim Bau des Soll/Ist-Vergleichs (Eintrag darunter) gestolpert, nicht gesucht.
  **Symptom:** jeder CLS-Scan brach ab mit `cannot reindex on an axis with
  duplicate labels`; 792 fehlgeschlagene Scans (Funded 633, FK 159), letzter
  um 10:28 am 2026-09-16. ~~EK war nicht betroffen.~~ *(falsch -- EK brach
  43-mal ab, siehe Tagesreview-Eintrag darueber)*
  **Ursache:** ~~TradingView lieferte~~ die beiden 2y-Zinsreihen kamen ab
  2026-09-15 eine Stunde spaeter gestempelt (DE02Y 08:00 -> 09:00, US02Y
  01:00 -> 02:00). *(Korrigiert im Tagesreview darueber: nicht die Quelle hat
  verschoben, sondern die springende Windows-Zeitzone -- tvDatafeed stempelt in
  Lokalzeit. Der Fix unten bleibt richtig.)* `data_lake/storage.py::write_bars()` dedupliziert auf den
  EXAKTEN Zeitstempel -- die verschobene Historie sah damit wie lauter neue
  Balken aus und wurde vollstaendig ein zweites Mal angehaengt (DE02Y
  3.657 -> 7.308 Zeilen, im Ingest-Log als Sprung sichtbar).
  `cls_practical/rates.py::compute_daily_rate_score_2y()` legt den Index auf
  `.date` um und traf danach auf 3.650 doppelte Kalendertage.
  **Fix zweistufig:** (a) `write_bars()` dedupliziert D1-Reihen zusaetzlich auf
  den Kalendertag (spaetester Stempel gewinnt) -- fuer korrekt gestempelte
  Reihen ein No-Op, gegen alle 62 D1-Reihen geprueft, nur die beiden
  Zinsreihen waren betroffen; (b) die beiden Parquet-Dateien einmalig bereinigt
  (7.308 -> 3.658 bzw. 7.321 -> 3.670 Zeilen, Backups `.bak_20260916`).
  Verifiziert: CLS-Scan laeuft auf FK und Challenge wieder durch.
  **Lehre:** die Deduplizierung auf den exakten Zeitstempel setzt stillschweigend
  voraus, dass eine Quelle ihre Stempel nie verschiebt. Genau das ist passiert,
  und der Lake hat es nicht gemerkt, sondern verdoppelt.

- **2026-09-16** [Reporting / alle 3 Bridges] **Soll/Ist-Vergleich gebaut --
  Backtest ueber dasselbe Kalenderfenster gegen die echten Zahlen.**
  Nutzerauftrag 2026-09-14; ersetzt die verworfene Paper-Zwilling-Idee.
  **Zwei neue Module.** `scripts/reports/mt5_pull.py`: rein lesender
  MT5-Abzug (account_info/history_deals_get/positions_get, nie order_send)
  ueber alle Konten -- loest die woechentlich neu geschriebenen Wegwerf-Skripte
  `_kw37_pull.py` & Co. ab und liest die Kontoliste aus den Bridge-Configs,
  statt sie zu duplizieren (die alten Skripte fuehrten IQ 15514 noch, neun Tage
  nach dessen Entfernung). `scripts/reports/soll_ist.py`: ruft die ECHTEN
  `_scan_*()`-Funktionen der drei `paper_bot.py` auf (keine zweite
  Formel-Implementierung), rechnet die Soll-Rendite ueber das jeweils vorhandene
  `compute_shared_equity()` und zerlegt die Differenz in `platziert` /
  `nicht_platziert` / `nie_gesehen`. **Keine paper_bot.py und keine
  Bridge-Datei wurde dafuer angefasst.**
  **Kosten je Bridge** (Nutzerentscheid): Funded 2,05 / FK 1,30 Pips gemessen,
  EK 0,50 geschaetzt. Angewandt als nachgelagerter R-Abschlag und NUR auf
  cls_practical, weil die Messung nur fuer EUR/USD existiert; abgezogen wird
  nur die Restkosten ueber den bereits von der Engine berechneten Spread hinaus.
  **Erstes Ergebnis KW37** (`scripts/reports/soll_ist_2026-W37.json`):
  EK Soll -0,33 % / Ist -90,56 EUR; Funded Soll -0,62 % / Ist -2.878,91 USD
  (3 von 10 Soll-Trades platziert, 7 von Gates verworfen); FK Soll -1,48 % /
  Ist 0,00 (alle 9 Soll-Trades von Gates verworfen). **In dieser Woche haben
  die Gates also Verluste VERHINDERT** -- das ist die Gegenprobe zum Befund
  vom 2026-09-13, der sie als reinen Kostenfaktor gelesen hat. Eine Woche ist
  noch kein Beweis; das MC-Erwartungsband fehlt bewusst (spaeterer Ausbau).
  **Wichtigster Vorbehalt, im Modul- und im Report-Prompt festgeschrieben:**
  das Soll rechnet mit der HEUTE gueltigen Konfiguration. Realfall aus KW37 --
  Funded nahm am 09-09 einen cls_practical-Trade mit 3,6 Pips Stop
  (-1.441,72 USD ueber drei Konten); der am 09-10 eingefuehrte 5-Pip-Boden
  verwirft ihn heute, das Soll zeigt dort "kein Signal". Die Luecke ist also
  kein Ausfuehrungsfehler, sondern der Beleg, dass der Filter wirkt.
  **Anbindung:** `weekly_report_prompt.md` Abschnitt 5 (neu) ruft beide Skripte
  im Sonntagslauf auf -- kein zusaetzlicher Scheduled Task (Nutzerentscheid).
  **Zwei Nebenbefunde:** EK laesst sich nur grob zerlegen (SQLite statt
  Signal-Ledger) -- unbelegbare Faelle heissen dort bewusst
  `nicht_ermittelbar` statt faelschlich `nie_gesehen`; und Funded/FK setzen
  kein Magic, die Zuordnung Trade->Bein laeuft ueber die Tickets im
  bridge_state (schwaechere Kopplung, aber sie trennt zuverlaessig die
  Fremdpositionen ab -- auf FK lagen am 09-14 zwei Positionen mit magic=0 und
  leerem Kommentar, die NICHT von der Bridge stammen).

- **2026-09-16** [EK-Portfolio-Bridge] **Config-Kommentar zur Kapitalscheibe
  korrigiert** (Aufraeumpunkt aus der Bein-Auszaehlung). `CAPITAL_WEIGHT = 1/8`
  war mit "OU-Modell zaehlt mit (eigenes echtes Konto, **keine Order hier**)"
  begruendet -- seit der Aufloesung der OU-Modell-MT5-Bridge sendet DIESE
  Bridge die OU-Orders selbst (9 im Log belegt). **An der Zahl aendert sich
  nichts**, 1/8 bleibt richtig; korrigiert wurde die Begruendung, weil sie
  sonst ein Achtel des Risikobudgets faelschlich als unbenutzt ausweist.

- **2026-09-16** [Funded-Portfolio-Bridge / ORB] **Ruhende Stop-Orders statt
  verzoegerter Marktorders -- auf den beiden DEMO-Konten scharf, Echtgeld-Konto
  bewusst noch nicht.** Damit handelt die Bridge endlich den Mechanismus, den
  der Backtest seit jeher modelliert ("resting stop at orb_high/orb_low,
  intrabar fill at the level").
  **Beleg** (2.336 Trades 2019-2026, gemessene Broker-Spreads):
  Stop-Order am Level PF 1,36 / Ø R +0,219 / P(Ø R<0) 0,0 % gegen Marktorder
  zum Bar-Schluss PF 0,82 / Ø R -0,144 / P(Ø R<0) 99,7 %. Entscheidend: EKs
  14-Sekunden-Pipeline ist fast genauso schlecht wie Funded's 3-Minuten-Pipeline
  -- es ist nicht die Pipeline, sondern das WARTEN auf den Bar-Schluss (Kurs
  laeuft im Median 6-18 % der Stopdistanz weiter). Am realen Trade vom
  2026-09-14 nachgerechnet: Fill am Level haette bei gleichem Dollar-Risiko rund
  das **2,7-fache** verdient, weil die kleinere Risikodistanz eine groessere
  Position erlaubt.
  **Neu:** `executor.py` bekommt `place_pending_stop()` (TRADE_ACTION_PENDING,
  ORDER_TYPE_BUY/SELL_STOP, ORDER_TIME_DAY), `cancel_pending()` und
  `pending_order_state()`. `orb_pending.py` (neu) bestimmt die Setups der
  heutigen Session VOR dem Ausbruch -- bisher reagierte die Bridge erst auf
  bereits ausgeloeste Trades. `run_once.py::manage_orb_pending()` verwaltet
  Platzieren/Verfolgen/Stornieren, beide Lanes rufen es auf.
  **Wichtigste Sicherheitsentscheidung:** auf Pending-Konten ist der
  Marktorder-Pfad fuer ORB KOMPLETT abgeschaltet (`_orb_pending_enabled()`).
  Liefe beides, wuerde eine bereits gefuellte Stop-Order vom Scan als "neuer
  Ausbruch" gesehen und ein zweites Mal gehandelt. Einen Marktorder-Fallback
  gibt es bewusst nicht -- ein Tag ohne Trade ist besser als ein Tag mit dem
  nachweislich verlustbringenden Pfad.
  **Sizing haengt am Level, nicht am Marktpreis** -- damit steht der
  Risikoabstand schon bei der Platzierung fest und kann nicht mehr durch
  Kursdrift aufgeblaeht werden. Der R-Detektor ist fuer diesen Pfad
  gegenstandslos.
  **Noch offen: OCO.** NASDAQ ist beidseitig, `_find_stop_breakout()` nimmt aber
  die zuerst brechende Seite und verwirft Tage, an denen beide brechen -- zwei
  ruhende Orders wuerden dagegen beide ausloesen. `orb_pending.py` meldet solche
  Setups als `skipped_needs_oco` und platziert NICHTS, statt eine halbe
  OCO-Logik zu bauen. Heute (Mittwoch) faellt NASDAQ ohnehin durch den
  Wochentagsfilter.
  **Verifiziert (alles im Trockenlauf, keine echte Order gesendet):**
  Filterkette 1:1 reproduziert (230 Ausbrueche ueber 3 Instrumente, **null
  Abweichungen** gegen die echte `_scan_orb`-Kette); Platzierung erzeugt
  korrekten State-Eintrag; Idempotenz (zweiter Lauf platziert nicht erneut);
  Kill-Switch (`entries_allowed=False`) verhindert Platzierung; Stop auf der
  falschen Seite wird abgelehnt; Verfolgung erkennt "gefuellt"/"verschwunden";
  Stornierung bei Session-Ende greift.
  **Staffelung:** `ORB_PENDING_ACCOUNTS = {"ttp", "iqmarkets"}` -- beide Demo.
  `ttp1` (Echtgeld) laeuft unveraendert ueber Marktorders, bis ein sauberer Tag
  vorliegt.

- **2026-09-15** [Funded-Portfolio-Bridge] **Ursache gefunden, warum auf TTP
  fast keine OU-Entries zustande kamen: ein frisch abonniertes MT5-Symbol
  liefert ~0,5 s lang `bid=ask=0.0` — und der Anti-Spam-Fix vom 2026-09-08
  machte daraus einen dauerhaften Signalverlust.** Nutzerfrage („warum auf
  Funded keine OU-Entries bei TTP? TROW gibt es auf TTP"), Umbau auf
  Nutzerfreigabe.
  **Kein Symbol-, Markt- oder Kommentar-Problem.** Read-only nachgemessen:
  TROW/IVZ/DD existieren auf TTP, `trade_mode=4`, und quotierten zum
  Signalzeitpunkt (letzter Tick der Montagssession 22:54 UTC, Signal 19:13
  UTC). Der Order-Kommentar `"FP ou_modell (TROW)"` ist 19 Zeichen, auf 31
  gekappt — der einzige kommentar-artige Fund im Log ist `comment='Market
  closed'` **im Antwortfeld** eines `OrderSendResult` vom 09-02, also die
  Rejection-Begruendung des Brokers.
  **Die Kette:** `resolve_symbol()` ruft `mt5.symbol_select()` und gibt sofort
  zurueck → `_process_leg()` ruft Mikrosekunden spaeter `symbol_info_tick()` →
  frisch abonniertes Symbol liefert `bid=ask=0.0` → Zweig `live_price <= 0`
  meldet „kein Live-Kurs" → **und schreibt seit 2026-09-08 `status="missed"`**
  → das Signal wird nie wieder angefasst, auch nicht 15 Min. spaeter, wenn der
  Kurs da ist. Getroffen hat das **jedes Symbol beim allerersten Mal**; bei
  `ou_modell` ist das fast jedes Signal (rotierendes Aktien-Universum).
  **Reproduktion (read-only, TTP Konto 2, 3/3):** CAT/CMCSA/COIN frisch
  selektiert → sofort `bid=0.0 ask=0.0`, nach <0,5 s 783,44 / 24,81 / 192,46.
  **Abgrenzung zum IQ-Fall:** auf TTP steht die Warnung je Symbol **genau
  einmal** (transient), auf IQ stand sie **48x** fuer dasselbe Symbol (der
  Broker quotiert Einzelaktien wirklich nie). Der `excluded_legs`-Ausschluss
  auf IQ bleibt damit richtig.
  **Vier Aenderungen** (`executor.py`, `run_once.py`; `run_once_fast.py` erbt
  sie automatisch ueber `slow._process_leg()`):
  **(1) `executor.wait_for_tick()`** — wartet bis zu 2 s auf den ersten Tick
  mit `bid>0 UND ask>0`. Gibt bewusst keinen 0-Tick als Notbehelf zurueck, ein
  wirklich kursloses Symbol faellt weiterhin sauber durch. Auch in
  `place_market_entry()` eingesetzt, wo bisher nur `tick is None` geprueft
  wurde — ein 0-Tick haette dort `entry_price = 0.0` ergeben und
  `calc_lot_size()` gegen einen Nullpreis rechnen lassen.
  **(2) `_select_and_wait()`** in `resolve_symbol()` — wartet nur, wenn
  `info.visible` vorher `False` war. Bei laengst abonnierten Symbolen kostet
  das nichts; ohne diese Bedingung wuerde ein dauerhaft kursloses Symbol in
  jedem Lauf und jedem Bein die vollen 2 s verbrennen.
  **(3) Retry-Marker statt endgueltigem `missed`** fuer die beiden
  VOROEBERGEHENDEN Ursachen (`_mark_for_retry()`, `MAX_TRANSIENT_ENTRY_RETRIES
  = 8`). Der Anti-Spam-Zweck von 09-08 bleibt: gemeldet werden nur der erste
  Versuch und das Aufgeben. Alle anderen Skip-Zweige (Signal zu alt, kein SL,
  schon ausgestoppt, R-Detektor) bleiben unveraendert endgueltig — ihre
  Ursachen aendern sich nicht von selbst.
  **(4) Broker-Ablehnungen werden klassifiziert** (`TRANSIENT_ENTRY_RETCODES`,
  `place_market_entry()` gibt den `retcode` jetzt strukturiert zurueck statt
  nur im repr-String). 10018 „Market closed" ist bei einem Aktien-Bein, das
  rund um die Uhr scannt, der Normalfall ausserhalb 15:30-22:00 Berlin — am
  2026-09-02 kostete die pauschale Behandlung ADI und FAST. Dauerhafte Gruende
  (10014/10015/10016/10017/10019/10030 und `retcode=None`, also der zu lange
  Order-Kommentar vom 2026-09-09) bleiben `missed`.
  **Verifiziert:** `py_compile` aller drei Module + **32 Offline-Testfaelle**
  gegen gestubbtes MT5, das den 0-Tick-nach-`symbol_select()` real nachbildet
  (`knowledge/scripts/test_funded_bridge_tick_retry.py`, git-getrackt, weil die
  Bridge-Dateien selbst kein Git-Netz haben): Tick-Waechter, Erstabo-Warten,
  Retry→Entry-Nachholung, Aufgeben nach 8 Versuchen ohne Spam,
  Nicht-Regression der dauerhaften Skip-Gruende, Retcode-Klassifikation.
  **(5) Verbrannte State-Eintraege bereinigt:** die drei Signale vom 09-14
  (DD/IVZ/TROW) auf **beiden** TTP-Konten aus `bridge_state_ttp*.json`
  entfernt — Signaltag 1,41 Tage alt, also noch innerhalb des 2-Tage-Gates.
  Nur `status="missed"` OHNE Ticket wurde angefasst, unter dem regulaeren
  `account_state_lock()`. Aeltere Signale (ADI/FAST/SYY/EXPE/APD) bewusst
  liegengelassen: sie waeren ohnehin am Alters-Gate gescheitert.
  Backup der vier beruehrten Dateien in `Funded-Portfolio-Bridge/
  _backup_20260915/`.
  **Einloesbar ist davon nur DD:** ein Re-Scan um 12:05 zeigt DD (09-14, Entry
  124,29) weiterhin als `data_end`; TROW und IVZ stehen im heutigen Scan gar
  nicht mehr -- `_scan_ou_modell()` leitet die Trades bei jedem Lauf neu her,
  ein am Vortag offenes Signal kann mit der neuesten Bar verschwinden.
  **Nachtrag zur Retcode-Klassifikation:** der 10018-Fall ist praktisch schon
  durch das bestehende `_nyse_is_open()`-Gate abgedeckt (es setzt
  `ou_entries_allowed=False` ausserhalb der US-Kassazeit -- deshalb war der
  11:58-Lauf still und nicht etwa fehlerhaft). Die Klassifikation bleibt
  trotzdem: sie greift fuer die Nicht-Aktien-Beine und an den Rand-Minuten der
  Session, wo das NYSE-Gate offen ist und der Broker trotzdem ablehnt.
  **Erster echter Lauf mit dem neuen Code (11:58) sauber durch**, alle drei
  Konten verbunden, keine Fehlerzeile.

- **2026-09-15** [Funded-Portfolio-Bridge / ORB] **ORB-Bars kommen jetzt vom
  Ausfuehrungs-Broker statt aus dukascopy/Lake -- und der Scan laeuft je Broker
  statt einmal fuer alle Konten.** Umsetzung des am selben Tag freigegebenen
  Plans; EK (seit 2026-08-28) und FK (seit 2026-09-09) hatten das bereits, nur
  Funded fehlte.
  **Warum:** die ORB-Level sind ABSOLUTE Preise, die Broker-Feeds liegen aber
  messbar neben Dukascopy (gemessen 2026-09-13, je 1.767 M15-Bars):
  TTPMarkets SP500 -1,97 / US30 -1,47 / NASDAQ -1,55 bps; BeyondIQCapital
  +0,09 / +0,24 / -0,10 bps; TickmillEU -1,74 / -1,34 / -1,40 bps. Bei einer
  Stopdistanz von 7,5-9,3 bps sind 1,5 bps **15-25 % des Risikos**. Live belegt
  am 2026-09-14: FK und Funded-IQ haengen am SELBEN Broker, handelten dasselbe
  NASDAQ-Signal -- FK (MT5) stieg 13:53 UTC bei 28.992,50 ein, Funded-IQ
  (Dukascopy) 13:58 bei 28.981,80.
  **Geaendert:** (1) `challenge_portfolio/paper_bot.py::_scan_orb()` bekommt
  `fetch_m5_override`/`fetch_m15_override` -- Signatur 1:1 aus
  `fk_instant_funding/paper_bot.py::_scan_orb()`, ohne Override aendert sich
  nichts. (2) Neu: `Funded-Portfolio-Bridge/orb_mt5_source.py`, portiert von FK.
  Anders als dort NICHT modulglobal, sondern `make_fetchers(account)` -- dieses
  Portfolio hat drei Konten an zwei Brokern mit verschiedenen Symbolnamen
  (TTP "US500" vs. IQ "SPX500.gbe"). (3) `run_once.py::orb_scan_for_broker()`
  neu, je `mt5_server` gecacht, HINTER dem Connect; `run_once_fast.py` nutzt
  dieselbe Funktion. ORB ist aus beiden geteilten Vorab-Scans entfernt.
  **Konsequenz fuer die Scan-Dedup vom 2026-09-03:** ORB kann nicht mehr geteilt
  werden (broker-spezifische Level). Die beiden TTP-Konten teilen sich aber
  weiterhin einen Scan -- **2 statt 1 ORB-Scan pro Zyklus, nicht 3.**
  Verifiziert (2026-09-15): `_scan_orb()` ohne Overrides unveraendert
  (425 Trades, explizite None-Overrides bit-identisch); Server-Zeitzone auf
  beiden Brokern verifiziert (-0,09 / -0,08 Min Abweichung); MT5-Level
  reproduzieren die gemessene Richtung (TTP -1,5 bis -4,5 bps unter Dukascopy,
  IQ -0,53 bis +0,18); genau 2 Scans fuer 3 Konten, drittes Konto aus dem Cache;
  Scan-Dauer 1,4 s je Broker (Fast-Task lag bisher bei 13-17 s); erzwungener
  Rueckfall greift und meldet sich in Log und Telegram.
  **Dabei gefunden und behoben:** die Rueckfall-Warnung enthielt ein Emoji und
  liess `print()` auf einer cp1252-Konsole abstuerzen -- ausgerechnet im
  Fehlerpfad. Telegram-Zeile behaelt das Emoji, Konsolen-Zeile nicht.
  **Noch nicht umgestellt:** die Stop-Order-Entry-Logik (naechster Schritt).
  `cls_practical` bleibt bewusst auf Dukascopy -- der EURUSD-Versatz betraegt
  0,00-0,20 Pips gegen >=5 Pips Stopdistanz (0-4 %), anders als bei Index-CFDs.

- **2026-09-15** [cls_practical/rates.py] **Bridge-Monitor-Routine: CLS-Practical-Scan
  auf Funded-Portfolio-Bridge (TTP + IQ, alle Konten) fiel seit 22:38 Uhr bei
  JEDEM ~15-Minuten-Zyklus mit `cannot reindex on an axis with duplicate
  labels` aus -- Ursache gefunden und gefixt, kein Order-/Risikopfad
  angefasst.** Snapshot zeigte 7 identische Fehler-Events zwischen 22:38 und
  23:58 auf allen drei Funded-Konten. Root Cause in
  `compute_daily_rate_score_2y()`: die Funktion trunkiert `de02y.index` /
  `us02y.index` (DatetimeIndex mit Uhrzeit) auf `.date`, bevor beide Series
  per `pd.concat(..., join="outer")` zusammengefuehrt werden.
  `fetch_2y_yield_daily()` dedupliziert nur auf exaktem Timestamp
  (`df[~df.index.duplicated(keep="last")]`) -- ein `force_refresh`-Live-Pull
  kann aber den letzten abgeschlossenen Tagesbalken UND einen noch laufenden
  Intraday-Snapshot fuer denselben Kalendertag mit zwei verschiedenen
  Timestamps liefern. Nach der `.date`-Trunkierung kollidieren beide zu
  einem doppelten Index-Label, worauf `pd.concat` mit genau dem beobachteten
  Fehlertext abbricht. Reproduziert lokal mit synthetischen Daten (zwei
  DE02Y-Zeilen am selben Kalendertag, unterschiedliche Uhrzeit) -- exakt
  derselbe Fehlertext. Fix: `de_chg`/`us_chg` werden nach der
  `.date`-Trunkierung zusaetzlich mit `keep="last"` dedupliziert, gleiche
  Konvention wie in `fetch_2y_yield_daily()` selbst. Verifiziert: Reproduktion
  crasht ohne den Fix, laeuft mit Fix sauber durch (inkl. End-to-End-Test von
  `compute_frontend_2y_risk_multiplier()` mit injizierter Duplikat-Zeile);
  `py_compile` auf der geaenderten Datei. **Kein Live-Lauf gegen echte
  TradingView-Daten abgewartet** (kein Zugriff auf die laufende Bridge von
  hier aus) -- reine Datenaufbereitung vor dem eigentlichen
  Risikomultiplikator, Order-Versand/Sizing-Logik selbst unveraendert.
  Der aeltere, separat dokumentierte `dukascopy_python-Hang` (12:15/12:34 Uhr,
  siehe DASHBOARD.md) ist ein anderer, bereits bekannter Fehlertext und nicht
  Teil dieses Fixes.
  **Nachtrag 2026-09-17 (lokale Session):** dieser Fix ist richtig und bleibt,
  war aber nicht die einzige Ursache -- die Stempel verschoben sich, weil die
  Windows-Zeitzone des Rechners sprang (siehe Eintraege vom 09-16/09-17).

- **2026-09-14** [Reporting / Forex-Weekly-Report] **Weekly Checkup KW37 fiel
  aus -- Ursache war NICHT der ausgeschaltete PC, sondern das 1-Stunden-
  Zeitlimit des Tasks. Limit auf 4h angehoben, Wochen-Logik fuer verspaetete
  Laeufe praezisiert, KW37 nachgeholt.**
  Nutzerwunsch: Checkup nachholen + "Backup-Task" einrichten, damit es bei
  ausgeschaltetem PC spaeter trotzdem entsteht.
  **Befund: dieser Backup-Mechanismus existiert bereits und hat funktioniert.**
  Der Task hat `StartWhenAvailable = True` (plus `WakeToRun`), ist deshalb am
  2026-09-13 um 21:21:40 nachtraeglich gestartet, nachdem der 18:00-Termin bei
  ausgeschaltetem PC verstrichen war. Ein zweiter Task waere reine Redundanz
  gewesen. Gescheitert ist der Lauf an etwas anderem: `ExecutionTimeLimit` war
  `PT1H`, der Task wurde nach 60 Minuten vom Scheduler abgeschossen
  (`LastTaskResult` 267014 = `SCHED_S_TASK_TERMINATED`, im `task_run.log` fehlt
  entsprechend die "beendet"-Zeile). Fertig geworden war bis dahin nur
  `KW37_2026_performance.md`; Education-Report, Checkup-HTML, PDF und Telegram
  fehlten. Zum Vergleich: die regulaeren Sonntagslaeufe brauchten 25-26 Min --
  der verspaetete Lauf hatte mehr aufzuarbeiten und lief in die Grenze.
  **(1) `ExecutionTimeLimit` `PT1H` -> `PT4H`** (Task Scheduler, kein Repo-
  Artefakt). `StartWhenAvailable`/`WakeToRun` blieben unveraendert an.
  **(2) `scripts/reports/weekly_report_prompt.md`: Wochen-Auswahl praezisiert.**
  Bisher stand dort nur "Compute the ISO week number for today; if today is
  Sunday, this report covers the Monday-Sunday week ending today" -- fuer einen
  verspaeteten Montagslauf undefiniert, der Lauf haette plausibel KW38 (die
  laufende Woche) statt KW37 produziert. Jetzt explizit: immer die LETZTE
  VOLLSTAENDIG ABGESCHLOSSENE Mo-So-Woche, bei Verspaetung also die Woche, die
  am letzten Sonntag endete; plus die Anweisung, eine bereits vorhandene Datei
  aus einem abgebrochenen Lauf zu lesen und darauf aufzubauen statt sie
  duenner zu ueberschreiben. Das ist inzwischen der dritte verspaetete Lauf,
  die Luecke war also keine Theorie.
  **(3) KW37 nachgeholt** ueber einen manuellen Start desselben Tasks
  (`Start-ScheduledTask`, 09-14 09:20), also exakt der normale Pfad. Die
  praezisierte Wochen-Logik hat gegriffen: der Lauf hat korrekt KW37
  (07.-13.09.) erzeugt, nicht die laufende KW38. **Auch dieser Lauf kam nicht
  ganz durch** -- nach 12 Minuten Claude-Session-Limit, direkt NACH dem
  Checkup-HTML, aber vor PDF/Telegram/Commit. Die drei Restschritte wurden am
  2026-09-15 von Hand nachgezogen (Edge-Headless-PDF 558 KB, Telegram-Versand,
  Commit `be3ef98`). Inhaltlich ist der Report vollstaendig -- er hat sogar den
  offenen KW34-Befund zum nicht zuordenbaren EURUSD-Trade aufgeloest (Handtrade
  auf dem FK-Konto, Zeitzonen-Artefakt Helsinki/Berlin).
  **(4) Stiller Teilabbruch wird jetzt erkannt** (`run_weekly_report_task.ps1`).
  Der eigentliche Skandal an beiden Fehllaeufen war nicht der Abbruch, sondern
  dass der Task **Erfolg meldete** (`LastTaskResult` 0): das Skript hat den
  Ausgang des `claude.exe`-Laufs nie ausgewertet, ein halb fertiger Lauf sah
  aus wie ein gelungener. Neu am Ende: Pruefung, ob seit Laufbeginn ein neues
  PDF in `Documents\Trading Reports` liegt (das PDF ist der letzte Schritt vor
  dem Versand, also der beste Einzelindikator; bewusst ueber den Zeitstempel
  statt ueber den erwarteten Dateinamen, weil die abgedeckte Kalenderwoche der
  Prompt entscheidet, nicht das Skript). Fehlt es: klare FEHLER-Zeile im Log,
  Telegram-Warnung und `exit 1`.
  **(5) Automatische Wiederholung** dank (4): `RestartCount = 3`,
  `RestartInterval = PT4H`. Bei einem Session-/Wochenlimit ist ein spaeterer
  Versuch genau die richtige Reaktion -- vorher konnte der Scheduler gar nicht
  wiederholen, weil der Lauf sich als erfolgreich ausgab.

- **2026-09-14** [Second Brain / Alle 3 Live-Bridges] **Bein-Ebene erstmals
  vollstaendig gezaehlt: Ist/Soll/Paper-Matrix + Systemlandkarte angelegt.**
  Nutzerauftrag ("Ist/Soll-Vergleich um eine Paper-Bot-Spalte ergaenzen, dazu
  ein frischer Ueberblick ueber Funktionsweise und Luecken"). **Reine
  Auswertung, kein Code geaendert.** Datenbasis: `bridge_state_*.json`,
  `ek_portfolio_55918977.sqlite3`, `logs/run_*.log` + `task_run*.log` aller
  drei Bridges, Task Scheduler, `data_lake_store/manifest.json`.
  **Zwei neue Seiten:** `areas/bein-matrix-ist-soll-paper.md` (je Bein je
  Bridge: Soll-Risiko laut Config, tatsaechlich platzierte Orders, Paper-Status)
  und `areas/systemlandkarte.md` (die sechsstufige Kette Datenquelle → Lake →
  Scan → Gates → Sizing → `order_send`, mit den Verlusten je Stufe und einer
  nach Gewicht sortierten Luecken-/Optimierungsliste).
  `areas/bridge-infrastruktur-vergleich.md` um zwei Zeilen erweitert (Bindung
  an den Paper-Bot: EK kopiert, Funded/FK importieren zur Laufzeit; laeuft ein
  Paper-Zwilling?) und um Luecke 5 ergaenzt.
  **Der zentrale Befund — „live" heisst nicht „handelt":** Funded platziert
  16 von 80 Signalen (20 %), **FK seit `DRY_RUN=False` am 2026-09-08 null von
  neun**, EK hat in 4 von 11 Bein-Keys je eine Order gesendet (ORB 9,
  ou_modell 9, ctnl_continuation 2; `gold_asb`, `gold_silver`,
  `trend_pullback`, `btc_ema_cross`, `cls_practical`, `ctnl_reversal`,
  `orb_us30` noch nie). Der Engpass sitzt nicht in der Strategie und nicht in
  der Verbindung, sondern zwischen „Signal erkannt" und „Order liegt beim
  Broker".
  **Vier Befunde, die erst auf Bein-Ebene sichtbar wurden:**
  (a) **`cls_practical` ist auf EK faktisch tot** — 104 Scan-Fehler zwischen
  08-31 und 09-11, immer dieselbe Kette: Lake-Eintrag gilt als veraltet →
  Fallback auf Live-Dukascopy → Hang → 90-s-Timeout → Bein faellt aus. Noch nie
  eine Order.
  (b) **Das 35-Minuten-Frischefenster des Lake passt nicht zur 15-Minuten-
  Kadenz** — es verzeiht genau einen ausgefallenen Ingest-Lauf. Gezaehlt:
  774 Lake-Fallbacks bei EK, >1.400 bei Funded, 728 bei FK, **ausnahmslos**
  `LakeStaleDataError`, kein einziges „Datensatz fehlt". Der Ingest selbst ist
  gesund (585 von 587 Fast-Laeufen sauber beendet) — Ingest und Bridge setzen
  gemeinsam aus. Ergaenzt den Kurztakt-Task-Befund vom 2026-09-13 um die
  Auslegungsfrage dahinter.
  (c) **Der Risikodeckel-Fix vom 2026-09-10 wirkt nachweislich.** `orb_us30`
  wurde auf EK 213× von `risk_cap` weggeworfen; seit der Anhebung 8 % → 30 %
  **kein einziger Skip mehr** (letzter 09-09). Das Bein hatte seitdem nur kein
  Signal — es ist nicht mehr blockiert.
  (d) **EKs `config.py` widerspricht dem eigenen Log.** Der Kommentar zu
  `CAPITAL_WEIGHT = 1/8` begruendet die Kapitalscheibe mit „OU-Modell zaehlt
  mit (eigenes echtes Konto, **keine Order hier**)" — die Bridge hat 9
  OU-Orders gesendet (D, FAST, SPG, SYY, AXP, ADI, EXPE, APD, AMGN), nachdem
  `OU-Modell-MT5-Bridge` deaktiviert wurde. Nur ein Kommentar, aber er traegt
  die Herleitung einer Risikokonstante. In DASHBOARD.md als Aufraeumpunkt.
  **Die Paper-Spalte ist der eigentliche blinde Fleck:** fuer zwei der drei
  Portfolios gibt es keinen laufenden Zwilling (EK Task Disabled seit 08-31,
  Challenge nie angelegt — `challenge_portfolio/paper_bot.py` hat als
  Simulation nie einen Trade gemacht, wird aber zur Laufzeit von der
  Echtgeld-Bridge importiert). Der einzige echte Vergleich, FK, geht
  auseinander: Paper 98.981,60 (−1,02 %, 24 Trades) gegen Live 100.159,75
  (+0,16 %, 0 Trades) — das Live-Plus kommt daher, dass nichts ausgefuehrt
  wurde, sagt also nichts ueber die Strategie.
  **Ueberschneidung mit den Parallel-Session-Eintraegen vom 2026-09-13**
  (Wochenauswertung + Funded-Bein-Audit) bewusst nicht doppelt gefuehrt: der
  `10016`-Befund, die ORB-Quote 2/24 und die Lake-Fallback-Zaehlung stehen
  dort, hier nur die Bein-Aufschluesselung und die Auslegungsfrage zum
  Frischefenster. Der IQ-`ou_modell`-Befund (0/7) war beim Schreiben bereits
  behoben (`excluded_legs` + `capital_weight=1/3`) und ist entsprechend als
  erledigt notiert.

- **2026-09-13** [EK-Portfolio-Bridge] **MT5-Passwort geaendert -- Bridge war
  zwischenzeitlich nicht login-faehig, wieder behoben und verifiziert.** Der
  Nutzer hat das Tickmill-Passwort zurueckgesetzt; `config.py::MT5_PASSWORD`
  enthielt danach den alten Wert. Symptom beim Verbindungsversuch:
  `login() fehlgeschlagen: (-6, 'Terminal: Authorization failed')` -- das
  Terminal selbst lief weiter (manuelle Sitzung), aber jeder programmatische
  `initialize()+login()`-Pfad waere gescheitert, also JEDER geplante Lauf aller
  9 Beine auf echtem Geld. Nutzer hat den neuen Wert selbst eingetragen
  (bewusst nicht ueber den Assistenten, damit das Passwort in keinem
  Gespraechsverlauf steht). **Verifiziert 2026-09-13:** Login mit dem
  Config-Wert erfolgreich, Konto 55918977 / TickmillEU-Live, Equity 3.351,63
  EUR, AutoTrading aktiv, 15 offene Positionen.
  Merkposten: ein Passwortwechsel beim Broker legt still ALLE Bridges des
  betroffenen Kontos lahm -- der Fehler taucht erst im naechsten geplanten Lauf
  auf, nicht beim Wechsel selbst.

- **2026-09-13** [Funded-Portfolio-Bridge / Challenge Portfolio] **IQ-Konto
  faehrt ab jetzt 5 statt 6 Beine, dafuer mit doppeltem Kapitalanteil
  (1/6 → 1/3).** Ausloeser: Nutzerinfo, dass IQ Markets/BeyondIQCapital
  **gar keine Einzelaktien** anbietet — das `ou_modell`-Bein handelt aber
  genau die. Der Live-Beleg lag schon vor (Dashboard-Befund vom selben Tag):
  0 von 7 OU-Signalen platziert, 48x `kein Live-Kurs fuer ou_modell (AMGN)`,
  Symbole per `symbol_select` waehlbar aber ask/bid dauerhaft 0. Das Konto
  fuhr damit seit Go-Live faktisch nur 5 Beine — aber mit dem Kapitalanteil
  von 6, ein Sechstel des Risikobudgets lag dauerhaft brach.
  **Umsetzung:** `AccountConfig` hat zwei neue Felder, `excluded_legs` und
  `capital_weight` (Defaults erhalten das bisherige Verhalten exakt). Nur der
  IQ-Eintrag setzt `excluded_legs=("ou_modell",)` und `capital_weight=1/3`.
  `run_once.py::_process_leg()` — die einzige Sizing-Stelle der Bridge, die
  5-Minuten-Fast-Lane ruft dieselbe Funktion — nutzt jetzt
  `account.capital_weight` statt des globalen `pb.CAPITAL_WEIGHT` und
  blockiert ausgeschlossene Beine ueber `entries_allowed`. **Bewusst ueber
  `entries_allowed` und nicht per frueherem `return`:** ein ausgeschlossenes
  Bein darf keine neuen Entries oeffnen, bereits offene Positionen muessen
  weiter ganz normal ueber den Re-Scan schliessen koennen (gleiche Logik wie
  beim Kill-Switch). Auf IQ ist aktuell keine OU-Position offen.
  **`challenge_portfolio/paper_bot.py` wurde NICHT angefasst** — die Datei
  wird von allen drei Konten live importiert, jede Aenderung dort haette auch
  die TTP-Konten getroffen. Sie bleibt reiner Signalgeber mit Default 1/6.
  **Zahlenbasis** (neues `scripts/research_challenge_iq_no_ou.py`, Monte Carlo
  3000 Pfade ueber das IQ-Regelwerk, CLS auf dem seit 09-10 gefahrenen
  1,0-%-Stand; Ergebnis in
  `portfolio_construction/results/challenge_portfolio_iq_no_ou.json`):
  Ist-Zustand 5 Beine @1/6 → CAGR 10,7 %, MaxDD 2,2 %, p_breach 0,000, Ziel in
  184 Tagen; **jetzt 5 Beine @1/3 → CAGR 22,3 %, MaxDD 4,4 %, p_breach 0,005,
  Ziel in 90 Tagen**. Vier Stufen (1/5, 1/4, 1/3,5, 1/3) wurden vorgelegt, der
  Nutzer hat bewusst die risikofreudigste gewaehlt. Der Puffer zur 6-%-IQ-
  Grenze ist damit real kleiner als vorher — bewusst gekauft.
  **Verifiziert** (ohne MT5-Verbindung, kein manueller Live-Lauf): Import- und
  Syntaxtest beider Bridge-Module; Risikotabelle je Konto gegen beide Deckel —
  IQ groesstes Einzelrisiko Gold ASB 0,667 % (1-%-Positionsdeckel haelt),
  Worst Case aller gleichzeitig offenen Beine 2,48 % gegen den seit heute
  aktiven 3,0-%-Aggregatdeckel; beide TTP-Konten unveraendert bei 1,41 %/3,5 %.
  Offen bis zum naechsten planmaessigen Lauf: die Live-Gegenprobe, dass die
  IQ-Lotgroesse fuer ein und dasselbe Signal **exakt doppelt** so gross ist wie
  die TTP-Lotgroesse.
  Geaendert: `Funded-Portfolio-Bridge/{config.py,run_once.py,run_once_fast.py,
  README.md}` (ausserhalb des Repos, nicht git-getrackt) sowie im Repo
  `scripts/research_challenge_iq_no_ou.py` (neu) +
  `portfolio_construction/results/challenge_portfolio_iq_no_ou.json` (neu).
  Commit `bc72053` (2026-09-14) -- der Commit enthaelt zusaetzlich die
  CHANGELOG/DASHBOARD-Aenderungen der parallelen Sessions vom 09-13
  (EK-MT5-Passwort, Wochenauswertung, Bein-Audit), die zu diesem Zeitpunkt
  noch uncommitted im Arbeitsverzeichnis lagen.

- **2026-09-13** [Second Brain / Alle 3 Live-Bridges] **Wochenauswertung
  2026-09-07 bis 09-13, CLS im Dashboard abgeschlossen, drei offene Rueckfragen
  mit NEIN entschieden.** Nutzerauftrag nach mehreren Tagen Abwesenheit. Reine
  Auswertung + Second-Brain-Pflege, **kein Code geaendert**. Lief parallel zur
  Bein-Audit-Session (Eintrag direkt darunter); doppelte Befunde wurden
  zusammengefuehrt, nicht zweimal gefuehrt.
  **(1) Dashboard von CLS befreit** (Nutzerauftrag "saeubere das Dashboard von
  allen CLS Tasks und halte nur die Beobachtung und Entscheidung des Beins
  fest"): entfernt wurden der erledigte Risiko-Anpassungs-Punkt, der
  Ideen-Inbox-Punkt "Gegen das Signal"-Check (am 2026-09-11 als R-Detektor
  gebaut, also erledigt), zwei erledigte CLS-Zeilen aus der Erledigt-Liste und
  die Aufgabe zu den 12 veralteten `cls_practical/results/`-CSVs; die
  Kostenmessungs-Annahmen wurden auf ihr Ergebnis eingekuerzt.
  **Die CSV-Aufgabe ist NICHT geloest, nur nicht mehr im Dashboard** -- sie ist
  vollstaendig nach `projects/cls-practical-kostenvalidierung.md` (neuer
  Abschnitt "Abschluss und verbleibende Punkte") verschoben, damit sie nicht
  verlorengeht. Im Dashboard bleibt als einziger CLS-Punkt die Bewaehrung des
  Beins (Abbruchkriterium + Calmar-Vergleich der anderen fuenf Beine).
  **(2) Drei Rueckfragen mit NEIN abgehakt** (Nutzerentscheid, bewusst ohne
  weitere Pruefung): Tickmill-Kosten per Vorwaerts-Sampling messen -> nein
  (Folge, bewusst akzeptiert: EK-Zahlen bleiben auf der geschaetzten
  0,50-Pips-Annahme und sind nicht mit den gemessenen Challenge-Zahlen
  vergleichbar); Sim-Risikodeckel des OU-Beins gegen die echten Positionen
  rechnen -> nein (die zwei Phantom-Positionen laufen am 09-16/09-17 selbst
  aus, das Muster kann aber wiederkommen); alte EK-ORB-Trades rueckwirkend
  auswerten -> nein.
  **(3) Drei neue Befunde aus Logs und State-Dateien:**
  (a) **Saemtliche Scan-Fehler der Woche haben eine gemeinsame, nicht-fachliche
  Ursache.** In zwei Fenstern am 2026-09-11 (00:14-02:29 und 13:16-14:38)
  schwiegen EKs 2-Minuten-Lane und `DataLake-Ingest-Fast`/`-Fast5` gemeinsam,
  der Lake lief trocken, alle drei Bridges fielen auf Live-dukascopy zurueck und
  liefen dort in den bekannten `'>' not supported between 'str' and 'float'`-Bug
  plus Timeouts. Belegt ueber die Stundenverteilung: Funded-Fast hatte 21/72/45
  Scan-Fehler in den Stunden 00/01/02 und 9/69 in 13/14 -- **null in allen
  uebrigen Stunden**, gleiches Muster bei FK. Der Ingest kam um 14:38:36 mit
  einem Lauf ausserhalb des Rasters zurueck (Nachhol-Lauf des Task Schedulers).
  Damit ist der am 2026-09-09 als Einzelfall bewusst liegengelassene
  Kurztakt-Task-Ausfall zum vierten Mal aufgetreten (vorher 09-07 Fast5 ~45 Min.
  und 09-10 EK-Fast 11:12-11:27) und im DASHBOARD auf Prioritaet Hoch
  hochgezogen, verknuepft mit dem Lake-Fallback-Punkt der Audit-Session.
  (b) **FK: der erste echte ORB-Entry ueber den neuen MT5-Pfad wurde vom Broker
  abgelehnt** -- 2026-09-11 16:03:08, SPX500.gbe, 25,3 Lots @ 7672,0,
  SL 7667,066270640961, `retcode=10016 "Invalid stops"`. Der Datenpfad trug, die
  Order-Ebene nicht. Zwei ungepruefte Kandidaten: SL nicht auf Tickgroesse
  gerundet (12 Dezimalstellen) oder Stopabstand (4,93 Punkte = 0,064 %) unter
  dem Broker-Mindestabstand; eine `symbol_info`-Abfrage (`digits`,
  `trade_stops_level`) klaert beides, braucht aber ein laufendes Terminal.
  EKs vorhandene Schutzpruefung greift nicht -- sie prueft nur die Seite von
  SL/TP, nicht Rundung und nicht Mindestabstand. **Folge fuer die Planung:
  Phase 2 (ORB-MT5-Pfad auf Funded) wartet nicht mehr auf Beobachtung, sondern
  auf diesen Fix.**
  (c) **FK: zwei Echtgeld-Entries am 2026-09-09 starben still an
  `order_send()=None`** (`10:30 cls_practical`, `17:20 ctnl_continuation`). Das
  SL-Sicherheitsnetz war es nicht (dessen Log-Zeile fehlt). Verdacht:
  `run_once.py:484` kappt den Order-Kommentar auf 31 Zeichen, das bekannte
  Broker-Limit liegt bei 16 -- `FKIF cls_practical` (18) und
  `FKIF ctnl_continuation` (22) scheiterten, `FKIF orb_sp500` (14) kam bis zu
  einem echten Retcode durch. Falls das stimmt, koennen die am 2026-09-09
  freigeschalteten Beine (gold_asb, cls_practical, ctnl_continuation,
  ctnl_reversal) auf FK derzeit ueberhaupt nicht einsteigen. Beweisbar beim
  naechsten Versuch: die `last_error()`-Ausgabe ist seit 2026-09-09 im Code,
  sie fehlte nur zum Zeitpunkt dieser beiden Fehlschlaege.
  **Handelsbilanz der Woche** (zur Einordnung, aus den Logs): Funded nahm 3x
  cls_practical am 09-09 (alle ausgestoppt, P/L -582,40 / -408,96 / -371,60),
  3x ctnl_continuation am 09-09 (alle ausgestoppt am 09-10, -266,00 / -243,97 /
  -268,77) und 4 ou_modell-Entries (AMGN 09-08 und 09-11, APD 09-11, laufen
  noch). FK: kein einziger erfolgreicher Live-Entry -- 3 Versuche, alle
  abgelehnt. EK: kein einziger Entry, Equity-Baseline trotzdem von 3.460,62 auf
  3.313,61 EUR gefallen (-4,3 %), kommt aus den vorher eroeffneten
  OU-Positionen. ORB-Trefferquote siehe den zusammengefuehrten DASHBOARD-Punkt
  der Audit-Session (2 von 24 auf Funded, 0 von 6 auf FK).

- **2026-09-13** [Funded-Portfolio-Bridge] **Bein-Audit gegen den Paper-Bot +
  die zwei offenen Risiko-Punkte nachgeholt.** Nutzerauftrag.
  **Statischer Abgleich -- sauber:** die Bridge importiert Scan-Funktionen,
  Risikokonstanten (`pb.CAPITAL_WEIGHT`, `pb.LEG_RISK_PCT`) UND die
  ORB-Exit-Config (`pb.ORB_EXIT_CFG_BY_INSTRUMENT`) zur Laufzeit aus
  `challenge_portfolio/paper_bot.py`; sie dupliziert nichts und kann deshalb
  strukturell nicht abdriften (im Gegensatz zu EK). Von den 6 Beinen hat nur
  `cls_practical` ueberhaupt einen Risiko-Modifikator.
  **Fix 1 -- Rates-Multiplikator erreicht jetzt das Live-Sizing.** Er wirkte
  bisher nur im Paper-Bot (engine.py: `day_risk_amount = risk_amount *
  risk_multiplier.get(day, 1.0)`) und auf das reportete `r_multiple`; die
  Bridge sizte flach. Jetzt gibt `_scan_cls_practical()` ihn als Spalte
  `risk_multiplier` aus (keine Duplikation der Berechnung), `_process_leg()`
  wendet ihn PRO TRADE an -- tagesabhaengig, ein Bein kann Trades mehrerer Tage
  in einem Lauf liefern. **Kritischer Fund dabei:** der Faktor ist ein
  VERSTAERKER, kein Daempfer (Median 1,75, Max 3,06, 53 % der Trades != 1,0).
  Die erste Implementierung multiplizierte NACH dem 1-%-Einzeltrade-Deckel --
  ein Faktor 3,06 haette daraus stillschweigend 3,06 % gemacht und die harte
  Nutzerregel vom 2026-09-01 ausgehebelt. Korrigiert: Multiplikator auf das
  ungedeckelte Risiko, Deckel zuletzt. Live-Wirkung: $165 -> bis $505 je Trade
  (0,17 % -> 0,51 % der Equity), Deckel bindet nicht.
  **Fix 2 -- aggregierter Offenes-Risiko-Kill-Switch**, baugleich zu
  `FKInstantFunding-MT5-Bridge` (Nutzerauftrag 2026-09-07, dort eingebaut, hier
  nicht). Deckel NICHT von FKIF uebernommen (fix 5 %), sondern an die
  Anbieter-Regel gebunden: Haelfte des jeweiligen Drawdown-Caps, also TTP 3,5 %,
  IQ 3,0 % -- bei 6-7 % Gesamt-Cap waeren 5 % fast der ganze Puffer. Stoppt NUR
  neue Entries; Exits und Positionsverwaltung laufen weiter.
  **Verifiziert:** `py_compile` + echter Import beider Lanes gegen gestubbtes
  MT5; 7 Offline-Testfaelle fuer das Gate (Normalbetrieb, knapp drunter/drueber
  an der Schwelle, Breakeven-Stop, Position ohne SL, beim Broker bereits
  geschlossene Position); Multiplikator gegen echte Lake-Daten gegengeprueft.
  `bridge_risk_audit.py` meldet fuer alle drei Live-Bridges jetzt **0 Befunde**.
  **Drei operative Befunde aus dem Audit** (nicht angefasst, in DASHBOARD.md):
  ORB platziert auf Funded nur 2 von 24 Signalen (Re-Simulation loest den Trade
  auf, bevor der erste Scan ihn sieht -- trifft systematisch die schnellen
  Verlierer); OU-Modell platziert auf dem IQ-Konto 0 von 7 (Einzelaktien
  liefern dort keinen Tick); der Data Lake faellt sehr haeufig auf Live-Fetch
  zurueck (SP500_M15 281x, EURUSD_M5 264x).

- **2026-09-13** [Scheduling / alle Bridges] **Wochenend-Pause eingerichtet:
  alle handelsbezogenen Tasks laufen nur noch Mo-Fr, Sa/So ist der PC still**
  (Nutzerauftrag -- Markt hat zu, es gibt ohnehin keine neuen Daten). Sieben
  Tasks hatten 7-Tage-Trigger (`TimeTrigger` ohne Wochentags-Einschraenkung):
  `EK-Portfolio-Bridge-Fast` (alle 2 Min, rund um die Uhr -- allein ~1.440
  Leerlaeufe pro Wochenende), `FKInstantFunding-MT5-Bridge`,
  `FK-Instant-Funding-Paper`, `DataLake-Ingest-Fast/-Fast5/-Slow`,
  `Bridge-Watchdog`. Drei weitere standen zwar auf Mo-Fr, ihre Wiederholung
  lief aber mit `P1D` noch Minuten in den Samstag hinein
  (`Funded-Portfolio-Bridge` bis Sa 00:13, `Funded-Portfolio-Bridge-Fast` und
  `FKInstantFunding-MT5-Bridge-Fast` bis Sa 00:03) -- Dauer auf Tagesende
  gekappt. Umgesetzt ueber das neue, git-getrackte
  `scripts/weekend_pause.ps1` (`-Verify` / `-Apply` / `-Revert`, legt vor jedem
  Apply XML-Backups nach `scripts/task_backups/` ab). Es haelt den Soll-Zustand
  deklarativ fest, damit ein spaeter neu angelegter Task nicht still wieder auf
  7 Tage zurueckfaellt. **Kritisch dabei:** die mm:ss-Versaetze der alten
  Trigger wurden 1:1 uebernommen (Ingest laeuft weiterhin ~70 s vor dem
  Bridge-Scan, siehe Fund 2026-09-09 Task-Offsets). Verifiziert: alle 11 Tasks
  zeigen `NextRunTime = Mo 2026-09-14`, seit dem Umstellen um 14:21 Uhr startet
  heute (Sonntag) kein Prozess mehr. Commit `56d36f7`.
  **Weiter aktiv am Wochenende** (Nutzerentscheid): `Forex-Weekly-Report`
  (So 18:00) und `Dashboard-Telegram-Digest` (taeglich 08:00) -- beide ohne
  MT5-/Marktdatenbezug. BTC-Tasks unangetastet.
  Bewusst in Kauf genommen: So 23:00-24:00 (erste Handelsstunde, duennste
  Liquiditaet) wird nicht mehr gehandelt, Start ist Mo 00:00.

- **2026-09-13** [Bridge-Watchdog] **Wochenend-/Montags-Karenz, sonst haette die
  neue Pause jedes Wochenende Fehlalarme ausgeloest.** `config.py`:
  `FKInstantFunding-MT5-Bridge` stand als einzige Bridge auf
  `weekdays_only=False` (weil ihr Task als einziger 7 Tage lief) -> `True`.
  `watchdog.py`: neue Hilfsfunktion `_in_weekend_pause()` ersetzt die beiden
  `now.weekday() >= 5`-Abfragen und deckt zusaetzlich **Montag vor 01:00** ab --
  der Watchdog feuert Mo 00:01:23, die erste Bridge erst 00:03; ohne Karenz
  waere der Log in diesem Moment ~24 h alt und jeder Montag begaenne mit einem
  Fehlalarm plus "laeuft wieder normal"-Nachzuegler. Getestet ueber sechs
  Zeitpunkte (Fr 23:59 / Sa / So / Mo 00:01 / Mo 01:01 / Di) sowie einen
  Snapshot-Lauf: alle drei Bridges melden heute korrekt
  `not_expected_today`, keine Telegram-Nachricht. Die Watchdog-Dateien liegen
  ausserhalb des Repos und sind NICHT git-getrackt (Skript + Doku: Commit
  `56d36f7`).

- **2026-09-11** [Second Brain / Bridges] **Audit-Punkt geschlossen: 5 Bridges
  als stillgelegt markiert, Probe meldet nur noch 1 echten Befund (9 -> 1).**
  Nutzerentscheid: die alten Ein-Strategie-Bridges (BTC-EMA-Cross,
  CLS-Practical, CTNL-Edge, GoldASB, OU-Modell) werden NICHT reaktiviert --
  jede Alt-Strategie bekommt stattdessen ein eigenes optimiertes Bein in den
  neuen Portfolio-Bridges. Ihre Befunde (tick_value-Sizing, fehlende
  Kill-Switches) sind damit gegenstandslos. Als `RETIRED_BRIDGES` in
  `bridge_risk_audit.py` hinterlegt statt nur im Dashboard abgehakt -- sonst
  meldet die Probe bei jedem Lauf dieselben 7 Befunde, die niemand mehr
  abarbeitet, und wird dadurch wertlos. Wird eine Bridge doch reaktiviert:
  Zeile entfernen, dann greift die volle Pruefung wieder.
  **Beim Aufraeumen NICHT mit weggeraeumt** (steht als eigener
  Dashboard-Punkt): `Funded-Portfolio-Bridge` fehlt der aggregierte
  Offenes-Risiko-Kill-Switch, den `FKInstantFunding-MT5-Bridge` am 2026-09-07
  auf Nutzerauftrag bekommen hat (`_aggregate_open_risk_dollars()` + Deckel
  gegen zu viele gleichzeitig offene Positionen). Beide sind LIVE-Prop-Bridges;
  moeglicherweise galt der Auftrag damals beiden und ist nur bei einer
  gelandet. Funded hat Einzeltrade-Cap (1 %), 20-%-Margin-Deckel und
  Trailing-DD-Kill-Switch, aber keine vorausschauende Summengrenze.

- **2026-09-11** [EK-Portfolio-Bridge] **cls_practical auf absoluten Signal-SL
  + R-Detektor umgestellt (Nutzerauftrag) -- alle drei Bridges fahren jetzt
  dieselbe Logik.** `legs/cls_practical/signal_source.py` liefert zusaetzlich
  `sl_price`/`tp_price` (vorher nur Distanzen); `run_once.py::_check_cls_practical()`
  nutzt diese absoluten Preise statt sie am Live-Kurs neu zu verankern, und
  bekommt denselben `MAX_CONSUMED_R_FOR_ENTRY = 0.50`-Detektor wie die anderen
  beiden Bridges -- der mit dem absoluten SL erst noetig wird, weil
  core/bracket_executor.py die Lots dann als Risiko / |Live-Kurs - SL| rechnet.
  Gilt NUR fuer cls_practical; die uebrigen Beine dieser Bridge setzen ihre
  Stops weiterhin relativ zum Fuellpreis und koennen sich nicht aufblaehen.
  Erwartete Wirkung (gemessen auf denselben Signalen, EK-Risiko, 0,50 Pips):
  PF 1,42 -> **1,85**, Ø R 0,25 -> **0,42**, Sharpe 0,65 -> **1,02**,
  MaxDD -5,57 % -> **-4,20 %**, Calmar 0,48 -> **0,93**; maximaler Hebel steigt
  dafuer von 11,0x auf 15,5x (vom Detektor bei 2x Aufblaehung gedeckelt).
  Verifiziert: importiert sauber, und die neue consumed_r-Rechnung blockt den
  realen 2026-09-09-Fall (0,61R) korrekt.
  **Wichtige Einordnung der EK-Zahlen (Nutzerfrage "warum sieht EK so viel
  besser aus?"):** Der Unterschied zu den Challenge-Zahlen ist FAST
  VOLLSTAENDIG die Kostenannahme, nicht die Strategie. Isoliert gemessen, selbe
  Signale, selber Code-Pfad: Ø R 0,357 bei 0,50 Pips gegen 0,179 bei 2,05 Pips
  -- Faktor 2,0, bei identischer Trefferquote (49,7 %) und Trade-Zahl (147).
  EK wurde mit 0,50 Pips gerechnet (**Annahme**, Tickmill ist nicht belastbar
  gemessen), die Challenge mit 2,05 Pips (**gemessen**). Das Risiko-Delta
  (0,55 % gegen 0,1667 %) erklaert zusaetzlich die CAGR-Differenz, beruehrt
  aber PF/Ø R nicht. **EKs Zahlen sind also nicht besser, sondern optimistischer
  angesetzt** -- genau der Fehlertyp, gegen den diese ganze Untersuchung
  angetreten ist. Tickmills Kosten muessen gemessen werden, bevor die EK-Zahlen
  belastbar sind.

- **2026-09-11** [Alle 3 Live-Bridges] **Neue SL-/Sizing-Logik auf alle
  Bridges portiert -- und dabei gefunden, dass sie NICHT dieselbe Schwachstelle
  haben.** Portiert (Herleitung siehe Eintraege 2026-09-09/10):
  | Bridge | Scan | SL-Behandlung | Pip-Boden | R-Detektor | Margin-Deckel |
  |---|---|---|---|---|---|
  | Funded (3 Konten) | `challenge_portfolio` | absoluter Signal-SL | 5 Pips | 0,50R | 20 % |
  | FK Instant Funding | `challenge_portfolio` | absoluter Signal-SL | (geerbt) | 0,50R neu | 20 % neu |
  | EK Portfolio | `ek_portfolio` | am Live-Kurs neu verankert | 5 Pips neu | bewusst KEINER | 80 % neu |
  **Drei Befunde beim Portieren:**
  (1) **FK hatte den Pip-Boden schon** -- es zieht seinen CLS-Scan aus
  `challenge_portfolio/paper_bot.py`, die Aenderung vom 2026-09-10 wirkte dort
  sofort mit. EK hat einen eigenen Scan (`ek_portfolio/paper_bot.py`) und
  brauchte ihn separat.
  (2) **EK kann die Hebel-Aufblaehung strukturell nicht bekommen.**
  `run_once.py::_check_cls_practical()` rechnet `stop_price = entry_price_now -
  direction * sl_distance`, verankert SL und TP also am Live-Kurs neu -- der
  Risiko-Abstand ist immer exakt `sl_distance`. Ein R-Detektor waere dort
  wirkungslos und wurde bewusst nicht eingebaut.
  (3) **Der 20-%-Margin-Deckel passt nicht auf EK.** Gemessen 2026-09-11:
  eine normale CLS-Position mit 5-Pip-Mindeststop braucht auf den Funded-Konten
  **7,7 %** der Equity an Margin, auf EK **42,6 %** (Equity ~3.343 EUR,
  Tickmill 1:30, 0,55 %/Trade aus der Kalibrierung vom 2026-09-10). 20 % haette
  diese Kalibrierung stillschweigend halbiert -> auf EK **80 %**, das bindet im
  Normalbetrieb nie. **Hinweis fuer den Nutzer:** bei 8 Beinen und 1:30 koennen
  zwei bis drei gleichzeitig offene Positionen EKs Margin ausreizen -- Folge der
  Kalibrierung, keine Fehlfunktion, aber ein Deckel richtet dort wenig aus.
  **Neuer Befund mit Entscheidungsbedarf:** EKs Neu-Verankern ist kein
  Gratis-Vorteil, sondern kostet Ergebnis. Auf denselben Signalen, EK-Risiko,
  0,50 Pips Kosten (`scripts/research_cls_practical_ek_reanchored.py`):
  neu verankert PF 1,42 / Ø R 0,25 / Sharpe 0,65 / MaxDD -5,57 % / Calmar 0,48
  gegen absoluter SL + R-Detektor PF **1,85** / Ø R **0,42** / Sharpe **1,02** /
  MaxDD **-4,20 %** / Calmar **0,93**. Die Alternative ist auf jeder Kennzahl
  besser ausser dem maximalen Hebel (15,5x statt 11,0x). Ursache: der neu
  verankerte Stop sitzt nicht mehr am strukturellen Invalidierungspunkt --
  dieselbe Ursache, aus der der volatilitaetsbasierte Stop in der SL-Studie
  scheiterte. **Nicht umgestellt** -- Architekturaenderung an einer
  Echtgeld-Bridge, Entscheidung liegt beim Nutzer (steht im `DASHBOARD.md`).
  Verifiziert: alle fuenf geaenderten Module kompilieren und importieren,
  Konstanten gesetzt (Funded/FK R-Detektor 0.50 + Deckel 0.20, EK Deckel 0.80).

- **2026-09-11** [Alle Live-Bridges / Second Brain] **Sizing-Logik der uebrigen
  Live-Bridges geprueft: kein Handlungsbedarf -- EK war der Ausreisser, und der
  Grund ist strukturell.** Nutzerauftrag war, den EK-Fix von gestern auf die
  anderen Live-Bridges zu uebertragen. Die Pruefung ergab, dass das nicht noetig
  ist: live sind nur `Funded-Portfolio-Bridge` und
  `FKInstantFunding-MT5-Bridge` (alle uebrigen Tasks Disabled), und beide haben
  Kapitalverduennung, Einzeltrade-Cap und Kill-Switch bereits -- Funded
  zusaetzlich einen Margin-Deckel (20 %), FKIF zusaetzlich die
  Mindestlot-Anhebung. **Der strukturelle Unterschied:** beide importieren ihren
  Paper-Bot zur Laufzeit (`import challenge_portfolio.paper_bot as pb` bzw.
  `fk_instant_funding.paper_bot`) und lesen `pb.CAPITAL_WEIGHT *
  pb.LEG_RISK_PCT[leg] * equity` direkt -- sie KOENNEN nicht abdriften. EK
  dupliziert die Werte in seine eigene `config.py` (5 Treffer gegen 0 bei den
  anderen beiden), und genau diese Kopie ist abgedriftet. Bewusst NICHT
  uebernommen: die Mindestlot-Anhebung bei Funded -- sie hat dort noch nie
  gegriffen (0 Treffer "unter volume_min" in allen Logs, 100k-Konten haben das
  Problem nicht), und auf einem Prop-Konto waere ein ueber das Zielrisiko
  angehobener Trade ein Regelverstoss-Risiko ohne Gegenwert.
  **Dabei eigene Drift gefunden und behoben:** die gestrige EK-Neukalibrierung
  setzte nur die Bridge auf die 2,20x-Werte, `ek_portfolio/paper_bot.py` blieb
  auf den alten -- 6 von 8 Beinen wichen ab. Paper-Bot nachgezogen
  (Nutzerentscheid), inkl. `ou_modell` und der vollstaendigen Herleitung als
  Kommentar; verifiziert: 0 Abweichungen.
  **Probe erweitert:** `bridge_risk_audit.py` vergleicht jetzt duplizierte
  Bridge-Risikowerte automatisch gegen den zugehoerigen Paper-Bot
  (`_paper_bot_drift()`), Bridges mit Laufzeit-Import werden uebersprungen.
  Die Pruefung wurde gegenprobiert (EK absichtlich auf einen fremden Paper-Bot
  gezeigt -> Drift wird gemeldet), damit sie nicht nur zufaellig "OK" sagt.
  EK und FKIF laufen jetzt ohne Befund durch.

- **2026-09-11** [Reporting] **Morgen-Digest von 4 Telegram-Nachrichten auf 1
  gekuerzt + Health-Zeilen aus den echten Logs ergaenzt.** Nutzerfeedback:
  "ich habe heute morgen 4 Seiten Dashboard bekommen, das ist viel zu viel".
  Gemessen: 16.066 Zeichen = 4 Nachrichten. Ursache war NICHT die Anzahl der
  offenen Punkte, sondern dass `dashboard_digest.py` jeden Punkt im VOLLTEXT
  ausschuettete -- die ausfuehrlichen Eintraege vom 2026-09-09/10 (inkl.
  Markdown-Tabellen) schlugen dadurch voll durch. Fix: neue `_item_title()`
  reduziert jeden Punkt auf EINE Zeile (erster `**Fettdruck**` = Titel, das ist
  die bestehende Dashboard-Konvention; Klammer-Zusaetze und Ueberlaenge werden
  gekappt). Der Digest haengt damit strukturell nicht mehr an der Laenge eines
  Eintrags. Es werden weiterhin ALLE offenen Punkte gezeigt (Nutzerentscheid:
  volle Lage auf einen Blick statt Top-3-Auswahl).
  Zusaetzlich neue `_health_lines()`: Scan-/Order-Fehler des Tages aus der
  EK-State-DB (read-only) und aktuelles offenes Risiko gegen den Deckel aus dem
  juengsten Log -- also der ECHTE Betriebszustand, nicht nur das, was im
  Dashboard steht. Genau diese Zeile haette den 4h haengenden CTNL-Exit vom
  2026-09-09 am naechsten Morgen sichtbar gemacht. Beide Health-Bloecke sind
  einzeln in try/except gekapselt; fehlt Bridge/DB/Log, entfaellt die Zeile.
  **Ergebnis: 16.066 -> 1.580 Zeichen, 4 -> 1 Nachricht** (Trockenlauf ohne
  Versand verifiziert). Nebenbei: Stand-Datum in DASHBOARD.md nachgefuehrt.

- **2026-09-11** [cls_practical / Funded-Portfolio-Bridge] **Umbau umgesetzt:
  Pip-Boden, R-Detektor und Margin-Deckel scharf; Risiko des Beins gesenkt.**
  Nach der Realkosten-/Ausfuehrungs-Probe (siehe Eintraege 2026-09-09/10)
  implementiert:
  (1) `challenge_portfolio/paper_bot.py`: `min_sl_pips=5` im CLS-Scan
  (Setups mit engerem strukturellem Stop werden VERWORFEN, nicht aufgeweitet)
  und `LEG_RISK_PCT["cls_practical"]` **0.015 -> 0.010** (Risiko je Trade
  0,25 % -> **0,1667 %**, auf 100k also $166,67). Gesenkt statt erhoeht, weil
  das Bein bei 0,25 % allein 2,81 % Drawdown zog -- 40 % des TTP-Budgets von
  7 %, als EINES von sechs Beinen, fuer 1,07 % CAGR bei Calmar 0,38.
  Alle uebrigen Beine unveraendert, `MAX_POSITION_RISK_PCT` unveraendert.
  (2) `Funded-Portfolio-Bridge/run_once.py`: R-Detektor
  `MAX_CONSUMED_R_FOR_ENTRY = 0.50` nach dem Restlaufzeit-Gate, plus
  bein-uebergreifender Helfer `_signal_sl_distance()`. ou_modell ausgenommen
  (Tagessignal, eigener Kurs-Waechter).
  (3) `Funded-Portfolio-Bridge/sizing.py`: harter Margin-Deckel
  `MAX_MARGIN_PCT_OF_EQUITY = 0.20`, gerechnet ueber `mt5.order_calc_margin()`
  statt selbstgebauter Nominalwerte (nur MT5 kennt Kontraktgroesse/Hebel je
  Symbol korrekt -- dieselbe Begruendung wie bei `order_calc_profit()`).
  Greift unabhaengig davon, WODURCH eine Groesse zustande kam; die
  20,8-Lot-Position vom 2026-09-09 waere daran gescheitert.
  **Zwei Korrekturen an eigenen frueheren Aussagen dieser Untersuchung:**
  (a) Der R-Detektor haette den Trade vom 2026-09-09 **NICHT** geblockt. Aus
  den echten Orderdaten nachgerechnet waren 0,61-0,67R gegen das Signal
  aufgebraucht, nicht die in der Ideen-Inbox genannten 0,76R (andere
  Referenzpreis-/sl_distance-Annahme). Geblockt haette ihn der **Pip-Boden**
  (3,6 < 5 Pips). Die beiden Massnahmen greifen in verschiedenen Faellen.
  (b) Schwelle **0,50R statt 0,75R**: bei 0,75R ist der Detektor beim REALEN
  Ausfuehrungsversatz wirkungslos -- er blockt nichts, was das
  Restlaufzeit-Gate nicht ohnehin blockt (1,00R bis 0,60R liefern identische
  142 Trades / PF 1,43). Erst ab 0,50R greift er. Zweck ist die
  **Hebel-Schranke** (2x statt 4x), nicht die Rendite.
  Verifiziert: Scan-Pfad liefert seit 2026-08-01 nur noch Signale ab 8,9 Pips
  Stopdistanz (die Signale vom 09-05 mit 2,9 und 09-09 mit 3,6 Pips fallen
  jetzt raus), beide Bridge-Module importieren sauber, Engine-Defaults
  unveraendert (Regressionslauf: 207 Trades, identische PnL).

- **2026-09-10** [EK-Portfolio-Bridge] **Kapitalverduennung scharf geschaltet,
  Mindestlot-Sizing, Portfolio-Kill-Switch und Risiko-Neukalibrierung auf 40 %
  Ziel-Drawdown.** `CAPITAL_WEIGHT = 1/8` war seit Einrichtung definiert und im
  config-Docstring als Formel festgeschrieben, wurde aber NIRGENDS angewendet --
  jedes Bein handelte ~8x groesser als validiert. **Backtest-Beleg**
  (Rekonstruktion von `ek_v2_realistic_final.json` aus
  `portfolio_construction/results/legs/`): mit Verduennung -16,1 % Max-Drawdown,
  ohne -73,7 %. Die Methodik wurde ZUERST gegen das repo-eigene Szenario
  `ek_flat1pct_comparison.json::flat_1pct` verifiziert (w=1/7 ergibt
  12,55 %/-5,34 % gegen publizierte 11,41 %/-5,50 %; ohne Verduennung
  116,86 %/-32,63 %) -- die Verduennungsformel IST die Backtest-Logik.
  **Reihenfolge bewusst** (Kill-Switch VOR der Deckel-Lockerung): (1)
  `core/state_store.py` Tabelle `eod_equity`; (2)
  `core/risk.py::check_trailing_dd()` portiert aus `ek_portfolio/paper_bot.py` --
  der heutige Equity-Wert geht bewusst NICHT in den Hoechststand ein, sonst zoege
  jeder der ~100 Laeufe/Tag den Floor an ein Intraday-Hoch (der im paper_bot
  dokumentierte Bug); (3) `entries_allowed()` als Gate an den 6 Entry-Punkten
  statt auf Bein-Ebene -- Exits und Positionsverwaltung laufen dadurch
  STRUKTURELL immer weiter, auch bei gerissener Grenze; (4) `core/sizing.py`:
  neue `calc_lot_size_detailed()` mit Verduennung + Anhebung aufs
  Broker-Mindestlot (Muster 1:1 aus `FKInstantFunding-MT5-Bridge/sizing.py`) +
  hartem Einzeltrade-Cap 3 %; die alte `calc_lot_size()` bleibt als
  float-Wrapper, damit der Code zwischen den Edits durchgehend lauffaehig war
  (die Bridge laeuft alle 2 Min.); (5) Config zuletzt.
  **Risiko-Kalibrierung** (Nutzerauftrag "40 % DD ausreizen, CAGR optimieren"):
  freie Optimierung VERWORFEN -- sie liefert CAGR 531 % bei Risikostufen bis
  58 %, aber Monte Carlo zerlegt sie (P(MaxDD>40 %) = 32,8 %, 5 %-Worst-Case
  -55,5 %). Stattdessen die MC-validierte Studien-Allokation relativ
  unveraendert gelassen und gleichmaessig mit **Faktor 2,20** hochskaliert:
  CAGR 227,8 %, hist. MaxDD -38,1 %, MC-Median -26,1 %, P(MaxDD>40 %) = 7,8 %
  (die Studie tolerierte 10,3 % bei ihrem 20 %-Ziel). `MAX_TOTAL_RISK_PCT`
  0.08 -> 0.30, neu `MAX_SINGLE_TRADE_RISK_PCT = 0.03` und
  `TRAILING_DD_PCT = 0.45`. **45 % statt der 20 % vom 2026-08-27**: ein
  20-%-Kill-Switch auf einem Portfolio mit -26 % MC-Median-Drawdown wuerde im
  NORMALBETRIEB ausloesen. Trotz aggressiverem Ziel liegt das effektive Risiko
  je Trade UNTER dem bisherigen Live-Zustand (Gold ASB 2,93 % statt 8,0 %).
  Deckel-Auslastung bei allen 6 Kernbeinen gleichzeitig offen: 11,6 % von 30 %.
  **Verifiziert:** `py_compile` + echter Import aller Module gegen gestubbtes
  MT5 (findet fehlende Namen, die py_compile nicht sieht); Offline-Test
  `calc_lot_size_detailed()` mit 5 Faellen (Verduennung exakt 1/8, Anhebung,
  3-%-Cap-Ablehnung, Aktien-Mindestlot, Wrapper-Rueckgabetyp); Offline-Test
  `check_trailing_dd()` inkl. der Kernbedingung "heutiger Wert zieht den Floor
  NICHT hoch", Testzeilen wieder entfernt. Parallel lief eine zweite Session am
  Bar-Fenster-Bug derselben Bridge -- Koexistenz geprueft, beide Aenderungssaetze
  intakt, alle 13 Module importieren sauber.

- **2026-09-10** [Second Brain / alle Bridges] **Standardprozess
  "Paper-Bot -> Live-Bridge" + automatisierte Probe angelegt** (Nutzerauftrag
  nach dem EK-Fund: "damit sowas in Zukunft nicht mehr vorkommt").
  `knowledge/areas/paper-bot-zu-live-bridge.md`: Regel (eine Bridge ist
  Uebertragung, keine Neuimplementierung), 8-Punkte-Checkliste mit
  Zeilenbeleg-Pflicht statt "ist sinngemaess drin", und die real passierten
  Fallstricke. `knowledge/scripts/bridge_risk_audit.py` prueft alle 8 Bridges
  rein statisch (AST, kein Import, keine MT5-Verbindung) auf tote
  Risikokonstanten (die EK-Signatur), fehlende Kill-Switches, fehlende
  Risikodeckel und die manuelle `trade_tick_value`-Sizing-Formel.
  **Erster Lauf: 9 Befunde**, wichtigster: `CLS-Practical-Bridge` und
  `OU-Modell-MT5-Bridge` sizen ueber `trade_tick_value` statt
  `order_calc_profit()` -- dieselbe Formel, die am 2026-08-06 um Faktor 8,6
  danebenlag (beide Bridges aktuell Disabled). Zwei Fehlalarme der ersten
  Fassung wurden vor der Uebergabe behoben und im Skript dokumentiert
  (Funded-Kill-Switch: deutsche Schreibweise mit Bindestrich; EKs
  `ORB_COMBINED_RISK_PCT`: Ableitungskette innerhalb config.py). Triage in
  DASHBOARD.md.

- **2026-09-10** [EK-Portfolio-Bridge] **Bar-Fenster-Bug behoben — er betraf
  ALLE DREI MT5-Beine, nicht nur ORB.** Nutzerauftrag ("Baue den Zeitversatz auf
  allen Konten so um, dass alles vernuenftig funktioniert"). `fetch_recent_mt5()`
  existierte dreimal als eigene Kopie (`legs/ny_open_orb`, `legs/gold_silver`,
  `legs/trend_pullback`) -- jeweils mit derselben kaputten Fensterlogik
  (`date_to = utcnow()` naiv). `legs/gold_asb` war nie betroffen, es laeuft
  ueber den Lake-Weg.
  Neu: **`core/mt5_bars.py`** (`recent_range()` / `copy_rates_recent()`) als
  gemeinsamer Helfer -- bewusst dorthin, damit sich derselbe Fehler nicht ein
  viertes Mal einschleicht; die Index-Umrechnung bleibt bei den Beinen, weil
  ORB nach America/New_York und die anderen beiden nach UTC rechnen. `date_to`
  liegt jetzt 12h in der Zukunft (MT5 kappt selbst auf Vorhandenes), `date_from`
  bleibt an der echten Jetzt-Zeit verankert. Bewusst keine exakt gerechnete
  Offset-Konstante: der Abstand Rechner/Server verschiebt sich mit jeder
  DST-Umstellung und waere die naechste stille Fehlerquelle.
  **Verifiziert** an den echten Funktionen (`verify_bar_window_fix.py`,
  read-only, 12:18): ORB M5 und M15 liefern Bars, die **3,4 Minuten** alt sind
  (vorher ~300), Gold-Silber H4 78 Min., Trend-Pullback H1 18 Min. -- alles im
  normalen Bereich des jeweiligen Timeframes. Der Fast-Lauf um 12:18:12 mit dem
  gefixten Code lief fehlerfrei durch.
  **Nicht aufgearbeitet:** EK hat wochenlang auf 5 Std. alten Bars gehandelt.
  Die bisherigen ORB-/Gold-Silber-/Trend-Pullback-Trades dieser Bridge sind
  unter falschen Voraussetzungen entstanden und taugen nicht als
  Leistungsnachweis -- Entscheidung ueber eine rueckwirkende Auswertung liegt
  beim Nutzer (DASHBOARD).
- **2026-09-10** [cls_practical] **SL-/TP-Varianten durchgetestet: der
  absolute Pip-Boden ist der einzige belastbare Hebel — TP-Änderungen und
  Break-even-Nachziehen fallen durch.** Neu:
  `scripts/research_cls_practical_sl_optimization.py` und
  `scripts/research_cls_practical_tp_variants.py`. Dafür `cls_practical/engine.py`
  um `min_sl_pips`, `sl_floor_mode` und `session_sl_mult` erweitert —
  **Defaults reproduzieren das bisherige Verhalten exakt** (Regressionslauf:
  207 Trades, identische PnL mit/ohne explizite No-Op-Parameter), wichtig weil
  der Live-Bot die Datei über `challenge_portfolio/paper_bot.py` direkt
  importiert. Keine Verhaltensänderung am laufenden Bot.
  **Gewinner: `min_sl_pips=5` im Modus "drop"** (Trade verwerfen, nicht Stop
  aufweiten). Unter TTP-Kosten: PF 1,11 → **1,52**, Ø R 0,09 → **0,34**,
  In-Sample dreht von −0,06 auf **+0,28**, MaxDD **7,34 % → 3,10 %** (damit
  wieder unter der 7-%-TTP-Grenze), max. Hebel 10,0 → 5,0. Kostet 27 % der
  Trades (207 → 152). Plateau von 4–6 mit Abfall ab 7, kein Einzelspike;
  Faustformel Boden ≈ 2,5 × Round-Trip-Kosten. Auf IQ-Kosten gegengeprüft
  (PF 1,70).
  **Verworfen:** Stop aufweiten statt verwerfen (PF 0,97–1,09 — das ADR-Ziel
  bleibt stehen, R:R kollabiert); volatilitätsgemittelter fester Stop
  (bestenfalls Baseline-Niveau, bei ×1,0 Ø R −0,47 — er wirft das strukturelle
  SL-Niveau weg, und genau das trägt den Edge); höheres ATR-Multiple (hilft,
  aber schwächer und teurer an Trades); **fester 2R-TP** (PF 1,14 vs. 1,52 —
  liegt in der Senke einer U-Form über 1R–4R); **Break-even-Nachziehen**
  (durchgehend schädlich, schneidet die tragenden Gewinner ab).
  **Ein weiteres ADR-Ziel (`adr_mult=0.75`, PF 1,64) wurde nach Prüfung
  ebenfalls verworfen:** das Optimum lag am Gitterrand, nach Erweiterung auf
  0,6–1,5 ist die Fläche zackig und nicht-monoton, und der Bootstrap (10.000
  Resamples) zeigt fast vollständig überlappende Konfidenzintervalle — die
  Trefferquote fällt von 48 % auf 23 %, die Unsicherheit wächst
  proportional zum Punktschätzer. **Belastbar ist dagegen der Boden selbst:
  P(Ø R < 0) fällt von 26,6 % auf 1,2 %.**
  Fazit: SL-Boden ändern, TP unangetastet lassen. Auswertung in
  `knowledge/projects/cls-practical-kostenvalidierung.md` (Befunde 5+6), CSVs
  in `cls_practical/results/`. Noch **nicht** scharfgestellt — Entscheidung
  liegt beim Nutzer.

- **2026-09-10** [EK-Portfolio-Bridge / Second Brain] **Der Bar-Fenster-Bug ist
  auf EKs Terminal bestaetigt — und er ist groesser als gestern notiert: 5
  Stunden, nicht 2.** `probe_orb_bar_window.py` (read-only) um 11:29 im freien
  Fenster nach einem beendeten Lauf ausgefuehrt, alle 3 ORB-Symbole identisch:
  `date_to = UTC now` -> letzter Bar **07:25** Serverzeit, mit `+12h` ->
  **12:25** (echte Serverzeit 12:29, Bars dazwischen lueckenlos). Mechanik
  damit geklaert: MT5 liest die naive Zeit als LOKALE Rechnerzeit (Berlin,
  UTC+2) und vergleicht gegen server-gestempelte Bars (UTC+3) -- Verlust
  2+3=5 Std. Erklaert beide Messungen exakt (FK 20:07 -> 18:05, EK 09:29 ->
  07:25). Bedeutung fuer EK: NY-Open ist 16:30 Serverzeit, die Opening Range
  wird fruehestens gegen 21:30 sichtbar -- rund 5 Std. zu spaet und kurz vor
  Session-Ende (23:00). **EKs Live-Code bewusst NICHT angefasst** (aendert das
  Verhalten eines Echtgeld-Beins im laufenden Betrieb), Freigabe steht aus,
  siehe DASHBOARD. Nebenbefund: EKs 2-Minuten-Fast-Lane hat am selben Vormittag
  sechs Laeufe ausgelassen (zwischen 11:14 und 11:27 gar keiner) -- gleiches
  Muster wie die bekannte DataLake-Ingest-Fast5-Luecke, nur vermerkt.

  **Neu: `knowledge/areas/bridge-infrastruktur-vergleich.md`** (Nutzerwunsch):
  Soll-Ist-Tabelle ueber alle drei Bridges (ORB-Datenquelle, Server-TZ-
  Behandlung, Hard-Timeouts, Retry-Werte, Lock-/Fehlerbehandlung, Kadenzen,
  Scan-Deduplizierung, Symbolnamen) plus die vier offenen Luecken. Kadenzen und
  Zeitlimits per `Get-ScheduledTask` gegengeprueft statt aus dem Gedaechtnis
  behauptet. Ausserdem im DASHBOARD der FK-Beobachtungsstand nach der
  ORB-Umstellung: null Fallback-Warnungen seit 2026-09-09 22:20, Fast-Laeufe
  ~8s -- der erste echte ORB-Entry ueber den neuen Pfad steht noch aus, und
  daran haengt Phase 2 (Funded).
- **2026-09-09** [cls_practical] **Phase-6-Kostenvalidierung abgeschlossen:
  bei echten Broker-Kosten bricht das CLS-Bein weitgehend zusammen — und der
  Schaden sitzt vollständig in den engen Stops.** Neu:
  `scripts/research_cls_practical_broker_cost_validation.py` und
  `scripts/research_cls_practical_entry_lag.py`. 206 Trades, 2018-12 bis
  2026-09, `risk_pct=0,25 %` (das real gehandelte Risiko).
  **Breakeven bei ~2,70 Pips Round-Trip.** TTP zahlt gemessene 2,05 Pips —
  nur 0,65 Pips Luft: PF fällt 1,57 → **1,12**, Ø R 0,36 → **0,10**, das
  In-Sample wird **negativ** (PF 0,94), **5 von 8 Jahren negativ**, und der
  MaxDD steigt 3,88 % → **7,34 % — über die eigene 7-%-Gesamtdrawdown-Grenze
  der TTP-Challenge**. Auf IQ Markets (1,30 Pips) bleibt PF 1,29 / Ø R 0,21.
  **Ursache lokalisiert:** Trades mit Stop < 6,15 Pips (42,2 % aller Trades)
  haben Ø R **−0,238**, die übrigen **+0,343**. Ein absoluter Pip-Floor von
  ~6 Pips würde Ø R auf TTP von 0,10 auf 0,343 heben. Der bestehende Schutz
  `min_sl_atr_mult = 1.0 × ATR(M5)` greift nicht, weil er relativ ist und in
  ruhigen Phasen mitschrumpft (2026-09-09: 3,6-Pip-Stop durchgelassen).
  **Entry-Lag als Hebel-Mechanik quantifiziert:** der Backtest steigt zum
  Schlusskurs der Signalbar ein, der Live-Bot beim nächsten 5-Min-Scan, der
  Stop bleibt aber auf dem absoluten Signalpreis — und `sizing.py` rechnet
  `risk_dollars / |Live-Kurs − SL|`. Im Median harmlos (Abstand wächst sogar
  auf 9,5 Pips, Lots schrumpfen aufs 0,74-fache), im Tail nicht: bei 10 Min.
  Lag kommen **13,1 % der Signale mit weniger Abstand zum Stop an, als der
  Round-Trip kostet**, 4,9 % sind schon hinter dem Stop, und **29,1 % erzeugen
  über 5x Equity an Nominal**. Der Trade vom 2026-09-09 war damit kein
  Ausreißer, sondern ein regelmäßig wiederkehrender Fall.
  Auswertung: `knowledge/projects/cls-practical-kostenvalidierung.md`,
  CSVs in `cls_practical/results/`. Weiterhin **keine** Änderung an
  Bridge-Code, Config oder Scheduled Tasks — die Risiko-Entscheidung liegt
  beim Nutzer.

- **2026-09-09** [FK Instant Funding] **NY-Open ORB holt seine Bars jetzt direkt
  aus MT5 statt aus dukascopy/Lake — plus ein dabei gefundener Bug, der auch
  EK-Portfolio-Bridge betrifft.** Nutzerauftrag, nachdem aufgefallen war, dass
  EK diese Datenbeschaffung laengst hat und die beiden anderen Bridges nicht.

  **Phase 0 (Probe, `FKInstantFunding-MT5-Bridge/probe_orb_mt5.py`, read-only):**
  vier Unbekannte am echten Terminal geklaert. Server-Zeitzone = **UTC+3**
  (= Europe/Helsinki, identisch zu Tickmill/EK); 24/7-Verifikationssymbol
  `BTCUSD.gbe` vorhanden; **M15-Historie 499 Tage / ~32.250 Bars** bei allen 3
  Symbolen (reicht fuer regime.ema_trend_bias()'s 200-Tage-Ribbon); M5 ueber 40
  Tage sauber, M5 ueber 500 Tage scheitert mit exakt `Invalid params` --
  bestaetigt EKs empirischen Fund vom 2026-08-28 punktgenau.

  **Dabei gefunden — abgeschnittenes Abfragefenster:** `copy_rates_range()`
  vergleicht `date_to` gegen SERVER-gestempelte Bar-Zeiten. Uebergibt man dort
  eine naive UTC-Zeit (genau das tut EKs `fetch_recent_mt5()`), endet das Fenster
  rund **fuenf Stunden vor dem neuesten verfuegbaren Bar** (am 2026-09-10 auf
  5 Std. praezisiert -- die zunaechst notierten "zwei Stunden" waren falsch
  abgelesen). Mechanik: MT5 interpretiert die naive Zeit als LOKALE Rechnerzeit
  (Berlin, UTC+2) und vergleicht sie gegen server-gestempelte Bars (UTC+3) --
  Verlust = 2+3 = 5 Std. Erklaert beide Messungen exakt (FK 20:07 -> 18:05,
  EK 09:29 -> 07:25). Nachgewiesen am selben
  Symbol/derselben Sekunde: `date_to = UTC now` -> letzter Bar 18:05 Serverzeit,
  `date_to = UTC now + 12h` -> letzter Bar 23:05, Bars dazwischen lueckenlos
  vorhanden. Fuer ORB waere das fatal (die Balken direkt nach 09:30 NY fehlen).
  Hier von vornherein richtig gebaut (`_FUTURE_PAD`, MT5 kappt selbst auf das
  Vorhandene). **EK ist nach Codelage genauso betroffen, aber noch NICHT
  geprueft** -- Diagnoseskript `EK-Portfolio-Bridge/probe_orb_bar_window.py`
  liegt bereit, siehe DASHBOARD "Braucht deine Bestaetigung".

  **Umsetzung:** neues `FKInstantFunding-MT5-Bridge/orb_mt5_source.py`
  (`fetch_m5`/`fetch_m15` signaturkompatibel zu `ny_open_orb/data.py` und
  `data_lake/reader.py`, `_to_ny_index()` + `verify_server_offset()` nach EKs
  Muster, eigenes `config.SERVER_TZ_NAME`). Im Repo bekam
  `fk_instant_funding/paper_bot.py::_scan_orb()` optionale Parameter
  `fetch_m5_override`/`fetch_m15_override` -- bewusst KEIN weiterer
  `source="mt5"`-String, weil die broker-spezifische Symbol-/Zeitzonen-
  Behandlung in die Bridge gehoert, nicht ins Repo. Ohne Override aendert sich
  nichts. `run_once.py` bekam `scan_orb_mt5_first()` (MT5 zuerst, bei JEDEM
  Fehler stiller Rueckfall auf den bisherigen Lake-Weg -- nie schlechter als
  vorher), `run_once_fast.py` scannt ORB jetzt erst NACH `executor.connect()`
  (vorher lief der Scan vor dem Verbindungsaufbau, was mit MT5-Bars nicht geht).

  **Verifiziert** (`compare_orb_sources.py`, read-only): Entry-Preise beider
  Quellen weichen um <0,03% ab, alle Richtungen identisch, NASDAQ 10/10 gleiche
  Entry-Tage. Die einzigen Abweichungen liegen im Juli, also vor der bewusst
  gesetzten 40-Tage-M5-Grenze -- kein Datenfehler, fuers Live-Trading (nur die
  heutige Session zaehlt) irrelevant. Erster echter Lauf um 22:23 lief in 7s
  sauber durch, ohne die Fallback-Warnung. Funded-Portfolio-Bridge folgt in
  Phase 2 nach einem Beobachtungstag (Nutzerentscheid: erst FK, dann Funded;
  dort ein Referenz-Terminal fuer alle 3 Konten).
- **2026-09-09** [Alle 3 Portfolio-Bridges] **Restlaufzeit-Gate: Bridges
  entern kein nachweislich totes Signal mehr.** Die vorhandenen
  `MAX_SIGNAL_AGE`-Wächter messen nur das ALTER eines Signals, nicht dessen
  Restlaufzeit — ein Signal kann beim Entry-Versuch längst ausgestoppt sein
  und trotzdem „unauffällig jung" wirken. Ein engeres Alterslimit löst das
  prinzipiell nicht, weil die Bridge unter ~10 Min. Latenz strukturell nicht
  kommt (Bar muss schließen + Lake-Ingest + Scan-Raster). Neu: vor jedem Entry
  an den **echten Broker-M5-Bars** prüfen, ob der SL des Signals seit Schluss
  der Signal-Bar schon berührt wurde — Broker-Bars, nicht der Lake, denn der
  Lake ist ja gerade das, was hinterherhinkt. Fällt bei jedem Zweifel (kein
  Server-Offset, keine Bars, Kurslücke) auf „nicht blockieren" zurück und
  meldet den blinden Fleck, statt ein lebendes Signal zu verwerfen.
  **Umsetzung:** FK + Funded je `executor.py::signal_already_stopped()`,
  aufgerufen in `run_once.py::_process_leg()` vor `place_market_entry()`;
  EK neu `core/signal_liveness.py`, aufgerufen in 6 Bein-`signal_source.py`
  (`cls_practical`, `gold_asb`, `ny_open_orb`, `gold_silver`,
  `trend_pullback`, `ctnl_edge` — letzteres reicht `date`/`stop` jetzt durch,
  die bisher verworfen wurden). **Nicht abgedeckt** (bewusst): `ou_modell`
  (Funded + EK) und `btc_ema_cross` (EK) — reine Tagessignale ohne
  Intraday-Zeitstempel, ein M5-Berührungscheck wäre dort sinnlos; `ou_modell`
  hat mit `MAX_OU_MODELL_ENTRY_DEVIATION_PCT` bereits einen eigenen
  Kurs-Wächter. **Zeitzonen:** EK nutzt seine bestehende
  `config.SERVER_TZ_NAME`+`verify_server_offset()`-Mechanik weiter; FK/Funded
  messen den Server-Offset pro Aufruf aus `symbol_info_tick().time`, weil
  Funded drei Konten über ZWEI Broker fährt (TTPMarkets + BeyondIQCapital) und
  eine einzelne Konstante dort falsch wäre. Verifiziert: FK-Broker misst
  +3.00h (EEST, deckt sich mit EKs Tickmill-Befund), EKs Konvertierung inkl.
  DST-Wechsel per Gegenprobe geprüft; Gate feuert korrekt auf einem real
  ausgestoppten Signal und lässt ein lebendes durch.
  **Wichtige Einschränkung — dieser Gate hätte den CLS-Trade von heute NICHT
  verhindert** (siehe Eintrag „Erster Live-Trade des CLS-Beins" unten): auf dem
  Broker-Feed lag das 08:25-UTC-Low bei 1.16360 und damit 0,1 Pip ÜBER dem SL
  1.163590 — der Stop fiel erst 16 Sekunden nach dem Entry. Das Signal war zum
  Entry-Zeitpunkt also tatsächlich noch am Leben, der Gate verhält sich
  korrekt. Er adressiert den Fall „Erkennung landet ganze Bars nach dem Stop"
  (Lock-Timeout, ausgefallener Zyklus, Kill-Switch-Freigabe), nicht die
  Kosten-/Slippage-Ursache des heutigen Verlusts. Dateien außerhalb des Repos,
  kein Commit-Hash.

- **2026-09-09** [Scheduled Tasks] **Bridge-Tasks hinter den DataLake-Ingest
  gelegt statt davor — bis zu eine volle M15-Bar Latenz gespart.** Die
  Bridge-Tasks liefen jeweils *vor* dem zugehörigen Ingest und arbeiteten damit
  auf Daten, die fast einen ganzen Zyklus alt waren. Verschoben (nur
  `StartBoundary`, Intervalle unverändert): `FKInstantFunding-MT5-Bridge-Fast`
  und `Funded-Portfolio-Bridge-Fast` von ≡0 auf **≡3 mod 5** (Fast5-Ingest
  läuft ≡1 mod 5 @:50s, Dauer 4–24s); `Funded-Portfolio-Bridge` von ≡4 auf
  **≡13 mod 15**, `EK-Portfolio-Bridge` von ≡0 auf **≡14 mod 15**,
  `FKInstantFunding-MT5-Bridge` von stündlich :06:19 auf **:14:00** (15-Min-
  Ingest ≡10 mod 15 @:28s, Dauer bis 62s). Die 15-Min-Lanes waren der größere
  Hebel: ein Consumer um :00 sah als neueste M15-Bar die von :30 davor.
  `EK-Portfolio-Bridge-Fast` blieb unverändert (läuft alle 2 Min, lag schon
  ≤20s hinter dem Ingest). Unkritisch, weil `data_lake/storage.py` über
  `.tmp`+`.replace()` atomar schreibt — ein Consumer, der den Ingest überholt,
  liest alt-oder-neu, nie halb. Verifiziert: alle 6 Tasks Ready, Intervalle und
  Repetition-Duration erhalten, NextRunTime auf der erwarteten Minute.

- **2026-09-09** [Funded-Portfolio-Bridge / cls_practical] **Erster
  Live-Trade des CLS-Beins verlor auf drei Konten zusammen das 2,2-fache
  seines Risikobudgets — Ursache vermessen, Kostenmodell des Backtests
  widerlegt.** Signal 10:20 Berlin (EURUSD long, Entry 1.163967, SL
  1.163590, `sl_distance` 3,6 Pips). Entry live erst 10:30 (5-Min-Fast-Lane),
  Stop 16 Sekunden später — die Bridge bemerkte den Exit erst 10:34.
  Budget $741,20, realisiert **−$1.634,08** (Kursverlust −$1.362,96 plus
  Kommission −$271,12): TTP Konto 2 2,67x, IQ Markets 2,09x, TTP Konto 1
  1,85x. Positionsgrößen 18,58–22,72 Lots, auf TTP Konto 2 ~$2,42 Mio.
  Nominal auf $99.842 Equity (~24:1).
  **Gemessen** (neu: `scripts/measure_broker_spreads.py`, rein lesend über
  `copy_ticks_range`/`history_orders_get`/`history_deals_get`, Fenster
  08:00–12:30 Berlin, 30 Tage): der **Spread ist NICHT die Ursache** —
  TTP 0,30 Pips (346.627 Ticks), IQ 0,10 Pips (250.588 Ticks); der
  Engine-Default `spread_bps=0.3` liegt damit ungefähr richtig. Die
  tatsächlich fehlenden Blöcke sind **Slippage** (`slippage_bps=0.0`:
  real TTP 0,70 Pips Entry + 0,65 Exit, IQ 0,30 + 0,40) und **Kommission**
  (gar nicht modelliert: TTP $4,00/Lot, IQ $5,00/Lot Round-Trip). Gesamte
  Round-Trip-Kosten: **TTP ~2,05 Pips, IQ ~1,30 Pips**. Messwerte in
  `knowledge/resources/broker-kostenmodell-eurusd.md`, Rohdaten in
  `knowledge/_data/broker_spreads_eurusd.json`.
  **EK/Tickmill konnte NICHT belastbar gemessen werden** — die Tickhistorie
  des Terminals deckt das Handelsfenster mit 15 Ticks praktisch nicht ab,
  das M1-`spread`-Feld ist dort durchgehend 0. Gesichert ist nur:
  Kommission $0,00 über 331 Lots. Braucht Vorwärts-Sampling.
  Keine Änderung an Bridge-Code, Config oder Scheduled Tasks — reine
  Messung und Analyse; `cls_practical` läuft unverändert weiter
  (Nutzerentscheid: erst Kostenmodell validieren, dann Risiko anpassen).

- **2026-09-09** [EK-Portfolio-Bridge] **Bugfix: Live-Position (echtes Geld)
  konnte 4h lang nicht geschlossen werden — Order-Kommentar zu lang, exakt
  derselbe Bug wie am 2026-09-04, dessen Fix nur in EINEM Bein landete.**
  Aufgefallen beim Nachgehen einer Nutzerfrage zu einem Telegram-Screenshot.
  `ctnl_continuation`-Position Ticket 264958111 (XAUUSD 0.01 Lots, Entry
  17:15) versuchte ab 18:15 Uhr bei jedem 15-Min-Lauf den VWAP-Exit und
  scheiterte 16x in Folge, Log jedes Mal nur `Exit-Order fehlgeschlagen:
  None`. Ursache: Tickmill lehnt `mt5.order_send()` clientseitig ohne
  Retcode ab (`result=None`, `mt5.last_error()` = `(-2, 'Invalid "comment"
  argument')`), wenn der Kommentar zu lang ist. Exit-Kommentar hier
  `"EK-ctnl_continuation auto-vwap_target"` = 37 Zeichen. Der am 2026-09-04
  live bestätigte Fix (`[:16]`-Kappung + `deviation: 20` +
  `mt5.last_error()`-Logging, siehe Eintrag von damals) war ausschliesslich
  in `legs/ny_open_orb/executor.py` eingebaut worden — jedes Bein hat aber
  seine eigene `_close_position()` mit identischem Request-Muster.
  **Fix: alle drei Härtungen in den gemeinsamen Engpass
  `core/order_send.py::send_order()` gezogen**, durch den laut Modul-Vertrag
  ohnehin jede Order dieser Bridge laufen muss — greift damit für alle 11
  Beine gleichzeitig, auch für künftige. Verifiziert: `py_compile` sauber,
  und die auf 16 Zeichen gekappten Kommentare bleiben für alle 11 Beine
  kollisionsfrei unterscheidbar (geprüft). Kein Risiko für die
  Positions-Zuordnung: die Beine filtern ausschliesslich über `magic`,
  `pos.comment` wird nur in `core/safety.py` zur Anzeige gelesen.
  Gleiches ungefixtes Muster steckt in `legs/btc_ema_cross/executor.py:53`
  (32 Zeichen) — durch den zentralen Fix jetzt mit abgedeckt; die
  gleichnamige `BTC-EMA-Cross-Bridge` (eigener Ordner,
  `order_comment + " exit"` = 21 Zeichen) hätte denselben Bug, ihr
  Scheduled Task ist aber Disabled. Alle übrigen Bridges bauen kurze
  Kommentare (`Funded-Portfolio-Bridge` kappt selbst auf 31) und sind nicht
  betroffen.
  **LIVE BESTÄTIGT 22:15:09 Uhr** (Lauf `run_20260909_221502.log`, kein
  reiner py_compile-Stand): `core.order_send` loggte
  `Order-Kommentar von 38 auf 16 Zeichen gekappt
  ('EK-ctnl_continuation auto-stale_target' -> 'EK-ctnl_continua')`, direkt
  danach `[EK-CTNL-Cont] EXIT (stale_target) 0.01 Lots @ 4397.45` und
  `ctnl_continuation: {'status': 'closed', 'ticket': 264958111}`. Position
  nach 16 Fehlversuchen und 4h beim ersten Lauf mit dem Fix geschlossen.
  **Nachtrag zum Exit-Grund:** es war `stale_target`, nicht `vwap_target` —
  die VWAP-Referenz war abgelaufen (H4-Kontext), das Bein wollte also die
  ganze Zeit DEFENSIV raus, nicht ins Ziel. Dass die Position in den 4h
  Zwangs-Haltezeit von ~4384 auf 4397.45 ins Plus lief, war Glück, kein
  Systemverhalten.

- **2026-09-09** [EK-Portfolio-Bridge] **Täglicher Order-Abgleich im
  Tagesabschluss ergänzt (Nutzerentscheid), statt mehr Sofort-Alarme.**
  Anlass: derselbe Vorfall — nach der einen 18:15-Warnung kam vier Stunden
  nichts mehr, "ein einzelner Fehlversuch" war von "hängt seit Stunden"
  nicht zu unterscheiden. Die Einmal-pro-Tag-Dedup aus `already_notified()`
  (Nutzerwunsch 2026-09-08, weniger Lärm) bleibt bewusst unverändert.
  Neu: Tabelle `order_failures` in `core/state_store.py` +
  `record_order_failure()`/`get_order_failures_today()`, befüllt zentral aus
  `core/order_send.py::send_order()` — erfasst damit JEDES Bein (auch
  künftige) und auch die Ablehnungen des SL-Sicherheitsnetzes, nicht nur
  CTNL. Der Tagesabschluss listet jetzt je betroffener Position
  `Art · Symbol/Ticket · Anzahl · zuletzt`, ab 3 Fehlversuchen bei
  Exit/SL-TP mit `⛔ hängt`-Markierung (die ANZAHL ist der eigentliche
  Mehrwert gegenüber dem Einmal-Alarm). Die Buchführung ist in try/except
  gekapselt — sie darf den Order-Versand niemals zum Absturz bringen.
  Verifiziert: `py_compile` über alle vier geänderten Dateien, plus
  Roundtrip-Test gegen die echte SQLite (Mehrfach-Zählung korrekt,
  Testzeilen wieder entfernt). Greift erstmals beim Tagesabschluss am
  2026-09-10 — der heutige war um 22:00 bereits raus.

- **2026-09-09** [FK Instant Funding Bridge] **Bugfix: die ersten beiden
  echten Orders dieser Bridge sind nie beim Broker angekommen — Lot-Größe
  wurde als Dataclass statt als `float` in den MT5-Request gelegt.**
  `FKInstantFunding-MT5-Bridge/sizing.py::calc_lot_size()` liefert seit
  2026-08-28 ein `SizingResult`-Dataclass (`lots`/`actual_risk_dollars`/
  `bumped_to_minimum`), `executor.py::place_market_entry()` reichte dieses
  Objekt aber unverändert als `request["volume"]` durch. `mt5.order_send()`
  lehnt das als Invalid Params ab und gibt `None` zurück → Log nur
  "Markt-Entry fehlgeschlagen: None", Signal landet als `status:"missed"`,
  `ticket:null` im `bridge_state.json`. Aufgefallen erst heute, weil mit der
  LIVE_LEGS-Erweiterung (09:47, `gold_asb`/`cls_practical`/
  `ctnl_continuation`/`ctnl_reversal` dazu) überhaupt zum ersten Mal echte
  Orders losgehen sollten — der DRY_RUN-Pfad baut den Request gar nicht
  erst und konnte den Fehler nie zeigen. **Zwei Signale verloren:**
  `cls_practical` EURUSD long (10:30 Berlin) und `ctnl_continuation` XAUUSD
  long (17:20 Berlin). Fix: `lots = sizing.lots` vor dem Request-Bau;
  `actual_risk_dollars`/`bumped_to_minimum` werden jetzt zusätzlich in
  State + Telegram-Meldung geführt (tatsächliches statt nur Ziel-Risiko).
  Zusätzlich: bei `order_send()==None` wird jetzt `mt5.last_error()` + der
  Request geloggt statt bloß "None". Andere Bridges nicht betroffen —
  Funded-/EK-/GoldASB-/CTNL-Edge-/OU-/BTC-Bridge geben in `calc_lot_size()`
  weiterhin ein blankes `float` zurück (geprüft). Dateien liegen außerhalb
  des Repos, kein Commit-Hash.

- **2026-09-09** [FK Instant Funding Bridge] **Signal-Erkennung hinkt
  strukturell ~10 Min. hinter dem Signal-Zeitstempel her — Ursachenkette
  vermessen, noch nichts geändert.** M5-Bar-Label 10:20 → Bar schließt
  10:25 → `DataLake-Ingest-Fast5` schreibt zur Minute ≡1 mod 5 (:26:51) →
  `FKInstantFunding-MT5-Bridge-Fast` scannt zur Minute ≡0 mod 5 (:30:00).
  Die beiden Tasks stehen ~2 Min. gegeneinander versetzt: die Bridge läuft
  jeweils *vor* dem frischen Ingest. Bei `cls_practical` heute war die
  Erkennung (10:30) damit später als der Ausstieg des Trades selbst
  (Entry 10:20, Stop 10:25) — `MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY = 60` greift
  hier nicht, weil es das ALTER des Signals misst, nicht dessen Restlaufzeit.
  Vorschläge (Task-Offset, Restlaufzeit-Gate) unter "🔍 Braucht deine
  Bestätigung" in `DASHBOARD.md`, nicht eigenmächtig umgesetzt.

- **2026-09-09** [Research / Second Brain] **JPM "Cross Asset Momentum
  Spillover"-Paper durch den 8-Phasen-Prozess: beide verfolgten Workstreams
  negativ, ehrlich dokumentiert, nichts live verdrahtet.** Nutzerentscheid
  nach Screening: FX-only-Nachbau (neues Package `fx_momentum_spillover/`)
  + Cross-Check-Filter für Gold ASB, volles 42-Asset-Universum bewusst
  zurückgestellt (Ideen-Inbox). **Workstream A** (FX-only, 7 Majors, eigenes
  Ersatz-Momentum-Signal + rollierende L1-Logit-Spillover-Regression,
  eigene Portfolio-Engine): reproduziert die Paper-These nicht (Sharpe
  Individual -0.37, Spillover -0.13, Combination -0.30 statt Paper-Claim
  +0.66/+0.75/+0.74), konsistent negativ über IS/OOS + Monte-Carlo +
  Kosten-Sweep. Dabei ein echter Datenlücken-Fund (Dukascopy NZDUSD
  2003-2009 lückenhaft, USDJPY-Lücke 2010) und ein echter Konstruktions-
  Bug gefunden+behoben (Turnover/Return-Skalen-Asymmetrie ließ Kosten
  Tagesrenditen bis -420% erzeugen — behoben durch Gross-Exposure-
  Normalisierung). **Workstream B** (Gold ASB: die bei `cls_practical`
  validierte Rate-Momentum-Risk-Scaling-Mechanik zum ersten Mal auf Gold
  angewendet, NICHT die bereits verworfene Alignment-Gate-Variante):
  besteht den Structure-Preserving-Randomisierungstest nicht (p=0.665-0.670,
  Muster nicht von Zufall unterscheidbar) — reines Leverage-Artefakt.
  Details: `knowledge/projects/fx-momentum-spillover.md`,
  `knowledge/resources/cross-asset-momentum-spillover.md`,
  `knowledge/resources/fx-microstructure.md`.

- **2026-09-09** [Second Brain / Funded-Portfolio-Bridge / EK-Portfolio-Bridge]
  **5 offene Dashboard-Punkte durchgearbeitet, keine Code-Aenderung — reine
  Log-/Git-Recherche.** (1) Terminal-Check Funded-Portfolio-Bridge: IPC-
  Timeouts vom 09-08 waren auf das Fenster 09:52-12:24 Uhr begrenzt, seither
  durchgehend stabil; wahrscheinliche Ursache gefunden (Prozess-Restart des
  GoldFKBot-Terminals faellt zeitlich exakt mit der Erholung zusammen,
  `_terminal_running()` prueft nur Prozess-Existenz statt Health, alle 3
  Konten teilen sich einen MT5-IPC-Client pro Lauf). (2) EK-Portfolio-Bridge/
  ou_modell EXPE "Market closed": wahrscheinliche Ursache gefunden (Deviation-
  Check meldete kurz vorher `deviation=1.0`, passt zu fehlendem Live-Kurs;
  spaetere Order scheiterte mit echtem Broker-Retcode 10018, kein Verbindungs-
  fehler — spricht fuer symbolspezifischen Session-/Halt-Zustand bei
  Tickmill, nicht fuer einen Gate-Bug). (3) EK-Portfolio-Bridge Log-Fragment:
  geklaert, kein Bug — normaler Python-3.14-Traceback, ausgeloest durch den
  bekannten dukascopy-`_stream()`-Bug (Zeile 219/242) beim Versuch des am
  selben Tag (09-07) neu gebauten Live-Fallbacks. (4) Second-Brain-Lint:
  der Dashboard-Eintrag "lint.py/Skill fehlen im Repo" (09-07) war ein
  Fehlbefund — `git ls-files`/`git log` bestaetigen, beide Dateien wurden
  bereits am 2026-09-07 committet (`af96c0e`) und sind auf `origin/main`;
  Lint danach tatsaechlich gelaufen (erster echter Durchlauf seit 09-01):
  8 tote Wikilinks (1 falsch-positiv), 6 verwaiste Seiten, 0 veraltete
  Statustabellen-Daten, 14 unverarbeitete Clippings; ein neuer Cross-System-
  Link-Fall (Wikilink auf eine Claude-Memory-Datei) als offene Konventions-
  frage vermerkt. (5) `DataLake-Ingest-Fast5`-Luecke vom 09-07 auf
  Nutzerentscheid verworfen (einmaliger Ausreisser, seither nicht
  wiederholt). Details/vollstaendiger Wortlaut je Punkt: `DASHBOARD.md`.

- **2026-09-09** [FK Instant Funding / Funded-Portfolio-Bridge] **dukascopy-
  Hang entschaerft: Slow-Pfad-Retry von 6x/8s/90s auf 3x/3s/20s verkuerzt
  (Worst Case pro Bein ~9,7 Min. -> ~66s) + FKs unbehandelten Lock-Absturz
  behoben.** Ausgeloest durch die Nutzerfrage zu wiederkehrenden
  "NY-Open-ORB-Scan fehlgeschlagen: Aufruf haengt noch nach 90s"-Telegram-
  Meldungen, seit NY-Open ORB am 2026-09-08 live auf echtem Geld laeuft.
  Zwei unabhaengige Befunde:
  (1) `FKInstantFunding-MT5-Bridge/run_once.py::_run_scans()` und
  `Funded-Portfolio-Bridge/run_once.py::run_shared_scans()` riefen
  `pb._retry(fn)` ohne Override auf (Default 6 Versuche/8s/90s) -- ein
  haengendes Bein konnte damit ~9,7 Min. blockieren, WAEHREND der
  Cross-Prozess-Lock gehalten wird, also lange genug, um ein Live-ORB-Signal
  komplett zu verpassen (ORB resolved in 15-20 Min.) und den parallelen
  5-Minuten-Fast-Lauf reihenweise am Lock scheitern zu lassen. Beide
  Fast-Lanes nutzen dieselben engeren Werte (3/3s/20s) bereits seit
  2026-09-04 bzw. 09-08 produktiv -- jetzt auch im Slow-Pfad, keine neuen
  Zahlen erfunden.
  (2) `FKInstantFunding-MT5-Bridge/run_once_fast.py` (und `run_once.py`)
  hatten KEIN try/except um den `state_lock()`-Erwerb: haelt der jeweils
  andere Lauf den Lock, wirft `state_lock()` nach 45s `TimeoutError` -- bisher
  ein unbehandelter Traceback ohne verwertbare Log-Zeile und ohne Telegram,
  d.h. ein komplett verlorener 5-Minuten-Zyklus genau dann, wenn ein
  Live-Trade Ueberwachung braucht. Funded-Portfolio-Bridge faengt exakt
  diesen Fall seit jeher pro Konto ab (Beleg: die real geloggte Meldung
  "State-Lock fuer Konto ttp nach 45s nicht frei geworden ... dieser
  Kontolauf wird fuer diesen Zyklus uebersprungen"); FK hat nur EIN Konto
  und damit keine Account-Loop, in der das automatisch mitkam. Jetzt am
  jeweiligen Einsprungpunkt abgefangen (bewusst dort statt per Neu-
  Einrueckung von ~80 Zeilen Echtgeld-Code).
  Bewusst NICHT geaendert: `fk_instant_funding/paper_bot.py`s eigener
  Paper-Loop (dort laeuft `source="live"`, also ein echter dukascopy-
  Netzwerkabruf -- ein 20s-Timeout wuerde dort legitime, nur langsame
  Abrufe abwuergen und die Meldungen eher haeufiger machen; die Begruendung
  fuer die engeren Werte gilt nur fuer `source="lake"`, wo der Normalfall
  ein Millisekunden-Parquet-Read ist). Ebenfalls nicht angefasst:
  `data_lake/ingest.py` (bereits durch `ExecutionTimeLimit=4min` +
  `MultipleInstances=IgnoreNew` auf Task-Scheduler-Ebene gedeckelt) und
  `EK-Portfolio-Bridge` (hat mit `LEG_TIMEOUT_S=600` + MT5-nativem Fetching
  fuer zeitkritische Beine bereits staerkere Absicherungen).
  Verifiziert: `python -m py_compile` gegen alle 3 geaenderten Dateien,
  `_retry()`-Signatur in beiden genutzten paper_bot-Modulen gegengeprueft.
  Kein Live-Testlauf (DRY_RUN=False) -- Wirkung zeigt sich im naechsten
  regulaeren Scheduled-Task-Lauf, Logs danach gegenlesen.
- **2026-09-08** [FK Instant Funding] **5-Minuten-Fast-Task fuer NY-Open ORB
  (+ ctnl_continuation/cls_practical) live geschaltet — behebt, dass seit
  `DRY_RUN=False` noch KEINE echte ORB-Order gesendet wurde.** Root Cause
  (im Log bestaetigt): der stuendliche Lauf sah beide bisherigen echten
  ORB-Signale (07./08.09., NASDAQ) erst, nachdem sie laengst ihren Stop
  erreicht hatten (ORB kann in 15-20 Min. resolven) -- markierte sie nur als
  "missed" statt eine Order zu senden. Identisches Muster wie bei EK-
  Portfolio-Bridge/Funded-Portfolio-Bridge uebernommen: neues
  `FKInstantFunding-MT5-Bridge/run_once_fast.py` (+`run_task_fast.ps1`),
  `import run_once as slow` (keine Logik-Kopie), nutzt die bereits seit
  09-06 laufende `source="lake"`-"fast5"-Lane (kein neuer Ingest noetig).
  Scheduled Task `FKInstantFunding-MT5-Bridge-Fast` (alle 5 Min., Mo-Fr)
  bereits registriert und laeuft sauber (`LastTaskResult=0`) -- Registrierung
  + finaler Feinschliff parallel zu meiner Plan-Session entstanden, beim
  Gegenlesen uebernommen statt dupliziert (siehe Memory "External Bridge
  Files Have No Git Safety Net").
- **2026-09-08** [FK Instant Funding / Funded-Portfolio-Bridge / EK-Portfolio-
  Bridge] **Wiederholende Telegram-Fehlermeldungen auf 1x/Tag begrenzt**
  (Nutzerauftrag, Screenshot als Beleg: "kein Live-Kurs fuer ou_modell
  (AMGN)" kam bei Funded-Portfolio-Bridge 6x identisch alle paar Minuten).
  Root Cause ueberall gleich: ein Signal/eine Order wird als
  gescheitert/uebersprungen gemeldet, aber NICHT im State vermerkt -- der
  naechste Lauf haelt es deshalb wieder fuer neu und meldet identisch erneut.
  - `FKInstantFunding-MT5-Bridge/run_once.py` + `Funded-Portfolio-Bridge/
    run_once.py::_process_leg()`: "kein SL", "kein Live-Kurs" (ou_modell,
    nur Funded), Entry-Exception/"Entry fehlgeschlagen" schreiben jetzt vor
    dem `continue` denselben `state["positions"][key]={"status":"missed",...}`-
    Eintrag wie die 2 bereits korrekten Nachbar-Zweige ("Signal zu alt"/
    "Kurs zu weit entfernt"). Fuer die EXIT-Seite bewusst NICHT komplett
    stummgeschaltet (Position bleibt echt offen) -- neues
    `"exit_error_notified"`-Flag alarmiert einmalig, der Schliessversuch
    selbst laeuft jeden Lauf weiter. **Zusaetzlicher echter Bug dabei
    gefunden**: `result["status"]=="error"` von `executor.close_position()`
    (ein normaler Rueckgabewert, keine Exception) setzte die Position bisher
    trotzdem unconditional auf `"closed"`, obwohl sie auf dem Broker
    weiterhin offen war -- liess sie aus `_aggregate_open_risk_dollars()`
    verschwinden (FK) und verhinderte jeden weiteren Schliessversuch. Beide
    Bridges gleich behandelt: nur bei echtem Erfolg als `"closed"` markieren.
  - `EK-Portfolio-Bridge` (andere Architektur, kein `_process_leg()`):
    bestehenden Praezedenzfall verallgemeinert -- `core/state_store.py`s
    `already_notified_risk_cap_skip()`/`mark_risk_cap_skip_notified()`
    (2026-09-02 fuer genau dieses Problem gebaut, aber nur fuer den
    Risiko-Deckel-Fall) sind jetzt duenne Wrapper um neue generische
    `already_notified(category, key)`/`mark_notified(category, key)`
    (neue `notified`-Tabelle, additive Migration, `risk_cap_notified`
    bleibt als Alt-Historie liegen). Angewendet auf jede bisher ungeschuetzte
    "Order/Exit-Order fehlgeschlagen"-Meldung in
    `legs/{gold_asb,btc_ema_cross,ctnl_edge,ny_open_orb,ou_modell}/
    executor.py` (`category="order_failed"`, `key=<Bein/Symbol>`) --
    deckt u.a. das bereits im Dashboard dokumentierte EXPE-"Market
    closed"-Wiederholungsmuster ab. Zwei bereits nur-lokal-loggende Stellen
    in `ny_open_orb/executor.py` (Teilausstieg/Session-Ende-Fehlschlag)
    unangetastet gelassen -- die spammen Telegram schon heute nicht.
  - Verifiziert: alle geaenderten Dateien `py_compile`-sauber; neue
    `already_notified()`/`mark_notified()` isoliert gegen eine Temp-DB
    getestet (inkl. Rueckwaertskompatibilitaet der alten Wrapper-Funktionen);
    FKs `_process_leg()`-Fix mit einem synthetischen wiederholten "kein
    SL"-Signal verifiziert (1. Aufruf meldet, 2. Aufruf mit identischem
    Signal meldet nichts mehr).

---

- **2026-09-09** [FK Instant Funding] **Paper-Bot (`fk_instant_funding/
  paper_bot.py::scan_once()`) auf die 2 noch nicht live geschalteten Beine
  reduziert** (Nutzerauftrag, direkte Folge der `LIVE_LEGS`-Erweiterung
  oben): scannt jetzt nur noch `trend_pullback`/`gold_silver`, die 5
  Scan-Bloecke fuer gold_asb/cls_practical/ctnl_continuation/ctnl_reversal/
  orb (alle 3 Maerkte) entfernt -- die live Bridge sendet fuer diese 7
  Beine bereits eigene Telegram-Meldungen zum selben Signal, ein paralleler
  Paper-Scan haette nur doppelte Meldungen erzeugt. Scan-Funktionen selbst
  (`_scan_gold_asb` etc.) bleiben unveraendert im Modul, werden weiterhin von
  `FKInstantFunding-MT5-Bridge/run_once.py` (`import fk_instant_funding.
  paper_bot as pb`) fuer die echte Bridge gebraucht -- nur die Aufrufe
  INNERHALB von `scan_once()` entfernt. Historische Trades der 7 Beine
  bleiben im State (fuer Equity-/Kill-Switch-Historie unveraendert), es
  kommen nur keine neuen mehr dazu. CTNL-Standalone-Kill-Switch-Check
  bewusst NICHT entfernt (arbeitet ab jetzt nur noch auf eingefrorener
  historischer Ctnl-Historie, aber erzeugt dadurch selbst keine neuen
  Meldungen -- kein zusaetzlicher Spam, Entfernen war nicht Teil des
  Auftrags). `py_compile` sauber. Getrennt vom separat dokumentierten
  dukascopy-Hang-Retry-Punkt (siehe DASHBOARD "Braucht deine Bestätigung") --
  dort ging es um Fehlermeldungs-Spam bei Scan-Fehlern, hier um doppelte
  Signal-Meldungen wegen Ueberschneidung mit der live Bridge; falls die
  dortige Meldung von einem der jetzt entfernten Beine stammte, sollte sie
  nebenbei mit verschwinden, das ist aber nicht verifiziert.
- **2026-09-09** [FK Instant Funding] **`LIVE_LEGS` um gold_asb/cls_practical/
  ctnl_continuation/ctnl_reversal erweitert** (Nutzerentscheid, nach zwei
  weiteren sauberen `run_once_fast.py`-Laeufen -- einer davon ausserhalb der
  Spread-Stunden-Pause mit vollem Connect-Scan-Gates-Durchlauf, nur zufaellig
  kein neues Signal). `LIVE_LEGS` ist jetzt `{orb_sp500, orb_us30,
  orb_nasdaq, gold_asb, cls_practical, ctnl_continuation, ctnl_reversal}` --
  `trend_pullback`/`gold_silver` bleiben bewusst DRY_RUN (kuerzere
  Live-Historie). Explizites Spannungsverhaeltnis zur 09-07-"schrittweise,
  nur bewaehrte Beine"-Regel benannt und vom Nutzer nach Hinweis bestaetigt,
  kein stillschweigendes Uebergehen -- siehe Konversation. Noch offen: ein
  echter Entry ueber die neue Fast-Lane wurde bisher nicht beobachtet
  (reiner Zufall, kein neues Signal seit Registrierung); Order-Versand-Code
  ist aber identisch zu dem der bereits seit 09-08 lebenden ORB-Beine, kein
  neuer Codepfad. Bei Gelegenheit gegenlesen, ob Sizing/SL/Telegram-Meldung
  beim ersten echten Entry der 4 neuen Beine wie erwartet aussehen.
- **2026-09-08** [FK Instant Funding] **Fast/M5-Scan-Lane + Terminal-Restart-
  Fix nachgeruestet** (Nutzerauftrag, nach Vergleich der drei Portfolio-
  Bridges bei Scan-/M5-Timing: EK hatte eine eigene 2-Min-Fast-Bridge,
  Funded eine 5-Min-fast5-Lane, FK lief komplett auf der alten stuendlichen
  Kadenz -- trotz seit heute live laufender NY-Open-ORB-Beine). Scope in
  drei Rueckfragen praezisiert (kein `ou_modell`, kein Telegram-Vendoring,
  konkrete Beine-Liste fuer den spaeteren Live-Rollout). Neu:
  `run_once_fast.py` (5-Min-Trigger fuer ctnl_continuation/orb_sp500/
  orb_us30/orb_nasdaq/cls_practical, `import run_once as slow`-Reuse-Prinzip
  wie bei Funded, aber an FKs Einzelkonto-Struktur + 4 einzelne Risk-Gates
  angepasst statt 1:1 kopiert) + `run_task_fast.ps1` + Scheduled Task
  `FKInstantFunding-MT5-Bridge-Fast` (per XML-Export von
  `Funded-Portfolio-Bridge-Fast` registriert, identische Repetition/
  Settings). Keine neue Data-Lake-Ingestion noetig (`DataLake-Ingest-Fast5`
  deckt GOLD/SP500/US30/NASDAQ/EURUSD M5 bereits ab, geteilter Lake mit
  EK/Funded). Zusaetzlich `executor.py::_connect_once()` bekommt jetzt
  `_ensure_terminal_running()` bei JEDEM Connect-Versuch (identisches Muster
  zu Funded-Portfolio-Bridge/executor.py, 09-07 dort gebaut) statt nur einmal
  beim Bridge-Start in `run_once.py::main()` -- der dortige alte
  Alleinstand-Check + `import subprocess` entfernt (jetzt redundant).
  Manueller Smoke-Test von `run_once_fast.py` durch den Nutzer lief sauber
  (traf die 23:00-Spread-Stunden-Pause, kein Traceback). Voller Connect-
  Scan-Gates-Entry-Pfad noch nicht beobachtet (Pause-Fenster) -- siehe
  DASHBOARD.md "Als Naechstes" fuer den offenen Verifikationsschritt vor der
  geplanten `LIVE_LEGS`-Erweiterung (gold_asb/cls_practical/
  ctnl_continuation/ctnl_reversal zusaetzlich zu den 3 ORB-Beinen).
- **2026-09-08** [FK Instant Funding] **`DRY_RUN=False` gesetzt — NY-Open
  ORB (SP500/US30/NASDAQ) ist LIVE auf echtem Geld** (BeyondIQCapital,
  Konto 17764, IQIF100K-144048). Expliziter Nutzerauftrag ("Setze dry run
  False, damit ist orb jetzt live"), `FKInstantFunding-MT5-Bridge/config.py`
  geaendert. Alle anderen 6 Beine bleiben ueber `LIVE_LEGS` weiterhin nur
  geplant/geloggt (kein echter Order-Versand). Voraussetzungen erfuellt vor
  dem Flip: echter Order-Executor gebaut + 3x sauber gegen das echte Konto
  smoke-getestet, alle 4 Design-Entscheidungen vom Nutzer bestaetigt/
  nachgeschaerft (Rollout-Umfang, aggregierte Offene-Risiko-Kill-Switches
  zusaetzlich zum Trailing-DD-Check, Konsistenz-Ampel, Telegram-Kennzeichnung
  -- siehe CHANGELOG 2026-09-07). Naechster stuendlicher Scheduled-Task-Lauf
  kann dadurch echte Orders senden, falls ein ORB-Signal vorliegt.
- **2026-09-08** [Second Brain] **Git-Sync-Reparatur: lokal 38 vs. `origin/
  main` 2 Commits auseinandergelaufen, dadurch Bridge-Watchdog/Scanner-
  Snapshots seit 2026-09-07 17:01 nicht mehr auf GitHub sichtbar (siehe
  DASHBOARD.md-Korrektur unten) -- war KEIN echter Bot-/Rechner-Ausfall,
  nur ein Push-Problem.** Root Cause: die automatischen Commit-Skripte
  (Bridge-Watchdog, FK Instant Funding Snapshot, OU-Modell Scanner) pushen
  ohne vorher zu pullen/fetchen; sobald irgendeine andere Session (hier: ein
  paralleler Cloud-Agent) zwischenzeitlich auf `main` gepusht hatte, schlug
  jeder weitere lokale Push seither mit "fetch first" fehl -- nur als
  Warnung geloggt, nie eskaliert, daher unbemerkt ueber ~30h aufgelaufen.
  Bots liefen die ganze Zeit normal weiter (lokale Logs/Snapshots
  durchgehend aktuell), nur der GitHub-/Streamlit-sichtbare Stand war
  eingefroren. Beim naechsten Status-Check zusammengefuehrt (dieser Merge)
  und gepusht. Automatisierungs-Luecke (kein Pull-vor-Push) bleibt bestehen,
  noch nicht behoben -- siehe DASHBOARD.md.
- **2026-09-07** [Bridge Error Monitor] **`validate_ohlc_numeric()`-Cache-Guard
  griff nur beim Neu-Fetch, nicht beim Lesen aus dem Cache -- eine bereits
  VOR dem 2026-09-02/-03-Fix gecachte korrupte Parquet-Datei haette denselben
  `'>' not supported between instances of 'str' and 'float'`-Fehler auf
  unbestimmte Zeit immer wieder ausgeloest.** Gefunden beim Nachgehen eines
  aktuellen `FKInstantFunding-MT5-Bridge`-Vorfalls (`cls_practical-Scan`
  scheiterte 2026-09-07 15:24 Uhr genau mit diesem Fehler, danach 16:14 Uhr
  mit einem zweiten, unklaren `KeyError`-artigen "0"-Fehler -- beide Symptome
  passen zu ein und derselben Ursache: irgendeine der vier von diesem Bein
  genutzten gecachten Dateien hat vermutlich ein falsches dtype-Schema aus
  der Zeit vor dem urspruenglichen Fix). Root Cause: `combined_strategy/
  data.py::fetch_timeframe()` sowie `cls_practical/data.py::
  fetch_rate_instrument_m5_berlin()/fetch_2y_yield_daily()/
  fetch_eurusd_entry_tf_berlin()` riefen `validate_ohlc_numeric()` bisher nur
  im "frisch gefetcht + cachen"-Zweig auf (verhindert seit 2026-09-02 NEUE
  Korruption) -- der "aus Cache lesen"-Zweig (`path.exists() and not
  force_refresh`) gab die Datei ungeprueft zurueck, eine schon VORHER
  korrupt gecachte Datei waere also nie geheilt worden. Fix: alle vier
  Cache-Lese-Zweige validieren jetzt genauso; schlaegt die Validierung fehl
  (`ValueError`), wird die Cache-Datei ignoriert und wie bei einem fehlenden
  Cache frisch nachgefetcht (self-healing, ueberschreibt die korrupte Datei
  automatisch beim naechsten Lauf statt bei jedem Aufruf erneut zu scheitern).
  Bewusst nur diese beiden Dateien angefasst (genau der Aufrufpfad des
  gemeldeten `cls_practical`-Scans, kein breiterer Auditsweep). Nur
  `python -m py_compile` gegen beide geaenderten Dateien verifiziert (dieses
  Environment hat keinen Pandas-Zugriff, daher kein Live-Test gegen echte
  Cache-Dateien moeglich) -- ob dies die konkrete "0"-Fehlermeldung vom
  16:14-Lauf tatsaechlich behebt, ist eine unbestaetigte, aber gut
  begruendete Vermutung, kein verifizierter Fix dieses einen Vorfalls.
- **2026-09-07** [Funded-Portfolio-Bridge] **TTP Konto 2 (Demo) Verbindungs-
  fehler behoben: fehlender `/portable`-Terminal-Start nachgeruestet.**
  Root Cause: `executor.py::_connect_once()` liess `mt5.initialize()` einen
  fehlenden Terminal-Prozess selbst starten, aber ohne `/portable` --
  kollidierte dadurch mit den anderen gleichzeitig laufenden MT5-Terminals
  auf der Maschine (identischer Bugtyp wie der 2026-08-28-Vorfall in
  FKInstantFunding-MT5-Bridge, dort bereits mit `_ensure_terminal_running()`
  gefixt, hier aber nie uebernommen). Sichtbar erst als `Authorization
  failed` (Konto 2s Terminal lief seit Samstag 11:07 Uhr durchgehend idle,
  Session zum TTP-Server vermutlich abgelaufen), nach einem Kopieren des
  Terminal-Ordners ("TTP MT5 Terminal Konto1neu" -> "...Konto2neu",
  Nutzerwunsch fuer einen frischen, dedizierten Ordner) dann als `IPC
  timeout`/`IPC send failed` -- beides derselbe zugrunde liegende Fehler,
  nur zu unterschiedlichen Zeitpunkten des Terminal-Lebenszyklus sichtbar.
  Fix: `_terminal_running()`/`_ensure_terminal_running()` (identisches
  Powershell-Prozess-Check + `/portable`-Vorstart-Muster wie
  FKInstantFunding-MT5-Bridge) neu in `executor.py`, aufgerufen in
  `_connect_once()` vor `mt5.initialize()` -- gilt fuer alle 3 Konten, da
  `run_once.py` `executor.connect()` wiederverwendet, keine zweite Kopie.
  `test_connection.py` importiert dieselbe Funktion statt sie zu
  duplizieren. `config.py` zeigt Konto 2 jetzt auf den frischen
  "Konto2neu"-Ordner. Verifiziert: `test_connection.py` verbindet sauber
  mit allen 3 Konten. Offen (nicht code-seitig loesbar): `AutoTrading` bei
  Konto 2 zeigt `False` (Terminal-GUI-Schalter, muss manuell aktiviert
  werden); alter, jetzt unbenutzter Ordner "TTP MT5 Terminal - Konto2"
  kann geschlossen werden.
- **2026-09-07** [Second Brain] **Neue Prozessregel in `CLAUDE.md`: größere
  neue Vorhaben laufen erst durch den Plan-Modus** (`EnterPlanMode` +
  `AskUserQuestion` zur Klärung offener Design-/Architekturfragen, dann
  `ExitPlanMode` zur Freigabe), statt direkt draufloszubauen — gilt nicht
  für kleine, klar umrissene Änderungen. Ausgelöst durch eine Planungssession
  zu einer Idee für ein agentisches Research-System (automatisiert den
  8-Phasen-Prozess, inkl. autonomer Ideen-Findung) + einen separaten,
  live-lernenden Bot (Hybrid ML/RL, zuerst Alpaca-Paper-Trading, strikt
  getrennt von allen Live-Money-Bots) — Kernentscheidungen dazu geklärt,
  Bau selbst aber bewusst auf "frühestens in ein paar Wochen" vertagt.
  Vollständiger Entscheidungs-/Rechercheanstand gesichert in
  `knowledge/projects/agentisches-research-system-und-self-learning-bot.md`
  + Pointer in `DASHBOARD.md`s Ideen-Inbox + aktualisierter Claude-Memory
  `ml-self-learning-idea`.
- **2026-09-07** [FK Instant Funding] **Echten Order-Executor gebaut --
  `FKInstantFunding-MT5-Bridge` war bisher ein reiner Order-PLANER, sendete
  auch bei DRY_RUN=False nie echte Orders.** Beim Vorbereiten des Live-
  Schaltens gefunden: `run_once.py` verband sich echt mit MT5, berechnete
  Lot-Groessen, rief aber nie `mt5.order_send()` -- der Status war bei
  DRY_RUN=False woertlich "NICHT GESENDET -- echte Ausfuehrung noch nicht
  implementiert". Zusaetzlich fehlten der 5%-EOD-Trailing-Drawdown-Kill-
  Switch, der CTNL-Standalone-Kill-Switch und der 30%-Konsistenzregel-Check
  komplett im Ausfuehrungspfad (existierten bisher nur in der Paper-
  Simulation `fk_instant_funding/paper_bot.py`). Nachgebaut, 1:1 nach dem
  bereits real getesteten Funded-Portfolio-Bridge-Muster: neues
  `executor.py` (connect/place_market_entry/partial_close_position/
  move_stop_to_breakeven/close_position/check_naked_positions), `run_once.py`
  komplett umgebaut auf Re-Scan-Vergleich (offen/neu -> Entry, geschlossen ->
  Exit, inkl. Signal-Alter-Gate 60 Min.) statt reinem Planen, Kill-Switches
  + Konsistenz-Ampel ueber `fk_instant_funding.paper_bot`s bereits
  validierte Formeln wiederverwendet (kein zweiter Code). Telegram-
  Nachrichten bekommen ein "🔴 LIVE"-Praefix, damit sie im selben Chat nie
  mit dem weiterlaufenden Paper-Bot verwechselt werden koennen.
  Schrittweiser Rollout (Nutzerentscheid): neues `config.py::LIVE_LEGS`
  steuert PRO BEIN, ob echte Orders gesendet werden, unabhaengig vom
  globalen `DRY_RUN`-Flag -- Start mit nur den 3 NY-Open-ORB-Beinen
  (hoechste Aktivitaet diese Woche, alle 10 geloggten Trades beim frischen
  Backtest-Vergleich exakt reproduziert, siehe
  `scripts/research_fk_instant_funding_week_reconstruction.py`). Smoke-Test
  gegen das echte Konto (DRY_RUN=True, also folgenlos) erfolgreich: echte
  Verbindung (Login 17764), Equity $100.000,00 bestaetigt exakt gegen
  `pb.STARTING_EQUITY`, alle 9 Scans + beide Kill-Switches + Konsistenz-
  Check liefen ohne Fehler. `DRY_RUN=False` NICHT gesetzt -- das bleibt
  bewusst dem Nutzer selbst ueberlassen.

  **Beinahe-Regression dabei gefunden+korrigiert**: eine parallele Session
  hatte `run_once.py` bereits am 2026-09-06 auf `source="lake"` (Data-Lake-
  Pilot, alle 6 Scan-Aufrufstellen) umgestellt -- beim kompletten Neuschreiben
  der Datei fuer den Executor-Umbau ist das zunaechst untergegangen (kein Git-
  Diff fuer diesen Ordner, da bewusst nicht getrackt), zurueckgefallen auf
  `source="live"`-Default. Vor dem finalen Smoke-Test bemerkt (DASHBOARD-
  Eintrag zufaellig gegengelesen) und nachgezogen, zweiter Smoke-Test danach
  nochmal sauber durchgelaufen (deutlich schneller, keine Dukascopy-Fetches).

  **Nachtrag selber Tag**: Nutzerauftrag, den Trailing-DD-Kill-Switch um zwei
  ZUSAETZLICHE, vorausschauende Kill-Switches zu ergaenzen (nicht ersetzen,
  explizit nachgefragt + bestaetigt): `config.py::AGGREGATE_OPEN_RISK_CAP_PCT`
  (5%, alle Beine) + `CTNL_OPEN_RISK_CAP_PCT` (1%, nur CTNL Continuation+
  Reversal) begrenzen das offene Risiko VOM AKTUELLEN Kurs bis zum
  (ggf. schon auf Breakeven verschobenen) Stop ueber alle offenen Positionen,
  gegen die aktuelle Kontoequity -- `mt5.order_calc_profit()` mit dem echten
  Positionstyp und live vom Broker gelesenem SL/Volumen, reflektiert also
  automatisch Teilausstiege/Breakeven-Verschiebungen. Punkt-in-Zeit-Check,
  kein Hysterese-Reset noetig (anders als die beiden bestehenden Drawdown-
  Kill-Switches). Dritter Smoke-Test lief trotz eines echten dukascopy-Hangs
  (orb-Scan) und einem bekannten Korruptions-Glitch (cls_practical) sauber
  durch -- beide Scan-Fehler wurden vom bestehenden Error-Handling
  abgefangen, keiner der neuen Risk-Gates crashte. Ungetesteter Rest: die
  MT5-Positions-Iteration selbst (aktuell 0 offene Positionen, da noch nie
  ein echter Trade platziert wurde) -- verifizierbar erst nach dem ersten
  echten Live-Entry.

- **2026-09-07** [Funded-Portfolio-Bridge] **cls_practical in den 5-Minuten-
  Fast-Task aufgenommen** (Nutzerauftrag "Bau das so um", nach Diagnose eines
  konkreten Live-Vorfalls: `cls_practical EURUSD.gbe war bereits offen UND
  geschlossen (stop), bevor diese Bridge es je gesehen hat` in allen drei
  Telegram-Kanälen um 00:04 Uhr). Root Cause: `cls_practical/engine.py::
  simulate_cls_practical()` triggert per Stop-Order auf M5 und kann direkt im
  ersten Balken nach Entry stoppen — bei der bisherigen 15-Minuten-Scan-Kadenz
  konnte ein kompletter Entry-plus-Stop-Exit-Zyklus komplett in EIN
  Scan-Intervall fallen und wurde nie als offene Position gesehen. Die
  ursprüngliche Einschätzung vom 2026-09-02 ("cls_practical hat keine
  M5-Timing-Abhängigkeit") war so nicht korrekt — nur die Trigger-Frequenz ist
  niedriger (max. 1x/Tag) als bei ctnl_continuation/orb, nicht die
  Timing-Granularität. Fix, analog zum bestehenden ctnl_continuation/orb-Muster:
  `data_lake/sources.py` — EURUSD M5 von Lane `"fast"` auf `"fast5"` gehoben
  (5-Minuten- statt 15-Minuten-Ingestion, die 5 Referenz-Majors/BUND/USTBOND/
  Yields bleiben unverändert auf `"fast"`/`"slow"`, reiner Cross-Check-/
  Sizing-Kontext ohne Entry-Timing-Wirkung); `Funded-Portfolio-Bridge/
  run_once_fast.py` (ausserhalb des Repos) — `cls_practical`-Scan +
  `_process_leg`-Verarbeitung ergänzt, Docstrings korrigiert. Slow-Loop
  (alle 15 Min) bleibt unverändert als Fallback bestehen, identisches
  Redundanz-Muster wie bei ctnl_continuation/orb. `data_lake/sources.py` noch
  nicht committet.
- **2026-09-07** [Funded-Portfolio-Bridge] **Konto IQ Markets/BeyondIQCapital
  Login 15514 (state_id `iqmarkets2`) auf Nutzerauftrag aus `ACCOUNTS` in
  `Funded-Portfolio-Bridge/config.py` entfernt** (Bridge liegt ausserhalb des
  Repos). Damit laeuft die Bridge (6 Beine, `DRY_RUN=False`) nur noch mit 3
  statt 4 Konten (TTP Konto 2 504072729, TTP Konto 1 504069845,
  BeyondIQCapital 16054). Keine offenen Broker-Positionen betroffen --
  `bridge_state_iqmarkets2.json` zeigte zum Zeitpunkt der Entfernung nur
  "missed"-Signale ohne echtes Ticket, State-Datei bleibt als Historie liegen.
  Veraltete "4 Konten"-Kommentare in `run_once.py`/`run_once_fast.py`
  mitkorrigiert.
- **2026-09-07** [Second Brain] **Wöchentliche Second-Brain-Lint-Routine
  lief zum ersten geplanten Termin ins Leere**: `knowledge/scripts/lint.py`
  + `.claude/skills/second-brain-lint/SKILL.md` — laut Eintrag vom
  2026-09-01 damals erstellt und committet, inkl. wöchentlichem
  Cloud-Trigger ab demselben Tag — sind in diesem Repo nicht auffindbar
  (`git log --all` liefert für beide Pfade auf keinem Branch je einen
  Treffer). Kein Lint durchgeführt; Befund unter "🔍 Braucht deine
  Bestätigung" in `DASHBOARD.md` vermerkt statt die Dateien auf Verdacht
  neu zu bauen (Risiko, eine evtl. nur lokal vorhandene Version zu
  duplizieren/überschreiben).
- **2026-09-07** [data_lake] **Automatischer Live-Fallback bei Cold Start /
  haengender Ingestion gebaut** (`1db4e52`, Nutzerauftrag "Baue den
  Fallback" nach Rueckfrage zur seit 2026-09-04 offenen Cold-Start-Frage im
  Dashboard). Neue `data_lake.reader.with_live_fallback(lake_fn, live_fn)`:
  faengt `LakeMissingDataError`/`LakeStaleDataError` genau EINES
  Fetch-Aufrufs ab und ruft stattdessen die uebergebene Live-Fetch-Funktion
  auf, statt den kompletten Scan-Zyklus scheitern zu lassen -- jeder andere
  Fehler (Netzwerk, Parsing) laeuft weiterhin ungefangen in den
  bestehenden `_retry()`-Pfad. Angewendet auf alle Lake-faehigen `_scan_*`
  in `challenge_portfolio/paper_bot.py` (gold_asb, cls_practical,
  trend_pullback, ctnl, orb), `ek_portfolio/paper_bot.py` (gold_asb,
  cls_practical), `fk_instant_funding/paper_bot.py` (alle 5) sowie
  `gold_smc_htf_ltf/live_signal.py::_fetch_window()` (EK's ctnl_edge-Pfad).
  Bewusst NICHT auf `_scan_ou_modell` angewendet: das hat bereits eine
  eigene, gewollte Skip-pro-Ticker-Logik bei fehlenden Lake-Daten (siehe
  Kommentar dort) -- ein Fallback auf `yf.download()` wuerde bei einem
  echten Cold Start (alle ~160 Ticker gleichzeitig fehlend) genau den
  yfinance-Rate-Limit-Ansturm reproduzieren, den die eigene Slow-Lane
  (stuendliche statt 15-Min-Ingestion) ueberhaupt vermeiden soll. Jeder
  Fallback loggt eine `WARNING` ueber den Modul-Logger (sichtbar im
  jeweiligen Bridge-Log), sendet aber bewusst KEINE Telegram-Nachricht --
  bei einem laengeren Ingest-Ausfall wuerde das sonst pro betroffenem Key
  und Zyklus spammen. Verifiziert: `with_live_fallback()` isoliert getestet
  (happy path, `LakeMissingDataError`, `LakeStaleDataError`, unabhaengiger
  Fehler laeuft weiterhin durch) sowie EK-Portfolio-Bridges gold_asb/
  cls_practical end-to-end nochmal gegen `source="lake"` gelaufen -- exakt
  dieselben Zeilenzahlen wie vor dem Umbau (188 bzw. 28), also kein
  Verhaltensunterschied im gesunden Lake-Fall.
- **2026-09-06** [data_lake / EK-Portfolio-Bridge / FK Instant Funding]
  **`data_lake/`-Paket committet (war seit 09-04 ungetrackt) + Data-Lake-
  Pilot auf EK-Portfolio-Bridge (3 Beine: gold_asb, cls_practical,
  ctnl_edge Continuation+Reversal) und FKInstantFunding-MT5-Bridge (alle 6
  Beine) erweitert.** Commits `19e5b2c` (Nachhol-Commit des
  `data_lake/`-Pakets) und `f8db9f3` (Erweiterung). `source: str = "live"`
  (Default-erhaltend) analog zu `challenge_portfolio/paper_bot.py` zu
  `ek_portfolio/paper_bot.py::_scan_gold_asb/_scan_cls_practical`,
  `fk_instant_funding/paper_bot.py` (alle 6 `_scan_*`) und neu
  `gold_smc_htf_ltf/live_signal.py::continuation_signal/reversal_signal/
  continuation_market_state` (EK's ctnl_edge-Bein haengt NICHT an
  `_scan_ctnl`, sondern an dieser eigenen Live-Signal-Implementierung)
  ergaenzt. Braucht keine neue Ingestion -- liest denselben, seit 09-04
  fuer Funded-Portfolio-Bridge laufenden Lake (GOLD H4/H1/M15/M5, EURUSD
  M5, Majors M15, BUND/USTBOND M5, DE02Y/US02Y liegen schon frisch vor);
  einzige Ergaenzung in `data_lake/sources.py`: SILVER H4 (bisher von
  keinem Funded-Portfolio-Bridge-Bein gebraucht, aber fuer FK Instant
  Funding's `gold_silver`-Bein noetig). Externe, nicht-Git-getrackte
  Bridge-Dateien im selben Zug umgestellt: `EK-Portfolio-Bridge/legs/
  {gold_asb,cls_practical,ctnl_edge}/signal_source.py` (`source="lake"`),
  `FKInstantFunding-MT5-Bridge/run_once.py` (alle 6 Scan-Aufrufstellen).
  Vor dem Umschalten jeden Pfad einzeln gegen `source="live"` verifiziert:
  gold_asb (188=188 Zeilen, identischer letzter Entry) und ctnl_edge
  (continuation/reversal/market_state: alle Werte identisch) matchten
  exakt; bei cls_practical war Dukascopy LIVE gerade selbst ~2 Tage
  veraltet (letzter live Trade 08-26 bereits geschlossen) waehrend der Lake
  ein aktuelles, gerade offenes Signal (09-06, `data_end`) korrekt zeigte
  -- ein reales Beispiel genau des Fehlerbilds ("Trade waere sonst komplett
  verpasst worden"), das dieser Umbau beheben soll. Nebenfund beim
  Verifizieren: `legs/cls_practical/signal_source.py::scan_signal()`
  crashte mit einem echten, reproduzierbaren tz-Vergleichsfehler
  (`entry_time` tz-aware/Europe-Berlin gegen tz-naives `end`), sobald ein
  offenes Signal vorlag -- derselbe Bugtyp, der fuer `gold_asb` bereits am
  2026-09-01 gefunden und mit `_utc_naive()` gefixt wurde, hier aber
  uebersehen; jetzt identisch nachgezogen. Gleicher `stable_end_str`-
  Cache-Bug wie bei `challenge_portfolio/paper_bot.py` (09-06, s.u.) auch
  unabhaengig in `ek_portfolio/paper_bot.py` und `fk_instant_funding/
  paper_bot.py` gefunden und mitgefixt. Push nach GitHub blockiert durch
  den separaten, unangetasteten Git-Sync-Konflikt (Dashboard, "Braucht
  deine Bestaetigung") -- beide Commits liegen bisher nur lokal in `main`.
- **2026-09-06** [Second Brain / Reporting] **Neuer Scheduled Task
  `Dashboard-Telegram-Digest`: schickt jeden Morgen 8:00 die offenen Punkte
  aus `knowledge/DASHBOARD.md` per Telegram** (Nutzerwunsch, direkt nach dem
  Dashboard-Redesign gestellt). Neues `scripts/reports/dashboard_digest.py`
  extrahiert per Regex "Als Nächstes"/"Braucht deine Bestätigung"/"Offene
  Aufgaben" (nur offene, durchgestrichene = erledigte Punkte werden
  uebersprungen) sowie eine Kurzstatistik der Status-Tabelle und den
  letzten "Letzte Aktivität"-Eintrag, formatiert als HTML (fette
  Ueberschriften, Leerzeilen zwischen Punkten — Nutzerfeedback nach dem
  ersten Testlauf) und verschickt per `send_telegram_message(...,
  parse_mode="HTML")`. Wiederverwendet `scripts/reports/telegram_notify.py`/
  `telegram_config.py` (gleicher Bot wie der Weekly-Report), kein neuer
  Bot noetig. Neuer `scripts/reports/dashboard_digest_task.ps1`-Wrapper +
  Scheduled Task (taeglich 8:00, `WakeToRun`+`StartWhenAvailable` wie die
  anderen Bridge-Tasks). End-to-end per `schtasks /run` zweimal getestet
  (Nutzer hat beide Testnachrichten in Telegram bestaetigt, zweite mit
  Formatierungs-Feedback). Bekannte kleine Einschraenkung: das Logfile
  (`dashboard_digest_task.log`) zeigt Umlaute/Emojis teils als Mojibave/
  Platzhalter (PowerShell dekodiert die UTF-8-Ausgabe des Python-Prozesses
  nicht immer sauber) — betrifft NUR das Logfile, nicht die tatsaechlich
  verschickte Telegram-Nachricht (die direkt per `requests.post()` aus
  Python kommt). Nicht weiter verfolgt, da rein kosmetisch und vermutlich
  ein bereits bestehendes Muster in den anderen `*_task.ps1`-Wrappern.
- **2026-09-06** [challenge_portfolio/paper_bot.py] **gold_asb-Cache-Bug
  behoben.** `_scan_gold_asb()`s Alt/Neu-Grenze (`stable_end_str`) lief auf
  "gestern" -- wandert taeglich, verfehlte `combined_strategy.data`s
  Datums-Bereich-Cache dadurch JEDEN Kalendertag komplett und zog die volle
  2016-bis-heute-Historie taeglich frisch von Dukascopy nach, was dieses
  eine Bein unnoetig oft dem bekannten 90s-Hang aussetzte. Auf Monatsanfang
  stabilisiert (aendert sich nur 1x/Monat); das "neue" `force_refresh=True`-
  Fenster deckt dafuer den laufenden Monat statt nur "seit gestern" ab --
  bleibt mit max. ~31 Tagen M15-Daten klein genug, um nicht das grosse-
  Fenster-Problem zu wiederholen. Funktional verifiziert: zwei
  aufeinanderfolgende `_scan_gold_asb(source="live")`-Aufrufe lieferten
  identische 188 Zeilen (2,5s -> 1,9s) -- der eigentliche Cache-Vorteil
  (kein taeglicher Full-Refetch mehr) zeigt sich erst ueber mehrere Tage,
  nicht in einem Einzeltest messbar. Nutzerauftrag: "damit die Bots naechste
  Woche maximal sauber laufen". Gleichzeitig die 3 Engineering-Entscheidungen
  beim 5-Min-Fast-Trigger (M15-Zusatz, Cross-Prozess-Lock, kuerzere Retry-
  Parameter) inhaltlich nachgeprueft (nicht nur pauschal bestaetigt) --
  `account_state_lock()`s Code gelesen, identische `os.O_CREAT|O_EXCL`-
  Technik wie unabhaengig davon am selben Tag fuer `data_lake/manifest.py`
  gebaut; Retry-Parameter 3x/3s/20s direkt in `run_once_fast.py` verifiziert.
  Alle drei bestaetigt, siehe DASHBOARD.md.

- **2026-09-06** [Data-Fetch] **`validate_ohlc_numeric()` false-positive bei
  leerem Fetch-Fenster behoben + doppelte Pruefstelle entfernt.** Gefunden
  beim FK-Instant-Funding-Wochen-Backtest-Vergleich: ein Dukascopy-Fetch
  ueber ein Fenster ganz ohne Handelstage (z.B. komplett am Wochenende)
  liefert einen legitim leeren (0 Zeilen) DataFrame, dessen Spalten mangels
  Werten `object`-statt `float`-dtype haben — die Korruptions-Guard in
  `combined_strategy/data.py` hielt das faelschlich fuer eine kaputte
  Dukascopy-Antwort, `_retry()` erschoepfte alle 6 Versuche erfolglos
  (~8 Min) und crashte dann. Fix: `validate_ohlc_numeric()` ueberspringt
  jetzt leere DataFrames (nichts zu validieren, kein Korruptionsfall). Dabei
  eine zweite, komplett duplizierte inline-Kopie derselben Pruefung direkt
  darunter in `fetch_timeframe()` gefunden und entfernt (haette den Fix
  sonst unwirksam gemacht, da sie den leeren-Fall nicht mitbekam) — vermutlich
  bei der Umstellung der ersten Version auf die wiederverwendbare Funktion
  (2026-09-02/03) liegengeblieben. Betrifft den echten Live-Betrieb nicht
  direkt (alle Bots ueberspringen Wochenend-Scans komplett via
  `is_market_paused()`/Task-Scheduler-Zeitplan, bevor ein solcher Fetch je
  passiert), macht `combined_strategy.fetch_timeframe()` (genutzt von
  `combined_strategy/data.py`, `cls_practical/data.py`,
  `data_lake/ingest.py` — Letzteres treibt Funded-Portfolio-Bridge, LIVE)
  aber robust gegen jedes zukuenftige leere Fenster (Feiertage,
  Datenluecken), statt 8 Min. Retry-Zeit zu verschwenden und dann zu
  crashen. Verifiziert: alle 100 bestehenden Tests weiterhin gruen, Original-
  Fehlerfall (`_scan_gold_asb()` mit Wochenend-`end`) laeuft jetzt sauber
  durch (188 Trades statt Crash).

- **2026-09-06** [Reporting] **Weekly Checkup KW36/2026 erstellt — erster Lauf
  im neuen Portfolio-Bridge-Format.** Dabei zwei neue Funde, in
  `DASHBOARD.md` unter "Als Nächstes"/"Offene Aufgaben" ergänzt: (1)
  `git log -- data_lake/` zeigt keinen einzigen Commit, obwohl der
  09-04-Eintrag unten das Paket als "git-getrackt" beschreibt — kompletter
  Ordner (`manifest.py`, `storage.py`, `sources.py`, `twelvedata_source.py`
  u.a.) existiert nur lokal, kein Git-Backup für die Dateninfrastruktur von
  Funded-Portfolio-Bridges 6 Beinen. (2) 12 neue, unverarbeitete Clippings
  seit 2026-09-03 in `knowledge/Clippings/` gefunden. Reports:
  `knowledge/reports/weekly/KW36_2026_{performance,education,checkup}.{md,html}`
  (PDF nur lokal unter `Documents/Trading Reports/`, nicht committet).

- **2026-09-06** [Data Lake] **Twelve-Data-Backup-Datenquelle gebaut + kritischen
  Concurrency-Bug im Manifest gefunden und behoben.** Nutzerauftrag: falls
  Dukascopy weiterhin haengt, nie wieder Trades verpassen. Erwogen wurde
  zunaechst "jeden Zyklus beide Quellen parallel abfragen" (Nutzeridee) --
  durchgerechnet und verworfen: bei 24 Keys x alle 5 Min. (288 Zyklen/Tag)
  bräuchte das >6900 Anfragen/Tag, Twelve Datas kostenloses Kontingent
  (verifiziert: 800/Tag) reicht dafuer nur fuer ~2-3 Instrumente durchgehend.
  Stattdessen reaktives Modell: `data_lake/twelvedata_source.py` (neu) springt
  erst nach `FAILOVER_AFTER_N_FAILURES=2` aufeinanderfolgenden Dukascopy-
  Fehlversuchen fuer denselben Key ein, schreibt aber in denselben Lake-
  Speicherplatz wie Dukascopy (source bleibt "dukascopy") -- reader.py
  braucht dadurch KEINE Aenderung. Deckt nur FX-Majors + Gold/Silber ab
  (SYMBOL_MAP) -- Platin/CHFJPY/Indizes/Anleihen/2Y-Renditen bewusst nicht
  geraten, da auf dem kostenlosen Twelve-Data-Plan nicht zuverlaessig
  verfuegbar. `timezone=UTC` wird IMMER explizit mitgegeben (empirisch
  verifiziert: ohne den Parameter war das Antwortformat mehrdeutig, zwei
  Calls Sekunden auseinander lieferten "aktuellste Kerze"-Zeitstempel mit
  ~10h Differenz). Alternative Anbieter gegengeprueft und verworfen: Finexly
  (Nutzervorschlag) liefert nur Einzel-Umrechnungskurse, KEINE OHLC-Kerzen --
  fuer Breakout-/ATR-basierte Strategien ungeeignet, dazu nur 1.000
  Anfragen/Monat und FX-only; Alpha Vantage nur 25/Tag, zu knapp.
  **Beim End-to-End-Test kritischen Bug gefunden**: `manifest.json` war
  korrupt (zwei aneinandergehaengte JSON-Objekte) -- `DataLake-Ingest-Fast`/
  `-Fast5`/`-Slow` koennen sich zeitlich ueberlappen und schrieben bisher
  ALLE ohne gegenseitige Sperre in dieselbe Datei; `storage.py`s Tmp-Datei-
  plus-Rename schuetzt nur vor einem halb geschriebenen Read, nicht vor zwei
  gleichzeitigen Schreibern mit demselben Tmp-Dateinamen. Legte dadurch ALLE
  6 Funded-Portfolio-Bridge-Beine lahm (jeder Freshness-Check crashte an der
  kaputten Datei), bis von Hand repariert (erstes vollstaendiges JSON-Objekt
  im File war zum Glueck noch unbeschaedigt, Rest verworfen). Fix: neue
  `manifest.py::_locked()`-Sperre um `record_success()`/`record_failure()`,
  identisches `os.O_CREAT|O_EXCL`-Muster wie Funded-Portfolio-Bridge/
  run_once.py::account_state_lock() (dort schon fuer denselben Bug bei
  bridge_state_*.json eingebaut). End-to-end verifiziert: 2 simulierte
  Dukascopy-Fehlversuche loesten den echten Twelve-Data-Failover erfolgreich
  aus (84.884 Zeilen EURUSD_M5 uebernommen, `consecutive_failures` korrekt
  auf 0 zurueckgesetzt, `last_source_used: "twelvedata"` vermerkt), danach
  `run_shared_scans()` komplett gegen die reparierte, gesperrte Version
  gegengeprueft.

- **2026-09-05** [Second Brain / Workflow] **Neuer Edge-Card-Workflow +
  Verzahnung mit Backtest-Standardprozess** (`knowledge/areas/
  edge-card-workflow.md`, Nutzer-Vorgabe vollständig übernommen). Prozess
  für händisch entwickelte/getradete Strategien: Phase 0 (Strategie-
  verständnis bestätigen) + 5 Felder (01 Idee, 02 Regel, 03 Mechanismus,
  04 Gegenprobe, 05 Test), Schritt für Schritt, Nutzer-Begriffe/-
  Definitionen übernehmen, keine Scheingenauigkeit. Auf Nutzerwunsch mit
  dem bestehenden [[backtest-standard-process]] verzahnt: ersetzt für
  händische Strategien dessen Phase 1-3, Feld 02 REGEL wird 1:1-
  Spezifikation für Phase 4, Feld 04 GEGENPROBE liefert zusätzliche
  Kontrollgruppen für Phase 6 Robustheit. `CLAUDE.md` um Referenz-Abschnitt
  "Edge-Card-Workflow" ergänzt. **Nutzerentscheid 2026-09-05 (Bestätigung
  nachgetragen)**: Zuordnung passt so; klare Abgrenzung nach Herkunft der
  Strategie -- Papers/Dokumente bleiben unverändert beim vollen
  8-Phasen-Prozess (Phase 1-3 inklusive), der Edge-Card-Workflow greift
  ausschließlich bei händisch entwickelten/getradeten Strategien ohne
  Paper-Ursprung. Punkt aus DASHBOARD "Braucht deine Bestätigung" entfernt.

- **2026-09-04** [Reporting] **Weekly Checkup - Performance auf Portfolio-
  statt Bein-Ebene umgestellt** (`scripts/reports/weekly_report_prompt.md`).
  Nutzerauftrag, bereits 2026-08-27 angekuendigt (Memory
  `portfolio_consolidation_pending`: "sobald die neuen Portfolios stehen,
  wird das nochmal geaendert") und heute explizit bestaetigt+umgesetzt. Die
  Trades/Winrate/PnL-Tabelle (Punkt 4) sowie Wochenkontext/Risk-Compliance/
  "Was hat funktioniert" (Punkte 1-3) berichten ab sofort NUR noch pro
  Portfolio-Bridge (EK-Portfolio-Bridge, Funded-Portfolio-Bridge/Challenge
  Portfolio, FK Instant Funding) statt pro Einzelbein (Gold ASB/CTNL/OU-
  Modell/etc., die als eigenstaendige Bots ohnehin aufgeloest sind).
  Nutzerentscheid zur Granularitaet (Rueckfrage gestellt, da nicht
  eindeutig): Funded-Portfolio-Bridge wird trotz 4 echter Broker-Konten zu
  EINER zusammengefassten Zeile aggregiert (gleicher Strategie-Blend, nur
  kapitalgewichtet pro Konto) -- kontospezifische Kill-Switch-/Drawdown-
  Ereignisse sollen aber weiterhin in der Risk-Compliance-Sektion einzeln
  auftauchen, nicht in der Aggregation verschwinden. Wirkt erst beim
  naechsten `Forex-Weekly-Report`-Lauf (naechste vollstaendige Woche ist
  KW36, noch kein Report dafuer generiert).

- **2026-09-04** [Second Brain / Claude-Workflow] **Neuer Skill `handoff`**
  (`.claude/skills/handoff/SKILL.md` + Inbox `knowledge/_handoff/`):
  schreibt am Ende einer Session (oder wenn das Kontextfenster sich der
  ~300k-Token-Grenze nähert) eine Handoff-Datei, die nur festhält, was
  sonst verlorenginge (Learnings, Fehlannahmen, offene Fäden) — kein
  Task-Recap, das aus Git/DASHBOARD/CHANGELOG rekonstruierbar wäre. Neue
  Sessions prüfen den Ordner zuerst (CLAUDE.md "Kontextfenster-Hygiene"
  entsprechend ergänzt). Nutzerentscheid nach Auswertung des "Everlast AI"-
  Claude-Workflow-Clips (siehe `resources/second-brain-methodik.md`) — von
  4 vorgeschlagenen Ideen nur diese eine übernommen, `/prime`-Command
  verworfen, `/doctor`-Check + CLAUDE.md-Englisch zurückgestellt/verworfen
  (Details in der Resource-Notiz).
- **2026-09-04** [EK-Portfolio-Bridge / Task Scheduler] **Telegram-Spam bei
  "Signal zu alt"-Warnungen behoben + zwei Scheduled-Task-Trigger entzerrt.**
  Nutzerauftrag nach Screenshots mit identischer NASDAQ-Stale-Warnung alle 2
  Minuten. Root Cause: `legs/ny_open_orb/executor.py`s SL-/TP-Stale-Checks
  (siehe Eintraege weiter oben) hatten anders als Funded-Portfolio-Bridge's
  `_process_leg()` keine Einmal-pro-Signal-Sperre — wiederverwendet jetzt
  das bereits vorhandene `already_notified_risk_cap_skip()`/`mark_risk_cap_
  skip_notified()`-Muster (`core/state_store.py`) mit einem eigenen
  `orb_stale_{instrument}_{entry_time}`-Key statt einer neuen Tabelle.
  Zusaetzlich beim Nachgehen der heutigen IPC-Timeout-Haeufung bei ttp1/
  iqmarkets2 gefunden: durch die neuen Fast-Tasks laufen jetzt 6-8 Scheduled
  Tasks dicht getaktet, EK-Portfolio-Bridge UND Funded-Portfolio-Bridge
  feuerten beide exakt auf demselben :00/:15/:30/:45-Raster — Funded-
  Portfolio-Bridges Trigger um 4 Minuten verschoben (jetzt :04/:19/:34/:49),
  Wiederholungsintervall (PT15M) dabei unveraendert verifiziert. Reduziert
  gleichzeitige MT5-Verbindungslast, behebt aber nicht zwangslaeufig die
  zugrundeliegende Terminal-Fragilitaet selbst — nur ein erster, risikoarmer
  Schritt, keine erneute Tiefen-Diagnose wie am Vortag.

- **2026-09-04** [Funded-Portfolio-Bridge / Data Lake] **5-Minuten-Scan-Trigger
  fuer ctnl_continuation + orb jetzt live geschaltet** (Fortsetzung des
  Eintrags direkt unten, gleicher Tag). Nutzer hat den vom aktiven Auto-Mode-
  Classifier geforderten, aktiv begleiteten manuellen `run_once_fast.py`-
  Testlauf selbst durchgefuehrt: alle 4 Konten sauber durchgelaufen, keine
  Fehler, keine unerwarteten Orders ("Keine offenen/neuen Signale in diesem
  Zyklus" bei allen). Beide Scheduled Tasks (`DataLake-Ingest-Fast5`,
  `Funded-Portfolio-Bridge-Fast`) vom Nutzer selbst registriert (der
  Classifier blockierte sowohl den direkten `run_once_fast.py`-Lauf als auch
  die Task-Registrierung als Claude-Aktion) — beide per `schtasks /XML`
  gegengeprueft: korrekte 5-Min-Wiederholung, Mo-Fr, `ExecutionTimeLimit`
  passend (PT4M). Nebenbefund waehrend der Umsetzung: eine PARALLELE Claude-
  Session (`knowledge-4c`) war vom selben Nutzer unabhaengig auf denselben
  DASHBOARD-Punkt angesetzt worden und hatte bereits `DataLake-Ingest-Fast5`
  registriert, bevor das hier bemerkt wurde -- ueber Cross-Session-
  Nachrichten abgeglichen (siehe DASHBOARD-Historie), keine doppelte
  Registrierung/kein doppelter Testlauf. Dieselbe Session hat zeitgleich,
  unabhaengig von diesem Feature, einen kleinen Bugfix in `run_once.py::
  _process_leg()` ergaenzt (OU-Modell: `live_price <= 0`-Check fuer einen
  Tick mit ask/bid=0.0 statt None) -- beide Aenderungen liegen konfliktfrei
  nebeneinander in der Datei, `py_compile` nach dem Zusammentreffen erneut
  sauber.

- **2026-09-04** [Funded-Portfolio-Bridge / Data Lake] **5-Minuten-Scan-Trigger
  fuer die zwei M5-Timing-kritischen Beine (ctnl_continuation, NY-Open ORB)
  gebaut — Code fertig, NOCH NICHT live geschaltet.** Nutzerentscheid
  2026-09-02 (DASHBOARD.md Punkt 1): Funded-Portfolio-Bridge scannt sonst nur
  alle 15 Min, ein frisches M5-Signal kann bis zu 3 Bars zu spaet erkannt
  werden. Zwei Ebenen noetig (Fund waehrend der Umsetzung: die 2026-09-02-
  Entscheidung war VOR dem selbentags-2026-09-04 live gegangenen Data-Lake-
  Pilot getroffen worden — ein reiner Bridge-Trigger allein haette nur
  dieselben 15 Min alten Lake-Bars 3x wiederholt gelesen):
  (1) `data_lake/sources.py`/`ingest.py`: neue Lane `"fast5"` fuer die 7
  M5/M15-Timing-kritischen Keys (GOLD M5, SP500/US30/NASDAQ M5+M15) —
  SP500/US30/NASDAQ M15 bewusst MIT drin, nicht nur M5 (`ny_open_orb/
  engine.py::build_frame()` haengt die Opening-Range am M15-Bar direkt nach
  NY-Open, sonst waere der allererste Breakout jeder Session weiterhin bis zu
  15 Min zu spaet). `ingest_fast()` filterte `FAST_SOURCES` bisher NICHT nach
  `lane` (das Feld existierte, wurde aber nirgends ausgewertet) — ohne
  Nachruesten dieses Filters haetten zwei Ingest-Kadenzen dieselbe Parquet-
  Datei gleichzeitig ueber einen nicht PID-eindeutigen Tmp-Pfad beschrieben
  (`storage.py`), echtes Korruptionsrisiko, jetzt behoben. Per drei manuellen
  Laeufen verifiziert: `--universe fast5` aktualisiert exakt die 7 Keys
  (Manifest-Zeitstempel geprueft), `--universe fast` beruehrt sie danach
  nicht mehr (verbleibende 19 Keys, kein Ueberlapp).
  (2) `Funded-Portfolio-Bridge/run_once.py`: neuer Cross-Prozess-Lock pro
  Konto (`account_state_lock()`, atomares `os.O_CREAT|O_EXCL`, Stale-Lock-
  Erkennung nach 16 Min) um `run_account()` — noetig, weil `_save_state()`
  ein blindes `write_text()` ohne Read-Merge ist (anders als EK-Portfolio-
  Bridges SQLite-State): ohne Lock haette ein spaeter speichernder Prozess
  ein vom parallel laufenden Fast-Prozess gerade real eroeffnetes MT5-Ticket
  aus dem State verschwinden lassen koennen -> echter Doppel-Entry beim
  naechsten Scan. Per eigenem Unit-Test verifiziert (Acquire/Release,
  Timeout bei gehaltenem Lock, Stale-Lock-Reclaim).
  (3) Neue `Funded-Portfolio-Bridge/run_once_fast.py` (+`run_task_fast.ps1`):
  Muster 1:1 von `EK-Portfolio-Bridge/run_once_fast.py` uebernommen
  (`import run_once as slow`, keine Logik-Kopie). Deckt NUR
  `ctnl_continuation` (nicht `ctnl_reversal`, kein M5-Timing) +
  `orb_sp500`/`orb_us30`/`orb_nasdaq` + `_manage_orb_partial_exits()` ab.
  `run_shared_scans_fast()` end-to-end gegen die echten Lake-Daten getestet
  (kein MT5, keine Order) — beide Scans liefen fehlerfrei, ORB lieferte 429
  Trades ueber alle 3 Maerkte, CTNL Continuation 0 (kein aktuelles Signal).
  **Zwei Scheduled Tasks (`DataLake-Ingest-Fast5`, `Funded-Portfolio-Bridge-
  Fast`) sind bewusst NOCH NICHT registriert** — `DRY_RUN=False` gilt
  bridge-weit fuer `run_once.py` UND `run_once_fast.py` gleichermassen, der
  allererste Lauf von `run_once_fast.py` kann bei einem echten offenen
  Signal eine echte Order ausloesen. Wartet auf einen vom Nutzer aktiv
  begleiteten manuellen Testlauf, siehe DASHBOARD.md "Braucht deine
  Bestaetigung".

- **2026-09-04** [EK-Portfolio-Bridge] **Zwei echte Order-Bugs in
  `legs/ny_open_orb/executor.py` gefunden + behoben, beim Nachgehen der drei
  offenen Bridge-Monitor-Fragen im Dashboard (dessen Snapshot-Zugriff keine
  vollen Logs/Root-Causes zeigt).** (1) NASDAQ-Ticket 262117522 hing seit
  ~22:00 Uhr Vortag durchgehend (297 Fehlversuche) am Session-Ende-
  Notausgang fest: der Order-Request hatte kein `deviation`-Feld, wodurch
  `mt5.order_send()` manche Marktorders clientseitig ohne Retcode ablehnte
  (`result=None`) — dazu fehlte `mt5.last_error()` im Log, jeder Versuch
  sah identisch nichtssagend aus. Fix: `deviation: 20` ergaenzt,
  `mt5.last_error()` mitgeloggt. (2) US30-Order scheiterte erneut mit
  "Invalid stops" trotz des 2026-09-02-SL-Fixes: TP wurde weiterhin aus dem
  alten Signalpreis berechnet und lag bei genug Kursbewegung auf der
  FALSCHEN Seite des Live-Preises (beobachtet: TP unter Einstiegspreis bei
  einer LONG) — der bestehende Fix prüfte nur das SL, nie das TP. Fix:
  identische Seiten-Pruefung jetzt auch fuers TP in `check_and_execute_
  entry()`, Signal wird bei ungueltiger TP-Seite als "zu alt" uebersprungen
  statt eine zum Scheitern verurteilte Order zu senden.
  **Update 10:48 Uhr**: der `deviation`-Fix allein reichte nicht -- das
  jetzt sichtbare `mt5.last_error()` zeigte den echten dritten Grund:
  `(-2, 'Invalid "comment" argument')`. Ein erster Versuch, den Kommentar
  auf 31 Zeichen zu kappen, war wirkungslos ("EK-orb_nasdaq auto-session_end"
  hatte nur 30 Zeichen, schon unter 31) — Tickmills tatsaechliches Limit
  liegt niedriger. Auf 16 Zeichen gekappt, damit griff es sofort: Ticket
  262117522 um 10:48:12 endgueltig geschlossen (0.21 Lots @ 29604.49), nach
  ~13h Haengen. Strukturell betraf das nur NASDAQ (laengster Leg-Name),
  SP500/US30 nie. Live bestaetigt, kein reiner py_compile-Stand mehr.

- **2026-09-04** [Data Lake / Funded-Portfolio-Bridge] **Neuer lokaler
  Data-Lake-Pilot gebaut und live geschaltet — Funded-Portfolio-Bridges 6
  Beine lesen ihre Marktdaten jetzt aus einem lokal gepflegten Parquet-Lake
  statt live von Dukascopy/TradingView/yfinance zu ziehen.** Nutzerauftrag
  nach der wiederholten Dukascopy-Instabilitaet ("ganz alles ordentlich
  machen"), Struktur explizit vom Nutzer vorgegeben: kostenlose Rohquellen
  -> lokaler Data Lake -> Validierung -> Normalisierung -> abgeleitete
  Daten -> Bots. Vollstaendiger Entwurf in
  `C:\Users\andre\.claude\plans\resilient-painting-raven.md`.
  Neues Paket `data_lake/` (git-getrackt) + gitignored Payload
  `data_lake_store/`: `sources.py` (Registry, jede (Quelle,Key,Timeframe)
  GENAU EINMAL, wiederverwendet ausschliesslich bereits bestehende, validierte
  Fetch-Funktionen -- keine neue Fetch-Logik), `storage.py` (atomares
  Parquet-Schreiben, inkrementell gemergt statt komplett neu geschrieben),
  `manifest.py` (Freshness-Kontrolle, JSON, pro Key last_success_at/
  last_error, Cutoff-Klassen 35 Min./4h/90 Min. je nach Timeframe -- deutlich
  unter dem bestehenden `MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY=60`-Gate),
  `reader.py` (Lake-gestuetzte Ersatzfunktionen fuer jede Original-Fetch-
  Funktion, identischer Name/identische Form, wirft `LakeMissingDataError`/
  `LakeStaleDataError` statt still leere/veraltete Daten zu liefern),
  `ingest.py` (Ingestion-Entrypoint, `--universe fast|slow`), eigene Kopie
  von `_retry()`/`_call_with_timeout()` in `retry_util.py` (bewusst NICHT
  die 3 bestehenden Bridge-Kopien angefasst, siehe Plan). `challenge_
  portfolio/paper_bot.py`: alle 6 `_scan_*()`-Funktionen um `source: str =
  "live"` erweitert (Default erhaelt bestehendes Verhalten fuer `scan_once()`
  + `catchup_ou_modell.py` unveraendert), `Funded-Portfolio-Bridge/
  run_once.py::run_shared_scans()` ruft jetzt mit `source="lake"`.
  Zwei neue Scheduled Tasks: `DataLake-Ingest-Fast` (alle 15 Min., 24
  Dukascopy/TradingView-Keys) und `DataLake-Ingest-Slow` (stuendlich, ~59
  aktuell gefilterte OU-Modell-Ticker -- Ticker-Liste wird ueber dieselbe
  theta/p-value/half-life-Filterlogik wie der Live-Scan dynamisch gebaut,
  driftet also nie davon ab). Vollstaendig verifiziert (nicht nur
  `py_compile`): erster Fast-Seed-Lauf 23/23 Quellen sauber (bis zu 95.530
  Zeilen bei SP500 M5), erster Slow-Lauf 59/59 Ticker sauber; `run_once.py::
  run_shared_scans()` DIREKT gegen die echte, live `DRY_RUN=False`-Config
  aufgerufen (liest/rechnet nur, ruehrt nie MT5/`executor.*` an) -- alle 6
  Beine liefern Ergebnisse, `gold_asb` mit EXAKT derselben Zeilenzahl (188)
  wie der fruehere Live-Dukascopy-Test; kuenstlich einen Key (GOLD_M15) als
  veraltet markiert -> `gold_asb`/`ctnl_edge` (beide von GOLD_M15 abhaengig)
  scheitern sauber mit klarer `LakeStaleDataError`, alle anderen 4 Beine
  unbeeinflusst -- danach echten Re-Ingest gefahren, Test-Zustand
  zurueckgesetzt. Pilot bewusst auf Funded-Portfolio-Bridge begrenzt --
  EK-Portfolio-Bridge (hat fuer ORB/Gold-Silber/Trend-Pullback bereits einen
  eigenen MT5-Pfad, siehe Eintrag "EK-Portfolio-Bridge-Fast" oben) und
  FK-Instant-Funding-MT5-Bridge folgen erst, sobald sich der Pilot bewaehrt
  hat.
- **2026-09-04** [EK-Portfolio/Challenge-Portfolio/FK-Instant-Funding-Paper]
  **CTNL-eigenen Kill-Switch (Stand-alone Cont+Rev-Drawdown gegen die
  Phase-6-P5-Schwelle -6,6%) in alle drei konsolidierten Portfolio-Bots
  nachgeruestet — Nutzerauftrag, nachdem sich herausstellte, dass dieser
  Monitor bei der Portfolio-Konsolidierung (2026-08-27) NICHT automatisch
  mit uebernommen wurde.** Fund vom Vortag (siehe Eintrag "CTNL Reversal:
  August 2026 lief 0/14"): der urspruengliche Kill-Switch existierte nur in
  der eigenstaendigen `gold_smc_htf_ltf/paper_bot.py`-Task
  ("CTNL-Edge-FK-Paper"), die deaktiviert wurde, ohne dass die drei
  Nachfolge-Bots (EK/Challenge/FK Instant Funding) diese spezifische Pruefung
  selbst nachgebaut haetten — lief seitdem live nirgends. Neue geteilte
  Funktion `gold_smc_htf_ltf/live_signal.py::ctnl_standalone_drawdown()`
  (+ Konstante `CTNL_KILL_SWITCH_DD_THRESHOLD=-0.066`) rechnet Continuation+
  Reversal auf einem EIGENEN 100k-Stand-alone-Konto mit den validierten
  FK-Risikogroessen (0,5%/0,15%) durch — unabhaengig von der jeweiligen
  Portfolio-Kapitalgewichtung, sonst wuerde CTNL Reversals winziger
  0,15%-Risikoanteil einen echten Bruch in der Portfolio-Gesamtkurve fuer
  immer unsichtbar verduennen. In allen drei `scan_once()`-Funktionen nach
  dem jeweils bestehenden Portfolio-Kill-Switch eingehaengt, eigener
  `ctnl_kill_switch_active`-State (kollidiert nicht mit dem bestehenden
  Flag), Telegram-Alarm bei Bruch/Erholung nach demselben Muster.
  **Betrifft `challenge_portfolio/paper_bot.py` — wird von der ECHTEN,
  live laufenden Funded-Portfolio-Bridge direkt aus diesem Repo importiert
  (kein eingefrorener Deploy-Snapshot), wirkt sich also ab dem naechsten
  Bridge-Lauf unmittelbar aus.** `ek_portfolio/paper_bot.py` (Task
  deaktiviert) und `fk_instant_funding/paper_bot.py` (DRY_RUN) sind davon
  nicht in Echtgeld-Hinsicht betroffen. Verifiziert: `py_compile` auf allen
  vier geaenderten Dateien + isolierter Funktionstest (`_state_trades_df` +
  `ctnl_standalone_drawdown()` mit synthetischen Trades, inkl. eines
  synthetischen Beinahe-Bruch-Szenarios) in allen drei Bots einzeln
  ausgefuehrt, kein echter Live-Lauf abgewartet.
- **2026-09-03** [Funded-Portfolio-Bridge] **Zeitlimit-Erhoehung (14->40 Min,
  siehe Eintrag weiter unten) wieder zurueckgenommen (40->14 Min) — war ein
  Fehlschluss.** Nutzerkorrektur: mit 40 Min. darf ein haengender Lauf viel
  laenger blockieren, und `MultipleInstances=IgnoreNew` ueberspringt in dieser
  laengeren Zeit entsprechend MEHR 15-Minuten-Trigger als vorher -- verschaerft
  also genau das Verzoegerungsproblem (spaete Entries), das an diesem Tag das
  eigentliche Thema war, statt es zu lindern. Die urspruengliche Sorge (ein
  zwangsbeendeter Lauf koennte mitten in einer echten Order-Versendung
  abgebrochen werden) bleibt zwar bestehen, aber ein kuerzeres statt laengeres
  Zeitlimit ist der richtige Hebel dagegen (schneller wieder ein frischer,
  hoffentlich saubererer Lauf) -- nicht ein laengeres. Zurueck auf 14 Minuten.
- **2026-09-03** [EK-Portfolio-Bridge] **MT5-native Beine (ORB, Gold-Silber,
  Trend Pullback) in einen eigenen, viel schnelleren Scheduled Task
  ausgelagert (`run_once_fast.py`, alle 2 Min., eigenes `IgnoreNew`+2-Min-
  Zeitlimit).** Nutzerauftrag nach Beobachtung, dass ein "sauberer" ORB-Trade
  trotzdem stundenlang zu spaet ausgefuehrt wurde: diese drei Beine ziehen
  ihre Kurse bereits ueber `mt5.copy_rates_range()` (kein Dukascopy), liefen
  aber bisher im selben sequenziellen `run_once.py`-Prozess wie die 6
  dukascopy-abhaengigen Beine (bis zu ~588s Worst-Case pro Bein) -- ein
  haengendes Dukascopy-Bein liess den GANZEN 15-Minuten-Task oft ueber das
  14-Minuten-`ExecutionTimeLimit` laufen, wodurch der naechste Trigger per
  `IgnoreNew` komplett uebersprungen wurde. Real beobachtet: ein NASDAQ-ORB-
  Signal haengte am 20:45-Uhr-`entry_on_forming_bar_wait`-Status fest, bis
  21:45 statt planmaessig 21:00 zu bestaetigen. Fix: `orb_executor.
  manage_open_positions()` + alle ORB-Entries + Gold-Silber + Trend-Pullback
  (4 Maerkte) aus `run_once.py::main()` entfernt, in neues `run_once_fast.py`
  verschoben (importiert `market_is_open()`/`_run_leg()`/`_check_trend_
  pullback()`/`_check_gold_silver()` aus `run_once.py` statt sie zu
  duplizieren). Geteilter State (SQLite, `core/state_store.py`) und Telegram-
  Queue (In-Memory pro Prozess, `core/telegram_notify.py`) sind fuer zwei
  parallel laufende Prozesse unproblematisch verifiziert (siehe Docstring
  `run_once_fast.py` fuer die einzige bekannte Restluecke: ein theoretisch
  zeitgleicher Risiko-Deckel-Check aus beiden Prozessen). Naked-SL-Watchdog +
  Tagesabschluss bewusst NUR im alten `run_once.py` belassen (nicht
  zeitkritisch, doppelte Meldungen waeren nur Spam). Nur Import-Wiring +
  `py_compile` verifiziert, kein echter Live-Lauf des neuen Tasks abgewartet
  (erster Trigger unmittelbar nach Registrierung faellig).
- **2026-09-03** [cls_practical/data.py] **Dritte, bisher übersehene Lücke im
  heutigen "OHLC vor dem Cachen validieren"-Fix geschlossen — `fetch_2y_yield_daily()`
  hatte gar keine `validate_ohlc_numeric()`-Prüfung.** Bridge-Monitor-Routine
  sah im Snapshot, dass `CLS-Practical-Scan fehlgeschlagen: '>' not supported
  between instances of 'str' and 'float'` auf Funded-Portfolio-Bridge UND
  FKInstantFunding-MT5-Bridge noch MEHRFACH auftrat (u.a. 21:35, 22:05,
  22:30 Uhr) — alles NACH dem heutigen Fix-Commit (15:11:59 UTC), und zwar
  exakt mit dem alten, unbehandelten `TypeError`-Text statt der neuen,
  saubereren `ValueError`-Meldung aus `validate_ohlc_numeric()`. Das zeigte:
  der Fix griff hier nicht. Nachverfolgt bis `challenge_portfolio/paper_bot.py::
  _scan_cls_practical()` — die ruft neben den zwei heute reparierten
  Funktionen (`fetch_rate_instrument_m5_berlin`, `fetch_eurusd_entry_tf_berlin`)
  auch `fetch_2y_yield_daily()` (TVC:DE02Y/TVC:US02Y via `tradingview/data.py`)
  auf, die denselben ungeprüften `to_parquet()`-Cache-Block hat wie die
  beiden vorhin gefixten Stellen, aber beim heutigen Fix übersehen wurde
  (Grund vermutlich: sie liegt in derselben Datei, aber nutzt TradingView
  statt Dukascopy als Quelle, `open/high/low/close`-Spalten aus
  `tradingview/data.py::fetch_ohlcv()` können genauso non-numerisch
  zurückkommen). `compute_frontend_2y_risk_multiplier()` in
  `cls_practical/rates.py` rechnet direkt mit `close-open`-Differenzen und
  Rolling-Z-Scores dieser Werte — genau der Vergleich, der bei
  String-Spalten mit `'>' not supported`-Fehlern crasht. Fix: dieselbe
  `validate_ohlc_numeric(df, ["open", "high", "low", "close", "volume"])`-
  Prüfung jetzt auch hier vor dem `to_parquet()`-Schreiben ergänzt — damit
  sind jetzt alle drei Cache-Schreibstellen in `cls_practical/data.py`
  abgedeckt (die zwei von heute Nachmittag plus diese). Reine
  Datenfetch-/Caching-Härtung, keine Order-/Risiko-/Entry-Exit-Logik
  angefasst. Nur `py_compile` geprüft (kein pandas/tradingview_ta in dieser
  Sandbox installierbar, kein echter Live-Lauf abgewartet) — ob das die
  verbleibenden Scan-Fehler tatsächlich stoppt, zeigt erst der nächste
  Bridge-Lauf, der auf einen wirklich kaputten TVC-Fetch trifft.
- **2026-09-03** [combined_strategy / cls_practical] **Der am 2026-09-02
  dokumentierte "OHLC vor dem Cachen validieren"-Fix war in Wahrheit nie im
  Code — jetzt tatsächlich umgesetzt, nachdem derselbe Fehler heute erneut
  auftrat.** Bridge-Monitor-Routine fand im heutigen Snapshot-Check den
  exakt gleichen `'>' not supported between instances of 'str' and 'float'`-
  Fehler zeitgleich in drei Beinen (`CTNL-Edge-Scan`, `Trend-Pullback-Scan`,
  `CLS-Practical-Scan`, alle 2026-09-03 13:13:40 laut `Funded-Portfolio-
  Bridge`-Snapshot) — derselbe Fehler, den der DASHBOARD-Eintrag vom
  2026-09-02 als "gehärtet" markiert hatte (Validierung numerischer OHLC-
  Spalten vor dem Cachen in `combined_strategy/data.py::fetch_timeframe()`).
  Beim Nachsehen im aktuellen Code existierte dort KEINE solche Validierung
  — `df.to_parquet(path)` cachte weiterhin ungeprüft, exakt wie vor dem
  damaligen Fund. Die damalige Beschreibung wurde offenbar nie tatsächlich
  umgesetzt (oder ist verlorengegangen). Jetzt wirklich ergänzt: neue
  `validate_ohlc_numeric()`-Hilfsfunktion in `combined_strategy/data.py`,
  prüft OHLC(V)-Spalten auf numerischen dtype VOR dem `to_parquet()`-
  Schreiben und wirft sonst einen `ValueError` statt die kaputten Daten zu
  cachen — dank der bestehenden `_retry()`-Wrapper (6 Versuche/8s, siehe
  Eintrag weiter unten) läuft das automatisch in einen frischen Fetch statt
  in einen dauerhaft kaputten Cache. Zusätzlich in `cls_practical/data.py`
  an den zwei Stellen ergänzt, die eigene, duplizierte Fetch-/Cache-Blöcke
  haben und NICHT über `fetch_timeframe()` laufen (`fetch_rate_instrument_
  m5_berlin` für BUND/USTBOND/UKGILT, `fetch_eurusd_entry_tf_berlin` für
  EUR/USD M1/M5/M15) — sonst wäre `CLS-Practical-Scan` weiterhin
  verwundbar geblieben. Reine Datenfetch-/Caching-Härtung, keine Order-/
  Risiko-/Entry-Exit-Logik angefasst. Nur `py_compile` auf beiden
  geänderten Dateien geprüft (kein pandas/dukascopy_python in dieser
  Sandbox installierbar, kein echter Live-Lauf abgewartet).
- **2026-09-03** [Funded-Portfolio-Bridge] **Scheduled-Task-Zeitlimit 14 -> 40
  Minuten angehoben, Diagnostik fuer bekannte vs. neue Scan-Fehler ergaenzt,
  OU-Modell-Nichtauftreten auf ttp1/iqmarkets2 aufgeklaert (kein Bug).**
  Beim Live-Beobachten des ersten Laufs nach dem Scan-Dedup-Umbau (Nutzerbitte
  "beobachte den Live Lauf") gefunden: der Lauf ab 14:00:00 wurde nach 15 Min.
  zwangsbeendet (`ExecutionTimeLimit: PT14M`, Task-Ergebnis 267009, kein
  sauberes "beendet" im Log) -- der Scan-Dedup-Umbau buendelt jetzt ALLE 6
  Scans fuer ALLE 4 Konten in einer Phase VOR der Kontoverarbeitung, wodurch
  ein Haenger dort (mehrere dukascopy-Retry-Erschoepfungen an diesem Tag)
  locker ueber 14 Minuten dauern kann -- Nebenwirkung des Umbaus, vorher
  haetten wenigstens frueher verarbeitete Konten ihre Order schon platziert
  gehabt. `MultipleInstances=IgnoreNew` verhindert zuverlaessig echte
  Ueberlappung (bestaetigt per Prozessliste), daher Zeitlimit einfach auf 40
  Minuten angehoben (Nutzerauftrag) statt das Retry-Budget zu kuerzen.
  Zusaetzlich `_record_scan_error()`/`_send_daily_summary()` erweitert:
  zaehlt jetzt getrennt, wie viele Scan-Fehler pro Bein dem bereits
  dokumentierten dukascopy-Bug (`_stream()` Zeile 219 ODER
  `dukascopy_python-Hang` ODER `KeyError(0)`) zuzuordnen sind vs. echten NEUEN
  Fehlern -- Tagesabschluss zeigt jetzt z.B. "ctnl_edge (2x, davon 1x
  bekannter dukascopy-Bug)" statt einer nackten Zahl. Per synthetischem Test
  verifiziert, inkl. sauberer Migration alter Nur-Zahl-Eintraege. Dabei auch
  geklaert, wieso OU-Modell auf den beiden neuen Konten (ttp1/iqmarkets2)
  bisher nichts tat: deren `account_start` liegt (durch die erst heute
  gelungene Erstverbindung) NACH dem heutigen OU-Modell-Tagessignal
  (Mitternacht) -- der bestehende account_start-Schutzfilter blendet das
  Signal fuer sie korrekt aus, kein Bug, loest sich mit dem naechsten
  Tagessignal von selbst. Nebenbefund: `ttp` platzierte FAST+ADI heute schon
  real, `iqmarkets` (noch auf dem alten, unabhaengigen Scan-Stand) nicht --
  genau die Divergenz, die der Scan-Dedup-Umbau kuenftig verhindern soll.
- **2026-09-03** [tradingview/data.py] **TradingView-Pro-Login entfernt —
  Ursache fuer taeglich hunderte `ERROR:tvDatafeed.main:error while signin`
  in Funded-Portfolio-Bridge + FK Instant Funding gefunden.** Nutzerfrage
  nach den taeglichen Datenfehlern (siehe DASHBOARD, "MT5 statt Dukascopy?")
  fuehrte zu diesem separaten Fund: TradingView verlangt seit einiger Zeit
  ein Captcha beim Passwort-Login, das die `tvDatafeed`-Bibliothek nicht
  loesen kann (offenes, seit 2024-12-07 ungeloestes Upstream-Issue,
  github.com/rongardF/tvdatafeed/issues/62, "recaptcha_required") — jeder
  Login-Versuch schlug seit mind. 2026-09-01 13:04 zuverlaessig fehl, ohne
  Bot-Ausfall (nur Log-Spam), da die Bibliothek intern anonym weiterlief.
  `_client()` in `tradingview/data.py` versucht den Login jetzt gar nicht
  mehr (anonymer Zugriff war laut `cls_practical/rates.py`-Docstring schon
  vor Einfuehrung des Pro-Logins nachweislich ausreichend, DE02Y/US02Y bis
  2014 zurueck). `tradingview/_secrets.py` entfernt (dadurch verwaist).
  Smoke-getestet: `fetch_ohlcv("DE02Y", "TVC", ...)` liefert saubere,
  aktuelle Daten ohne Fehlermeldung.
- **2026-09-03** [Funded-Portfolio-Bridge] **Redundante Scans behoben — 6
  Strategie-Scans laufen jetzt 1x pro Bridge-Lauf statt 1x pro Konto.**
  Umsetzung der bereits im DASHBOARD skizzierten Idee (Nutzerauftrag nach
  Ruecksprache: MT5 als Datenquellen-Ersatz geprueft und verworfen, da die 4
  TTP/IQ-Konten nur 9 der ~30 gebrauchten Instrumente abdecken — stattdessen
  die Redundanz selbst beseitigen). `run_once.py`: neue `run_shared_scans(end)`
  fuehrt alle 6 Scans (`pb._scan_gold_asb/_cls_practical/_trend_pullback/
  _ctnl/_ou_modell/_orb`) einmal aus und gibt pro Bein Ergebnis ODER
  Exception zurueck; `process_account_signals()` verarbeitet daraus nur noch
  (kein eigener Scan-Aufruf mehr), `main()` scannt einmal VOR der
  Konten-Schleife und reicht das Ergebnis an alle 4 Konten durch. Viertelt
  die dukascopy/tvDatafeed-Anfragen pro Zyklus; ein Scan-Fehler betrifft
  jetzt deterministisch alle 4 Konten gleich statt zufaellig nur eines
  (vorher beobachtet: "TTP 5 Fehler, IQ 0, reiner Zufall im Timing"). Per
  Smoke-Test verifiziert (`run_shared_scans()` direkt aufgerufen): lief
  fehlerfrei durch, isolierte 3 von 6 aktuell dukascopy-bedingt fehlschlagende
  Beine korrekt einzeln (siehe Eintrag oben zum `_stream()`-Bug — bereits
  bekannt, kein neuer Fehler). Kein echter Live-Lauf ueber Task Scheduler
  abgewartet.
- **2026-09-03** [Funded-Portfolio-Bridge] **Alle 4 Konten verbinden jetzt —
  IPC-Timeout-Saga nach fast 24h abgeschlossen.** Root Cause hatte am Ende
  ZWEI Teile: (1) **"DLL-Importe zulassen"** (Extras -> Optionen ->
  Experten-Berater) war in beiden neu installierten Terminals aus — eine
  von "Automatisierten Handel zulassen"/AutoTrading GETRENNTE Einstellung,
  die die `MetaTrader5`-Python-Bruecke selbst braucht; ohne sie verbindet
  sich das Terminal im Broker ganz normal (GUI zeigt korrektes Login), aber
  `mt5.initialize()` bekommt zuverlässig `IPC timeout`. Neu in
  `knowledge/areas/mt5-bot-deployment.md` (Schritt 2 + neuer Punkt 12)
  aufgenommen. (2) Selbst danach blieb EINER der zwei neu installierten
  Terminal-ORDNER strukturell defekt, UNABHAENGIG vom eingeloggten Konto
  (empirisch bestaetigt: Nutzer tauschte die Konten zwischen beiden
  Terminals, der "gesunde" Ordner blieb gesund, der "kranke" blieb krank —
  nie geklaert warum). Pragmatischer Fix statt weiterer Fehlersuche: Konten
  in `Funded-Portfolio-Bridge/config.py` dem Ordner zugewiesen, der
  nachweislich funktioniert (`ttp1`/504069845 -> Ordner "IQ MT5 Terminal -
  Konto1", `iqmarkets2`/15514 -> Ordner "TTP MT5 Terminal Konto1neu" —
  Ordnernamen jetzt bewusst irrefuehrend, im Code kommentiert). Ausserdem
  ausprobiert und wieder verworfen: Terminal-Verzeichnis-Kopien statt echter
  Installation (nicht die Ursache), Rechner-Neustart (behob nichts),
  `MetaTrader5`-Python-Paket-Upgrade 5.0.5735->5.0.6147 (Installation von
  einem laufenden `run_once.py`-Prozess blockiert, dann durch den DLL-Fund
  ueberholt — Upgrade am Ende nicht mehr noetig, alte Paketversion
  funktioniert mit dem finalen Fix einwandfrei). Verifiziert:
  `test_connection.py` zeigt alle 4 Konten (504072729/16054/504069845/15514)
  mit `Verbindung erfolgreich`, `AutoTrading: True`, plausible Balances.
  Naechster echter Live-Lauf (naechste 15-Min-Taktung) ist der erste
  produktive Test mit allen 4 Konten.
- **2026-09-03** [Weekly-Report] **Education-Report-Prompt um festen Punkt
  "Neues Wissen diese Woche (Papers/Ideen)" ergaenzt.** Nutzerwunsch: neu
  gesammeltes Research-Wissen (Papers, Strategie-Ideen) und Eintraege aus
  der DASHBOARD-Ideen-Inbox sollen regelmaessig im Weekly/Monthly Education
  Journal auftauchen, nicht nur beilaeufig beim Verarbeiten eines
  Clippings-Batches erwaehnt werden. `scripts/reports/weekly_report_prompt.md`
  Report 2 (Education) hatte dafuer noch keinen expliziten Punkt -- neuer
  Punkt 4 weist den (unbeaufsichtigten) Report-Generator an, `git log
  --since="7 days ago" -- knowledge/resources/ knowledge/projects/` sowie
  neue Ideen-Inbox-Eintraege in `knowledge/DASHBOARD.md` seit dem letzten
  Report zu pruefen und kurz zu nennen (Titel/Kernaussage, `Wikilink-Beispiel`-Link),
  auch wenn noch nichts Konkretes draus wurde. Nachfolgende Punkte 4-6 zu
  5-7 umnummeriert. `scripts/reports/monthly_report_prompt.md` verweist nur
  auf "gleiche Struktur wie Weekly" (kein eigener nummerierter Abschnitt),
  erbt die Ergaenzung deshalb automatisch, keine separate Aenderung noetig.
  Reine Prompt-/Markdown-Anpassung, kein Code -- erster echter Beweis ist
  der naechste automatische Sonntagabend-Lauf.

- **2026-09-02** [EK/Challenge/FK Instant Funding] **Tagesabschluss-Uhrzeit von
  21 auf 22 Uhr verschoben, alle 4 Kopien der Konstante.** Nutzerauftrag nach
  Nachfrage zur TTP/IQ-Zeitversatz-Ursache: der beobachtete 1h-Versatz kam vom
  dukascopy-Hang (bereits gefixt), 22 Uhr war aber ohnehin die vom Nutzer
  urspruenglich gewuenschte Zielzeit fuer den gemeinsamen Tagesabschluss aller
  3 Portfolios. `DAILY_SUMMARY_HOUR_LOCAL`/`DAILY_SUMMARY_HOUR` 21->22 in
  `EK-Portfolio-Bridge/run_once.py`, `Funded-Portfolio-Bridge/run_once.py`,
  `fk_instant_funding/paper_bot.py`, `challenge_portfolio/paper_bot.py`
  (letzterer aktuell nicht scheduled, nur fuer Konsistenz mitgezogen).
  Strukturelle Feinsynchronisierung (Funded-Portfolio-Bridges 4 Konten
  parallel statt sequenziell verarbeiten) bewusst NICHT umgesetzt -- Nutzer
  will erst den naechsten echten 22-Uhr-Tagesabschluss beobachten, bevor
  entschieden wird, ob der verbleibende Minuten-Versatz noch stoert. Nur
  `py_compile`-geprueft, kein echter Live-Lauf abgewartet.
- **2026-09-02** [Prozess/CLAUDE.md] **Neue Standardregel: nicht-offensichtliche
  Erkenntnisse proaktiv in die Memory statt nur auf Zuruf.** Nutzeranstoß:
  Frage, ob es für den Weekly-Checkup-Education-Report ("Meine Main
  Erkenntnisse") schon einen Standardprozess gibt oder ob dafür jedes Mal
  ein expliziter Befehl nötig ist — Anlass war der zuvor manuell
  festgehaltene ORB-Per-Konto-Exit-Divergenz-Fund (siehe Memory
  `orb-per-account-exit-divergence-20260902`). Nutzerentscheid (per
  Rückfrage): feste Regel statt Zuruf-only. `CLAUDE.md` Punkt 7 ergänzt
  (Operative Übersicht) — Architektur-Erkenntnisse/überraschendes
  Systemverhalten/wiederkehrende Muster künftig eigenständig als
  Memory-Eintrag (Typ `project`) festhalten, da der wöchentliche
  `Forex-Weekly-Report`-Task laut `scripts/reports/weekly_report_prompt.md`
  für den Education-Report automatisch `MEMORY.md` liest. Abgrenzung zur
  Ideen-Inbox (Punkt 5, unentschiedene künftige Arbeit) explizit vermerkt.
- **2026-09-02** [Prozess/CLAUDE.md] **Punkt 7 präzisiert: Schwelle statt
  "jeder Fund".** Nutzer-Feedback direkt im Anschluss an obigen Eintrag:
  nicht jede Kleinigkeit soll in die Memory, nur spürbar größere
  Fortschritte/Optimierungen/"spannende" Themen — UND/ODER wenn der Nutzer
  sichtbar positiv reagiert (auch bei einem für sich kleineren Fund gilt
  die Reaktion dann als eigenständiger Auslöser). Zwei Signale statt eins,
  je eins reicht; im Graubereich lieber kurz anbieten statt schweigend
  übergehen oder schweigend jede Kleinigkeit mitschreiben. Routine-
  Änderungen bleiben wie zuvor nur im Changelog (Punkt 1), nicht in der
  Memory.
- **2026-09-02** [Prozess/CLAUDE.md] **Punkt 7 nochmal präzisiert: im
  Zweifelsfall aktiv fragen statt nur "anbieten".** Nutzer-Feedback direkt
  im Anschluss: bei unklaren Fällen (Fund wirkt bedeutsam, aber keine
  klare Nutzerreaktion) soll Claude explizit nachfragen, ob geloggt werden
  soll, statt es nur beiläufig zu erwähnen/anzubieten. Eindeutige Fälle
  (Schwelle klar erfüllt) weiterhin ohne Rückfrage direkt in die Memory.
- **2026-09-02** [EK-Portfolio-Bridge] **Risiko-Deckel-Skip-Warnungen spammten
  bei jedem Lauf identisch weiter, jetzt einmal pro Tag+Signal.**
  Nutzer-Feedback (Screenshot: dieselbe "[EK-ORB] Risiko-Deckel erreicht,
  SP500/US30-Entry uebersprungen"-Meldung kam 22:37 und 22:49 wortgleich
  wieder). Root Cause: `check_cap()`-Skip-Pfad in 5 Bein-Executors
  (`legs/gold_asb`, `legs/btc_ema_cross`, `legs/ctnl_edge`, `legs/ou_modell`,
  `legs/ny_open_orb`) rief `queue_message()` bisher UNBEDINGT bei jedem
  einzelnen Lauf auf, ohne jede Dedup-Logik -- anders als z.B. Funded-
  Portfolio-Bridges "missed"-Signal-Tracking. Fix: neue
  `already_notified_risk_cap_skip(leg_key, day)` / `mark_risk_cap_skip_
  notified(leg_key, day)` in `core/state_store.py` (SQLite-Tabelle
  `risk_cap_notified`, PK `(day, leg_key)`), in allen 5 Executors vor dem
  `queue_message()`-Aufruf eingebaut -- `leg_key` traegt die volle
  Signal-Granularitaet (z.B. `orb_SP500`, `ou_modell_ADI`,
  `ctnl_continuation`). Per Smoke-Test gegen isolierte Test-DB verifiziert
  (initial ungemeldet -> nach Markierung gemeldet -> unabhaengige
  Instrumente getrennt getrackt -> doppeltes Markieren harmlos -> neuer Tag
  setzt zurueck). Kein echter Live-Lauf seitdem abgewartet.
- **2026-09-02** [EK-Portfolio-Bridge] **Per-Bein-Timeout in allen Live-Bridges
  umgesetzt (Nutzerauftrag) — dabei eigene Duplikate wieder entfernt, da eine
  parallele Session dieselbe Absicherung bereits an der richtigen Stelle
  gebaut hatte.** Erst versucht: einen `_with_timeout()`-Wrapper direkt um
  jeden Bein-Scan in `Funded-Portfolio-Bridge/run_once.py`,
  `EK-Portfolio-Bridge/run_once.py` und `FKInstantFunding-MT5-Bridge/
  run_once.py` gelegt. Beim Pruefen aufgefallen: der eigentliche Fund (siehe
  Eintrag weiter unten, `_call_with_timeout()` in allen 3 `_retry()`-Kopien)
  war bereits genau dafuer gebaut, nur eine Ebene tiefer (innerhalb `_retry()`,
  90s x 6 Versuche). Mein aeusseres 120s-Limit haette diese geduldigere
  Mehrfachversuch-Logik fuer GENAU die Beine, die `_retry()` nutzen
  (gold_asb/cls_practical/ctnl_edge), vorzeitig abgewuergt statt sie ergaenzt.
  Deshalb: Funded-Portfolio-Bridge und FKInstantFunding-MT5-Bridge komplett
  zurueckgesetzt (dort nutzen ALLE Beine `_retry()`, der aeussere Wrapper war
  dort 100% redundant). In EK-Portfolio-Bridge/run_once.py::`_run_leg()`
  blieb der Wrapper, ABER auf `LEG_TIMEOUT_S=600` (statt 120) angehoben --
  muss ueber `_retry()`s eigenem ~588s-Worst-Case liegen, damit er die 3
  dukascopy-Beine nicht stoert, deckt dafuer zusaetzlich die 6 EK-Beine ab,
  die KEIN `_retry()` verwenden (orb, trend_pullback, gold_silver,
  btc_ema_cross, ou_modell) und bisher gar keinen Hang-Schutz hatten -- das
  ist der einzige echte Mehrwert gegenueber dem bereits vorhandenen Fix.
  Alle 3 Dateien `py_compile`-geprueft, kein echter Live-Lauf mit einem
  Hang seitdem abgewartet.
- **2026-09-02** [EK/Challenge/FK Instant Funding] **Harter Timeout gegen den
  dukascopy_python-Hang in allen 3 `_retry()`-Kopien (`ek_portfolio/paper_bot.py`,
  `challenge_portfolio/paper_bot.py`, `fk_instant_funding/paper_bot.py`).**
  Nutzerentscheid nach Nachfrage zu inkonsistenten Tagesabschluessen (TTP
  Konto2 zeigte 5 Scan-Fehler heute, IQ Markets 0 -- reiner Zufall, da jedes
  der 4 Funded-Portfolio-Bridge-Konten dieselben 6 Scans unabhaengig
  voneinander neu zieht, 4-fache Exposition gegenueber der bekannten
  Bibliotheks-Instabilitaet). Neue Funktion `_call_with_timeout()`: fn()
  laeuft in einem Daemon-Thread, `_retry()` wartet pro Versuch maximal
  `timeout_seconds=90.0`; ueberschritten, zaehlt der Versuch als
  gescheitert (TimeoutError) und wird wie jeder andere Fehler behandelt --
  identisches Verhalten fuer den bereits bekannten KeyError/TypeError-Fall,
  zusaetzlich jetzt auch fuer den STILLEN Hang (23 Prozesse liefen dadurch
  frueher am Abend stundenlang fest, siehe Eintrag weiter unten). Ein echter
  Thread-Abbruch ist in Python nicht moeglich -- der haengende Aufruf laeuft
  im Hintergrund weiter, aber `daemon=True` verhindert, dass er den Prozess
  am sauberen Beenden hindert. Verifiziert per eigenem Smoke-Test
  (`hangs_forever()` mit `time.sleep(999)`): `_retry()` bricht nach exakt der
  erwarteten Zeit sauber mit `TimeoutError` ab, normales Retry-Verhalten
  (transiente Fehler) unveraendert korrekt, UND der Prozess beendet sich
  trotz des im Hintergrund weiterlaufenden Hang-Threads sofort sauber (Exit
  Code 0, keine Leiche zurueckgelassen). Alte, mit dem ungefixten Code
  gestartete haengende Prozesse (22:00/22:06/22:55/23:15) danach beendet --
  naechster Scheduled-Task-Lauf nutzt automatisch den neuen Code. Kein echter
  Live-Lauf mit echtem dukascopy-Hang seitdem abgewartet (nur der
  synthetische Smoke-Test), aber Mechanismus isoliert bewiesen.
- **2026-09-02** [Funded-Portfolio-Bridge] **Root Cause fuer die IPC-Timeouts der
  zwei neuen Konten gefunden: kopierte statt echt installierte Terminals.**
  Ausfuehrlich getestet (isolierter Python-Prozess, sequenzielles statt
  gleichzeitiges Starten, `portable=True`, bis zu 60s Wartezeit/Timeout,
  Terminal-Ersatz FK2->CLSPractical-Kopie): alle Varianten weiterhin
  `IPC timeout`, obwohl das Terminal-Fenster nachweislich korrekt eingeloggt
  ist und AutoTrading an ist (`term.trade_allowed=True`) -- einmal bestaetigt
  per direktem `account_info()`-Check NACH einem als "fehlgeschlagen"
  gemeldeten `login()`: Server-seitig hatte der Login tatsaechlich geklappt,
  nur die Bestaetigung kam nicht rechtzeitig zurueck. Die 2 URSPRUENGLICHEN
  Konten (Login 504072729, 16054) verbinden dagegen bei JEDEM Test sofort
  fehlerfrei. Vermutete Ursache: eine echte MT5-Installation registriert
  etwas fuers Python-IPC, das eine reine Verzeichnis-Kopie (wie meine
  `TTP MT5 Terminal - Konto3`/`IQ MT5 Terminal - Konto2`, urspruenglich aus
  den ruhenden FK1/FK2-Installationen kopiert) nicht mitbringt -- alle 4
  bisher funktionierenden Terminals in diesem Projekt sind echte
  Installationen. Versuch, `C:\Users\andre\Downloads\mt5setup.exe` per
  `/auto /dir=...` still in einen neuen Ordner zu installieren, schlug fehl
  (Installer liess sich nicht zuverlaessig per Kommandozeile steuern).
  **Kein Order wurde in der gesamten Fehlersuche riskiert** -- jeder
  Fehlversuch endete sauber mit einem Verbindungsfehler, nie mit einer
  falschen Order; die 2 bestehenden Live-Beine sind komplett unberuehrt.
  Nutzerentscheid: macht die 2 echten MT5-Installationen selbst (GUI,
  ~60 Sek. pro Konto) statt weiterer automatisierter Versuche -- ich trage
  danach die neuen Pfade in `config.py` ein und teste erneut.
- **2026-09-02** [OU-Modell-Scanner] **3 Tagesscans (15:35/18:35/21:35) senden
  jetzt eine Telegram-Zusammenfassung** (Nutzerauftrag, nachdem entschieden
  wurde, `OU-Modell-ScannerHourly` fuer die Streamlit-Seite weiterlaufen zu
  lassen statt komplett auf Telegram umzustellen). Neu: `ou_paper_backtest/
  telegram_notify.py` + `telegram_config.py`/`.example.py` (identisches
  Muster wie `fk_instant_funding/telegram_notify.py`, `telegram_config.py`
  in `.gitignore`, gleicher Bot/Chat wie alle anderen Bots dieses Users).
  `scanner.py::main()` sendet nur bei den 3 genannten Zeiten (+/-10 Min.
  Toleranz) eine Nachricht mit Signalen je Markt oder "Keine Signale" --
  NICHT bei den anderen 5 taeglichen Task-Scheduler-Laeufen. Der
  `telegram_notify`-Import ist bewusst in `try/except ImportError`
  gekapselt: `challenge_portfolio/paper_bot.py::_import_ou_paper_backtest()`
  laedt `scanner.py` per `importlib.util.spec_from_file_location` OHNE
  `ou_paper_backtest/` auf `sys.path` -- dieser Pfad treibt die LIVE
  Funded-Portfolio-Bridge (OU-Modell-Bein), ein harter Import haette sie
  kaputt gemacht. Verifiziert: `py_compile` aller 4 neuen/geaenderten
  Dateien, Zeitfenster-/Format-Logik isoliert getestet, UND der isolierte
  Live-Lade-Pfad (`_import_ou_paper_backtest()`) laeuft weiterhin fehlerfrei
  mit dem No-Op-Fallback.
- **2026-09-02** [Streamlit/Portfolio-Konstruktion] **Neuer Tab "Challenge-Portfolio
  (live)" auf `app_pages/portfolio_construction.py`** — Nutzerauftrag, EK+Challenge
  mit aktuellen Backtest-Zahlen zu aktualisieren. Bisher zeigte die Seite nur einen
  generischen "FK-Portfolio"-Tab (aeltere 5-Bein-Konzeptstufe ohne ORB), obwohl
  `portfolio_construction/results/challenge_portfolio_6leg.json` (aus
  `scripts/research_challenge_portfolio_6leg.py`) bereits die Zahlen der tatsaechlich
  LIVE laufenden 6-Bein-Kombination (Gold ASB, CLS Practical, OU-Modell, Trend
  Pullback, CTNL Edge, NY-Open ORB) enthielt, aber nirgends in der UI verdrahtet war.
  Neuer Tab zeigt: TTP/IQ-Markets-Regelwerk-Badges (Tageslimit/Gesamt-Drawdown/
  Gewinnziel), alle 6 aktuellen Beine, 5-vs-6-Beine-Vergleich (Outcome-Bar +
  Median-Tage-bis-Ziel je Regelwerk), Kennzahlen-Kacheln, Equity-Kurve. Per
  Playwright-Browsertest verifiziert (beide Regelwerke durchgeklickt, gescrollt,
  `stException`-Check + Konsolen-Fehler-Check) — keine Fehler. EK-Tabs nicht
  angefasst, wirkten bereits aktuell (CTNL-Erweiterung als 8. Strategie schon
  vorhanden). **Nachtrag selber Abend:** Nutzer meldete "ORB-Bein fehlt
  komplett" — Ursache war Tab-Position: der neue Tab sass an 6. Stelle neben
  dem aehnlich benannten alten "FK-Portfolio"-Tab (bewusst ohne ORB), leicht
  verwechselbar/uebersehen. Tab auf Nutzerwunsch ("verschiebe die finale
  aktuell genutzte Konfiguration ganz oben") an die ERSTE Stelle verschoben
  (`tab_challenge` jetzt zuerst in `st.tabs([...])` UND im Lazy-Dispatch,
  Label ergaenzt um "6 Beine" fuer sofortige Erkennbarkeit) — Streamlit
  oeffnet den ersten Tab automatisch, ORB ist damit ohne Klick sichtbar. Per
  Playwright erneut verifiziert (kein Tab-Klick noetig, Screenshot zeigt
  Challenge-Tab direkt offen mit allen 6 Beinen inkl. NY-Open ORB) — keine
  Fehler.
- **2026-09-02** [Funded-Portfolio-Bridge] **OU-Modell-Bein: Signal-Alter-Bremse
  gefixt, Preis-Abweichungs-Check ergaenzt, Prozess-Stau bereinigt, manueller
  Nachhol-Lauf gebaut — kein neuer Entry heute moeglich (NYSE zu + 2 Konten
  ohne Verbindung).** Nutzeranstoss: "bei OU macht diese Bremse keinen Sinn".
  Root Cause: `MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY=60` in `run_once.py::
  _process_leg()` verglich bei OU-Modell (Tages-Bar-Datum als `entry_time`,
  kein Intraday-Zeitstempel wie bei ORB) strukturell IMMER >60 Min. seit
  Mitternacht des Signaltags — hat NICHT vor alten Signalen geschuetzt,
  sondern JEDES frische OU-Modell-Signal blockiert (identischer Bug-
  Charakter wie der `include_open_positions`-Fund vom selben Tag, nur einen
  Schritt weiter). Referenz `EK-Portfolio-Bridge/legs/ou_modell/executor.py`
  hat gar keine Alters-Pruefung, nur das NYSE-Gate. Fix (Nutzerentscheid,
  nicht komplette Ausnahme): neue `MAX_SIGNAL_AGE_DAYS_FOR_ENTRY_OU_MODELL=2`
  fuer `leg.startswith("ou_modell")`, Minuten-Regel unveraendert fuer alle
  anderen Beine. Zusaetzlich (Nutzerentscheid): neuer Preis-Abweichungs-Check
  `MAX_OU_MODELL_ENTRY_DEVIATION_PCT=0.035`, identisch zu EK's bereits live
  bewaehrtem `OU_MODELL_MAX_ENTRY_DEVIATION_PCT` — Entry nur, wenn der
  Live-Kurs (`mt5.symbol_info_tick`) noch max. 3,5% vom Signal-Kurs entfernt
  ist, sonst "missed" statt einem laengst gelaufenen Kurs hinterherzujagen.
  Beim Nachpruefen zusaetzlich gefunden: **23 haengende `python.exe`-Prozesse**
  (`run_once.py` UND `fk_instant_funding.paper_bot`, Start alle 15 Min von
  15:45 bis 21:45 durchgezogen, keiner je beendet) — vermutlich derselbe
  bereits dokumentierte `dukascopy_python`-Bug (siehe DASHBOARD.md), diesmal
  ohne Timeout komplett blockierend statt nur langsam. Alle 23 beendet
  (`Stop-Process`); ein sofortiger frischer `run_once.py`-Testlauf haengte
  SOFORT wieder in `gold_asb` fest — **Root Cause NICHT behoben, nur der
  Rueckstau bereinigt**, naechster Scheduled-Task-Lauf haengt vermutlich
  erneut. Fuer den Nachholbedarf ("hole die Entries aller Aktien nach")
  deshalb neues Wegwerf-Skript `catchup_ou_modell.py` gebaut — ruft NUR den
  OU-Modell-Scan+Entry-Block auf, an den haengenden Beinen (gold_asb/
  cls_practical/trend_pullback/ctnl) vorbei, sonst identische Logik
  (State/Sizing/Risk-Gate) wie `run_once.py`. Lauf heute Abend: `ttp`/
  `iqmarkets` (Demo) verbanden sauber, aber `_nyse_is_open()` war bereits
  False (Handelsschluss) — keine neuen Entries erlaubt, nur Exit-Pfad aktiv.
  `ttp1` (echtes Geld, Konto 1)/`iqmarkets2` weiterhin `IPC timeout` — GUI-
  Login (siehe DASHBOARD.md) noch nicht nachgeholt. Ergebnis: **heute Abend
  keine einzige Order gesendet**, weder automatisch noch manuell. Nur
  `py_compile`-geprueft, kein echter Order-Versand verifiziert.
- **2026-09-02** [Funded-Portfolio-Bridge] **Verbindungstest der zwei neuen
  Konten deckt Terminal-Verwechslung auf, kein Order gesendet.**
  `test_connection.py` (reiner Lese-Test) gegen alle 4 Konten gelaufen: die
  zwei bestehenden Konten OK (dabei nebenbei Trade-Modus geprueft: TTP
  Konto 2 ist `demo`, IQ Markets 16054 ist laut MT5 selbst `real`, trotz
  Namens "Demo Challenge"). Die zwei neuen Terminals (`TTP MT5 Terminal -
  Konto3`, `IQ MT5 Terminal - Konto2`, frische Kopien der ruhenden FK1/FK2-
  Installationen) zeigten wiederholt IPC-Timeouts bzw. verbanden sich mit
  dem JEWEILS FALSCHEN Konto (Konto3-Pfad landete bei Login 15514) — die
  eingebaute Kontonummer-Verifikation (identisch zu `executor.py::connect()`)
  hat das jedes Mal erkannt und abgebrochen, **kein Order gesendet**. Ursache
  vermutlich eine gemeinsame Windows-weite MT5-Session-Ablage zwischen zwei
  frischen Kopien desselben Builds, verstaerkt durch mehrere gleichzeitig
  gestartete Terminal-Prozesse. Fix nicht automatisiert moeglich -- braucht
  einmaligen manuellen GUI-Login (File -> "Login to Trade Account") in jedem
  der zwei neuen Terminals, siehe DASHBOARD.md. Beide Terminals laufen
  bereits (manuell gestartet).
- **2026-09-02** [Portfolio-Konsolidierung] **Nutzer bestaetigt: TTP
  Konto 1 (504069845, echtes Geld) + IQ Markets Login 15514 sollen DOCH in
  die Funded-Portfolio-Bridge (`state_id="ttp1"`/`"iqmarkets2"`) — beide
  waren zuvor als "anderweitig vergeben" gestoppt worden (siehe Eintrag
  weiter unten). Nutzer will bewusst konsolidieren ("bester Usecase im
  Vergleich zu allen Einzelstrategien"). Umgesetzt: Konto 1 aus
  `OU-Modell-MT5-Bridge/config.py::ACCOUNTS` entfernt (Bridge hat damit
  JETZT KEINE Konten mehr — faktisch aufgeloest), Login 15514 aus
  `GoldASB-MT5-Bridge/config.py` UND `BTC-EMA-Cross-Bridge/config.py`
  entfernt (beide hatten es sich bisher geteilt). Alte Konfigurationen
  jeweils als Kommentar aufgehoben (kein Git-Verlauf in diesen Ordnern).
  Neue Terminals: `TTP MT5 Terminal - Konto3` fuer Konto 1 (dediziert,
  ersetzt das bisher genutzte `C:\Program Files\TTP MT5 Terminal\`), `IQ
  MT5 Terminal - Konto2` fuer Login 15514 (dediziert, ersetzt das bisher
  mit GoldASB/BTC-EMA-Cross geteilte `C:\Program Files\MetaTrader 5\`).
  `symbol_map` je 1:1 vom jeweiligen Schwesterkonto uebernommen (gleicher
  Server), NICHT per `check_symbols.py` fuer die neuen Konten selbst
  verifiziert. **Noch offen**: AutoTrading in beiden neuen Terminals
  manuell verifizieren (siehe DASHBOARD.md) — bis dahin bricht
  `executor.py::connect()` fuer diese zwei Konten sauber mit Fehlermeldung
  ab, sendet aber keine Order. Ausserdem im selben Zug auf Nutzerauftrag
  ("nur noch die Portfolios als offene Strategien") alle verbliebenen
  Einzelstrategien/-Tests ausserhalb der drei Portfolios (EK, Funded/
  Challenge, FK Instant Funding) als aufgeloest markiert — Live-Check
  (`Get-ScheduledTask`) bestaetigt: bis auf `OU-Modell-ScannerHourly`
  waren alle bereits `Disabled` (BTC-EMA-Cross-Bridge/-Scan, CLS-Practical-
  Bridge/-Scan, CTNL-Edge-FK-Paper, CTNL-Edge-MT5-Bridge, Gold-ASB-Scan,
  GoldASB-MT5-Bridge, OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat). Details
  siehe DASHBOARD.md.
- **2026-09-02** [Funded Portfolio] **Echtgeld-Aenderung: echter Stage-6-
  Teilausstieg fuer die ORB-Beine implementiert** (Nutzerauftrag "Setze um",
  nachdem der EK-vs-Challenge-Architekturunterschied besprochen wurde). Neu
  in `Funded-Portfolio-Bridge/executor.py`: `partial_close_position()` (echter
  Teil-Close per `TRADE_ACTION_DEAL` auf dasselbe Ticket) + `move_stop_to_
  breakeven()` (echtes `TRADE_ACTION_SLTP`, ueber das bestehende `_send_order()`-
  Sicherheitsnetz). Neu in `run_once.py`: `_manage_orb_partial_exits()` -
  pollt bei jedem 15-Min-Lauf offene ORB-Positionen gegen ihr aus entry_price/
  sl berechnetes Teilausstiegs-Level (liest `partial_exit_r`/-fraction/
  move_stop_to_be_after_partial live aus `challenge_portfolio/paper_bot.py::
  ORB_EXIT_CFG_BY_INSTRUMENT`, die jetzt ebenfalls diese Felder traegt - Single
  Source of Truth, identisch zu `app_pages/ny_open_orb_portfolio.py`/
  `EK-Portfolio-Bridge/config.py`). Neue Positionen bekommen ein `partial_done`-
  Flag; ein VOR diesem Feature eroeffnetes Ticket hat den Key nicht und wird
  deshalb NIE rueckwirkend angefasst (`.get(..., True)` faellt sicher auf
  "nichts tun" zurueck) - nur neue Entries ab jetzt. **19 gemockte Logik-Tests**
  (Treffer/kein Treffer, bereits erledigt, Legacy-Position ohne den State-Key,
  Long+Short, DRY_RUN-Verzweigung, zu-kleines Restvolumen) bestanden, KEIN
  echter MT5-Kontakt. **Noch nicht live verifiziert** - der naechste Bridge-
  Lauf, der wirklich eine offene ORB-Position ueber ihr Teilausstiegs-Level
  laufen sieht, ist der erste echte Test. Damit haben jetzt alle drei aktiven
  ORB-Traeger (EK, Challenge, FK Instant Funding) denselben Stand INKLUSIVE
  Teilausstieg.
- **2026-09-02** [Funded-Portfolio-Bridge] **Versuch, zwei weitere Konten
  anzubinden, GESTOPPT vor dem Scharfschalten** (Nutzerauftrag, TTP-Login
  504069845 + IQ-Login 15514 vom Nutzer genannt): Cross-Check gegen andere
  Bridge-Configs ergab, dass BEIDE Logins bereits anderweitig vergeben
  sind — TTP 504069845 ist `OU-Modell-MT5-Bridge`'s echtes Live-Konto
  "Konto 1" (dessen `config.py`: "ab jetzt echte Orders"), IQ
  15514/Sm6^znlf/BeyondIQCapital-Server ist das von `GoldASB-MT5-Bridge` +
  `BTC-EMA-Cross-Bridge` geteilte Demo/Eval-Konto, nicht das hier bereits
  aktive IQ-Konto 16054. `config.py`-Eintrag NICHT vorgenommen (nur ein
  Kommentar mit dem Befund hinterlassen); zwei neue, ungenutzte
  MT5-Terminal-Kopien (`TTP MT5 Terminal - Konto3` / `IQ MT5 Terminal -
  Konto2`, aus den ruhenden `MT5 Terminal - FK1`/`FK2`-Installationen)
  bleiben vorsorglich liegen, falls sich die Konten nach Klaerung als
  korrekt herausstellen. Klaerung mit Nutzer ausstehend (siehe
  DASHBOARD.md).
- **2026-09-02** [System] **Cloud-Routine "Forex-Backtesting Bridge Error
  Monitor" eingerichtet** (`trig_01PN2SADKXZDkvgs3Zkno4xe`, 3x werktags
  9/15/21 Uhr UTC = 11/17/23 Uhr Berlin, vor/waehrend/nach NYSE-Handel):
  liest `bridge_status/snapshot.json` (siehe Bridge-Watchdog-Eintrag oben)
  und CHANGELOG/DASHBOARD, um Doppelmeldungen zu vermeiden. Zweistufige
  Autonomie-Policy (Nutzerauftrag): Fehler mit Traceback INNERHALB des
  Repos (z.B. `combined_strategy/data.py`, `challenge_portfolio/
  paper_bot.py`) darf sie selbststaendig fixen (`py_compile` + Commit+Push
  + CHANGELOG-Eintrag), aber NUR wenn keine Order-/Risiko-Logik betroffen
  ist. Alles ausserhalb des Repos (die eigentlichen Bridge-Ordner, fuer die
  Routine unsichtbar) oder mit Order-/Risiko-Bezug: nur dokumentieren als
  neuer Punkt in `DASHBOARD.md` "🔍 Braucht deine Bestätigung", nie selbst
  aendern. Bei nichts Neuem: stiller Lauf, keine Aenderung.
- **2026-09-02** [Shared] `_retry()` (3 identische Kopien: `ek_portfolio/
  paper_bot.py`, `challenge_portfolio/paper_bot.py`, `fk_instant_funding/
  paper_bot.py`) von 3 Versuchen/5s Pause auf 6 Versuche/8s Pause erhoeht
  (Nutzerentscheid nach dem CLS-Practical/dukascopy_python-Fund von heute
  Morgen: mehr Retries statt yfinance-Fallback). Root Cause bleibt ein Bug
  in der Drittanbieter-Bibliothek selbst (`dukascopy_python/__init__.py::
  _stream()` Zeile 219), nicht behebbar — nur die Toleranz dagegen erhoeht.
  Nur `py_compile`-geprueft.
- **2026-09-02** [Funded Portfolio] **Echtgeld-Aenderung**: neuer "Signal zu
  alt"-Schutz in `_process_leg()` (`MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY = 60`)
  — ein Signal, dessen Signalzeit mehr als 60 Min. zurueckliegt, wird beim
  ersten Erkennen als "missed" vermerkt statt real zum laengst gelaufenen
  Kurs zu jagen (genau das Muster vom ersten Gold-ASB-Entry heute Nacht:
  05:15 UTC Signal, 09:30 UTC Fill). Nutzerentscheid nach Rueckfrage. Nur
  `py_compile`-geprueft, kein echter Live-Lauf abgewartet.

- **2026-09-02** [NY-Open ORB / FK Instant Funding] `fk_instant_funding/paper_bot.py`
  auf Nutzerauftrag ("voller Umfang", da kein Echtgeld-Risiko) als letzte
  verbliebene ORB-Kopie synchronisiert: `ORB_EXIT_CFG` durch
  `ORB_EXIT_CFG_BY_INSTRUMENT` ersetzt — NASDAQ `target_mode=None` (EOD-Exit)
  UND Stage-6-Teilausstieg (1.5R/2R, 50%, Rest auf Breakeven) fuer alle drei
  Instrumente, identisch zu `app_pages/ny_open_orb_portfolio.py`/
  `EK-Portfolio-Bridge/config.py`. Anders als bei `challenge_portfolio/
  paper_bot.py` (Funded-Portfolio-Bridge sendet echte Orders, kann nur
  ganz/offen pro Ticket) ist der Teilausstieg hier unproblematisch, da dieses
  Modul nur FKInstantFunding-MT5-Bridge (reiner Order-Planer ohne echten
  Order-Versand) und FK-Instant-Funding-Paper (reine Simulation) treibt.
  Smoke-getestet mit gecachten Daten (422 Trades, 2026-07-15): NASDAQ zeigt
  keinen `exit_reason="target"` mehr (nur noch `stop`/`session_end`),
  `had_partial_exit`-Rate 34.2-44.8% je Instrument, 0 NaN-r_multiple. Damit
  sind alle drei aktiven ORB-Traeger (EK-Portfolio-Bridge, Funded-Portfolio-
  Bridge/Challenge, FK Instant Funding) auf demselben Stand — nur
  `ek_portfolio/paper_bot.py` (pausiert) bewusst nicht angefasst.
- **2026-09-02** [Streamlit] **Portfolio-Bridge-Status-Seiten neu gebaut,
  alte Einzelstrategie-Live-Logs entfernt** (Nutzerauftrag: "wir fokussieren
  uns jetzt erstmal nur noch auf die portfolio Arbeit"). Entfernt (per
  `git rm`, aus `app.py`/`section_live_logs.py` ausgetragen): `ou_modell.py`,
  `cls_practical_live_log.py`, `btc_ema_cross_live_log.py`,
  `gold_asb_live_log.py`, `ek_portfolio_live_log.py` (dangling
  `st.page_link` in `cls_cross_filter.py` mit entfernt). Neu:
  `app_pages/_bridge_status_data.py` (gemeinsame Lade-/Render-Helfer) +
  drei Detail-Seiten (`ek_portfolio_bridge_status.py`,
  `funded_portfolio_bridge_status.py` mit TTP/IQ-Konto-Kacheln,
  `fk_instant_funding_bridge_status.py`) + neu fokussierte
  `section_live_logs.py`-Übersicht ("Portfolio-Bridges"). Alle lesen
  ausschließlich `bridge_status/snapshot.json` (siehe naechster Eintrag),
  rufen nie selbst MT5/eine Bridge auf — identisches "Collector laeuft
  lokal, Seite liest nur committete Daten"-Muster wie jede bisherige
  Live-Log-Seite. Verifiziert per `streamlit.testing.v1.AppTest` durch die
  volle `app.py`-Navigation (alle 4 Seiten: keine Exceptions, korrekte
  Metrik-/Status-Werte) — ausserdem kurz per echtem `streamlit run`
  gegengeprüft. Committet+gepusht (`00f31a9`) — dabei einen eigenen Fehler
  korrigiert: die `git rm`-Löschungen waren versehentlich in einen der
  automatischen Bridge-Watchdog-Commits gerutscht und bereits ohne die
  zugehörigen `app.py`-Anpassungen gepusht (`git add <snapshot>` staged
  nur die eine Datei ZUSÄTZLICH zum bereits Gestagten, ersetzt es nicht) —
  Remote war kurzzeitig inkonsistent (Seiten gelöscht, aber noch
  registriert), jetzt behoben.
- **2026-09-02** [Bridge-Watchdog] Um Status-Snapshot erweitert
  (Nutzerauftrag): schreibt jetzt zusätzlich `bridge_status/snapshot.json`
  im Forex-Backtesting-Repo (letzter Lauf/Status je Bridge, bei
  Funded-Portfolio-Bridge pro Konto TTP/IQ getrennt via Banner-Zeilen-
  Erkennung im Log, letzte Equity-/Fehler-Zeile, letzte ~12 Entry/Exit/
  Fehler-Ereignisse) und committet+pusht sie — identisches Muster wie
  `ou_paper_backtest/scanner.py` seit Wochen mit seinen eigenen Ergebnissen.
  Bewusst NICHT die Bridges selbst pushen lassen (kein Git im Order-Pfad).
  Ermöglicht sowohl die neuen Streamlit-Statusseiten als auch eine
  zukünftige Cloud-Routine (kein lokaler Dateizugriff, aber GitHub-Zugriff)
  echten Status zu lesen. Zwei Bugs beim ersten Testlauf gefunden+behoben:
  (1) Konto-Aufsplittung nutzte `.match()` statt `.search()` (Banner-Zeilen
  haben einen Zeitstempel-Prefix, `.match()` ankert immer an Position 0) —
  lief anfangs komplett leer durch; (2) `_EVENT_RE` ohne Wortgrenzen matchte
  faelschlich Substrings wie "entry" in "fetch_eurusd_**entry**_tf_berlin".
  Mehrfach real committet+gepusht (3x waehrend des Testens, jeweils
  erfolgreich).

- **2026-09-02** [Shared/Data] `combined_strategy/data.py::fetch_timeframe()`
  validiert jetzt vor dem Cachen, dass die OHLC-Spalten numerisch sind —
  bester Erklaerungsversuch fuer den `'>' not supported between instances
  of 'str' and 'float'`-Fund von heute Morgen (nicht reproduziert, Netzwerk
  war beim Nachpruefen schon wieder stabil): nach der Standby-Pause hat
  `dukascopy_python.fetch()` vermutlich einmal kaputte (nicht-numerische)
  Daten geliefert, die ungeprueft gecacht wurden und mehrere Ebenen tiefer
  bei Regime-/Friction-Vergleichen crashten. Jetzt: bei nicht-numerischen
  Spalten sauberer `ValueError` statt stillem Cache-Write — der bestehende
  `_retry()`-Wrapper der Aufrufer bekommt dadurch einen klaren Grund zum
  Neuversuch statt kaputter Daten drei Ebenen tiefer. Rein additiv (nur ein
  zusaetzlicher Check vor dem bestehenden `df.to_parquet()`), betrifft
  keine Order-/Risiko-Logik. Nur `py_compile`-geprueft.

- **2026-09-02** [System] **Absicherung gegen die naechtliche ~9h-Standby-
  Luecke**: Ursache war nicht "PC aus", sondern Windows Modern Standby (S0),
  ausgeloest ueber die Display-Idle-Timeout-Kette (AC-Bildschirm-Timeout war
  auf 5 Min. gestellt) — von aussen sah der Rechner "an" aus. Drei Massnahmen:
  (1) `powercfg /change monitor-timeout-ac 0` + `standby-timeout-ac 0` +
  `hibernate-timeout-ac 0` — Display/Standby auf Netzbetrieb schaltet nicht
  mehr automatisch ab. (2) Alle 5 Bridge-/Scanner-Tasks (EK-Portfolio-Bridge,
  FKInstantFunding-MT5-Bridge, Funded-Portfolio-Bridge, OU-Modell-
  ScannerHourly, Forex-Weekly-Report) auf `WakeToRun=True` +
  `StartWhenAvailable=True` gestellt — falls der Rechner trotzdem mal
  einschlaeft, weckt der Task-Scheduler ihn gezielt fuer diese Laeufe statt
  sie zu verpassen. (3) Neuer **Bridge-Watchdog**
  (`C:\Users\andre\Bridge-Watchdog\`, ausserhalb des Repos wie jede andere
  Bridge, eigener Scheduled Task alle 30 Min): prueft Log-Frische von
  EK-Portfolio-Bridge/Funded-Portfolio-Bridge (Toleranz 40 Min, nur Mo-Fr)
  und FKInstantFunding-MT5-Bridge (Toleranz 100 Min, taeglich), meldet einen
  Ausfall EINMAL per Telegram (kein Spam bei mehrstuendiger Downtime) +
  Erholungsmeldung, sobald wieder frisch. Einmal manuell getestet (kein
  Fehlalarm, alles war frisch).
- **2026-09-02** [FK Instant Funding] Telegram-Logik auf dasselbe Muster wie
  EK-Portfolio-Bridge/Funded-Portfolio-Bridge gebracht (Nutzerauftrag nach
  Abgleich-Nachfrage): neues `fk_instant_funding/telegram_format.py`
  (`fk_message()`, aus `paper_bot.py` herausgezogen) + `queue_message()`/
  `flush_queued_messages()` in `telegram_notify.py` ergaenzt (vorher nur
  nacktes `send_telegram_message()`). `paper_bot.py::scan_once()` schickt
  die gesammelten Lauf-Ereignisse jetzt ueber dieselbe Queue/Flush-
  Infrastruktur statt eines eigenen lokalen Listen-Patterns — `messages`
  bleibt fuer den bestehenden Rueckgabewert (`row["messages"]`) unveraendert
  bestehen, nur der Versandweg ist jetzt gemeinsam. Sichtbares Ergebnis
  (eine gebuendelte "Scan-Update"-Nachricht pro Lauf) bleibt identisch,
  verifiziert per Smoke-Test (Queue sammelt/leert korrekt, Banner-Format
  bytegleich). Reines DRY_RUN/Paper-Bein, kein Echtgeld betroffen. Keine
  weiteren Referenzen auf die entfernten `_FK_BANNER`/`_FK_RULE`-Konstanten
  im Repo gefunden.

- **2026-09-02** [Funded Portfolio] **Echtgeld-Bugfix, direkt nach dem
  OU-Modell-Root-Cause-Fix gefunden**: um 00:05 Uhr versuchte die Bridge auf
  BEIDEN Konten echte Aktien-Entries fuer ADI/FAST (die frisch wieder
  sichtbaren OU-Modell-Signale) — mitten in der Nacht, NYSE laengst zu.
  TTP: `retcode=10018 "Market closed"`. IQMARKETS: `no_tick` (Broker liefert
  ausserhalb der Handelszeiten keine Kurse fuer Aktien). Ursache: anders als
  EK-Portfolio-Bridge (Gate seit 2026-08-31) hatte `run_once.py` fuer das
  ou_modell-Bein KEIN NYSE-Handelszeiten-Gate — bisher folgenlos, weil das
  Bein bis zum Root-Cause-Fix nie ein offenes Signal melden konnte, hat sich
  aber sofort gezeigt, sobald es zum ersten Mal wirklich feuerte. Fix: neue
  `_nyse_is_open()` (identisches Muster zu EK), gated NUR neue Entries fuer
  ou_modell (`entries_allowed`) — ein bereits offenes Signal wird weiterhin
  jederzeit normal geschlossen, kein Handelszeiten-Bezug fuer den Exit
  noetig. Nur `py_compile`-geprueft.
- **2026-09-01** [Second Brain] `knowledge/scripts/lint.py` + Skill
  `second-brain-lint` um Check (e) erweitert: unverarbeitete Dateien in
  `Clippings/` (Raw-Inbox), Heuristik = Dateiname wird bisher nirgends
  außerhalb von `Clippings/` erwähnt. Anlass: Nutzerauftrag, nachdem die
  Video-Wissen-Einbindung besprochen wurde. Erster Lauf fand direkt 5
  echte Treffer (3 Themen wie besprochen: Trading/Orderflow, Claude-
  Workflow/Token-Sparen x3, plus ein vermutliches Duplikat des bereits
  verarbeiteten Second-Brain-Clips) — in `DASHBOARD.md` unter "Offene
  Aufgaben" (Mittel) eingetragen, noch nicht distilliert.
- **2026-09-02** [NY-Open ORB] **Beide Live-Bridges auf NASDAQ-EOD-Exit
  umgestellt (echtes Geld, Nutzerauftrag)**: `challenge_portfolio/paper_bot.py`
  (live importiert von Funded-Portfolio-Bridge, DRY_RUN=False) -
  `ORB_EXIT_CFG` durch `ORB_EXIT_CFG_BY_INSTRUMENT` ersetzt, NASDAQ
  `target_mode=None`; Smoke-getestet mit gecachten Daten. **Teilausstieg
  bewusst NICHT ergaenzt** - `Funded-Portfolio-Bridge/run_once.py::_process_leg()`
  hat keine Teilschliessungs-Verwaltung, ein Config-Flip haette Papier- und
  echtes Broker-P&L unbemerkt auseinanderlaufen lassen (Details:
  `knowledge/projects/ny-open-orb-sp500.md`). `EK-Portfolio-Bridge/legs/ny_open_orb/`
  (Tickmill LIVE) - echte Code-Aenderung (nicht nur Config): `config.py`s
  NASDAQ-`target_r_mult` auf `None`, `signal_source.py` berechnet dann kein
  `target_price`, `executor.py` sendet `tp=0.0` (kein Broker-TP, bestehende
  Konvention aus `legs/ctnl_edge/executor.py` wiederverwendet) - der bereits
  vorhandene Session-Ende-Notausgang in `manage_open_positions()` wird fuer
  NASDAQ zum primaeren statt nur Fallback-Exit, keine Aenderung an dieser
  Funktion noetig. Teilausstieg (1.5R/50%+BE) blieb hier unveraendert aktiv,
  da diese Bridge bereits echte Teilschliessungs-Verwaltung hat. Nur
  `ast.parse`-syntaxgeprueft, NICHT gegen den echten MT5-Terminal getestet -
  naechster 15-Minuten-Lauf verifiziert es; bereits offene Positionen
  unberuehrt. **Nebenfund**: zwei weitere ORB-Kopien (`ek_portfolio/paper_bot.py`,
  pausiert; `fk_instant_funding/paper_bot.py`, DRY_RUN) noch auf altem Stand,
  bewusst nicht angefasst, siehe `DASHBOARD.md`.
- **2026-09-01** [Second Brain] `yt-dlp` installiert (`python -m pip install
  --user yt-dlp`, aufgerufen via `python -m yt_dlp` da nicht auf PATH) und
  gegen den bereits bekannten Second-Brain-Video-Clip verifiziert
  (Auto-Untertitel-Download funktioniert trotz fehlender JS-Runtime-Warnung).
  Ermöglicht, YouTube-Transkripte künftig selbst zu ziehen statt auf
  manuelles Copy-Paste vom Nutzer angewiesen zu sein — Nutzer muss nur noch
  den Link geben.
- **2026-09-02** [EK-Portfolio] Kleiner Nachzug zum ORB-Fix: `legs/ny_open_orb/
  executor.py` zeigte bei einem echten Entry "@ 0.00" in Telegram (SP500
  Ticket 260635110) — derselbe bekannte `result.price`-Broker-Quirk, der in
  Funded-Portfolio-Bridge/executor.py schon behoben war, hier aber noch
  nicht. Echten Preis jetzt aus der frisch eroeffneten Position gelesen.
  Rein kosmetisch (SL/TP/Order selbst waren nie betroffen). Nur
  `py_compile`-geprueft.
- **2026-09-02** [Funded Portfolio / OU-Modell] **Echtgeld-Bugfix (Root Cause,
  nicht nur Config)**: `challenge_portfolio/paper_bot.py::_scan_ou_modell()`
  konnte strukturell NIE ein aktuell offenes OU-Modell-Signal an
  Funded-Portfolio-Bridge (TTP/IQ) melden — unabhaengig von Config oder
  Marktlage. Ursache: `ou_paper_backtest/portfolio.py::simulate_bracket_
  portfolio()` liess jede beim Rueckgabe-Zeitpunkt noch OFFENE Position
  einfach unter den Tisch fallen (nur geschlossene Trades landeten in
  `trades`), jede vom Bein gefundene Zeile hatte deshalb immer einen
  konkreten exit_reason (nie "data_end") und wurde von `_process_leg()`
  automatisch als "laengst verpasst" statt als neuer Entry behandelt. Fix:
  neuer `include_open_positions`-Parameter (additiv, Default `False` --
  aendert nichts an den ~10 anderen Aufrufern/Sweep-Skripten dieser
  Funktion). Verifiziert an FAST/SPG/SYY (denselben 3 Tickern, die der
  Standalone-Scanner um 21:35 fand) — erscheinen jetzt korrekt als offenes
  Signal (`entry_date=2026-08-31`). Zusaetzlich, auf Nutzerwunsch nach
  Pruefung der 2025er-Holdout-Drawdown-Daten: Exit-Logik von der reinen
  "gesperrten Baseline" auf die zuletzt live auf Konto 2 (TTP, bis
  2026-09-01) gefahrene, validierte Konfiguration umgestellt (TP 1:1.5R nur
  S&P, be_trigger_r 0.25→0.35, internes Risiko-Gate 15%→5%) — schlechtester
  Einzeltag im Holdout -1.31%, deutlich unter der 3%-Tagesverlust-Regel.
  Reales Order-Sizing (`LEG_RISK_PCT["ou_modell"]`) bewusst NICHT angetastet
  (Nutzerentscheidung: die 1/6-Kapitalgewichtung macht das reale Risiko/
  Trade schon konservativer als Konto 2s eigenstaendige 0.25%). Nur
  `py_compile`-geprueft, nicht live getestet — naechster Lauf von
  Funded-Portfolio-Bridge wird dadurch voraussichtlich 3 neue echte Entries
  (FAST/SPG/SYY, TTP+IQ) platzieren.
- **2026-09-01** [Second Brain] Scope von `projects/strategie-backlog-inventar.md`
  auf Nutzerauftrag eingegrenzt: kein Vollsweep mehr über alle ~26
  unerfassten Strategie-Ordner, sondern nur (a) aktuell relevante
  Projekte/Strategien mit Dashboard-Bezug und (b) Filter/Bausteine mit
  bestätigtem Mehrwert. Daraus 5 echte Lücken bei laufenden/pausierten Bots
  abgeleitet (`asian_range_breakout`, `cls_practical`, `btc_ema_cross`,
  `ek_portfolio`, OU-Modell — alle bisher ohne PARA-Notiz trotz Live-/
  Paper-Relevanz), `asia_ote`/`checklist_strategy` aus dem aktiven Backlog
  genommen (kein Dashboard-Bezug). Dashboard-Abgleich durchgeführt: Task
  Scheduler-Status + `DRY_RUN`-Flags aller Live-Bridges gegen die
  Statustabelle geprüft, keine Abweichung gefunden.
- **2026-09-01** [Second Brain] Zwei Second-Brain-Methodik-Video-Vorschläge
  übernommen (Nutzerauftrag): (a) `CLAUDE.md` um eine Kontextfenster-
  Hygiene-Regel ergänzt (Chats nicht über ~300k Token laufen lassen), (b)
  Lint-Check von "auf Zuruf" auf wöchentlich geplant umgestellt — neue
  Cloud-Routine "Second-Brain-Lint (weekly)" (`trig_01TRG6KMs4Eh1cjWpnB21A4L`,
  jeden Montag 08:00 Europe/Berlin), die `knowledge/scripts/lint.py` +
  die Triage-Logik aus `.claude/skills/second-brain-lint/SKILL.md` ausführt
  und Ergebnisse selbstständig committet/pusht. Zusätzlich
  `knowledge/areas/backtest-standard-process.md` angelegt (löst 8 tote
  `[[backtest-standard-process]]`-Links auf, referenziert den 8-Phasen-Code
  in `app_pages/education_gold_intraday.py`).
- **2026-09-02** [NY-Open ORB] **Nur Research-Dashboard geaendert, KEINE
  Live-Bridge betroffen**: `app_pages/ny_open_orb_portfolio.py::EXIT_CFG_BY_INSTRUMENT["NASDAQ"]`
  auf `eod_partial` umgestellt (Restposition nach 1.5R/50%-Teilausstieg+BE
  laeuft jetzt bis Handelsschluss statt bis 4R-Cap) - Phase-6-bestaetigt
  (`scripts/research_nasdaq_orb_phase6_eod_exit.py`), seit-2025 auf allen
  vier Kennzahlen (Return/Sharpe/CAGR/MaxDD) besser als die alte Config,
  siehe `knowledge/projects/ny-open-orb-sp500.md` Stage 8/9. **Wichtiger
  Nebenbefund beim Abgleich**: die zwei tatsaechlichen Live-Bridges mit
  ORB-Bein (`challenge_portfolio/paper_bot.py`, live importiert von
  Funded-Portfolio-Bridge/DRY_RUN=False; `EK-Portfolio-Bridge/legs/ny_open_orb/`,
  Tickmill LIVE) haben BEIDE eigene, unabhaengige Exit-Configs, die von
  dieser Aenderung nicht beruehrt werden - `challenge_portfolio` fehlt sogar
  noch der seit 2026-08-27 adoptierte Teilausstieg. Nichts an einer
  Live-Bridge geaendert, siehe `DASHBOARD.md` "🔍 Braucht deine Bestätigung".
- **2026-09-02** [EK-Portfolio] **Echtgeld-Bugfix (2 Stellen, live)**:
  (1) `legs/ny_open_orb/executor.py::check_and_execute_entry()` — SP500/US30-
  Entries scheiterten seit 2026-09-01 wiederholt mit `retcode=10016 "Invalid
  stops"`, weil der SL relativ zum SIGNAL-Preis (M5-Historie) berechnet,
  aber zum LIVE-Preis gesendet wurde; war der Kurs seit dem Signal
  gefallen, landete der SL fuer eine BUY-Order ueber dem aktuellen Kurs.
  Fix: SL-Seite gegen den tatsaechlichen Fill-Preis validieren, bei
  Mismatch als "Signal zu alt" sauber ueberspringen statt mit ungueltigem
  SL zu senden. (2) `legs/ou_modell/executor.py::manage_open_positions()` —
  der Break-Even-SLTP-Modify hatte das NYSE-Handelszeiten-Gate nicht, das
  fuer neue Entries schon am 2026-08-31 wegen desselben `retcode=10018
  "Market closed"`-Problems ergaenzt wurde; lief dadurch ausserhalb der
  Handelszeiten weiter erfolglos gegen die geschlossene Boerse. Fix:
  Break-Even-Versuch jetzt ebenfalls hinter `_nyse_is_open()` gated. Beide
  Fixes nur per `py_compile` syntaktisch geprueft, NICHT live gegen das
  Echtgeld-Konto getestet (kein DRY_RUN-Testlauf ausgeloest, um keine
  ungewollte reale Order zu riskieren) — naechster reale Lauf verifiziert.
- **2026-09-02** [Funded Portfolio] `executor.py::close_position()` meldete
  bei einer bereits (broker-seitig) geschlossenen Position nur `not_found`
  — sah wie ein Fehler aus, obwohl der Trade sauber beendet war. Ursache
  rekonstruiert (TTP Ticket 18202597, Gold ASB SHORT): real geoeffnet
  09:30:57 UTC @ 4367.13, real automatisch geschlossen ca. 15:30 UTC @
  4366.16, P/L **+$2.91** (per `mt5.history_deals_get()` direkt am TTP-Konto
  verifiziert) — der geplante Exit-Versuch um 17:48 kam nur deshalb als
  `not_found` zurueck, weil `bridge_state_ttp.json` den fruehen Close nie
  als "closed" vermerkt hatte (vermutlich Race mit einem der manuellen,
  nicht ueber `run_task.ps1` geloggten Laeufe waehrend der Inbetriebnahme
  heute). Fix: bei `not_found` jetzt die echte Historie nachschlagen und
  Preis/P&L mitmelden statt nur "not_found".
- **2026-09-01** [EK-Portfolio] **Echtgeld-Bugfix**: `legs/gold_asb/signal_
  source.py` verglich seit 11:30 Uhr bei JEDEM Lauf einen tz-naiven mit
  einem tz-behafteten Timestamp (`TypeError`) — der Scan crashte komplett,
  bevor er pruefen konnte, ob ein Signal da ist (3 aufeinanderfolgende
  Laeufe betroffen, 11:30/11:45/12:00). Behoben (`_utc_naive()` nachgezogen,
  identisches Muster wie ueberall sonst im Repo). Danach zusaetzlich
  `_retry()` (bereits etablierter Dukascopy-Flakiness-Workaround) in den
  drei noch Dukascopy-abhaengigen Beinen nachgezogen: `gold_asb`,
  `cls_practical`, `ctnl_edge` (Continuation/Reversal + die dynamische
  VWAP-Ziel-Abfrage fuer offene Continuation-Positionen). Nebenbefund:
  `trend_pullback`/`gold_silver`/`ny_open_orb` nutzen in dieser Bridge
  bereits `mt5.copy_rates_range()` direkt statt Dukascopy — der
  MT5-Umstieg ist dort schon gemacht, wo die Historientiefe das zulaesst.
  Verifiziert per sauberem 13-Bein-Komplettlauf um 12:15 ohne einen
  einzigen Fehler.
- **2026-09-01** [Funded Portfolio] Scheduled Task `Funded-Portfolio-Bridge`
  angelegt (alle 15 Min, Mo–Fr, wie EK-Portfolio-Bridge) — vorher liefen
  die 2 offenen Positionen nur bei manuellen Laeufen. 2 weitere Bugs beim
  ersten automatischen Lauf gefunden + behoben: (1) die "Signal bereits
  geschlossen, bevor die Bridge es sah"-Meldung wurde nie im State
  vermerkt und wiederholte sich dadurch bei JEDEM Lauf fuer immer (reiner
  Telegram-Spam ohne neuen Informationswert) — jetzt einmalig als
  "missed" vermerkt; (2) `place_market_entry()`s `result.price` kam beim
  ersten echten Order-Send als `0.0` zurueck (Position war broker-seitig
  korrekt offen, nur das State-Feld `entry_price` betroffen) — liest den
  echten Preis jetzt direkt aus der frisch eroeffneten Position. Ausserdem
  `run_task.ps1`: UTF-8-Erzwingung fuer die PowerShell-Prozess-Erfassung
  ergaenzt (Emojis kamen im lokalen Log verstuemmelt an — Telegram selbst
  war davon nie betroffen, rein kosmetisch).
- **2026-09-01** [Second Brain] Lint-Check aus `CLAUDE.md` Regel 6
  automatisiert: neues Skript `knowledge/scripts/lint.py` (tote Wikilinks,
  verwaiste Seiten, veraltete Dashboard-Daten) + Skill
  `.claude/skills/second-brain-lint/SKILL.md` mit der Triage-Logik
  (False-Positives/Cross-System-Links/Bestätigung/Aufräumen). Erster Lauf
  durchgeführt, Befunde in `DASHBOARD.md` eingetragen (kein
  automatisch geplanter Task — bleibt auf Zuruf, bis Nutzer das bestätigt).
  Anlass: ECC (externes npm-Tool) sollte installiert werden, dessen Setup
  scheiterte aber (kein `claude`-Binary auf PATH in dieser Session) und
  hätte ohnehin ein zweites, paralleles Memory-System eingeführt — stattdessen
  schlanke, repo-eigene Lösung ohne Drittanbieter-Abhängigkeit.

- **2026-09-01** [Funded Portfolio] **`DRY_RUN=False`** auf Nutzerauftrag
  ("stelle dry run auf false dann gehen wir rein") — erste echte Orders
  gesendet: Gold ASB SHORT je 0.03 Lots, TTP Ticket 18202597 @ 4367.13,
  IQ Markets Ticket 1284739 @ 4370.73 (beide broker-seitig verifiziert,
  korrekter SL, kein TP). Vorbedingung dafür zuerst erledigt: OU-Modell-MT5-
  Bridge/config.py's Konto-2-Eintrag (504072729) komplett aus `ACCOUNTS`
  entfernt (nicht nur Task deaktiviert — Konto 1, echtes Geld, unverändert),
  CTNL-Edge-MT5-Bridge/config.py mit Warnhinweis versehen (Task war schon
  deaktiviert) — verhindert, dass beide alten Solo-Bots je wieder
  gleichzeitig mit der neuen Bridge auf denselben Konten/Terminals laufen.
  Zusätzlich: 1%-Positionsdeckel und Gesamt-Drawdown-Kill-Switch in Paper-Bot
  + Bridge von statisch (fixer $100k-Referenzwert) auf dynamisch (echte
  aktuelle Kontoequity, trailing Peak) umgestellt (Nutzerauftrag), sowie ein
  Fund direkt aus dem ersten Live-Lauf behoben (`place_market_entry()`s
  `result.price` kam als 0.0 zurück, echter Preis wird jetzt aus der
  Position selbst gelesen — betraf nur das State-Feld, keine Fehlausführung).
  **Kein Scheduled Task angelegt** — die zwei offenen Positionen werden
  aktuell nur bei einem manuellen `run_once.py`-Lauf verwaltet.
- **2026-09-01** [Second Brain] Strategie-Backlog-Inventar gestartet
  (`projects/strategie-backlog-inventar.md`, Batch 1/mehrere: asia_ote,
  asian_range_breakout, auction_playbook, btc_ema_cross, checklist_strategy)
  — Ziel: alle ~26 Strategie-Ordner ohne PARA-Notiz erfassen, bevor sie
  einen vollen CODE-Distill bekommen; bewusst in Häppchen statt einem
  Rutsch (Nutzer-Entscheidung). Dabei gefunden: `cls_practical` hat trotz
  bestehender Recherche keine `knowledge/`-Notiz, nur einen Eintrag in
  Claudes eigenem Memory-System. Außerdem `resources/second-brain-methodik.md`
  angelegt (Distill des Clippings-Artikels "Der einfachste Einstieg in
  Second Brains!", Jonas Keil/Karpathys LLM-Wiki-Konzept) — Abgleich zeigt
  unsere Struktur deckt 2 von 3 Kernkonzepten bereits ab.
- **2026-09-01** [Second Brain] Lint-Check als wiederkehrender Prozess in
  `CLAUDE.md` (Regel 6) + Tracking-Zeile in `DASHBOARD.md` ergänzt (Anstoß:
  Vergleich mit Karpathys "LLM Wiki"-Ansatz — Lint war dort explizit
  vorgesehen, bei uns fehlte der wiederkehrende Charakter, nur ein
  einmaliger Aufräum-Punkt in "Offene Aufgaben").
- **2026-09-01** [Infrastruktur] 5 verwaiste MT5-Terminals geschlossen
  (GoldFKBot/16054, CLSPractical/MetaQuotes-Demo, TTP/504069845,
  TTP-Konto2/504072729, generischer Default-Terminal/15514) — alle gehörten
  zu bereits deaktivierten Tasks, waren nach einem Systemneustart automatisch
  wieder aufgegangen. Nur die 2 aktiven Terminals (Tickmill/55918977,
  BeyondIQCapital/17764) blieben offen.
- **2026-09-01** [Challenge Portfolio] CTNL-Reversal-Kaskade auf reales
  3er-Gleichzeitigkeits-Limit gekappt (`_cap_concurrent_reversals`, wie
  FK Instant Funding) + unabhängiger OU-Modell-Import-Kollisions-Fix
  mitcommittet. Commit `69f9ca6`.
- **2026-09-01** [EK-Portfolio] CTNL-Reversal-Kaskade auf reales 3er-Limit
  gekappt (Paper-Bot überzeichnete bis zu 9 gleichzeitige Positionen statt
  der real gültigen 3 — Fund aus einer EK-Jahres-Rekonstruktion, 1122/1417
  Trades betroffen). Commit `c195924`.
- **2026-08-31** [FK Instant Funding] `scan_errors_today`-Tageswechsel von
  UTC- auf echten lokalen Kalendertag umgestellt (Fehler von 01:20 Uhr
  wurden durch den UTC/Lokalzeit-Versatz faelschlich vor dem Tagesabschluss
  wieder zurückgesetzt). Commit `adc7d7c`.
- **2026-08-29** [EK-Portfolio, CTNL-Edge-FK-Paper] Wochenend- +
  Spread-Stunden-Sperre (23:00 lokal) auch hier eingebaut, inkl. bewusster
  Ausnahme für BTC EMA9/21 (24/7-Krypto-Markt, wird bei EK-Portfolio NICHT
  pausiert). Neues gemeinsames Modul `strategy/schedule_guard.py`. Commit
  `5fcf1da`.
- **2026-08-29** [FK Instant Funding] Wochenend- + Spread-Stunden-Sperre
  eingebaut (User-Wunsch: "damit nichts unnötig am Wochenende läuft").
  Dabei gefunden: `DAILY_SUMMARY_HOUR` verglich fälschlich gegen UTC statt
  Lokalzeit (Tagesabschluss feuerte real 2h später als beabsichtigt) — mit
  behoben. Commit `79df9f3`.
- **2026-08-29** [FK Instant Funding] Eigenes Telegram-Layout ("🏦 FK
  INSTANT FUNDING"-Banner) + alle Scan-Ereignisse eines Laufs zu EINER
  Nachricht gebündelt statt je Strategie einzeln; Tagesabschluss bekommt
  System-Status-Zeile (Scan-Fehler heute ja/nein). `telegram_config.py`
  erstmals angelegt (fehlte komplett — Bot hatte vorher NIE eine echte
  Telegram-Nachricht verschickt). Commit `8f9a11a`.
- **2026-08-29** [FK Instant Funding] `CAPITAL_WEIGHT` von Gleichgewichtung
  (1/6) auf Monte-Carlo-optimierte Pro-Bein-Gewichte umgestellt (Gold ASB/
  Trend Pullback/Gold-Silber je 6,06%, CLS Practical 19,19%, CTNL Edge
  25,25%, ORB-Portfolio 37,37%) — sowohl im Paper-Bot als auch in der
  echten Bridge `run_once.py`. Commit `11f8979`.
- **2026-08-29** [FK Instant Funding / Portfolio-Konstruktion] Gewichts-
  Optimierung der 6 Beine, Monte-Carlo-geprüft (CAGR 15,6%→24,8%, MaxDD
  -1,78%→-2,27%, P(Trailing-DD-Bruch>5%) 0,0%→2,1%). Persistiert in
  `fk_instant_funding_final.json` + Streamlit-Tab. Commit `59ba4df`.
- **2026-08-29** [FK Instant Funding] Echte Instant-Funding-Bridge
  (BeyondIQCapital, Login 17764) angebunden und live im DRY_RUN getestet;
  Positionsgrößen-Policy "bei Unterschreitung des Mindestlots auf Mindestlot
  anheben, gedeckelt auf 0,5% Startkapital" implementiert.
- **2026-08-27** [FK Instant Funding] NY-Open ORB als 6. Strategie in den
  Live-Scan integriert (verbessert alle Kennzahlen gleichzeitig). Commits
  `d6d0f42`, `652f88f`.
- **2026-08-27** [EK-Portfolio] Neuer, separater 8-Bein Paper-Forward-Test-
  Bot angelegt (Architektur-Vorbild: FK Instant Funding). Commit `1b48562`.
- **2026-08-26** [FK Instant Funding] Neuer Paper-Forward-Test-Bot (5 Beine)
  angelegt, danach vollständiger Fehler-Audit auf Nutzerwunsch: fehlendes
  `r_multiple` bei Gold ASB/CLS Practical (Trades wurden komplett
  stillschweigend verworfen), Trade-Key-Kollisionsrisiko, Kontostart-
  Mehrjahres-Blend-Bug, EOD-Trailing-DD-Floor-Bug — alle behoben. Commits
  `3c717e3`, `51a783d`, `efa528c`, `d82c979`.

<!-- Älter als diese Session: nicht rückwirkend erfasst, siehe `git log` für vollständige Historie. -->
