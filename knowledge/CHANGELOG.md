# Changelog

Vollständiges, chronologisches Log relevanter Änderungen (neueste oben).
Ein Eintrag pro Änderung: Datum, Bereich, Kurzbeschreibung, Commit-Hash wo
zutreffend. Wird von Claude bei jeder relevanten Änderung ergänzt (siehe
`CLAUDE.md`). Nicht committen vergessen wird hier nichts eingetragen, was
nicht auch tatsächlich passiert ist — dieses Log ist reine Beobachtung,
keine Planung (dafür ist `DASHBOARD.md`).

---

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
  Report zu pruefen und kurz zu nennen (Titel/Kernaussage, `[[slug]]`-Link),
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
