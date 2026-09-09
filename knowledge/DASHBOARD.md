# Dashboard

**Stand: 2026-09-09** _(wird bei jeder Session von Claude auf das aktuelle
Datum nachgeführt — "Zuletzt geprüft" in der Statustabelle unten kann davon
abweichen und älter sein, siehe `CLAUDE.md` Punkt 4)._

Die tägliche Cockpit-Ansicht — hier reinschauen, nicht in Task Scheduler,
config.py-Dateien oder Chat-Verläufe wühlen. Funktioniert in jedem Editor,
kein Obsidian nötig. Wird von Claude bei jeder relevanten Änderung
nachgeführt (siehe `CLAUDE.md`).

Research-Wissen (Papers, Strategie-Findings) gehört NICHT hierher, sondern
in die PARA-Struktur (`projects/`, `areas/`, `resources/`, `archive/`,
siehe `README.md`). Hier geht es nur um: was läuft gerade, was ist zuletzt
passiert, was steht an.

---

## ▶️ Als Nächstes

1. ~~`data_lake/`-Paket nie committet~~ — **committet + gepusht 2026-09-06**
   (`19e5b2c`) + im selben Zug auf EK-Portfolio-Bridge (gold_asb,
   cls_practical, ctnl_edge) und FKInstantFunding-MT5-Bridge (alle 6 Beine)
   erweitert (`f8db9f3`), inkl. Verifikation jedes Pfads gegen `source=
   "live"` und Fix eines dabei gefundenen echten tz-Bugs in cls_practical.
   Details: CHANGELOG. Push zunaechst durch den separaten Sync-Konflikt
   blockiert, nach dessen Merge durch eine parallele Session (siehe unten)
   sauber als Fast-Forward durchgegangen (`e592d4d..f8db9f3`).
2. ~~gold_asb: Historie-Cache greift nie~~ — **behoben 2026-09-06.**
   `stable_end_str` (Alt/Neu-Grenze) lief auf "gestern" (wandert täglich,
   verfehlte den Datums-Cache dadurch jeden Tag) → jetzt auf Monatsanfang
   stabilisiert (ändert sich nur 1x/Monat), "neues" Fenster deckt dafür den
   laufenden Monat ab (max. ~31 Tage, bleibt klein). Verifiziert: zwei
   Aufrufe lieferten identische 188 Zeilen, zweiter schneller. Voller
   Cache-Vorteil zeigt sich über die nächsten Tage.
3. **Manuelles Monatsjournal + Quant-System-Verschmelzung** (Nutzerwunsch
   2026-09-02): händisches Monatsjournal + Plan, wie manuelles Trading und
   das Quant-System sinnvoll verschmolzen werden — braucht zuerst ein
   klärendes Gespräch (Format, Kennzahlen). Noch nichts gebaut.
3. ~~M5-Scan-Frequenz für CTNL Continuation + NY-Open ORB~~ — **erledigt,
   live seit 2026-09-04.** Neue `data_lake`-Lane `"fast5"` + eigener
   Fast-Task, Cross-Prozess-Lock gegen Doppel-Ausführung. Nutzer hat
   Testlauf + beide Scheduled Tasks selbst verifiziert. Details: CHANGELOG.
4. ~~Funded-Portfolio-Bridge: redundante Scans vermeiden~~ — **erledigt
   2026-09-03.** MT5 als Datenquellen-Ersatz geprüft und verworfen (deckt
   nur 9 von ~30 gebrauchten Instrumenten ab). Stattdessen `run_once.py`
   umgebaut: 6 Scans laufen jetzt 1x pro Bridge-Lauf statt 1x pro Konto.
   Nebenfund: `tvDatafeed`-Pro-Login entfernt (TradingView-Captcha-Wall).
   Details: CHANGELOG.
5. ~~FKInstantFunding-MT5-Bridge: vollen Connect-Scan-Gates-Entry-Pfad nach
   Fast-Lane-/Terminal-Fix-Umbau beobachten, dann LIVE_LEGS erweitern~~ —
   **erledigt 2026-09-09.** Task Scheduler bestätigt (`LastTaskResult=0`,
   läuft sauber im 5-Min-Takt Mo–Fr); Root Cause des eigentlichen Auslösers
   (beide bisherigen ORB-Signale 07./08.09. vom stündlichen Takt verpasst)
   damit behoben. Ein zweiter Testlauf außerhalb der Spread-Stunden-Pause
   zeigte den vollen Connect-Scan-Gates-Durchlauf fehlerfrei (nur zufällig
   kein neues Signal) — auf dieser Basis hat der Nutzer entschieden, nicht
   erst auf einen echten Entry zu warten (Order-Versand-Code ist identisch
   zu dem der schon lebenden ORB-Beine). `LIVE_LEGS` jetzt erweitert um
   gold_asb/cls_practical/ctnl_continuation/ctnl_reversal. Noch offen: der
   erste echte Entry der 4 neuen Beine ist noch nicht beobachtet — bei
   Gelegenheit gegenlesen. Details: CHANGELOG.

---

## 📋 Offene Punkte (nach Priorität)

Zusammengeführt aus "Braucht deine Bestätigung" + "Offene Aufgaben" — nach
Priorität sortiert, erledigte Punkte pro Kategorie unten. Höchste Priorität:
offene Projekte mit konkretem nächstem Schritt (aktuell keins offen — der
gold_asb-Cache-Bug oben läuft über "Als Nächstes"). Danach: Bestätigungs-
Bedarf vor generischem Aufräumen.

