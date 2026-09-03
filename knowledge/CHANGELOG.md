# Changelog

Vollständiges, chronologisches Log relevanter Änderungen (neueste oben).
Ein Eintrag pro Änderung: Datum, Bereich, Kurzbeschreibung, Commit-Hash wo
zutreffend. Wird von Claude bei jeder relevanten Änderung ergänzt (siehe
`CLAUDE.md`). Nicht committen vergessen wird hier nichts eingetragen, was
nicht auch tatsächlich passiert ist — dieses Log ist reine Beobachtung,
keine Planung (dafür ist `DASHBOARD.md`).

---

- **2026-09-03** [Funded-Portfolio-Bridge] **Diagnose (keine Code-Aenderung):
  warum die beiden neuen Konten TTP Konto 1 (504069845, echtes Geld) und IQ
  15514 noch keine OU-Entries bekommen haben.** Quelle ausschliesslich die
  committete `bridge_status/snapshot.json`-Historie — der Bridge-Code liegt
  ausserhalb des Repos und war aus dieser Session nicht einsehbar, die Ursache
  ist also plausibel hergeleitet, nicht im Code verifiziert. (1) Von
  2026-09-02 19:27 bis 2026-09-03 12:04 scheiterte auf beiden neuen Konten
  JEDER Lauf schon an der Verbindung (`mt5.initialize()` `-10005 IPC timeout`,
  ab 12:04 `-6 'Terminal: Authorization failed'`) — in diesem Fenster lief dort
  kein einziges Bein. Erste erfolgreiche Verbindung: 2026-09-03 12:37:03
  (seitdem in jedem Snapshot Equity-Zeilen fuer beide). Damit ist der bisher
  offene Punkt "AutoTrading/Terminal der zwei neuen Konten" faktisch erledigt.
  (2) Seit 12:37 verbinden beide sauber, haben aber nichts gehandelt: der
  einzige OU-Entry der Bridge (`2026-09-03 15:42:39 [TTP] ENTRY ou_modell
  (FAST) FAST BUY lots=40.0 risk=$166.79 sl=44.09007 -- placed`) ging nur auf
  TTP Konto 2, obwohl die neuen Konten in genau diesem Lauf verbunden waren
  (gleiche 15:42:39-Equity-Zeile) und dazu weder Entry noch Fehlerzeile
  loggen. (3) Wahrscheinlichste Ursache: das dokumentierte `account_start`-
  Gating (`run_once.py`/`bridge_state_<id>.json`, "verhindert faelschliches
  Nacheroeffnen von Alt-Signalen beim ersten Lauf") — das FAST-Signal traegt
  `scan_date=2026-09-02` und liegt damit vor dem `account_start` der neuen
  Konten (2026-09-03 12:37), auf Konto 2 (`account_start` 2026-09-01) nicht.
  Nachzupruefende Kommandos, moegliche Folgewirkung (OU-Signale tragen ein
  00:00-Datum, das Gate koennte die neuen Konten einen weiteren Tag blockieren)
  und die offene Entscheidung "Alt-Signale nachziehen oder nicht" stehen in
  DASHBOARD.md. Nebenbefund: auch IQ 16054 (altes Konto, kein
  `account_start`-Thema) hat den FAST-Entry nicht bekommen — eigene, noch
  nicht untersuchte Ursache im OU-Bein auf BeyondIQCapital.

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