### 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **EK-Portfolio-Bridge: ORB sieht die laufende Session vermutlich ~2 Stunden
  zu spät — Diagnoseskript liegt bereit, aber NICHT ausgeführt** (gefunden
  2026-09-09 beim FK-Umbau, Details CHANGELOG). `copy_rates_range()` vergleicht
  `date_to` gegen server-gestempelte Bar-Zeiten; `legs/ny_open_orb/
  signal_source.py:88` übergibt dort eine naive UTC-Zeit. Am FK-Terminal
  nachgewiesen: das Abfragefenster endet dadurch ~2 Std. vor dem neuesten
  vorhandenen Bar (`date_to = UTC now` → letzter Bar 18:05 Serverzeit, mit +12h
  → 23:05, Bars dazwischen lückenlos da). EK nutzt identischen Code auf
  demselben Rechner, Tickmills Server steht wie BeyondIQCapital auf UTC+3 —
  der Mechanismus müsste dort genauso greifen. **Belegt ist das bisher nur am
  FK-Terminal**, EKs eigenes habe ich nicht angefasst (Fast-Task alle 2 Min.).
  Falls es zutrifft, würde EKs ORB-Bein Entries systematisch verspätet sehen —
  das würde zum dokumentierten 2026-09-03-Vorfall passen ("NASDAQ-ORB-Signal
  hing bis 21:45 statt 21:00"), der damals dem blockierenden dukascopy-Bein
  zugeschrieben wurde. Fertig zum Ausführen: `EK-Portfolio-Bridge/
  probe_orb_bar_window.py` (read-only, sendet keine Order) — am besten direkt
  nach einem beendeten Fast-Lauf. Soll ich das ausführen, oder machst du es?

- **Kostenmessung EUR/USD: vier Annahmen von mir, die deine Bestätigung
  brauchen** (2026-09-09, im Rahmen der CLS-Kostenvalidierung).
  (a) **Messfenster 08:00–12:30 Berlin** — abgeleitet aus der Handelszeit von
  `cls_practical` selbst (`test_hour=9.0` bis `entry_cutoff="12:00"`), nicht
  von dir vorgegeben. Ein 24h-Mittel wäre durch Asien-Session und Rollover
  verzerrt, aber die Fenstergrenzen sind meine Wahl.
  (b) **Alle Kostenblöcke werden im Backtest in `spread_bps` gebündelt**
  statt Slippage getrennt in `slippage_bps` — Begründung: der Live-Bot setzt
  keinen Broker-TP (`target=None`), jeder Ausstieg ist eine Marktorder und
  slippt, während `slippage_bps` in der Engine NUR auf Stop-Exits wirkt.
  (c) **`risk_pct=0.25 %` im Validierungslauf** (= `CAPITAL_WEIGHT` 1/6 ×
  `LEG_RISK_PCT` 1,5 %, also das real gehandelte Risiko) statt des
  Engine-Defaults 0,5 %.
  (d) **EK/Tickmill-Kosten sind im Validierungslauf GESCHÄTZT, nicht
  gemessen** (0,20 Spread / 0,50 Entry-Slip / 0,50 Exit-Slip). Die
  Tickhistorie des Terminals deckt das Handelsfenster mit 15 Ticks nicht ab.
  Sauber wird das nur mit Vorwärts-Sampling während der Handelszeit — sag,
  ob ich das aufsetzen soll.

- **EK-Portfolio-Bridge: `CAPITAL_WEIGHT` (1/8) ist definiert, wird aber
  NIRGENDS im Code verwendet** (2026-09-09 gefunden). `config.py:57` schreibt
  die Formel `risk_dollars = CAPITAL_WEIGHT * LEG_RISK_PCT * equity` explizit
  fest (identisch zu `ek_portfolio/paper_bot.py`, das sie auch so rechnet) —
  die Bridge uebergibt aber ueberall nur `config.LEG_RISK_PCT[leg]` an
  `calc_lot_size()`. Live verifiziert im Log: OU-Modell rechnet
  `risk_amount=33.67 EUR` bei Equity 3367.90 = **exakt 1,0 %**, also die
  volle `LEG_RISK_PCT`-Stufe ohne die 1/8-Verduennung. Jedes Bein handelt
  damit ~8x groesser als dokumentiert. Gebremst wird das nur noch von
  `MAX_TOTAL_RISK_PCT = 8 %` — was erklaert, warum das Konto praktisch
  dauerhaft am Deckel klebt (heute durchgehend ~247–256 von ~269 EUR) und
  Beine sich gegenseitig aushungern: **der CLS-Practical-Entry vom 2026-09-09
  10:30 (EURUSD, den alle 3 Challenge-Konten genommen haben) wurde auf EK
  genau deswegen uebersprungen** ("offen 251.32 + neu 50.94 > Deckel 272.36").
  Wer zuerst laeuft, bekommt das Risiko — das ist kein gewolltes Portfolio-
  Verhalten.
  **BACKTEST-ANTWORT (2026-09-09, auf deinen Auftrag):** eindeutig ein Bug,
  keine Absicht. Ich habe die `ek_v2_realistic_final.json`-Studie aus den
  Bein-Kurven in `portfolio_construction/results/legs/` rekonstruiert (5 von
  6 Beinen reproduzieren die dortigen `per_leg_standalone`-Zahlen exakt, btc
  minimal ab durch die Renditen-Skalierung) und dann beide Risikologiken
  gegeneinander gerechnet:
  | Variante | CAGR | Max Drawdown |
  |---|---|---|
  | mit 1/6-Kapitalverduennung (= Studie, = `paper_bot.py`) | 75,2 % | **-16,1 %** |
  | Studie `riskopt_20dd` zum Abgleich | 76,8 % | **-19,2 %** |
  | **ohne Verduennung (= was die Live-Bridge tut)** | 1199 % | **-73,7 %** |
  Die 8 % je Bein sind also die Risikostufe INNERHALB einer Kapitalscheibe,
  nicht auf das ganze Konto. Ohne Verduennung liegt der Max Drawdown bei
  -73,7 % statt der validierten -19,2 %, gegen die auch der 20 %-Kill-Switch
  ausgelegt wurde. **Nach deinem eigenen Kriterium ("wenn die Werte deutlich
  schlechter werden muessen wir das Risiko anpassen") ist damit klar: Risiko
  anpassen, BEVOR am Deckel etwas passiert.**
  ⚠️ **Deshalb den aggregierten Deckel NICHT auf 30 % erhoeht.** Genau dieser
  8 %-Deckel ist aktuell die einzige Bremse, die das 8x-Risiko im Zaum haelt
  (er tut unfreiwillig die Arbeit der fehlenden Verduennung). Von 8 % auf
  30 % zu gehen, solange die Verduennung fehlt, wuerde die Bremse loesen
  statt das Risiko zu ordnen. Braucht deine ausdrueckliche Bestaetigung —
  siehe Vorschlag unten.
  **Offen:** mit 1/8-Verduennung faellt bei 3,4k Equity fast jedes Bein unter
  das Broker-Mindestlot (ctnl_continuation 2,10 EUR statt 16,80). Verduennung
  einbauen erfordert deshalb im selben Zug eine Neukalibrierung von
  `LEG_RISK_PCT` auf die echte Kontogroesse (Phase-6-Arbeit, eigene Session).

- **Challenge/Funded OU-Bein: der Entry-Filter haengt an einem simulierten
  Buch, das von den echten Positionen abgedriftet ist** (2026-09-09).
  Warum heute kein OU-Trade auf Challenge kam, obwohl EK APD genommen hat:
  `challenge_portfolio/paper_bot.py::_scan_ou_modell()` laesst
  `simulate_bracket_portfolio()` ueber 450 Tage durchlaufen und uebernimmt
  dessen internen `max_total_risk_pct = 5 %`-Deckel. Instrumentierter Lauf
  (2026-09-09): das SIMULIERTE S&P-Buch haelt 4 offene Positionen (RL ab
  08-27, D ab 08-28, EXPE + SYY ab 09-04) mit 4626.5 von 5727.7 Risiko —
  ein 5. Slot braucht 1145.5 und passt um ~45 nicht mehr rein. Blockiert
  wurden dadurch am 09-08 und 09-09 **alle** Kandidaten (APD, AIG, AMGN,
  DHI, LEN, SPG, TROW, UPS). Der Haken: **RL und D wurden live nie eroeffnet**
  (stehen in keinem `bridge_state_*.json`) — sie stammen aus der Zeit vor dem
  `include_open_positions=True`-Fix (2026-09-02) und belegen jetzt 2 der
  ~4 nutzbaren Risiko-Slots, bis sie simuliert per max_holding auslaufen
  (~09-16/09-17). Das Bein ist also nicht "still", sondern durch Phantom-
  Positionen blockiert. **Frage: soll der Sim-Risikodeckel gegen die ECHTEN
  offenen Positionen laufen statt gegen das simulierte Buch?**

- **Restlaufzeit-Gate: eine Design-Entscheidung + eine offene Frage**
  (2026-09-09, Details CHANGELOG). Die beiden Latenz-Vorschläge von gestern
  Abend hast du freigegeben und sie sind umgesetzt (Gate in allen 3
  Portfolio-Bridges, Task-Offsets verschoben). Zwei Punkte bleiben:
  (1) **Ausgenommen habe ich `ou_modell` und `btc_ema_cross`** — reine
  Tagessignale, ein M5-SL-Berührungscheck wäre dort sinnlos. Das war meine
  Einschätzung, nicht deine Ansage.
  (2) **Der Gate hätte den CLS-Trade von heute NICHT verhindert.** Auf dem
  Broker-Feed lag das 08:25-UTC-Low 0,1 Pip ÜBER dem SL; der Stop fiel erst
  16 Sekunden nach dem Entry (siehe den parallel entstandenen
  Kostenmodell-Eintrag im CHANGELOG). Das Signal war zum Entry-Zeitpunkt also
  wirklich noch am Leben — der Gate verhält sich korrekt, greift aber bei
  dieser Verlustursache nicht. Die strengere Variante, die heute
  gegriffen hätte, liegt als eigener Punkt in der Ideen-Inbox
  („Gegen das Signal"-Check) — dort mit allen Zahlen zum Abwägen.
  (3) **Ungefragt mitgemacht:** `Funded-Portfolio-Bridge/executor.py` loggte
  bei `order_send()==None` weiterhin nur „None". FK hat das heute früh
  bekommen, EK parallel über `core/order_send.py` — Funded war die letzte
  Bridge ohne. Genau dieser blinde Fleck hat heute auf zwei Bridges je Stunden
  Diagnose gekostet, deshalb habe ich `mt5.last_error()` + Request dort
  nachgezogen. Rein diagnostisch, ändert nichts daran, ob oder was gesendet
  wird — sag Bescheid, falls du das zurückgedreht haben willst.
- **dukascopy-Hang-Fix: eine Plan-Abweichung + Verifikation steht noch aus**
  (2026-09-09, Details CHANGELOG). Der freigegebene Plan sah zusätzlich vor,
  dieselben engeren Retry-Werte auch in `fk_instant_funding/paper_bot.py`s
  eigenem Paper-Loop zu setzen (der die Telegram-Meldung aus deinem
  Screenshot erzeugt). **Habe ich beim Umsetzen bewusst weggelassen**: dort
  läuft `source="live"`, also ein echter dukascopy-Netzwerkabruf — ein
  20s-Timeout würde dort legitime, nur langsame Abrufe abwürgen und die
  Meldungen eher häufiger machen statt seltener. Die Begründung für die
  engeren Werte gilt nur bei `source="lake"` (Normalfall = Millisekunden-
  Parquet-Read). Heißt konkret: **die Meldungen aus deinem Screenshot
  (Paper-Bot) werden vorerst weiter auftreten** — die Änderung wirkt nur auf
  die beiden Echtgeld-Bridges. Sag Bescheid, falls du die Paper-Meldungen
  trotzdem stummer haben willst (dann eher über eine Dedup-/Sammelmeldung
  als über kürzere Timeouts). Zweitens: verifiziert ist bisher nur die
  Syntax + die `_retry()`-Signatur — ob der Fix im echten Lauf greift,
  zeigt erst der nächste reguläre Scheduled-Task-Lauf beider Bridges
  (danach `task_run.log`/`task_run_fast.log` gegenlesen: keine
  unbehandelten Tracebacks mehr, im Fehlerfall die neue "...wird fuer
  diesen Zyklus uebersprungen"-Zeile).
- **Wiederholende-Fehlermeldung-Fix: Design-Entscheidungen waren eigenes
  Judgement** (2026-09-08, Details CHANGELOG). (1) Dedup ist 1x/TAG pro
  Signal/Order, nicht 1x fuer immer — reagiert am nächsten Tag wieder frisch.
  (2) Bei fehlgeschlagenem EXIT wird nur die Telegram-Meldung gedämpft, der
  Schliessversuch selbst läuft weiter jeden Zyklus (kein stilles Aufgeben).
  (3) Dabei einen zusätzlichen echten Bug gefunden+mitbehoben: ein
  fehlgeschlagener Exit setzte die Position bisher trotzdem auf "closed",
  obwohl sie real offen blieb (betraf FK Instant Funding + Funded-Portfolio-
  Bridge). Nur `py_compile` + isolierte Funktionstests, kein echter Live-Lauf
  mit einem echten wiederholten Fehler abgewartet.
- ~~`bridge_status/snapshot.json` seit Montag 17:01 Uhr (CEST) nicht mehr
  aktualisiert -- Bridge-Watchdog liefert seit ~18h/~30h keinen neuen
  Stand~~ — **war ein Fehlalarm, aufgeklärt 2026-09-08 (heutige Session):
  kein Bot-/Rechner-Ausfall, sondern reines Git-Push-Problem.** Der lokale
  Rechner hatte durchgehend weiterlaufende, aktuelle Snapshots (lokale
  `bridge_status/snapshot.json`/Logs zeigten beim Gegencheck Läufe bis
  wenige Minuten vor der Prüfung) — nur die Pushes zu GitHub schlugen seit
  2026-09-07 ~17:xx durchgehend fehl ("fetch first", weil die
  Auto-Commit-Skripte vor dem Push nicht pullen), nachdem eine parallele
  Cloud-Session zwischenzeitlich selbst auf `main` gepusht hatte. Dadurch
  sah GitHub/Streamlit einen eingefrorenen Stand, obwohl lokal alles lief.
  Jetzt zusammengeführt + gepusht (dieser Merge), siehe CHANGELOG
  2026-09-08 "Git-Sync-Reparatur". **Root Cause inzwischen ebenfalls behoben
  (2026-09-09, Commit `a34cb8a`)**: neue gemeinsame
  `scripts/lib/git_sync_push.ps1` (`Sync-AndPush`) fetcht+merged jetzt vor
  jedem Push, eingebunden in alle 11 `scripts/*_task.ps1` + analog in
  `C:\Users\andre\Bridge-Watchdog\watchdog.py`. Bei einem echten
  Merge-Konflikt wird der Merge abgebrochen und der Push für diesen Lauf
  ausgelassen (statt in einem kaputten Merge-Zustand zu landen). Verifiziert:
  PowerShell-Parser + `py_compile` sauber; der praktische Beweis kommt mit
  dem nächsten Push-Zyklus der geplanten Tasks.
- ~~EK-Portfolio-Bridge/ou_modell: Order fuer EXPE scheiterte am 2026-09-07
  wiederholt mit "Market closed"~~ — **wahrscheinliche Ursache gefunden
  2026-09-09** (volle Log-Auswertung `EK-Portfolio-Bridge/logs/task_run.log`).
  Um 15:54:27 Uhr, kurz VOR der ersten fehlgeschlagenen Order, meldete der
  eigene Deviation-Schutz (`legs/ou_modell/executor.py:192`)
  `entry_deviation_too_large` mit `deviation=1.0` fuer EXPE — eine Abweichung
  von exakt 100% zwischen Zielpreis (297.51) und `symbol_info_tick().ask`
  deutet auf `ask=0` hin, also KEINEN Live-Kurs fuer dieses Symbol zu dem
  Zeitpunkt (kein Rundungsfehler, ein "kein Kurs verfuegbar"-Symptom). 6
  Minuten spaeter (ab 16:00 Uhr) kam wieder ein Tick-Wert zurueck, der
  Deviation-Check liess die Order durch, aber `order_send()` wurde vom
  Broker mit `retcode=10018` (`TRADE_RETCODE_MARKET_CLOSED`) abgelehnt — ein
  echter Broker-seitiger Ablehnungscode, kein Verbindungs-/Timeout-Fehler.
  Zusammengenommen spricht das dafuer: der generische
  `_nyse_is_open()`-Handelszeiten-Gate war korrekt offen, aber die
  tatsaechliche, symbolspezifische Handelssession fuer EXPE bei Tickmill war
  zu dem Zeitpunkt noch nicht aktiv (verzoegerter Session-Start fuer dieses
  eine CFD, oder ein Symbol-seitiger Halt) — passt auch dazu, dass Zielpreis
  UND SL/TP ueber alle ~15 Wiederholungen (15:15-17:42 Uhr) identisch blieben
  (festgehaltenes Tagessignal, kein Refresh). Nicht 100% zweifelsfrei (kein
  Broker-Session-Log einsehbar), aber deutlich konkreter als der bisherige
  Stand. Kein Code-Bug, kein Handlungsbedarf — falls es sich wiederholt,
  waere Tickmills tatsaechliche Handelszeit fuer US-Aktien-CFDs (ggf.
  abweichend von den generischen NYSE-Kernzeiten) der naechste Schritt.
- ~~EK-Portfolio-Bridge: unformatiertes Log-Fragment in `recent_events`
  (Rohtext eines f-Strings statt ausgewerteter Werte)~~ — **geklaert
  2026-09-09, kein Bug.** Volle Einzel-Run-Logs
  (`logs/run_20260907_151503.log` Zeile 274ff, `run_20260907_164504.log`
  Zeile 500ff) zeigen: das ist ein ganz normaler Python-Traceback (`ERROR
  run_once: cls_practical: unerwarteter Fehler`), bei dem Python 3.14 die
  Quellzeile des `raise LakeStaleDataError(...)`-Statements woertlich mit
  ausgibt (Standard-Traceback-Format seit Python 3.11) — erklaert die "rohe
  f-String"-Optik vollstaendig. Ablauf beide Male identisch: Lake-Daten zu
  alt -> `with_live_fallback()` (erst am selben Tag, 09-07, gebaut) greift
  korrekt und versucht Live-Fetch -> Live-Fetch scheitert SEINERSEITS am
  bereits bekannten dukascopy-Bug (`_stream()` Zeile 219/242, `TypeError:
  '>' not supported between instances of 'str' and 'float'`, identisch fuer
  beide Vorkommen: EURUSD_M5 um 15:21 und USDCHF_M15 um 16:53) -> keine
  weitere Fallback-Ebene mehr -> Exception propagiert bis `_run_leg()` hoch
  und wird dort mit vollem Traceback geloggt (kein Telegram-Spam,
  Bridge-Status blieb "ok", wie schon vermutet). Kein neuer Bug — nur eine
  bisher nicht explizit beobachtete Kombination zweier bekannter Dinge
  (Lake-Staleness + dukascopy-Bug). Idee fuer spaeter (kein Auftrag):
  `with_live_fallback()` koennte einen fehlschlagenden Live-Fallback selbst
  auch abfangen und als "no_signal" statt als harten Leg-Fehler behandeln —
  aktuell nicht gebaut.
- ~~Funded-Portfolio-Bridge: wiederholte `IPC timeout`-Verbindungsfehler auf
  allen 3 MT5-Konten, seit ca. 11:52 Uhr 09-08 andauernd~~ — **war zeitlich
  begrenzt, seit 2026-09-08 12:34 Uhr durchgehend stabil** (geprueft
  2026-09-09, inkl. sauberer Laeufe den gesamten heutigen Vormittag).
  Log-Auswertung: Fehler traten durchgehend von 09:52 bis 12:24 Uhr auf
  09-08 auf (alle 3 Konten pro Zyklus gemeinsam betroffen), endeten
  schlagartig ab 12:34 Uhr. Prozessliste zeigt: der Terminal-Prozess "MT5
  Terminal - GoldFKBot" (IQ-Markets/BeyondIQCapital-Konto 16054) wurde exakt
  in diesem Fenster (12:19:36 Uhr) neu gestartet — passt zum ersten wieder
  erfolgreichen Connect fuer genau dieses Konto um 12:24 Uhr. Wahr-
  scheinlichste Ursache: `_terminal_running()` in `executor.py` prueft nur,
  OB ein Terminal-Prozess mit passendem Pfad LAEUFT (PowerShell-
  Prozessliste), nicht ob er noch reagiert — ein haengender, aber technisch
  noch laufender GoldFKBot-Prozess waere von `_ensure_terminal_running()`
  nie automatisch neugestartet worden. Da `run_once.py` alle 3 Konten
  sequenziell in EINEM Python-Prozess mit gemeinsamem MT5-IPC-Client
  abarbeitet, wuerde ein haengender Connect fuer ein Konto plausibel auch
  die beiden anderen im selben Zyklus mitreissen — passt zum beobachteten
  Muster (immer alle 3 gemeinsam betroffen). Nicht zweifelsfrei bewiesen
  (kein Log vom haengenden Prozess selbst), aber die zeitliche Deckung ist
  sehr stark. Terminals nicht angefasst, aktuell kein Handlungsbedarf, da
  stabil. Idee fuer spaeter (kein Auftrag): `_terminal_running()` um einen
  echten Health-Check erweitern statt nur Prozess-Existenz zu pruefen.
- ~~Second-Brain-Lint (wöchentliche Routine) lief heute ins Leere:
  `knowledge/scripts/lint.py` + `.claude/skills/second-brain-lint/SKILL.md`
  fehlen im Repo~~ — **Korrektur 2026-09-09: falscher Befund, beide Dateien
  waren die ganze Zeit da.** `git ls-files`/`git log` bestaetigen: beide
  wurden bereits am 2026-09-07 committet (`af96c0e`, "Second Brain:
  Handoff-Skill, Edge-Card-Workflow, PARA-Notizen, Tooling") und sind auf
  `origin/main` gepusht — der Eintrag vom 2026-09-07 beruhte auf einem
  fehlerhaften `git log`-Check der damaligen Session (Detail nicht mehr
  rekonstruierbar). Lint jetzt tatsaechlich gelaufen (erster echter
  Durchlauf seit 2026-09-01): 8 tote Wikilinks (1 davon falsch-positiv,
  `[[slug]]` in CHANGELOG.md:1008 ist literaler Beispieltext, kein echter
  Link), 6 verwaiste Seiten, 0 veraltete Statustabellen-Daten, 14
  unverarbeitete Clippings. Details/Einsortierung: CHANGELOG + unten.
- **Neuer Wikilink-Typ beim heutigen Lint-Lauf: Cross-System-Link auf eine
  Claude-Memory-Datei** (`resources/cross-asset-momentum-spillover.md:86`,
  `[[cls-practical-strategy-state]]` — zeigt auf die Memory-Notiz
  `cls_practical_strategy_state.md`, nicht auf eine `knowledge/`-Datei).
  Fuer Obsidian technisch ein toter Link, obwohl der referenzierte Inhalt
  existiert — reine Konventionsfrage (z.B. eigene Zitierform statt
  `[[...]]` fuer Memory-Referenzen), siehe Skill `second-brain-lint`.
  Bisher einziges bekanntes Vorkommen dieses Typs. Wie soll auf Memory-
  Inhalte aus `knowledge/`-Notizen kuenftig verwiesen werden?
- ~~`DataLake-Ingest-Fast5` + `FKInstantFunding-MT5-Bridge` (stündlich):
  auffällige Lücke ~14:31-15:0x Uhr~~ — **bewusst verworfen 2026-09-09
  (Nutzerentscheid)**: einmaliger ~45-Minuten-Ausreisser am 2026-09-07,
  seither nicht wiederholt, ungeprüfte Akku-/Energieverwaltungs-Vermutung
  bleibt unverifiziert. Keine weitere Untersuchung — bei erneutem Auftreten
  neu aufgreifen.
- ~~FKInstantFunding-MT5-Bridge: echter Order-Executor gebaut, wartet auf
  `DRY_RUN=False`~~ — **`DRY_RUN=False` gesetzt 2026-09-08** (expliziter
  Nutzerauftrag "Setze dry run False, damit ist orb jetzt live"). NY-Open
  ORB (SP500/US30/NASDAQ) ist damit LIVE auf echtem Geld, alle anderen 6
  Beine bleiben ueber `LIVE_LEGS` weiterhin nur geplant/geloggt. Details/
  Vorgeschichte: CHANGELOG 2026-09-07+08. Weiterhin ungetestet bis zum ersten
  echten Entry: die MT5-Live-Positions-Iteration der Offene-Risiko-Checks
  (aktuell 0 offene Positionen) — beim ersten echten Trade gegenlesen, ob
  Sizing/SL/Telegram-Meldung wie erwartet aussehen.
- ~~Funded-Portfolio-Bridge: TTP Konto 2 (Demo, #504072729) verbindet seit
  Wochenschluss nicht mehr~~ — **behoben 2026-09-07** (gefunden beim
  Log-Check nach dem Data-Lake-Fallback-Umbau, gemeinsam mit Nutzer geloest).
  Ursprünglicher Prozess-Neustart (Task Manager) half nicht wirklich weiter
  (Prozess lief laut Startzeit unveraendert weiter) — eigentliche Root
  Cause erst beim Versuch, einen komplett frischen, dedizierten
  Terminal-Ordner anzulegen (Nutzerwunsch, Kopie von "TTP MT5 Terminal
  Konto1neu" nach "...Konto2neu"): der frisch kopierte, noch nie gestartete
  Terminal scheiterte dabei zunaechst mit `IPC timeout`/`IPC send failed`
  statt "Authorization failed" -- `executor.py::_connect_once()` liess
  `mt5.initialize()` einen fehlenden Terminal-Prozess selbst starten, aber
  OHNE `/portable`-Flag, wodurch der neue Prozess mit den anderen
  gleichzeitig laufenden MT5-Terminals auf der Maschine kollidierte
  (identisches Fehlerbild + identische Ursache wie der 2026-08-28-Vorfall,
  der `FKInstantFunding-MT5-Bridge` bereits einen `_ensure_terminal_running()`
  -Schutz eingebaut hat -- Funded-Portfolio-Bridge hatte den bisher NICHT
  uebernommen). Fix: identisches `_ensure_terminal_running()`-Muster
  (Powershell-Prozess-Check + `/portable`-Vorstart) jetzt auch in
  `Funded-Portfolio-Bridge/executor.py::_connect_once()` + `test_connection.py`
  ergaenzt -- gilt automatisch fuer alle 3 Konten, da `run_once.py` dieselbe
  `executor.connect()` wiederverwendet. Verifiziert: `test_connection.py`
  verbindet jetzt sauber mit allen 3 Konten inkl. Konto 2 (Equity
  $100.102,87). Offen: `AutoTrading` zeigt bei Konto 2 noch `False` (bei den
  anderen beiden `True`) — reiner Terminal-GUI-Schalter ("Algo Trading"-
  Button), muss einmalig manuell im neuen Terminal-Fenster aktiviert werden,
  sonst koennte dieses Konto spaeter keine echten Orders senden. Alter,
  verwaister Ordner "TTP MT5 Terminal - Konto2" (Prozess lief seit Samstag
  durch) kann geschlossen werden, config.py zeigt seit dem Fix nicht mehr
  darauf.
- ~~Lokaler `main` 64 vor / 1 hinter `origin/main`~~ — **gemergt 2026-09-06**
  (Nutzer-OK): der eine fremde Commit (`7616951`) betraf nur `DASHBOARD.md`
  und stammte noch von der alten, unredesignten Dashboard-Struktur (Sept 4)
  — Merge-Konflikt manuell aufgelöst, alte Struktur verworfen (längst durch
  das Sept-6-Redesign abgelöst), aber der einzige darin noch NICHT
  anderswo erfasste Punkt unten neu aufgenommen (siehe nächster Punkt).
- ~~Funded-Portfolio-Bridge: Data-Lake-Cold-Start-Lücke vom 2026-09-04,
  Frage nie beantwortet~~ — **gebaut 2026-09-07** (Nutzerauftrag "Baue den
  Fallback"): neue `data_lake.reader.with_live_fallback()` faengt
  `LakeMissingDataError`/`LakeStaleDataError` pro Fetch-Aufruf ab und weicht
  fuer genau diesen Aufruf auf die echte Live-Fetch-Funktion aus, statt den
  Scan-Zyklus hart scheitern zu lassen. Angewendet auf alle Lake-faehigen
  Beine in allen 3 Bridges (Funded-Portfolio-Bridge, EK-Portfolio-Bridge,
  FKInstantFunding-MT5-Bridge) — bewusst NICHT auf OU-Modell (eigene,
  gewollte Skip-pro-Ticker-Logik, ein Fallback dort wuerde bei einem echten
  Cold Start den yfinance-Rate-Limit-Ansturm reproduzieren, den die eigene
  Slow-Lane vermeiden soll). Jeder Fallback loggt eine Warnung, spammt aber
  kein Telegram. Verifiziert (isolierter Wrapper-Test + unveraenderte
  Zeilenzahlen im gesunden Lake-Fall). Details: CHANGELOG.
- ~~5-Min-Fast-Trigger: 3 Engineering-Entscheidungen unbestätigt~~ —
  **bestätigt 2026-09-06** (Nutzerauftrag, echt nachgeprüft statt pauschal
  abgenickt): M15-Zusatz für SP500/US30/NASDAQ (Begründung Opening-Range-
  Timing schlüssig), `account_state_lock()` (Code gelesen — identische
  `os.O_CREAT|O_EXCL`-Technik, die unabhängig davon am selben Tag für
  `data_lake/manifest.py`s analoges Problem gebaut wurde, starkes Indiz für
  den richtigen Ansatz), Retry-Parameter 3x/3s/20s im Fast-Pfad direkt im
  Code verifiziert (`run_once_fast.py`). Alle drei sinnvoll.
- ~~Funded-Portfolio-Bridge: kein "Signal zu alt"-Schutz beim Echt-Entry~~
  — **Korrektur 2026-09-06**: war bereits längst umgesetzt
  (`MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY=60` in `_process_leg()`, gilt generisch
  für alle Beine, per Code-Check bestätigt) — der gegenteilige "noch
  offen"-Eintrag hier war ein stehengebliebener Duplikat-Stand vom selben
  Tag, jetzt entfernt.
- ~~2 neue Funded-Portfolio-Bridge-Konten (TTP #504069845, IQ 15514)
  verbanden nicht~~ — **Korrektur 2026-09-06**: war bereits am 2026-09-03
  gelöst (Status-Tabelle unten zeigt seitdem "alle 4 verbunden"), der
  "Fix in Arbeit"-Eintrag hier war stehengeblieben. Tatsächliche Ursache:
  "DLL-Importe zulassen" (eigene Einstellung, getrennt von AutoTrading) +
  ein strukturell defekter Terminal-Ordner → Konten auf funktionierende
  Ordner umgehängt.
- ~~Merge-Konflikt in diesem Abschnitt + CHANGELOG~~ — nachgeprüft
  2026-09-04, keine Widersprüche/Duplikate gefunden.
- ~~CLS Practical scheitert wiederholt an `dukascopy_python`~~ — Retries
  in allen 3 Bridges erhöht (3→6 Versuche), 2026-09-02. Bug bleibt in der
  Bibliothek selbst, nur Toleranz erhöht.
- ~~Rechner-/Task-Lücke ~9h über Nacht~~ — Ursache: Windows Modern Standby
  über AC-Display-Idle-Timeout, nicht "Rechner aus". Cache-Validierung +
  WakeToRun + neuer Bridge-Watchdog als Absicherung, 2026-09-02.
- ~~Telegram-Logik uneinheitlich zwischen den drei Portfolios~~ —
  `fk_instant_funding` auf gleiche Queue-Infrastruktur gehoben, 2026-09-02.
- ~~`fk_instant_funding/paper_bot.py`: letzte ORB-Kopie auf altem Stand~~ —
  nachgezogen 2026-09-02, alle 3 aktiven ORB-Träger jetzt gleich.
- ~~Funded-Portfolio-Bridge OU-Modell-Bein meldete nie offene Signale~~ —
  Root Cause (offene Positionen fielen unter den Tisch) + NYSE-Gate
  gefixt, 2026-09-02.
- ~~EK-Portfolio-Bridge: vage "cls_practical: unerwarteter Fehler"~~ —
  geklärt 2026-09-04: bekannter dukascopy-90s-Hang, kein neuer Fehler.
- ~~EK-Portfolio-Bridge: NASDAQ-Ticket 262117522 hing am Session-Ende-Exit~~
  — geschlossen 2026-09-04 (Comment-Feld für Tickmill zu lang, gekappt).
- ~~EK-Portfolio-Bridge: US30 "Invalid stops"~~ — zweiter Bug gefunden
  2026-09-04 (TP auf falscher Seite bei LONG), SL-Prüfung aufs TP erweitert.
- ~~2 neue Funded-Portfolio-Bridge-Konten waren bereits anderweitig
  vergeben~~ — bewusste Konsolidierung (Nutzerentscheid 2026-09-02).
- ~~`dukascopy_python` hing komplett fest, ohne Timeout~~ — neue
  `_call_with_timeout()` (90s) um jeden Retry, 2026-09-02, alle 3 Bridges.
- ~~`OU-Modell-ScannerHourly` verwaist~~ — bewusst weiterlaufen lassen
  (Streamlit-Seite braucht ihn), 2026-09-02.

### Offene Aufgaben

- **`cls_practical/results/final_verification_vs_buyhold.csv` ist veraltet und
  irreführend** (2026-09-09 gefunden). Die CSV stammt vom 2026-08-13, die
  Engine wurde am 2026-08-20 geändert (`f549b23`, u.a. neuer `test_hour=9.0`).
  Derselbe Aufruf liefert heute $73.558,93 statt der dort ausgewiesenen
  $60.393,55 (+22 %). Neu erzeugen — bis dahin ist jede Zahl daraus falsch.
  Zweiter Fall dieser Art nach dem Gold-ASB-Liquiditätsfilter; lohnt zu prüfen,
  ob weitere `results/`-CSVs älter sind als ihre Engine. Priorität: Mittel.

- **Risiko-Anpassung CLS/Challenges — Entscheidung steht aus** (2026-09-09).
  Nach deinem Entscheid "erst Kostenmodell validieren, dann Risiko anpassen"
  ist die Messung fertig (siehe `CHANGELOG.md` und
  `resources/broker-kostenmodell-eurusd.md`), die Risiko-Runde noch nicht.
  Offen bleiben: Mindest-SL-Abstand gegen den Live-Spread, Nominal-/
  Hebel-Deckel, absoluter Pip-Floor statt/zusätzlich zum relativen
  `min_sl_atr_mult`, und ob `cls_practical` in dieser Form weiterläuft.
  Reihenfolge laut deinem Entscheid: Challenges zuerst, dann EK, dann FK.
  **Bis dahin läuft `cls_practical` auf allen drei Portfolios unverändert
  live** — bewusst so entschieden, kein Versehen.
- **Kein Hebel-/Mindestabstand-Schutz in ALLEN vier Bridges** (2026-09-09
  gefunden). `Funded-Portfolio-Bridge/sizing.py`,
  `EK-Portfolio-Bridge/core/sizing.py`, `FKInstantFunding-MT5-Bridge/sizing.py`
  und `CLS-Practical-Bridge/sizing.py` haben identisch nur
  `min(lots, info.volume_max)` als Obergrenze. Die Abweichungsprüfung
  `MAX_OU_MODELL_ENTRY_DEVIATION_PCT` existiert nur für `ou_modell`. Gehört
  in die Risiko-Runde oben. Priorität: Hoch.
- **Rates-Risikomultiplikator erreicht das Live-Sizing nie** (2026-09-09
  gefunden). `challenge_portfolio/paper_bot.py:361` skaliert mit
  `combined_mult` nur das *reportete* `r_multiple`; das Live-`risk_dollars`
  in `run_once.py::_process_leg` ist ein flaches
  `CAPITAL_WEIGHT × LEG_RISK_PCT × equity`. Die als "übernommen"
  dokumentierte Daily-Rates-Risikoskalierung wirkt live also nicht.
  Priorität: Mittel.
- **Fill-Rücklesepfad greift auf TTP nicht** (2026-09-09 gefunden).
  `Funded-Portfolio-Bridge/executor.py` speichert `entry_price: 0.0` (weder
  `result.price` noch `positions_get(ticket=…)` lieferten einen Preis); auf
  IQ funktioniert derselbe Pfad. Ohne echten Fill sind TTP-Trades
  nachträglich nicht auditierbar — die Slippage-Messung musste deshalb über
  `history_orders_get()` gehen. Priorität: Niedrig-Mittel.

**Mittel**
- **14 unverarbeitete Clippings** in `knowledge/Clippings/` (Stand
  2026-09-09-Lint, davor 12 seit 2026-09-03) — u.a. Edge-Genesis/-Decay,
  Risk-Factor-Investing, Sektor-Rotation, "Six Repos One System", "How
  system works" — noch nicht durch den CODE-Prozess.
- ~~Second-Brain/Dashboard-Struktur: Feedback nach ein paar Tagen
  einholen~~ — erhalten 2026-09-06: Nutzer sehr zufrieden mit dem neuen
  Workflow, Dashboard passt gut rein. Redesign (Prioritäten-Sortierung,
  kürzere Texte, Status-Tabellen-Split) heute umgesetzt.
- ~~5 unverarbeitete Clippings~~ — verarbeitet 2026-09-02, Ordner geleert.
- ~~EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00)~~ — bewusst
  zurückgestellt 2026-09-01 (0% historische Relevanz, noch nicht lohnend
  genug) — nicht erneut vorschlagen ohne neuen Trigger.
- ~~EK-Portfolio-Bridge/NY-Open-ORB: "Invalid stops"~~ — behoben
  2026-09-02.

**Niedrig**
- `knowledge/`-Altlasten (Lint 2026-09-09, vorher 2026-09-01): tote
  Wikilinks (`[[cls-practical]]`, `[[gap-fade]]`, `[[execution-overlay]]`,
  je 2 Vorkommen) + 6 verwaiste Seiten, meist unkritisch. Details:
  Lint-Output/CHANGELOG.

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld** (btc/ou_modell weiterhin direkt Dukascopy/yfinance; gold_asb/cls_practical/ctnl x2 jetzt `source="lake"`) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-08      |
| EK-Portfolio-Bridge-Fast                                | Tickmill Live (55918977, geteiltes Terminal)                                             | **LIVE — echtes Geld** (3 MT5-native Beine: ORB/Gold-Silber/Trend-Pullback, kein Dukascopy)  | Ready (alle 2 Min, Mo–Fr)       | 2026-09-03      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | **LIVE — echtes Geld** (7 Beine via `LIVE_LEGS`: orb_sp500/us30/nasdaq + gold_asb/cls_practical/ctnl_continuation/ctnl_reversal seit 09-09; trend_pullback/gold_silver bleiben geplant/geloggt) | Ready (stündlich)               | 2026-09-09      |
| FKInstantFunding-MT5-Bridge-Fast                        | BeyondIQCapital (17764, geteiltes Terminal)                                              | **LIVE — echtes Geld** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`, analog Funded-Fast) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-09      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram, **nur noch trend_pullback/gold_silver** (die anderen 7 Beine laufen live über die Bridge, seit 09-09 hier entfernt) | Ready (stündlich)               | 2026-09-09      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator                                                                             | Ready                           | 2026-09-02      |
| Bridge-Watchdog                                         | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min)             | 2026-09-08      |
| Funded-Portfolio-Bridge (TTP+IQ Markets, 6 Beine)       | TTP Konto 2 (504072729) + TTP Konto 1 (504069845) + BeyondIQCapital (16054) — **alle 3 verbunden** (IQ 15514 am 2026-09-07 entfernt) | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`; IPC-Timeouts 09-08 09:52-12:24 Uhr, seither stabil, siehe 🔍 Bestätigung) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-09      |
| Funded-Portfolio-Bridge-Fast                            | Gleiche 3 Konten (geteilte Terminals)                                                    | **LIVE — DRY_RUN=False** (ctnl_continuation + orb_sp500/us30/nasdaq + cls_practical, `source="lake"`) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-08      |
| DataLake-Ingest-Fast                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt `data_lake_store/` für Funded-Portfolio-Bridge (19 Keys, 15-Min-Kadenz)                | Ready (alle 15 Min, Mo–Fr)      | 2026-09-04      |
| DataLake-Ingest-Fast5                                   | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt 8 M5/M15-Timing-kritische Keys für ctnl_continuation/orb/cls_practical (EURUSD M5 seit 2026-09-07) | Ready (alle 5 Min, Mo–Fr)       | 2026-09-07      |
| DataLake-Ingest-Slow                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt OU-Modell-Universum (~59 Ticker) via yfinance                                          | Ready (stündlich, Mo–Fr)        | 2026-09-04      |
| Dashboard-Telegram-Digest (neu)                         | — (nur Lesezugriff auf DASHBOARD.md, kein Order-Bezug)                                   | Schickt offene Punkte aus DASHBOARD.md per Telegram                                          | Ready (täglich 8:00)            | 2026-09-06      |

Live-Status aller drei Portfolio-Bridges jetzt auch als Streamlit-Seiten
(„Portfolio-Bridges" in der Sidebar) — lesen `bridge_status/snapshot.json`,
das der Bridge-Watchdog alle 30 Min. committet.

_Letzter Lint-Check (tote Wikilinks, veraltete Daten, Widersprüche,
verwaiste Seiten, unverarbeitete Clippings): **2026-09-09** (erster
tatsaechlich erfolgreiche Lauf seit 2026-09-01 — der Fehlversuch vom
2026-09-07 war ein falscher Befund, siehe "🔍 Braucht deine Bestätigung").
Ergebnis: 0 veraltete Statustabellen-Daten, 6 verwaiste Seiten, 8 tote
Wikilinks (1 falsch-positiv), davon 1 neuer Cross-System-Link-Fall
(Memory-Verweis, siehe oben), 14 unverarbeitete Clippings (siehe "Offene
Aufgaben"). Widersprüche (c) weiterhin nur stichprobenartig, nicht
vollstaendig manuell durchgegangen._

## Status — aktuell nicht aktiv

| Bot/Bridge                                              | Konto/Broker                                                                             | Status                                                                                          | Task Scheduler | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------- | --------------- |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt, kein Task angelegt                                                | —              | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance / BeyondIQCapital (15514, geteilt mit GoldASB)                                   | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS_MT5` leer                       | Disabled       | 2026-09-02      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | aufgelöst — Konto/Terminal bereits bei Funded-Portfolio-Bridge live                            | Disabled       | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (15514)                                                                  | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` leer                           | Disabled       | 2026-09-02      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | —                                                                                         | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` komplett leer                  | Disabled       | 2026-09-02      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert (Paper-Zwilling von EK-Portfolio-Bridge, gehört zum Portfolio)                        | Disabled       | 2026-09-01      |

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen.

- **„Gegen das Signal"-Check als Ergänzung zum Restlaufzeit-Gate**
  (2026-09-09, offen — deine Entscheidung): Der heute gebaute Gate fragt
  „wurde der SL schon berührt?". Die Alternative, die ich beim Planen
  angeboten hatte und die du damals bewusst nicht gewählt hast, fragt
  zusätzlich „wie weit ist der Kurs schon **gegen** das Signal gelaufen?" —
  Entry abbrechen, wenn beim Versuch bereits mehr als ~0,5R der Stopdistanz
  aufgebraucht sind.
  **Warum es jetzt wieder auf dem Tisch liegt:** der CLS-Trade vom
  2026-09-09 wäre davon erfasst worden, vom gebauten Gate dagegen nicht.
  Zahlen: Entry-Signal 1.163967, SL 1.163590 (3,8 Pips). Beim Entry-Versuch
  um 10:30 Berlin stand der Kurs bei 1.163680 — **0,76R schon gegen das
  Signal**. Der SL war auf dem Broker-Feed zu dem Zeitpunkt noch nicht
  berührt (08:25-UTC-Low 1.16360, 0,1 Pip darüber), der Stop fiel erst
  16 Sekunden nach dem Entry.
  **Wogegen es abzuwägen ist:** verwirft zwangsläufig auch Trades, die noch
  gelaufen wären — bei einem Bein mit 3,8 Pips Stopdistanz ist 0,76R
  Vorlauf keine ungewöhnliche Marktbewegung, sondern gut eine Minute
  normales Rauschen. Und 0,5R wäre ein gesetzter Wert, kein aus einem
  Backtest abgeleiteter. Sauber wäre, die Schwelle gegen die Bein-Historie
  zu prüfen (welcher Anteil der Gewinner startete mit wieviel Vorlauf?),
  statt sie zu raten. Zusammen mit dem parallel laufenden Kostenmodell-Thema
  (Slippage/Kommission, siehe CHANGELOG 2026-09-09) zu entscheiden — beide
  drehen an derselben Schraube „später Entry kostet mehr, als der Backtest
  denkt".
- **NY-Open ORB komplett von dukascopy lösen** (2026-09-09): der heutige
  Fix verkürzt nur die Hang-Dauer (3x/20s statt 6x/90s), beseitigt sie
  nicht. Strukturell sauberer wäre, die ORB-Entry-Daten direkt per MT5
  (`mt5.copy_rates_range()`) zu holen — genau das macht
  `EK-Portfolio-Bridge/run_once_fast.py` für seine 3 zeitkritischen Beine
  bereits ("sie haengen NIE an einem dukascopy_python-Hang"). Bewusst
  zurückgestellt (Nutzerentscheid 2026-09-09): braucht neuen Code +
  Validierung (Symbol-Suffixe, Zeitzonen, Abgleich gegen den bestehenden
  dukascopy-basierten Backtest), also eine eigene Session wert.
- **Periodischer `/doctor`-Check** (2026-09-04): zurückgestellt, noch keine
  nennenswerte Skill/MCP-Altlast bei aktuell nur 2 Skills.
- **CFDs → echte Futures umstellen** (2026-09-03): zwei getrennte,
  unentschiedene Punkte — (a) "echtere" Daten, aber eigene Rollover-Logik +
  Neuvalidierung nötig; (b) eigene Futures-Challenges bei Prop-Firms als
  möglicher neuer Track.
- **OU-Modell-Scanner ggf. komplett auf Telegram umstellen** (2026-09-02):
  Website bleibt vorerst, nicht entschieden.
- **PDFs/Bücher bulk-einbinden** (2026-09-01): prüfen ob
  `paper_dropbox/`-Pipeline dafür wiederverwendbar ist.
- **TTP/IQ ORB-Exits laufen pro Konto unabhängig auseinander** (2026-09-02):
  kein Bug (beide folgen korrekt ihrer Regel), aber noch nicht bewertet ob
  Exits kontoübergreifend synchronisiert werden sollten.
- **Stocks-in-Play 5-Min-ORB als neue Asset-Klasse** (2026-09-01, Paper
  Zarattini/Barbon/Aziz 2024, siehe [[opening-range-breakout]]): braucht
  neue Datenquelle (breites US-Aktienuniversum) + eigene Selektionslogik —
  eigenständige Idee, kein Filter-Add-on.
- **Volles 42-Asset-Futures-Universum aus dem JPM-Spillover-Paper**
  (2026-09-09, siehe [[cross-asset-momentum-spillover]]): Commodities/
  Aktienindizes/US-Treasury-Futures über den aktuellen FX/Gold-Fokus
  hinaus -- bewusst zurückgestellt, kein Termin. FX-only-Teilmenge +
  Gold-Cross-Check laufen stattdessen jetzt als eigenes Project.
- **Agentisches Research-System + separater Self-Learning-Bot** (2026-09-07):
  Konzept steht (Kernentscheidungen geklärt — autonome Ideen-Findung,
  Hybrid ML/RL, Alpaca Paper-Trading, erst Agentensystem dann Lern-Bot),
  siehe [[agentisches-research-system-und-self-learning-bot]]. Bau
  frühestens in ein paar Wochen (Nutzerentscheid), aktuell nichts zu tun.

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

- 2026-09-09 — FK Instant Funding: Paper-Bot auf die 2 noch nicht live
  geschalteten Beine (trend_pullback/gold_silver) reduziert, um doppelte
  Telegram-Meldungen mit der jetzt 7-beinigen live Bridge zu vermeiden.
  Details: CHANGELOG.
- 2026-09-09 — dukascopy-Hang entschärft: Slow-Pfad-Retry bei FK Instant
  Funding + Funded-Portfolio-Bridge von 6x/8s/90s auf die in beiden
  Fast-Lanes längst bewährten 3x/3s/20s verkürzt (Worst Case pro Bein
  ~9,7 Min. → ~66s, gehalten wird dabei der State-Lock) + FKs unbehandelten
  Lock-Absturz behoben (Fast-Lauf crashte ohne Log-Zeile, wenn der Slow-Lauf
  den Lock hielt — Funded fängt das seit jeher ab). Details: CHANGELOG.
- 2026-09-09 — FK Instant Funding: `LIVE_LEGS` um gold_asb/cls_practical/
  ctnl_continuation/ctnl_reversal erweitert (Nutzerentscheid, nach zwei
  weiteren sauberen `run_once_fast.py`-Testläufen). Damit sind 7 von 9
  Beinen live; trend_pullback/gold_silver bleiben bewusst DRY_RUN. Details:
  CHANGELOG.
- 2026-09-08 — FK Instant Funding: Fast/M5-Scan-Lane (`run_once_fast.py` +
  Scheduled Task `FKInstantFunding-MT5-Bridge-Fast`, 5 Min) + Terminal-
  Restart-Fix in `executor.py` nachgerüstet, nach Vergleich der drei
  Portfolio-Bridges beim Scan-/M5-Timing (Nutzerauftrag). `LIVE_LEGS`-
  Erweiterung (gold_asb/cls_practical/ctnl_continuation/ctnl_reversal)
  steht noch aus, wartet auf einen vollen Connect-Test außerhalb der
  Spread-Stunden-Pause. Details: CHANGELOG.
- 2026-09-08 — FK Instant Funding: `DRY_RUN=False` gesetzt (Nutzerauftrag),
  NY-Open ORB live auf echtem Geld. Second Brain: Git-Sync-Reparatur
  (lokal/GitHub 38 vs. 2 Commits auseinandergelaufen, Bridge-Watchdog-
  "Ausfall" war ein Fehlalarm), cls_practical-Cache-Bugfix einer parallelen
  Session eingespielt, neuer Fund: Funded-Portfolio-Bridge IPC-Timeouts auf
  allen 3 Konten. Details: CHANGELOG.
- 2026-09-07 — Data Lake: automatischer Live-Fallback bei Cold Start/
  haengender Ingestion gebaut (`with_live_fallback()`), beantwortet die
  seit 2026-09-04 offene Cold-Start-Frage. Details: CHANGELOG.
- 2026-09-06 — `data_lake/`-Paket committet + gepusht, Data-Lake-Pilot von
  Funded-Portfolio-Bridge auf EK-Portfolio-Bridge (gold_asb, cls_practical,
  ctnl_edge) und FKInstantFunding-MT5-Bridge (alle 6 Beine) erweitert —
  keine neue Ingestion noetig (liest denselben laufenden Lake), ein neuer
  Key (SILVER H4) ergaenzt. Jeder Pfad vor dem Umschalten gegen
  `source="live"` verifiziert; dabei echten tz-Bug in `legs/cls_practical/
  signal_source.py` gefunden und gefixt (identischer Bugtyp wie der am
  2026-09-01 fuer gold_asb behobene). Details: CHANGELOG.
- 2026-09-06 — Neuer Scheduled Task `Dashboard-Telegram-Digest`: schickt
  jeden Morgen 8:00 die offenen Punkte aus diesem Dashboard per Telegram
  (Nutzerwunsch). Details: CHANGELOG.
- 2026-09-04 — Second Brain: neuer Skill `handoff` (+ Inbox
  `knowledge/_handoff/`) für Session-Übergaben am Kontextfenster-Limit,
  aus dem "Everlast AI"-Clip übernommen (3 der 4 vorgeschlagenen Ideen
  bewusst verworfen/zurückgestellt, siehe `resources/second-brain-methodik.md`).
- 2026-09-04 — Data-Lake-Pilot gebaut + live geschaltet: Funded-Portfolio-
  Bridges 6 Beine lesen jetzt aus einem lokalen Parquet-Lake
  (`data_lake/`) statt live von Dukascopy/TradingView/yfinance. Neue
  Scheduled Tasks `DataLake-Ingest-Fast`/`-Slow`. Vollstaendig end-to-end
  verifiziert (Seed-Laeufe, `run_shared_scans()` direkt gegen die echte
  Config, kuenstlicher Stale-Test) — siehe CHANGELOG fuer Details. EK-
  Portfolio-Bridge/FK Instant Funding folgen erst nach Bewaehrung.
- 2026-09-04 — CTNL-eigener Kill-Switch (Stand-alone Cont+Rev-Drawdown
  gegen die Phase-6-P5-Schwelle) in EK-Portfolio/Challenge-Portfolio/FK
  Instant Funding nachgeruestet, nachdem er bei der Portfolio-Konsolidierung
  nicht automatisch mit uebernommen wurde — siehe CHANGELOG.
- 2026-09-03 (spät) — Bridge Error Monitor: dritte Lücke im heutigen OHLC-
  Validierungsfix geschlossen (`fetch_2y_yield_daily()` in
  `cls_practical/data.py`, siehe CHANGELOG). Zwei neue Echtgeld-Befunde auf
  EK-Portfolio-Bridge zur Bestätigung im Dashboard vermerkt: NASDAQ-Ticket
  262117522 scheitert wiederholt am Session-Ende-Exit, US30-Order erneut
  mit "Invalid stops" (derselbe, am 2026-09-02 als behoben dokumentierte
  Fehler) gescheitert.
- 2026-09-03 — Bridge Error Monitor: den am 2026-09-02 dokumentierten, aber
  nie tatsächlich umgesetzten "OHLC vor dem Cachen validieren"-Fix jetzt
  wirklich in `combined_strategy/data.py` + `cls_practical/data.py`
  ergänzt, nachdem derselbe `str`/`float`-Fehler heute erneut in drei
  Beinen gleichzeitig auftrat. Neue vage Fehlerzeile auf EK-Portfolio-
  Bridge zur Bestätigung im Dashboard vermerkt.
- 2026-09-03 — Funded-Portfolio-Bridge: redundante Scans behoben (6 Scans
  1x/Lauf statt 1x/Konto) + tvDatafeed-Pro-Login entfernt (TradingView-
  Captcha-Wall, seit 2026-09-01 taeglich hunderte Signin-Fehler). MT5 als
  Dukascopy-Ersatz geprueft und verworfen (Instrumenten-Abdeckung zu duenn).
- 2026-09-02 — Second Brain: 5 offene Clippings verarbeitet (CODE-Prozess) —
  3 Claude-Workflow-Videos als neue Einträge in
  `resources/second-brain-methodik.md`, 1 Trading-Video (Order Flow, nicht
  quant-übertragbar) als neue `resources/order-flow-trading.md`, 1 bestätigtes
  Duplikat. 4 Workflow-Verbesserungsideen daraus in DASHBOARD "Braucht deine
  Bestätigung" vermerkt. `Clippings/`-Ordner danach geleert.
- 2026-09-01 — Second Brain: Scope von `strategie-backlog-inventar.md`
  eingegrenzt (nur aktuell relevante Strategien + Filter mit echtem
  Mehrwert, kein Vollsweep über alle Ordner mehr), 5 echte Lücken bei
  laufenden/pausierten Bots identifiziert (`asian_range_breakout`,
  `cls_practical`, `btc_ema_cross`, `ek_portfolio`, OU-Modell). Dabei
  Task Scheduler + alle Live-Bridge-`DRY_RUN`-Flags gegen die Statustabelle
  geprüft — keine Abweichung gefunden.
- 2026-09-01 — EK-Portfolio: Echtgeld-Bugfix (Gold-ASB-Scan crashte seit
  11:30 bei jedem Lauf, tz-Vergleichsfehler) + Dukascopy-Retry in 3 Beinen
  nachgezogen. Verifiziert per fehlerfreiem 13-Bein-Lauf um 12:15.
- 2026-09-01 — Funded-Portfolio-Bridge: Scheduled Task angelegt (alle 15
  Min Mo–Fr) + 2 Bugs beim ersten automatischen Lauf gefunden/behoben
  (endlos wiederholte "verpasst"-Meldung, falscher `entry_price` im State).
- 2026-09-01 — Funded-Portfolio-Bridge (TTP/IQ Markets) auf `DRY_RUN=False`
  gestellt, erste 2 echten Orders platziert; OU-Modell/CTNL-Edge-MT5-Bridge
  sauber von den Zielkonten abgekoppelt.
- 2026-09-01 — 5 verwaiste MT5-Terminals geschlossen, nur die 2 aktiven blieben offen.
- 2026-09-01 — Challenge Portfolio: CTNL-Reversal-Kaskade gekappt + OU-Modell-Import-Fix (`69f9ca6`).
- 2026-09-01 — EK-Portfolio: CTNL-Reversal-Kaskade auf reales 3er-Limit gekappt (`c195924`).
- 2026-08-31 — FK Instant Funding: `scan_errors_today` auf lokalen Kalendertag umgestellt (`adc7d7c`).
- 2026-08-29 — Wochenend-/Spread-Stunden-Sperre auf EK-Portfolio + CTNL-Edge-FK-Paper ausgeweitet (`5fcf1da`).
- 2026-08-29 — FK Instant Funding: Wochenend-/Spread-Stunden-Sperre + UTC/Lokalzeit-Bug behoben (`79df9f3`).
- 2026-08-29 — FK Instant Funding: eigenes Telegram-Layout + gebündelte Nachrichten (`8f9a11a`).
- 2026-08-29 — FK Instant Funding: Gewichts-Optimierung + `CAPITAL_WEIGHT`-Umbau (`59ba4df`, `11f8979`).
